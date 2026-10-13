"""Streamlit interface for the document management system."""

from datetime import datetime
import math

import streamlit as st

from algorithms import dfs_search, merge_sort
from data_structures import DocumentHashTable, FolderTree, VersionStack
from file_manager import (
    DEFAULT_DOCUMENTS_FILE,
    initialize_document_hash_table,
    initialize_folder_tree,
    load_documents,
    save_documents,
)


PAGE_SIZE = 20

st.set_page_config(
    page_title="Document Library",
    page_icon="D",
    layout="centered",
    initial_sidebar_state="collapsed",
)

def count_folders(folder_tree):
    """Count folders below the root without counting the root itself."""

    def count_children(folder):
        count = 0
        child = folder.first_child
        while child is not None:
            count += 1 + count_children(child)
            child = child.next_sibling
        return count

    return count_children(folder_tree.root)


def count_file_types(documents):
    """Count distinct file types without relying on a built-in set."""
    unique_count = 0
    index = 0
    while index < len(documents):
        earlier_index = 0
        already_counted = False
        while earlier_index < index:
            if (
                documents[earlier_index]["file_type"]
                == documents[index]["file_type"]
            ):
                already_counted = True
                break
            earlier_index += 1
        if not already_counted:
            unique_count += 1
        index += 1
    return unique_count


def find_documents(documents, document_table, query, archived_table=None):
    """Find records by ID, title, file type, or folder path."""
    search_text = query.strip()
    if not search_text:
        return documents

    # Use the custom hash table for a direct ID lookup before a text scan.
    exact_match = document_table.get(search_text)
    if exact_match is None and archived_table is not None:
        exact_match = archived_table.get(search_text)
    if exact_match is not None:
        return [exact_match]

    folded_query = search_text.casefold()
    matches = []
    for document in documents:
        searchable_text = " ".join(
            (
                document["document_id"],
                document["title"],
                document["file_type"],
                document["folder_path"],
            )
        ).casefold()
        if folded_query in searchable_text:
            matches.append(document)
    return matches


def sort_documents(documents, sort_field):
    """Sort records using merge_sort, with original order breaking ties."""
    sortable_records = []
    index = 0
    for document in documents:
        if sort_field == "Size":
            raw_size = document.get("size_bytes", document.get("size"))
            try:
                numeric_size = float(raw_size)
            except (TypeError, ValueError):
                numeric_size = None
            if (
                numeric_size is None
                or not math.isfinite(numeric_size)
                or numeric_size < 0
            ):
                sort_value = (1, 0)
            else:
                sort_value = (0, numeric_size)
        elif sort_field == "Date Modified":
            date_value = document.get(
                "date_modified", document.get("modified_at")
            )
            if not isinstance(date_value, str) or not date_value.strip():
                sort_value = (1, ())
            else:
                # Complement each character so ascending merge sort returns
                # dates newest-first for ISO-formatted timestamps.
                descending_date = tuple(
                    -ord(character) for character in date_value
                ) + (0,)
                sort_value = (0, descending_date)
        else:
            sort_value = (0, document["title"].casefold())

        # The index keeps equal values in their original order.
        sortable_records.append((sort_value, index, document))
        index += 1

    ordered_records = merge_sort(sortable_records)
    sorted_documents = []
    for sortable_record in ordered_records:
        sorted_documents.append(sortable_record[2])
    return sorted_documents


def format_file_size(document):
    """Format known byte counts; do not invent a size when metadata is absent."""
    raw_size = document.get("size_bytes", document.get("size"))
    try:
        size = float(raw_size)
    except (TypeError, ValueError):
        return "Size unavailable"
    if not math.isfinite(size) or size < 0:
        return "Size unavailable"
    if size < 1024:
        return "{0} B".format(int(size))
    if size < 1024 * 1024:
        return "{0:.1f} KB".format(size / 1024)
    if size < 1024 * 1024 * 1024:
        return "{0:.1f} MB".format(size / (1024 * 1024))
    return "{0:.1f} GB".format(size / (1024 * 1024 * 1024))


