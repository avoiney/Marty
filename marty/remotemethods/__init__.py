import os

from confiture.schema.containers import Section, Value, List
from confiture.schema.types import String


class RemoteOperationError(RuntimeError):

    """ Error raised during a remote method operation.
    """


class DefaultRemoteMethodSchema(Section):

    _meta = {'args': Value(String())}
    method = Value(String())
    includes = List(String(), default=[])
    excludes = List(String(), default=[])


class PathPolicy:

    """ Handle policy (include/exclude) of a given path.
    """

    def __init__(self, includes=None, excludes=None):
        paths = {}

        # Get paths from configuration:
        paths.update({PathPolicy.normalize(x): {'policy': 'include',
                                                'recursive': True} for x in includes})
        paths.update({PathPolicy.normalize(x): {'policy': 'exclude',
                                                'recursive': True} for x in excludes})

        # Add non-recursive include paths:
        for prefix, props in dict(paths).items():
            if props['policy'] == 'include':
                while prefix != b'/':
                    if prefix not in paths:
                        paths[prefix] = {'policy': props['policy'], 'recursive': False}
                    prefix = os.path.dirname(prefix)
        self.paths = list(sorted(paths.items(), reverse=True))

    @staticmethod
    def normalize(path):
        if isinstance(path, str):
            path = path.encode('utf-8')
        return os.path.normpath(os.path.join(b'/', path))

    def included(self, path):
        """ Return True if the path has to be included.
        """

        for prefix, props in self.paths:
            if props['recursive'] and path.startswith(prefix):
                return props['policy'] == 'include'
            elif not props['recursive'] and path == prefix:
                return props['policy'] == 'include'
        else:
            return True  # Default policy is to include


class RemoteMethod(object):

    """ Base class for all remotes methods.
    """

    config_schema = DefaultRemoteMethodSchema()

    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.policy = PathPolicy(includes=self.config.get('includes'),
                                 excludes=self.config.get('excludes'))

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.name)

    @property
    def type(self):
        return self.__class__.__name__

    # Remote method interface API

    def initialize(self):
        """ Initialize the RemoteMethod before to use it.

        This is a good place to put connection / authentication routines.
        """

    def get_tree(self, path):
        """ Return a Tree object for the specified path.
        """
        raise NotImplementedError('%s remote type does not implement list_directory' % self.__class__.__name__)

    def get_blob(self, path):
        """ Return a Blob object for the specified path.
        """
        raise NotImplementedError('%s remote type does not implement get_blob' % self.__class__.__name__)

    def checksum(self, path):
        """ Compute checksum of the provided path to blob object.
        """
        raise NotImplementedError('%s remote type does not implement checksum' % self.__class__.__name__)

    def newer(self, attr_new, attr_old):
        """ Compare two dicts of Tree item attributes.

        Returns True if attr_new is newer than attr_old.

        This method is is a part of the RemoteMethod interface because each
        RemoteMethod class can define its own set of Tree items attributes.
        """
        raise NotImplementedError('%s remote type does not implement newer' % self.__class__.__name__)


class RemoteManager(object):

    """ Manage remotes.
    """

    def __init__(self, config):
        self._config = config
        self._remotes = {}
        self._load_remotes()

    def _load_remotes(self):
        """ Load remotes from configuration.

        This method do the following things::
            - List remotes from configuration file
            - Validate remote specific configuration according to remote method chosen
            - Instanciate the remote method class for the remote
        """
        for remote in self._config.subsections('remote'):
            name, class_ = remote.get('method')
            self._remotes[remote.args] = class_(remote.args, class_.config_schema.validate(remote))

    def get(self, name, initialize=True):
        """ Get remote with provided name or None if remote is unknown.
        """
        remote = self._remotes.get(name)
        if remote is not None and initialize:
            remote.initialize()
        return remote
