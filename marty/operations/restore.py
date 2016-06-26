""" Set of operation relative to backup restoration.
"""

import os

from marty.printer import printer
from marty.operations.objects import walk_tree


def restore(storage, remote, tree, prefix=b'/'):
    """ Restore a tree object into the remote.
    """

    prefix = os.path.join(b'/', prefix)

    with remote:
        remote.put_tree(tree, prefix)
        printer.verbose('Tree: <b>{path}</b>', path=prefix.decode('utf-8', 'replace'))

        for fullname, item in walk_tree(storage, tree, prefix):
            if item.type == 'tree':
                printer.verbose('Tree: <b>{path}</b>', path=fullname.decode('utf-8', 'replace'))
                tree = storage.get_tree(item.ref)
                remote.put_tree(tree, fullname)
            elif item.type == 'blob':
                printer.verbose('Blob: <b>{path}</b>', path=fullname.decode('utf-8', 'replace'))
                blob = storage.get_blob(item.ref)
                remote.put_blob(blob, fullname)