def document_modified_date(document):
    """Return available modification metadata or an honest empty-state label."""
    date_value = document.get("date_modified", document.get("modified_at"))
    if isinstance(date_value, str) and date_value.strip():
        return date_value.replace("T", " ")
    return "Date not recorded"


def current_timestamp():
    """Return a local, timezone-aware ISO timestamp for new edits."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def render_version_history(document):
    """Display stored history through the custom LIFO VersionStack."""
    version_stack = VersionStack()
    stored_history = document.get("version_history")
    has_saved_history = isinstance(stored_history, list) and bool(stored_history)
    if has_saved_history:
        for version_record in stored_history:
            version_stack.push(version_record)

    # Push the current version last so it appears at the top of the LIFO view.
    current_snapshot = {}
    for field in document:
        if field != "version_history":
            current_snapshot[field] = document[field]
    version_stack.push(current_snapshot)

    newest_version = version_stack.peek()
    history_items = []
    while not version_stack.is_empty():
        history_items.append(version_stack.pop())

    if not has_saved_history:
        st.caption("No earlier saved versions yet. Editing creates the first snapshot.")

    history_index = 0
    while history_index < len(history_items):
        history_item = history_items[history_index]
        if isinstance(history_item, dict):
            version_number = history_item.get("version", "unknown")
            note = history_item.get("note")
            saved_at = history_item.get("saved_at")
        else:
            version_number = history_item
            note = None
            saved_at = None

        is_current = history_index == 0 and history_item == newest_version
        title = "Version {0}".format(version_number)
        if is_current:
            title += " · current"
        st.markdown("**{0}**".format(title))
        if isinstance(history_item, dict):
            snapshot_title = history_item.get("title")
            snapshot_folder = history_item.get("folder_path")
            if snapshot_title:
                st.caption("Title: {0}".format(snapshot_title))
            if snapshot_folder:
                st.caption("Folder: {0}".format(snapshot_folder))
        if note:
            st.caption(str(note))
        if saved_at:
            st.caption("Saved {0}".format(saved_at))
        history_index += 1


def next_document_id(document_table):
    """Return the first unused ID in the DOC-0001, DOC-0002, ... sequence."""
    number = 1
    while document_table.contains("DOC-{0:04d}".format(number)):
        number += 1
    return "DOC-{0:04d}".format(number)


def make_versioned_document(
    old_document, title, folder_path, file_type, description
):
    """Snapshot the old document using VersionStack, then apply edited fields."""
    version_stack = VersionStack()

    # Keep prior snapshots in chronological order before pushing the version
    # that is about to be replaced.
    previous_history = old_document.get("version_history", [])
    for snapshot in previous_history:
        version_stack.push(snapshot)

    old_snapshot = {}
    for field in old_document:
        if field != "version_history":
            old_snapshot[field] = old_document[field]
    version_stack.push(old_snapshot)

    # Pop from newest to oldest, then restore chronological JSON storage order.
    newest_first = []
    while not version_stack.is_empty():
        newest_first.append(version_stack.pop())

    chronological_history = [None] * len(newest_first)
    history_index = 0
    while history_index < len(newest_first):
        chronological_history[len(newest_first) - history_index - 1] = (
            newest_first[history_index]
        )
        history_index += 1

    updated_document = {}
    for field in old_document:
        if field != "version_history":
            updated_document[field] = old_document[field]

    updated_document["title"] = title.strip()
    updated_document["folder_path"] = folder_path.strip().strip("/")
    updated_document["file_type"] = file_type.strip()
    updated_document["description"] = description.strip()
    updated_document["version"] = old_document["version"] + 1
    updated_document["is_archived"] = old_document.get("is_archived", False)
    updated_document["date_modified"] = current_timestamp()
    updated_document["version_history"] = chronological_history
    return updated_document


def documents_without_id(documents, document_id):
    """Return a new record list that excludes one document ID."""
    remaining_documents = []
    for document in documents:
        if document["document_id"] != document_id:
            remaining_documents.append(document)
    return remaining_documents


def replace_document_record(documents, replacement):
    """Return a record sequence with one matching document ID replaced."""
    updated_documents = []
    found_document = False
    for document in documents:
        if document["document_id"] == replacement["document_id"]:
            updated_documents.append(replacement)
            found_document = True
        else:
            updated_documents.append(document)
    if not found_document:
        raise ValueError(
            "Document not found: " + replacement["document_id"]
        )
    return updated_documents


def filter_documents(
    documents, document_table, archived_table, query, archived
):
    """Search records, then select either active or archived documents."""
    matching_documents = find_documents(
        documents, document_table, query, archived_table
    )
    selected_documents = []
    for document in matching_documents:
        if document.get("is_archived", False) is archived:
            selected_documents.append(document)
    return selected_documents


def save_archive_status(
    documents,
    document_table,
    archived_table,
    folder_tree,
    document_id,
    is_archived,
):
    """Persist an archive/restore change and move it between active indexes."""
    document = document_table.get(document_id)
    if document is None:
        document = archived_table.get(document_id)
    if document is None:
        raise ValueError("Document not found: " + document_id)

    updated_document = {}
    for field in document:
        updated_document[field] = document[field]
    updated_document["is_archived"] = is_archived

    updated_documents = replace_document_record(documents, updated_document)
    save_documents(updated_documents, DEFAULT_DOCUMENTS_FILE)
    if is_archived:
        # Archived records stay in JSON and the archive hash table, but leave
        # the active hash table and folder tree.
        document_table.remove(document_id)
        folder_tree.remove_document(document["folder_path"], document_id)
        archived_table.put(document_id, updated_document)
    else:
        archived_table.remove(document_id)
        document_table.put(document_id, updated_document)
        folder_tree.add_document(document["folder_path"], document_id)
    return updated_documents


def permanently_delete_document(
    documents, document_table, archived_table, folder_tree, document_id
):
    """Remove one document permanently from JSON, hash table, and folder tree."""
    document = document_table.get(document_id)
    if document is None:
        document = archived_table.get(document_id)
    if document is None:
        raise ValueError("Document not found: " + document_id)
    is_archived = document.get("is_archived", False)
    if (
        not is_archived
        and not folder_tree.contains_document(
            document["folder_path"], document_id
        )
    ):
        raise ValueError("Document is missing from its folder tree.")

    remaining_documents = documents_without_id(documents, document_id)
    if len(remaining_documents) == len(documents):
        raise ValueError("Document is missing from documents.json data.")

    # Save first. If file writing fails, keep both in-memory structures intact.
    save_documents(remaining_documents, DEFAULT_DOCUMENTS_FILE)
    removed_active = document_table.remove(document_id)
    removed_archived = archived_table.remove(document_id)
    removed_from_tree = folder_tree.remove_document(
        document["folder_path"], document_id
    )
    if (
        (removed_active is None and removed_archived is None)
        or (not is_archived and not removed_from_tree)
    ):
        raise RuntimeError(
            "The JSON file was updated, but the in-memory structures "
            "could not be synchronized."
        )
    return remaining_documents


def file_type_icon(file_type):
    """Choose a small native emoji icon from the document's file extension."""
    extension = file_type.strip().casefold().lstrip(".")
    if extension == "pdf":
        return "📄"
    if extension in ("docx", "doc"):
        return "📝"
    if extension == "txt":
        return "📃"
    if extension in ("jpg", "jpeg", "png", "webp"):
        return "🖼️"
    return "📄"


