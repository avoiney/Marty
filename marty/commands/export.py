import humanize

from marty.commands import Command
from marty.operations.export import EXPORT_FORMATS
from marty.printer import printer


class Export(Command):

    """ Export a backup.
    """

    help = 'Export a backup'

    def prepare(self):
        self._aparser.add_argument('remote', nargs='?')
        self._aparser.add_argument('name')
        self._aparser.add_argument('output')
        self._aparser.add_argument('-f', '--format', choices=EXPORT_FORMATS, help='Ouput format')

    def run(self, args, config, storage, remotes):
        name = '%s/%s' % (args.remote, args.name) if args.remote else args.name
        backup = storage.get_backup(name)
        exporter = EXPORT_FORMATS[args.format]
        exporter(backup.root, storage, args.output)
