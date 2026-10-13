"""Basic data structures for a file and document management system.

The hash table uses Python lists only for its bucket array and collision
chains, as requested. The folder tree and version stack use linked nodes.
"""


class _DocumentEntry:
    """One document record stored in a hash-table bucket."""

    def __init__(self, document_id, details):
        self.document_id = document_id
        self.details = details


class DocumentHashTable:
    """Store document details by ID using a hash table with separate chaining."""

    def __init__(self, bucket_count=16):
        # Each bucket is a list. Entries with the same bucket index share it.
        if bucket_count <= 0:
            raise ValueError("bucket_count must be greater than zero")
        self._buckets = [[] for _ in range(bucket_count)]
        self._size = 0

    def _bucket_index(self, document_id):
        """Calculate a bucket index without using Python's built-in hash()."""
        if not isinstance(document_id, str):
            raise TypeError("document_id must be a string")

        hash_value = 0
        for character in document_id:
            hash_value = (hash_value * 31 + ord(character)) % len(self._buckets)
        return hash_value

    def put(self, document_id, details):
        """Add a document, or replace its details if its ID already exists."""
        bucket = self._buckets[self._bucket_index(document_id)]

        # Search the collision chain before adding a new entry.
        for entry in bucket:
            if entry.document_id == document_id:
                entry.details = details
                return

        bucket.append(_DocumentEntry(document_id, details))
        self._size += 1

    def get(self, document_id):
        """Return the details for an ID, or None if the ID is not stored."""
        bucket = self._buckets[self._bucket_index(document_id)]
        for entry in bucket:
            if entry.document_id == document_id:
                return entry.details
        return None

    def contains(self, document_id):
        """Return True if the hash table contains this document ID."""
        bucket = self._buckets[self._bucket_index(document_id)]
        for entry in bucket:
            if entry.document_id == document_id:
                return True
        return False

    def remove(self, document_id):
        """Remove an ID and return its details, or return None if not found."""
        bucket = self._buckets[self._bucket_index(document_id)]
        index = 0
        while index < len(bucket):
            if bucket[index].document_id == document_id:
                details = bucket[index].details

                # Shift entries left to remove this item without using a
                # sorting operation or another data structure.
                shift_index = index
                while shift_index < len(bucket) - 1:
                    bucket[shift_index] = bucket[shift_index + 1]
                    shift_index += 1
                bucket.pop()

                self._size -= 1
                return details
            index += 1
        return None

    def __len__(self):
        """Return the number of document IDs currently stored."""
        return self._size


def _read_path_part(path, position):
    """Read the next slash-separated folder name without making a list."""
    path_length = len(path)

    # Ignore repeated or leading slashes.
    while position < path_length and path[position] == "/":
        position += 1

    start = position
    while position < path_length and path[position] != "/":
        position += 1

    return path[start:position], position


class FolderNode:
    """A folder node with linked child folders and linked document IDs."""

    def __init__(self, name):
        self.name = name
        self.first_child = None
        self.next_sibling = None
        self.first_document = None

    def find_child(self, folder_name):
        """Find a direct child folder by name, or return None."""
        child = self.first_child
        while child is not None:
            if child.name == folder_name:
                return child
            child = child.next_sibling
        return None

    def add_child(self, folder_name):
        """Add a direct child unless one with that name already exists."""
        existing = self.find_child(folder_name)
        if existing is not None:
            return existing

        new_child = FolderNode(folder_name)
        if self.first_child is None:
            self.first_child = new_child
            return new_child

        # Walk to the last sibling and link the new folder there.
        sibling = self.first_child
        while sibling.next_sibling is not None:
            sibling = sibling.next_sibling
        sibling.next_sibling = new_child
        return new_child

    def add_document(self, document_id):
        """Attach a document ID to this folder unless it is already present."""
        if not isinstance(document_id, str) or not document_id:
            raise ValueError("document_id must be a non-empty string")
        if self.contains_document(document_id):
            return

        new_document = _FolderDocumentNode(document_id)
        if self.first_document is None:
            self.first_document = new_document
            return

        document = self.first_document
        while document.next_document is not None:
            document = document.next_document
        document.next_document = new_document

    def contains_document(self, document_id):
        """Return True if this folder directly contains the given document ID."""
        document = self.first_document
        while document is not None:
            if document.document_id == document_id:
                return True
            document = document.next_document
        return False

    def remove_document(self, document_id):
        """Remove a document ID from this folder; return whether it was found."""
        previous = None
        document = self.first_document
        while document is not None:
            if document.document_id == document_id:
                if previous is None:
                    self.first_document = document.next_document
                else:
                    previous.next_document = document.next_document
                return True
            previous = document
            document = document.next_document
        return False


