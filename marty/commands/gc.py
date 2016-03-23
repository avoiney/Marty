import humanize

from marty.commands import Command
from marty.operations.objects import gc
from marty.printer import printer


class Gc(Command):

    """ Garbage collect unused objects in pool.
    """

    help = 'Garbage collect unused objects in pool'

    def prepare(self):
        self._aparser.add_argument('-r', '--dry-run', action='store_true',
                                   help='Do not delete selected objects')

    def run(self, args, config, storage, remotes):
        count, size = gc(storage, delete=not args.dry_run)
        if count:
            printer.p('Done. Deleted {n} objects, total size: {s}', n=count, s=humanize.naturalsize(size, binary=True))
        else:
            printer.p('Done. Nothing to delete.')
