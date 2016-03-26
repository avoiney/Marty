import datetime

import arrow

from marty.commands import Command
from marty.printer import printer


class Remotes(Command):

    """ Show the list of configured remotes.
    """

    help = 'Show the list of configured remotes'

    def run(self, args, config, storage, remotes):
        table_lines = [('<b>NAME</b>', '<b>TYPE</b>', '<b>LAST</b>', '<b>NEXT</b>')]
        for remote in sorted(remotes.list(), key=lambda x: x.name):
            latest_ref = '%s/latest' % remote.name
            latest_backup = storage.get_backup(latest_ref)
            latest_date_text = '-'
            next_date_text = '-'
            if latest_backup is None:
                if remote.scheduler is not None:
                    next_date_text = '<color fg=yellow>now</color>'
            else:
                latest_date_text = latest_backup.start_date.humanize()
                if remote.scheduler is not None and remote.scheduler['enabled']:
                    next_date = latest_backup.start_date + datetime.timedelta(seconds=remote.scheduler['interval'] * 60)
                    if next_date > arrow.now():
                        next_date_text = '<color fg=green>%s</color>' % next_date.humanize()
                    else:
                        next_date_text = '<color fg=red>%s</color>' % next_date.humanize()

            table_lines.append((remote.name, remote.type, latest_date_text, next_date_text))
        printer.table(table_lines)