def folder_paths_depth_first(folder_tree):
    """Return every folder path in a preorder walk of the custom FolderTree."""
    paths = []

    def visit(folder, current_path):
        child = folder.first_child
        while child is not None:
            if current_path:
                child_path = current_path + "/" + child.name
            else:
                child_path = child.name
            paths.append(child_path)
            visit(child, child_path)
            child = child.next_sibling

    visit(folder_tree.root, "")
    return paths


def find_folder_node_by_path(folder_tree, folder_path):
    """Resolve a selected path through FolderTree and the custom DFS search."""
    current = folder_tree.root
    path_parts = folder_path.strip("/").split("/")
    part_index = 0
    if path_parts and path_parts[0] == folder_tree.root.name:
        part_index = 1

    while part_index < len(path_parts):
        part = path_parts[part_index]
        child = current.find_child(part)
        if child is None or dfs_search(child, part) is None:
            return None
        current = child
        part_index += 1
    return current


def document_ids_depth_first(folder_node):
    """Collect direct and nested document IDs by walking folders depth-first."""
    document_ids = []

    def visit(folder):
        document = folder.first_document
        while document is not None:
            document_ids.append(document.document_id)
            document = document.next_document

        child = folder.first_child
        while child is not None:
            visit(child)
            child = child.next_sibling

    if folder_node is not None:
        visit(folder_node)
    return document_ids