class _FolderDocumentNode:
    """A linked reference to one document stored inside a folder."""

    def __init__(self, document_id, next_document=None):
        self.document_id = document_id
        self.next_document = next_document


class FolderTree:
    """Represent nested folders and the documents stored in each folder."""

    def __init__(self, root_name="root"):
        """Create a tree with the named root folder."""
        if not root_name or "/" in root_name:
            raise ValueError("root_name must be non-empty and cannot contain '/'")
        self.root = FolderNode(root_name)

    def find_folder(self, folder_path):
        """Find a folder by path, returning None when any part is missing.

        Paths are slash-separated and may be relative to the root
        (``DSA/Project``) or include the root name (``School/DSA/Project``).
        An empty path, or the root name alone, refers to the root folder.
        """
        if not isinstance(folder_path, str):
            raise TypeError("folder_path must be a string")

        current = self.root
        position = 0
        first_part = True

        while position < len(folder_path):
            part, position = _read_path_part(folder_path, position)
            if not part:
                break

            if first_part and part == self.root.name:
                first_part = False
                continue

            first_part = False
            current = current.find_child(part)
            if current is None:
                return None

        return current

    def add_folder(self, parent_path, folder_name):
        """Add a folder under an existing parent and return its FolderNode.

        If a child with the same name is already present, return that child
        instead of creating a duplicate.
        """
        if not isinstance(folder_name, str) or not folder_name:
            raise ValueError("folder_name must be a non-empty string")
        if "/" in folder_name:
            raise ValueError("folder_name cannot contain '/'")

        parent = self.find_folder(parent_path)
        if parent is None:
            raise ValueError("parent folder does not exist: " + parent_path)
        return parent.add_child(folder_name)

    def get_or_create_folder(self, folder_path):
        """Return a folder at folder_path, creating missing path parts.

        The path may be relative to the root or may begin with the root name.
        """
        if not isinstance(folder_path, str):
            raise TypeError("folder_path must be a string")

        current = self.root
        position = 0
        first_part = True
        while position < len(folder_path):
            part, position = _read_path_part(folder_path, position)
            if not part:
                continue

            if first_part and part == self.root.name:
                first_part = False
                continue

            first_part = False
            current = current.add_child(part)

        return current

    def add_document(self, folder_path, document_id):
        """Add a document reference to its folder, creating missing folders."""
        folder = self.get_or_create_folder(folder_path)
        folder.add_document(document_id)

    def contains_document(self, folder_path, document_id):
        """Return True if the specified folder contains this document ID."""
        folder = self.find_folder(folder_path)
        return folder is not None and folder.contains_document(document_id)

    def remove_document(self, folder_path, document_id):
        """Remove a document reference from its folder; return whether found."""
        folder = self.find_folder(folder_path)
        if folder is None:
            return False
        return folder.remove_document(document_id)


class _VersionNode:
    """One version stored in the linked version stack."""

    def __init__(self, version, next_node=None):
        self.version = version
        self.next_node = next_node


class VersionStack:
    """Track document versions in last-in, first-out (LIFO) order."""

    def __init__(self):
        self._top = None
        self._size = 0

    def push(self, version):
        """Put a new version on top of the stack."""
        self._top = _VersionNode(version, self._top)
        self._size += 1

    def pop(self):
        """Remove and return the newest version.

        Raises IndexError if the stack is empty.
        """
        if self._top is None:
            raise IndexError("pop from empty VersionStack")

        version = self._top.version
        self._top = self._top.next_node
        self._size -= 1
        return version

    def peek(self):
        """Return the newest version without removing it.

        Raises IndexError if the stack is empty.
        """
        if self._top is None:
            raise IndexError("peek from empty VersionStack")
        return self._top.version

    def is_empty(self):
        """Return True if the stack has no versions."""
        return self._top is None

    def __len__(self):
        """Return the number of versions in the stack."""
        return self._size
