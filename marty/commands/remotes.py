import datetime

import arrow
import humanize

from marty.commands import Command
from marty.printer import printer


STATS_TOTAL = ('new-blob-size', 'reused-blob-size', 'skipped-blob-size', 'new-tree-size', 'reused-tree-size')
STATS_NEW = ('new-blob-size', 'new-tree-size')


class Remotes(Command):

    """ Show the list of configured remotes.
    """

    help = 'Show the list of configured remotes'

    def run(self, args, config, storage, remotes):
        table_lines = [('<b>NAME</b>', '<b>TYPE</b>', '<b>LAST</b>', '<b>NEXT</b>', '<b>LAST SIZE</b>')]
        for remote in sorted(remotes.list(), key=lambda x: x.name):
            latest_ref = '%s/latest' % remote.name
            latest_backup = storage.get_backup(latest_ref)
            latest_date_text = '-'
            next_date_text = '-'
            size = '-'
            if latest_backup is None:
                if remote.scheduler is not None:
                    next_date_text = '<color fg=yellow>now</color>'
            else:
                size_total = sum(latest_backup.stats.get(x, 0) for x in STATS_TOTAL)
                size_new = sum(latest_backup.stats.get(x, 0) for x in STATS_NEW)
                size = '%s (+%s)' % (humanize.naturalsize(size_total, binary=True),
                                     humanize.naturalsize(size_new, binary=True))
                latest_date_text = latest_backup.start_date.humanize()
                if remote.scheduler is not None and remote.scheduler['enabled']:
                    next_date = latest_backup.start_date + datetime.timedelta(seconds=remote.scheduler['interval'] * 60)
                    if next_date > arrow.now():
                        next_date_text = '<color fg=green>%s</color>' % next_date.humanize()
                    else:
                        next_date_text = '<color fg=red>%s</color>' % next_date.humanize()

            table_lines.append((remote.name, remote.type, latest_date_text, next_date_text, size))
        printer.table(table_lines)
