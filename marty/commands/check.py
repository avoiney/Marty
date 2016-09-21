from marty.commands import Command
from marty.operations.objects import check
from marty.printer import printer


class Check(Command):

    """ Check all object into the pool.
    """

    help = 'Check all object into the pool'

    def run(self, args, config, storage, remotes):
        check(storage)
