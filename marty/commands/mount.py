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
        self._aparser.add_argument('names', nargs=2)

    def run(self, args, config, storage, remotes):
        names = ['%s/%s' % (args.remote, name) if args.remote else name for name in args.names]
        trees = [storage.get_tree(name) for name in names]

        with tempfile.TemporaryDirectory() as fullname1, tempfile.TemporaryDirectory() as fullname2:
            fs1 = MartyFS(storage, trees[0], fullname1)
            fs2 = MartyFS(storage, trees[1], fullname2)
            fs1.mount()
            fs2.mount()
            pshell = subprocess.Popen(['diff', '-q', '-r', '--no-dereference', '--suppress-common-lines',
                                       fullname1, fullname2], stdout=subprocess.PIPE)
            pshell.wait()
            output = pshell.stdout.read().decode('utf8')
            fs2.umount()
            fs1.umount()
            names_filenames = zip((fullname1, fullname2), names)
            for name_filename in names_filenames:
                output = output.replace(*name_filename)
            printer.p('Diff output betwwen <b>%s</b> and <b>%s</b>:\n\n%s' % (*names, output))