try:
    documents = load_documents(DEFAULT_DOCUMENTS_FILE)
    document_table: DocumentHashTable = initialize_document_hash_table(
        documents, is_archived=False
    )
    archived_table: DocumentHashTable = initialize_document_hash_table(
        documents, is_archived=True
    )
    folder_tree: FolderTree = initialize_folder_tree(
        documents, include_archived=False
    )
except (OSError, TypeError, ValueError) as error:
    st.error("The document library could not be loaded.")
    st.caption(str(error))
    st.stop()

if "editing_document_id" not in st.session_state:
    st.session_state["editing_document_id"] = None
if "pending_delete_document_id" not in st.session_state:
    st.session_state["pending_delete_document_id"] = None
if "editor_nonce" not in st.session_state:
    st.session_state["editor_nonce"] = 0
if "active_page" not in st.session_state:
    st.session_state["active_page"] = 0
if "archived_page" not in st.session_state:
    st.session_state["archived_page"] = 0
if "folder_page" not in st.session_state:
    st.session_state["folder_page"] = 0
if "show_add_form" not in st.session_state:
    st.session_state["show_add_form"] = False
if "history_document_id" not in st.session_state:
    st.session_state["history_document_id"] = None

notice = st.session_state.pop("library_notice", None)
if notice:
    st.success(notice)

with st.container(horizontal=True, wrap=False, gap="small"):
    st.metric("Total Documents", len(documents))
    st.metric("Total Folders", count_folders(folder_tree))
    st.metric("File Types", count_file_types(documents))

st.header("Document Library")

sort_options = ("Name", "Size", "Date Modified")
if st.session_state.get("sort_by") not in sort_options:
    st.session_state["sort_by"] = "Date Modified"

query = st.sidebar.text_input(
    "Search documents",
    placeholder="Search documents...",
)
sort_by = st.sidebar.selectbox(
    "Sort by",
    options=sort_options,
    key="sort_by",
)
filter_signature = (query, sort_by)
if st.session_state.get("filter_signature") != filter_signature:
    st.session_state["filter_signature"] = filter_signature
    st.session_state["active_page"] = 0
    st.session_state["archived_page"] = 0
    st.session_state["folder_page"] = 0

if st.sidebar.button(
    "+ Add Document",
    key="open_add_form",
    type="primary",
    use_container_width=True,
):
    st.session_state["show_add_form"] = True
    st.rerun()

