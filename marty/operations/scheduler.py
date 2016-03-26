import time
import datetime
import concurrent.futures

import arrow

from marty.printer import printer
from marty.operations.backup import create_backup


def scheduler_task(storage, remote, parent):
    backup_label = arrow.now().strftime('%Y-%m-%d_%H-%M-%S')

    ref, backup = create_backup(storage, remote, parent=parent)

    # Create labels for the new backup:
    storage.set_label('%s/%s' % (remote.name, backup_label), ref)
    storage.set_label('%s/latest' % remote.name, ref)

    return backup


def scheduler(storage, remotes, workers=1, loop_interval=10):
    """ Execute the scheduler for the specified remotes.
    """

    printer.p('Scheduler started for {n} remotes', n=len(remotes))
    running = {}  # remote -> future backup task result

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        while True:
            for remote in remotes:
                if remote in running:
                    continue  # Ignore still running remotes

                # Check if the remote has been backuped since configured interval:
                interval = datetime.timedelta(seconds=remote.scheduler['interval'] * 60)
                parent = '%s/latest' % remote.name
                backup = storage.get_backup(parent)
                if backup is None:
                    parent = None

                if backup is None or backup.start_date + interval < arrow.now():
                    running[remote] = executor.submit(scheduler_task, storage, remote, parent)
                    printer.p('Queued a new backup for {n}', n=remote.name)

            # Handle completed backups:
            for remote, result in list(running.items()):
                if result.done():
                    if result.exception() is not None:
                        printer.p('Backup for {n} failed: {e}', n=remote.name, e=result.exception())
                    else:
                        backup = result.result()
                        printer.p('Backup for {n} has been completed in {d} seconds',
                                  n=remote.name,
                                  d=backup.duration.seconds)

                    del running[remote]

            time.sleep(loop_interval)
