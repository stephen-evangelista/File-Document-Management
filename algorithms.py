"""Custom algorithms for sorting values and searching the folder tree."""


def merge_sort(values):
    """Return a new list containing values in ascending order.

    This is a stable merge sort. It compares items with ``<=`` and does not
    call Python's built-in ``sort`` or ``sorted`` functions.
    """
    item_count = len(values)

    # Copy by index so the caller's input is not changed.
    result = [None] * item_count
    temporary = [None] * item_count
    index = 0
    while index < item_count:
        result[index] = values[index]
        index += 1

    def sort_range(start, end):
        """Sort the half-open range [start, end) inside result."""
        if end - start <= 1:
            return

        middle = (start + end) // 2
        sort_range(start, middle)
        sort_range(middle, end)

        left_index = start
        right_index = middle
        write_index = start

        # Merge the two sorted halves into the temporary array.
        while left_index < middle and right_index < end:
            if result[left_index] <= result[right_index]:
                temporary[write_index] = result[left_index]
                left_index += 1
            else:
                temporary[write_index] = result[right_index]
                right_index += 1
            write_index += 1

        # Copy any values left in either half.
        while left_index < middle:
            temporary[write_index] = result[left_index]
            left_index += 1
            write_index += 1

        while right_index < end:
            temporary[write_index] = result[right_index]
            right_index += 1
            write_index += 1

        # Copy the merged range back so the next merge can use it.
        copy_index = start
        while copy_index < end:
            result[copy_index] = temporary[copy_index]
            copy_index += 1

    sort_range(0, item_count)
    return result


def dfs_search(root, target_name):
    """Search a FolderNode tree depth-first for a folder with target_name.

    Visit order is preorder: check the current folder, then each child
    subtree from left to right. Return the matching FolderNode, or None if
    no folder has that name. Pass the tree's root node as ``root``.
    """
    if root is None:
        return None

    if root.name == target_name:
        return root

    # Explore each child subtree before moving to the next sibling.
    child = root.first_child
    while child is not None:
        match = dfs_search(child, target_name)
        if match is not None:
            return match
        child = child.next_sibling

    return None
