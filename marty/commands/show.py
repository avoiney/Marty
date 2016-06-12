from marty.commands import Command
from marty.printer import printer


WELLKNOW_TREE_ATTR_ORDER = ('filetype', 'mode', 'uid', 'gid', 'atime', 'mtime',
                            'ctime')


def tree_attr_sorter(value):
    value = value[0]
    try:
        first = WELLKNOW_TREE_ATTR_ORDER.index(value)
    except ValueError:
        first = float('inf')

    return (first, value)


class ShowTree(Command):

    """ Show details about a tree object.
    """

    help = 'Show details about a tree object'
    aliases = ['ls']

    def prepare(self):
        self._aparser.add_argument('remote', nargs='?')
        self._aparser.add_argument('name')

    def run(self, args, config, storage, remotes):
        name = '%s/%s' % (args.remote, args.name) if args.remote else args.name
        tree = storage.get_tree(name)
        table_lines = [('<b>NAME</b>', '<b>TYPE</b>', '<b>REF</b>', '<b>ATTRIBUTES</b>')]
        for name, details in sorted(tree.items()):
            name = '<b>%s</b>' % name.decode('utf-8', 'replace')
            type = details.pop('type', '')
            ref = details.pop('ref', '')
            fmt = '<color fg=green>%s</color>:<color fg=cyan>%s</color>'
            attributes = ' '.join(fmt % (k, v) for k, v in sorted(details.items(), key=tree_attr_sorter))
            table_lines.append((name, type, ref, attributes))

        printer.table(table_lines)


class ShowBackup(Command):

    """ Show details about a backup object.
    """

    help = 'Show details about a backup object'
    aliases = ['show']

    def prepare(self):
        self._aparser.add_argument('remote', nargs='?')
        self._aparser.add_argument('name')

    def run(self, args, config, storage, remotes):
        name = '%s/%s' % (args.remote, args.name) if args.remote else args.name
        backup = storage.get_backup(name)
        printer.p('<b>Date:</b> {s} -> {e} ({d})',
                  s=backup.start_date.format('DD/MM/YYYY HH:mm:ss'),
                  e=backup.end_date.format('DD/MM/YYYY HH:mm:ss'),
                  d=backup.duration)
        printer.p('<b>Root:</b> {r}', r=backup.root)
        if backup.parent:
            printer.p('<b>Parent:</b> {b}', b=backup.parent)
        if backup.errors:
            printer.hr()

            printer.p('<b>{n} errors:</b>', n=len(backup.errors))
            printer.p()
            for filename, error in backup.errors.items():
                printer.p(' - <b>{fn}</b>: {error}', fn=filename.decode('utf-8', 'replace'), error=error)
        printer.p()
        printer.p('-' * 80)
        printer.p()
        printer.table(backup.stats_table(), fixed_width=80, center=True)
        printer.p()