if st.session_state["show_add_form"]:
    with st.sidebar.form("add_document_form", clear_on_submit=True):
        new_title = st.text_input("Document name", key="new_document_title")
        new_folder = st.text_input(
            "Folder path",
            value="DSA/Assignments",
            key="new_document_folder",
        )
        new_file_type = st.text_input(
            "File type", value="pdf", key="new_document_type"
        )
        new_description = st.text_area(
            "Description", key="new_document_description"
        )
        add_submitted = st.form_submit_button(
            "Save Document",
            type="primary",
            use_container_width=True,
        )
    if st.sidebar.button("Cancel", key="cancel_add_form"):
        st.session_state["show_add_form"] = False
        st.rerun()

    if add_submitted:
        if (
            not new_title.strip()
            or not new_folder.strip()
            or not new_file_type.strip()
        ):
            st.sidebar.error("Name, folder path, and file type are required.")
        else:
            new_document_id = next_document_id(document_table)
            new_document = {
                "document_id": new_document_id,
                "title": new_title.strip(),
                "folder_path": new_folder.strip().strip("/"),
                "file_type": new_file_type.strip(),
                "version": 1,
                "version_history": [],
                "description": new_description.strip(),
                "is_archived": False,
                "date_modified": current_timestamp(),
            }
            updated_documents = []
            for existing_document in documents:
                updated_documents.append(existing_document)
            updated_documents.append(new_document)
            try:
                save_documents(updated_documents, DEFAULT_DOCUMENTS_FILE)
            except (OSError, TypeError, ValueError) as error:
                st.sidebar.error(
                    "The document could not be saved: {0}".format(error)
                )
            else:
                document_table.put(new_document_id, new_document)
                folder_tree.add_document(
                    new_document["folder_path"], new_document_id
                )
                st.session_state["library_notice"] = (
                    "Added {0}.".format(new_document_id)
                )
                st.session_state["show_add_form"] = False
                st.session_state["active_page"] = 0
                st.rerun()


def render_document_actions(document, archived, row_key):
    """Render the overflow-menu actions for one document row."""
    document_id = document["document_id"]

    if st.button(
        "Edit",
        key="edit_" + row_key,
        use_container_width=True,
    ):
        st.session_state["editing_document_id"] = document_id
        st.session_state["pending_delete_document_id"] = None
        st.session_state["editor_nonce"] += 1
        st.rerun()

    if archived:
        if st.button(
            "Restore",
            key="restore_" + row_key,
            use_container_width=True,
        ):
            try:
                save_archive_status(
                    documents,
                    document_table,
                    archived_table,
                    folder_tree,
                    document_id,
                    False,
                )
            except (OSError, TypeError, ValueError) as error:
                st.error(
                    "The document could not be restored: {0}".format(error)
                )
            else:
                st.session_state["library_notice"] = (
                    "Restored {0}.".format(document_id)
                )
                st.session_state["archived_page"] = 0
                st.session_state["folder_page"] = 0
                st.rerun()
    elif st.button(
        "Archive",
        key="archive_" + row_key,
        use_container_width=True,
    ):
        try:
            save_archive_status(
                documents,
                document_table,
                archived_table,
                folder_tree,
                document_id,
                True,
            )
        except (OSError, TypeError, ValueError) as error:
            st.error("The document could not be archived: {0}".format(error))
        else:
            st.session_state["library_notice"] = (
                "Archived {0}.".format(document_id)
            )
            st.session_state["active_page"] = 0
            st.session_state["folder_page"] = 0
            st.rerun()

    if st.button(
        "Version History",
        key="history_" + row_key,
        use_container_width=True,
    ):
        if st.session_state["history_document_id"] == document_id:
            st.session_state["history_document_id"] = None
        else:
            st.session_state["history_document_id"] = document_id
        st.rerun()

    st.divider()
    if st.button(
        "Delete",
        key="delete_" + row_key,
        use_container_width=True,
    ):
        st.session_state["pending_delete_document_id"] = document_id
        st.session_state["editing_document_id"] = None
        st.rerun()


