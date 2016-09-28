import arrow

from marty.commands import Command
from marty.operations.backup import create_backup
from marty.printer import printer


class Backup(Command):

    """ Create a new backup of the remote.
    """

    help = 'Create a new backup of the remote'

    def prepare(self):
        self._aparser.add_argument('remote')
        self._aparser.add_argument('name', nargs='?',
                                   default=arrow.now().strftime('%Y-%m-%d_%H-%M-%S'))
        self._aparser.add_argument('-o', '--overwrite', action='store_true',
                                   help='Overwrite existing backup')
        self._aparser.add_argument('-p', '--parent',
                                   help='Name of the parent backup')
        self._aparser.add_argument('-s', '--stats', action='store_true',
                                   help='Show statistics about backup')

    def run(self, args, config, storage, remotes):
        remote = remotes.get(args.remote)
        if remote is None:
            raise RuntimeError('Given remote (%s) does not exist' % args.remote)

        backup_label = '%s/%s' % (remote.name, args.name)

        if not args.overwrite and storage.resolve(backup_label):
            raise RuntimeError('A backup with this name already exists for this remote')

        if args.parent:
            parent = '%s/%s' % (remote.name, args.parent)
        else:
            parent = None

        ref, backup = create_backup(storage, remote, parent=parent)

        # Create labels for the new backup:
        storage.set_label(backup_label, ref)
        storage.set_label('%s/latest' % remote.name, ref)

        printer.p('<b>Duration:</b> {d}', d=backup.duration)
        printer.p('<b>Root:</b> {r}', r=backup.root)

        if backup.errors:
            printer.hr()

            printer.p('<b>{n} errors:</b>', n=len(backup.errors))
            printer.p()
            for filename, error in backup.errors.items():
                printer.p(' - <b>{fn}</b>: {error}', fn=filename.decode('utf-8', 'replace'), error=error)

        if args.stats:
            printer.hr()
            printer.table(backup.stats_table(), fixed_width=80, center=True)
            printer.p()
