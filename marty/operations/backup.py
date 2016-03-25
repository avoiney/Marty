""" Set of operations related to backups.
"""

import os
import collections

from marty.datastructures import Backup
from marty.printer import printer


def create_backup(storage, remote, parent=None):
    """ Create a new backup of provided remote and return its backup object.

    .. warning:: Do not forget to add a label on returned backup to avoid its
       removal by the garbage collector.
    """

    if parent:
        parent_ref = storage.resolve(parent)
        parent_backup = storage.get_backup(parent_ref)
        if parent_backup:
            parent_root = storage.get_tree(parent_backup.root)
    else:
        parent_ref = None
        parent_root = None

    backup = Backup(parent=parent_ref)

    with backup, remote:
        backup.errors, backup.stats, backup.root = walk_and_ingest_remote(remote, storage, parent=parent_root)
    ref, size, stored_size = storage.ingest(backup)
    return ref, backup


def walk_and_ingest_remote(remote, storage, path=b'/', parent=None):
    """ Recursively walk the remote, ingesting data into provided storage.

    Returns a tuple (errors, stats, tree_ref) where errors is a dict of errors
    by filename, stats a dictionnary of statistics and tree_ref the reference
    on the top level tree.
    """
    errors = {}
    stats = collections.Counter()
    tree = remote.get_tree(path)

    for filename, item in tree.items():
        fullname = os.path.join(path, filename)
        if not remote.policy.included(fullname):
            # Skip excluded paths
            tree.discard(filename)
            continue
        parent_item = parent[filename] if parent is not None and filename in parent else None
        if item.type == 'blob':
            try:
                stats['total-blob'] += 1
                # Check if the item has changed since last backup:
                if parent_item is not None and not remote.newer(item, parent_item):
                    item.ref = parent_item.ref
                    stats['skipped-blob'] += 1
                    stats['skipped-blob-size'] += storage.size(item.ref)
                    action = 'SKIP'
                else:
                    # Blob items are ingested into the storage if it do not reused already
                    item.ref = remote.checksum(fullname)
                    if item.ref is None or not storage.exists(item.ref):
                        blob = remote.get_blob(fullname)
                        item.ref, size, stored_size = storage.ingest(blob)
                        if stored_size:
                            stats['new-blob'] += 1
                            stats['new-blob-size'] += size
                            stats['new-blob-stored-size'] += stored_size
                            action = 'NEW'
                        else:
                            stats['reused-blob'] += 1
                            stats['reused-blob-size'] += size
                            action = 'REUSE'
                    else:
                        stats['reused-blob'] += 1
                        stats['reused-blob-size'] += storage.size(item.ref)
                        action = 'REUSE'

                printer.verbose('Blob: <b>{path}</b> {action}', path=fullname.decode('utf-8', 'replace'), action=action)
            except Exception as err:
                errors[fullname] = str(err)
                printer.verbose('Blob: <b>{path}</b> <color fg=red><b>Error:</b> '
                                '{error}</color>', path=fullname.decode('utf-8', 'replace'), error=err)
                tree.discard(filename)
                raise

        elif item.type == 'tree':
            # Tree items are recursively browsed:
            if parent_item is not None and parent_item.type == 'tree' and parent_item.ref is not None:
                parent_object = storage.get_tree(parent_item.ref)
            else:
                parent_object = None
            try:
                child_errors, child_stats, item.ref = walk_and_ingest_remote(remote,
                                                                             storage,
                                                                             fullname,
                                                                             parent_object)
            except Exception as err:
                errors[fullname] = str(err)
                printer.verbose('Tree: <b>{path}</b> <color fg=red><b>Error:</b> '
                                '{error}</color>', path=fullname.decode('utf-8', 'replace'), error=err)
                tree.discard(filename)
            else:
                errors.update(child_errors)
                stats.update(child_stats)

    # Ingest the tree into the storage:
    stats['total-tree'] += 1
    tree_ref, size, stored_size = storage.ingest(tree)
    if stored_size:
        stats['new-tree'] += 1
        stats['new-tree-size'] += size
        stats['new-tree-stored-size'] += stored_size
        action = 'NEW'
    else:
        stats['reused-tree'] += 1
        stats['reused-tree-size'] += size
        action = 'REUSED'
    printer.verbose('Tree: <b>{path}</b> {action}', path=path.decode('utf-8', 'replace'), action=action)
    return errors, stats, tree_ref
