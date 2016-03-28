""" Operations on Marty objects.
"""

import os

from marty.printer import printer


def walk_tree(storage, tree, prefix=b'/'):
    """ Recursively walk a tree on the provided storage.
    """

    for name, item in tree.items():
        fullname = os.path.join(prefix, name)
        yield (fullname, item)
        if item.type == 'tree':
            yield from walk_tree(storage, storage.get_tree(item.ref), fullname)


def gc_walk_used(storage):
    """ Get the list of known objects.
    """

    known_objects = set()

    def _walker(ref):
        if int(ref, 16) not in known_objects:
            # Add the tree ref in list of known objects:
            known_objects.add(int(ref, 16))

            # Get the tree to browse it:
            tree = storage.get_tree(ref)
            for name, item in tree.items():
                if item.ref:
                    if item.type == 'blob':
                        known_objects.add(int(item.ref, 16))
                    elif item.type == 'tree':
                        _walker(item.ref)

    for label in storage.list_labels():
        ref = storage.resolve(label)
        known_objects.add(int(ref, 16))
        backup = storage.get_backup(ref)
        _walker(backup.root)

    return known_objects


def gc_iter_unused(storage):
    """ Iterate over the list of unused objects.
    """
    known_objects = gc_walk_used(storage)
    for ref in storage.list():
        if int(ref, 16) not in known_objects:
            yield ref


def gc(storage, delete=True):
    """ Delete unused objects.
    """
    count = 0
    size = 0
    for ref in gc_iter_unused(storage):
        printer.verbose('Removing object {ref}', ref=ref)
        size += storage.size(ref)
        count += 1
        if delete:
            storage.delete(ref)
    return count, size
