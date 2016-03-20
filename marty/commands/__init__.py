import pkg_resources


class Command(object):

    """
    Base class for a command.

    :cvar help: the help for the command
    """

    help = None

    @classmethod
    def load_commands(cls, parser):
        """ Load commands and attach them to the provided parser.
        """

        for entrypoint in pkg_resources.iter_entry_points(group='marty.commands'):
            command_class = entrypoint.load()
            command_class(entrypoint.name, parser).prepare()

    def __init__(self, name, aparser_subs):
        self.name = name
        self._aparser = aparser_subs.add_parser(name, help=self.help)
        self._aparser.set_defaults(command=self.run, command_name=name)

    def add_arg(self, *args, **kwargs):
        """ Add an argument to the command argument parser.
        """

        self._aparser.add_argument(*args, **kwargs)

    def prepare(self):
        """ Method to override, executed before to parse arguments from command
            line. This is a good place to call :meth:`add_arg`.
        """
        pass

    def run(self, args, config, storage, remotes):
        """ Method to override, executed if command has been selected.

        :param args: parsed arguments
        :param config: parsed configuration
        :param storage: storage object
        :param remotes: remote manager
        """
        pass
