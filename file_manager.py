"""Load, save, and organize document records for the management system.

The first call to load_documents() creates documents.json with 500 sample
records if the file does not exist. Existing files are loaded as-is.
"""

import json
from pathlib import Path

from data_structures import DocumentHashTable, FolderTree


DEFAULT_DOCUMENTS_FILE = Path(__file__).resolve().parent / "documents.json"
DUMMY_RECORD_COUNT = 500


def generate_dummy_documents(count=DUMMY_RECORD_COUNT):
    """Create sample document records for testing the management system."""
    if not isinstance(count, int) or count < 0:
        raise ValueError("count must be a non-negative integer")

    folder_paths = (
        "DSA/Assignments",
        "DSA/Projects",
        "Reference/Reading",
    )
    file_types = ("pdf", "docx", "txt")
    documents = []

    number = 1
    while number <= count:
        folder_index = (number - 1) % len(folder_paths)
        type_index = (number - 1) % len(file_types)
        documents.append(
            {
                "document_id": "DOC-{0:04d}".format(number),
                "title": "Sample Document {0:04d}".format(number),
                "folder_path": folder_paths[folder_index],
                "file_type": file_types[type_index],
                "version": 1,
                "description": "Dummy document record {0:04d}.".format(number),
                "is_archived": False,
            }
        )
        number += 1

    return documents


def _validate_documents(documents):
    """Check that records have the fields needed by the table and tree."""
    if not isinstance(documents, list):
        raise ValueError("documents.json must contain a JSON array")

    required_fields = (
        "document_id",
        "title",
        "folder_path",
        "file_type",
        "version",
    )
    index = 0
    while index < len(documents):
        document = documents[index]
        if not isinstance(document, dict):
            raise ValueError("document record {0} must be an object".format(index))

        for field in required_fields:
            if field not in document:
                raise ValueError(
                    "document record {0} is missing '{1}'".format(index, field)
                )

        for field in ("document_id", "title", "folder_path", "file_type"):
            if not isinstance(document[field], str) or not document[field]:
                raise ValueError(
                    "document record {0} has an invalid '{1}'".format(index, field)
                )

        if not isinstance(document["version"], int) or document["version"] < 1:
            raise ValueError(
                "document record {0} must have a positive integer version".format(
                    index
                )
            )

        if (
            "is_archived" in document
            and not isinstance(document["is_archived"], bool)
        ):
            raise ValueError(
                "document record {0} is_archived must be a boolean".format(index)
            )

        if "size_bytes" in document and document["size_bytes"] is not None:
            size_bytes = document["size_bytes"]
            if (
                isinstance(size_bytes, bool)
                or not isinstance(size_bytes, (int, float))
                or size_bytes < 0
            ):
                raise ValueError(
                    "document record {0} size_bytes must be a non-negative number"
                    .format(index)
                )

        if (
            "date_modified" in document
            and document["date_modified"] is not None
            and not isinstance(document["date_modified"], str)
        ):
            raise ValueError(
                "document record {0} date_modified must be text".format(index)
            )

        if "version_history" in document:
            history = document["version_history"]
            if not isinstance(history, list):
                raise ValueError(
                    "document record {0} version_history must be an array".format(
                        index
                    )
                )
            for snapshot in history:
                if not isinstance(snapshot, dict):
                    raise ValueError(
                        "document record {0} has an invalid version snapshot".format(
                            index
                        )
                    )
                if (
                    not isinstance(snapshot.get("version"), int)
                    or snapshot["version"] < 1
                ):
                    raise ValueError(
                        "document record {0} has a snapshot with an invalid version"
                        .format(index)
                    )

        # Duplicate IDs would overwrite one another in DocumentHashTable.
        earlier_index = 0
        while earlier_index < index:
            if (
                documents[earlier_index]["document_id"]
                == document["document_id"]
            ):
                raise ValueError(
                    "duplicate document_id: " + document["document_id"]
                )
            earlier_index += 1

        index += 1


def save_documents(documents, file_path=DEFAULT_DOCUMENTS_FILE):
    """Validate and save document records as formatted JSON.

    Calling this function replaces the contents of file_path.
    """
    _validate_documents(documents)
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as output_file:
        json.dump(documents, output_file, indent=2, ensure_ascii=False)
        output_file.write("\n")


def load_documents(file_path=DEFAULT_DOCUMENTS_FILE):
    """Load records from JSON, creating 500 sample records if the file is absent.

    Invalid JSON or invalid document records raise an error rather than being
    silently replaced with sample data.
    """
    path = Path(file_path)
    if not path.exists():
        documents = generate_dummy_documents()
        save_documents(documents, path)
        return documents

    with path.open("r", encoding="utf-8") as input_file:
        documents = json.load(input_file)

    _validate_documents(documents)
    added_archive_defaults = False
    for document in documents:
        if "is_archived" not in document:
            document["is_archived"] = False
            added_archive_defaults = True
    if added_archive_defaults:
        save_documents(documents, path)
    return documents


def initialize_document_hash_table(
    documents=None,
    file_path=DEFAULT_DOCUMENTS_FILE,
    is_archived=None,
):
    """Build a custom hash table, optionally selecting an archive status.

    With the default ``is_archived=None``, all records are indexed. Pass
    ``False`` for the active index or ``True`` for the archived index.
    """
    if documents is None:
        documents = load_documents(file_path)
    _validate_documents(documents)

    # Allocate enough buckets to keep the average collision chain short.
    matching_count = 0
    for document in documents:
        if (
            is_archived is None
            or document.get("is_archived", False) is is_archived
        ):
            matching_count += 1
    bucket_count = max(16, matching_count * 2)
    document_table = DocumentHashTable(bucket_count=bucket_count)
    for document in documents:
        if (
            is_archived is None
            or document.get("is_archived", False) is is_archived
        ):
            document_table.put(document["document_id"], document)
    return document_table


def initialize_folder_tree(
    documents=None,
    file_path=DEFAULT_DOCUMENTS_FILE,
    root_name="School",
    include_archived=True,
):
    """Build the folder tree and index active documents by default when asked.

    Folder paths are created for archived documents too, but their IDs are
    attached only when ``include_archived`` is True or the record is active.
    """
    if documents is None:
        documents = load_documents(file_path)
    _validate_documents(documents)

    folder_tree = FolderTree(root_name=root_name)
    for document in documents:
        folder_tree.get_or_create_folder(document["folder_path"])
        if include_archived or not document.get("is_archived", False):
            folder_tree.add_document(document["folder_path"], document["document_id"])
    return folder_tree


if __name__ == "__main__":
    loaded_documents = load_documents()
    document_table = initialize_document_hash_table(loaded_documents)
    folder_tree = initialize_folder_tree(loaded_documents)
    print("Loaded {0} documents.".format(len(loaded_documents)))
    print(
        "Hash table entries: {0}; root folder: {1}".format(
            len(document_table), folder_tree.root.name
        )
    )
