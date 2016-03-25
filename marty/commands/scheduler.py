from marty.commands import Command
from marty.operations.scheduler import scheduler


class Scheduler(Command):

    """ Run the scheduler.
    """

    help = 'Run the scheduler'

    def run(self, args, config, storage, remotes):
        scheduled_remotes = []
        for remote in remotes.list():
            if remote.scheduler is not None:
                scheduled_remotes.append(remote)
        workers = config.subsection('scheduler').get('workers')
        loop_interval = config.subsection('scheduler').get('loop_interval')
        scheduler(storage, scheduled_remotes, workers=workers, loop_interval=loop_interval)
