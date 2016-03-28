from marty.commands import Command
from marty.operations.export import EXPORT_FORMATS


class Export(Command):

    """ Export a backup or tree.
    """

    help = 'Export a backup or tree'

    def prepare(self):
        self._aparser.add_argument('remote', nargs='?')
        self._aparser.add_argument('name')
        self._aparser.add_argument('output')
        self._aparser.add_argument('-f', '--format', choices=EXPORT_FORMATS,
                                   default='dir', help='Ouput format')

    def run(self, args, config, storage, remotes):
        name = '%s/%s' % (args.remote, args.name) if args.remote else args.name
        tree = storage.get_tree(name)
        exporter = EXPORT_FORMATS[args.format]
        exporter(tree, storage, args.output)
