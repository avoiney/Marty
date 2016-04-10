import arrow

from marty.commands import Command
from marty.printer import printer


DATE_FORMAT = 'DD/MM/YYYY HH:mm:ss'
ORDERS = {'name': lambda x: x[0],
          'date': lambda x: x[1].start_date,
          'duration': lambda x: x[1].duration}


class List(Command):

    """ List backups.
    """

    help = 'List backups'

    def prepare(self):
        self._aparser.add_argument('remote', nargs='?')
        self._aparser.add_argument('-s', '--since', type=arrow.get)
        self._aparser.add_argument('-u', '--until', type=arrow.get)
        self._aparser.add_argument('-o', '--order', choices=ORDERS, default='name')

    def run(self, args, config, storage, remotes):
        table_lines = [('', '<b>NAME</b>', '<b>START DATE</b>', '<b>DURATION</b>')]

        pattern = '%s/*' % args.remote if args.remote else None

        for label, backup in sorted(storage.list_backups(pattern=pattern,
                                                         since=args.since,
                                                         until=args.until),
                                    key=ORDERS[args.order]):
            flags = []
            if backup.parent:
                flags.append('<b>P</b>')
            if backup.errors:
                flags.append('<color fg=red><b>E</b></color>')

            # Extract remote from backup name:
            name = label
            split_name = label.split('/', 1)
            if len(split_name) == 2 and remotes.get(split_name[0]):
                name = '<b>%s</b>/%s' % tuple(split_name)
            else:
                flags.append('<b>O</b>')

            table_lines.append((''.join(flags),
                               name,
                               backup.start_date.format(DATE_FORMAT),
                               str(backup.duration)))

        printer.table(table_lines)
        printer.p('\nFlags: <b>P</b> have parent, '
                  '<color fg=red><b>E</b></color> - have errors, '
                  '<b>O</b> orphan backup')
