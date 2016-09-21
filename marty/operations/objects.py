""" Operations on Marty objects.
"""

import os
import hashlib

from marty.datastructures import Tree
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


def check(storage, read_size=4096):
    """ Check hash of all objects in the pool.
    """
    for ref in storage.list():
        printer.verbose('Checking {ref}', ref=ref, err=True)
        hasher = hashlib.sha1()
        fobject = storage.open(ref)
        buf = fobject.read(read_size)
        while buf:
            hasher.update(buf)
            buf = fobject.read(read_size)
        if hasher.hexdigest() != ref:
            printer.p(ref)


def get_parent_tree(storage, root_tree, path):
    """ Get parent tree and parent path for the provided root tree and path.

    Return a couple (parent_tree, parent_path) where parent_tree is a forged
    tree with the last path component as single item and parent_path the path
    to the latest base directory (eg: path is "/foo/bar", parent_tree will be
    created with a single item "bar" and parent_path will be "/foo").

    If path is "/" or "", parent_tree will be root_tree and parent_path will be
    empty.
    """

    components = [x for x in path.strip(b'/').split(b'/') if x]
    tree = root_tree

    for component in components[:-1]:
        if component in tree:
            item = tree[component]
            if item.type == 'tree' and item.ref:
                tree = storage.get_tree(item.ref)
            else:
                raise RuntimeError('Not a tree: %s' % component.decode('utf8', 'ignore'))
        else:
            raise RuntimeError('Unknown tree: %s' % component.decode('utf8', 'ignore'))

    if components:
        component = components[-1]
        if component in tree:
            item = tree[component]
            tree = Tree()
            tree.add(component, item)
        else:
            raise RuntimeError('Unknown item: %s' % component.decode('utf8', 'ignore'))
        return tree, b'/'.join(components[:-1])
    else:
        return root_tree, b''
