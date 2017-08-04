import tempfile
import os
import os.path
import subprocess

from marty.printer import printer
from marty.commands import Command
from marty.operations.fs import MartyFS


class Mount(Command):

    """ Mount a backup or a tree into a directory.
    """

    help = 'Mount a backup or a tree into a directory'

    def prepare(self):
        self._aparser.add_argument('remote', nargs='?')
        self._aparser.add_argument('name')
        self._aparser.add_argument('mountpoint')

    def run(self, args, config, storage, remotes):
        mountpoint = os.path.abspath(os.path.expanduser(args.mountpoint))
        if not os.path.exists(mountpoint):
            raise RuntimeError('Given mountpoint (%s) does not exist' % mountpoint)

        name = '%s/%s' % (args.remote, args.name) if args.remote else args.name
        tree = storage.get_tree(name)
        MartyFS(storage, tree, mountpoint).mount()


class Explore(Command):

    """ Explore a backup or tree by mounting it into a temporary directory.
    """

    help = 'Explore a backup or tree'

    def prepare(self):
        self._aparser.add_argument('remote', nargs='?')
        self._aparser.add_argument('name')

    def run(self, args, config, storage, remotes):
        name = '%s/%s' % (args.remote, args.name) if args.remote else args.name
        tree = storage.get_tree(name)

        with tempfile.TemporaryDirectory() as fullname:
            fs = MartyFS(storage, tree, fullname)
            fs.mount()
            shell = os.environ.get('SHELL', '/bin/sh')
            pshell = subprocess.Popen([shell], cwd=fullname)
            pshell.wait()
            fs.umount()


class Diff(Command):

    """ Make a diff of two backups or tree for a remote.
    """

    help = 'Make a diff of two backups or tree for a remote'

    def prepare(self):
        self._aparser.add_argument('remote', nargs='?')
        self._aparser.add_argument('ref_name')
        self._aparser.add_argument('name')

    def _print_diff_tree(self, storage, ref_tree, tree, level=()):
        last = False
        next_level = level + (True,)

        ref_tree_set = set(ref_tree.names()) if ref_tree else set()
        tree_set = set(tree.names())
        adds = tree_set.difference(ref_tree_set)
        deletions = ref_tree_set.difference(tree_set)

        all_items = tree_set.union(ref_tree_set)

        for i, (name) in enumerate(sorted(all_items)):
            if len(tree) == i + 1:
                last = True
                next_level = level + (False,)
            header = ''.join([u'│   ' if x else '    ' for x in level])
            if last:
                header += '└── '
            else:
                header += '├── '

            # setup filename colors
            color = 'yellow'
            ref_item = None
            item = None
            if name in adds:
                item = tree[name]
                color = 'green'
            elif name in deletions:
                item = ref_tree[name]
                ref_item = ref_tree[name]
                color = 'red'
            else:
                item = tree[name]
                ref_item = ref_tree[name]

            filename = name.decode('utf-8', 'replace')
            # only print filename when there is a diff
            if name in adds or name in deletions or item.ref != ref_item.ref:
                if item.type == 'tree':
                    printer.p('{h}<color fg={color}><b>{f}</b></color>',
                              h=header, f=filename, color=color)
                    ref_object = storage.get_tree(ref_item.ref) if ref_item else None
                    self._print_diff_tree(storage, ref_object,
                                          storage.get_tree(item.ref), level=next_level)
                elif item.get('filetype') == 'link':
                    printer.p('{h}<color fg={color}><b>{f}</b> -> {l}</color>',
                              h=header, f=filename, l=item.get('link', '?'),
                              color=color)
                else:
                    printer.p('{h}<color fg={color}>{f}</color>',
                              h=header, color=color, f=filename)

    def run(self, args, config, storage, remotes):
        ref_name = '%s/%s' % (args.remote, args.ref_name) if args.remote else args.ref_name
        other_name = '%s/%s' % (args.remote, args.name) if args.remote else args.name
        ref_backup = storage.get_backup(ref_name)
        ref_tree = storage.get_tree(ref_name)
        other_tree = storage.get_tree(other_name)
        printer.p('<b>Backup reference date:</b> {backup_date}',
                  backup_date=ref_backup.start_date.format('DD/MM/YYYY HH:mm:ss'))
        printer.p('<b>Backup reference root:</b> {backup_root}\n', backup_root=ref_backup.root)
        self._print_diff_tree(storage, ref_tree, other_tree)