def render_document_tab(records, archived, page_key, empty_message=None):
    """Render one list in custom merge-sort order."""
    ordered_documents = sort_documents(records, sort_by)
    page_count = max(1, (len(ordered_documents) + PAGE_SIZE - 1) // PAGE_SIZE)
    page_number = min(st.session_state[page_key], page_count - 1)
    st.session_state[page_key] = page_number

    if not ordered_documents:
        if empty_message:
            st.info(empty_message)
        elif archived:
            st.info("No archived documents match this search.")
        else:
            st.info("No active documents match this search.")
        return

    st.caption(
        "{0} {1}".format(
            len(ordered_documents),
            "document" if len(ordered_documents) == 1 else "documents",
        )
    )
    start_index = page_number * PAGE_SIZE
    end_index = min(start_index + PAGE_SIZE, len(ordered_documents))

    for document_index in range(start_index, end_index):
        document = ordered_documents[document_index]
        document_id = document["document_id"]
        row_key = page_key + "_" + document_id
        with st.container(border=True):
            with st.container(
                horizontal=True,
                wrap=False,
                vertical_alignment="center",
                gap="small",
            ):
                with st.container(width=48):
                    st.markdown(file_type_icon(document["file_type"]))
                with st.container(width="stretch"):
                    st.markdown("**{0}**".format(document["title"]))
                    st.caption(
                        "{0} • {1} • {2}".format(
                            document["folder_path"],
                            document_modified_date(document),
                            format_file_size(document),
                        )
                    )

                with st.container(width=48):
                    with st.popover("⋮", key="actions_" + row_key):
                        render_document_actions(document, archived, row_key)

            if st.session_state["editing_document_id"] == document_id:
                editor_nonce = st.session_state["editor_nonce"]
                with st.form(
                    "edit_form_{0}_{1}_{2}".format(
                        page_key, document_id, editor_nonce
                    )
                ):
                    edited_title = st.text_input(
                        "Name",
                        value=document["title"],
                        key="edit_title_{0}_{1}_{2}".format(
                            page_key, document_id, editor_nonce
                        ),
                    )
                    edited_folder = st.text_input(
                        "Folder path",
                        value=document["folder_path"],
                        key="edit_folder_{0}_{1}_{2}".format(
                            page_key, document_id, editor_nonce
                        ),
                    )
                    edited_file_type = st.text_input(
                        "File type",
                        value=document["file_type"],
                        key="edit_type_{0}_{1}_{2}".format(
                            page_key, document_id, editor_nonce
                        ),
                    )
                    edited_description = st.text_area(
                        "Description",
                        value=document.get("description", ""),
                        key="edit_description_{0}_{1}_{2}".format(
                            page_key, document_id, editor_nonce
                        ),
                    )
                    save_edit = st.form_submit_button(
                        "Save Changes",
                        type="primary",
                        use_container_width=True,
                    )
                    cancel_edit = st.form_submit_button(
                        "Cancel",
                        use_container_width=True,
                    )

                if cancel_edit:
                    st.session_state["editing_document_id"] = None
                    st.rerun()
                elif save_edit:
                    cleaned_folder = edited_folder.strip().strip("/")
                    if (
                        not edited_title.strip()
                        or not cleaned_folder
                        or not edited_file_type.strip()
                    ):
                        st.error(
                            "Name, folder path, and file type are required."
                        )
                    elif (
                        not archived
                        and not folder_tree.contains_document(
                            document["folder_path"], document_id
                        )
                    ):
                        st.error("This document is missing from its folder.")
                    else:
                        updated_document = make_versioned_document(
                            document,
                            edited_title,
                            cleaned_folder,
                            edited_file_type,
                            edited_description,
                        )
                        updated_documents = replace_document_record(
                            documents, updated_document
                        )
                        try:
                            save_documents(
                                updated_documents, DEFAULT_DOCUMENTS_FILE
                            )
                        except (OSError, TypeError, ValueError) as error:
                            st.error(
                                "The document could not be updated: {0}"
                                .format(error)
                            )
                        else:
                            if archived:
                                archived_table.put(document_id, updated_document)
                            else:
                                if (
                                    document["folder_path"]
                                    != updated_document["folder_path"]
                                ):
                                    folder_tree.remove_document(
                                        document["folder_path"], document_id
                                    )
                                    folder_tree.add_document(
                                        updated_document["folder_path"],
                                        document_id,
                                    )
                                document_table.put(
                                    document_id, updated_document
                                )
                            st.session_state["library_notice"] = (
                                "Updated {0} to version {1}.".format(
                                    document_id, updated_document["version"]
                                )
                            )
                            st.session_state["editing_document_id"] = None
                            st.session_state["active_page"] = 0
                            st.session_state["archived_page"] = 0
                            st.session_state["folder_page"] = 0
                            st.rerun()

            if st.session_state["history_document_id"] == document_id:
                st.markdown("**Version History**")
                render_version_history(document)
                if st.button(
                    "Close history",
                    key="close_history_" + row_key,
                    use_container_width=True,
                ):
                    st.session_state["history_document_id"] = None
                    st.rerun()

    if page_count > 1:
        previous_column, page_column, next_column = st.columns([1, 1, 1])
        if previous_column.button(
            "Previous",
            key="previous_" + page_key,
            disabled=page_number == 0,
            use_container_width=True,
        ):
            st.session_state[page_key] = page_number - 1
            st.rerun()
        page_column.caption("Page {0} of {1}".format(page_number + 1, page_count))
        if next_column.button(
            "Next",
            key="next_" + page_key,
            disabled=page_number >= page_count - 1,
            use_container_width=True,
        ):
            st.session_state[page_key] = page_number + 1
            st.rerun()


search_results = find_documents(
    documents, document_table, query, archived_table
)
active_records = []
archived_records = []
for record in search_results:
    if record.get("is_archived", False):
        archived_records.append(record)
    else:
        active_records.append(record)

recent_tab, folders_tab, archived_tab_view = st.tabs(
    ["🕒 Recents", "📁 Browse Folders", "🗄️ Archived"]
)
with recent_tab:
    render_document_tab(active_records, False, "active_page")

with folders_tab:
    available_folder_paths = folder_paths_depth_first(folder_tree)
    if not available_folder_paths:
        st.info("There are no folders to browse yet.")
    else:
        selected_folder_path = st.selectbox(
            "Choose a folder",
            options=available_folder_paths,
            key="selected_folder_path",
        )
        if st.session_state.get("previous_folder_path") != selected_folder_path:
            st.session_state["previous_folder_path"] = selected_folder_path
            st.session_state["folder_page"] = 0

        selected_folder = find_folder_node_by_path(
            folder_tree, selected_folder_path
        )
        folder_document_ids = document_ids_depth_first(selected_folder)
        folder_records = []
        for record in active_records:
            is_in_folder = False
            for folder_document_id in folder_document_ids:
                if folder_document_id == record["document_id"]:
                    is_in_folder = True
                    break
            if is_in_folder:
                folder_records.append(record)
        render_document_tab(
            folder_records,
            False,
            "folder_page",
            empty_message="No active documents in this folder match the search.",
        )

with archived_tab_view:
    render_document_tab(archived_records, True, "archived_page")


@st.dialog("Permanently delete this document?")
def confirm_permanent_delete():
    """Confirm the permanent removal requested from a document's Actions menu."""
    document_id = st.session_state.get("pending_delete_document_id")
    document = None
    if document_id:
        document = document_table.get(document_id)
        if document is None:
            document = archived_table.get(document_id)
    if document is None:
        st.error("This document is no longer available.")
    else:
        st.write(
            "This will permanently remove **{0}** from the JSON file, "
            "hash table, and folder tree.".format(document["title"])
        )

    confirm_column, cancel_column = st.columns(2)
    if confirm_column.button(
        "Delete permanently",
        key="confirm_permanent_delete",
        type="primary",
        use_container_width=True,
        disabled=document is None,
    ):
        try:
            permanently_delete_document(
                documents,
                document_table,
                archived_table,
                folder_tree,
                document_id,
            )
        except (OSError, TypeError, ValueError, RuntimeError) as error:
            st.error("The document could not be deleted: {0}".format(error))
        else:
            st.session_state["library_notice"] = (
                "Permanently deleted {0}.".format(document_id)
            )
            st.session_state["pending_delete_document_id"] = None
            st.session_state["editing_document_id"] = None
            st.session_state["active_page"] = 0
            st.session_state["archived_page"] = 0
            st.session_state["folder_page"] = 0
            st.rerun()

    if cancel_column.button(
        "Cancel",
        key="cancel_permanent_delete",
        use_container_width=True,
    ):
        st.session_state["pending_delete_document_id"] = None
        st.rerun()


if st.session_state.get("pending_delete_document_id"):
    confirm_permanent_delete()
