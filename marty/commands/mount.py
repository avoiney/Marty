import tempfile
import os
import os.path
import subprocess

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
