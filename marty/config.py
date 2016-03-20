""" Marty configuration parsers.
"""

import pkg_resources

from confiture import Confiture
from confiture.schema import ValidationError
from confiture.schema.containers import Section, Value, once
from confiture.schema.types import String


class EntryPoint(String):

    """ Distutil entrypoint type.
    """

    def __init__(self, entrypoint, **kwargs):
        self._entrypoint = entrypoint
        super(EntryPoint, self).__init__(**kwargs)

    def validate(self, value):
        value = super(EntryPoint, self).validate(value)
        # Get the first entry-point to match the provided value:
        entrypoint = next(pkg_resources.iter_entry_points(self._entrypoint, str(value)), None)
        if entrypoint is None:
            raise ValidationError('Unknown %s entry-point' % self._entrypoint)
        return entrypoint.name, entrypoint.load()

    def cast(self, value):
        raise NotImplementedError()


class RemoteConfig(Section):

    _meta = {'args': Value(String()),
             'unique': True,
             'repeat': (0, None),
             'allow_unknown': True}

    method = Value(EntryPoint('marty.remotemethods'))


class RemotesConfig(Section):

    _meta = {'repeat': once}

    remote = RemoteConfig()


class StorageConfig(Section):

    _meta = {'repeat': once,
             'allow_unknown': True}

    type = Value(EntryPoint('marty.storages'))


class RootMartyConfig(Section):

    storage = StorageConfig()
    remotes = RemotesConfig()


def parse_config(filename):
    conf = Confiture.from_filename(filename, schema=RootMartyConfig())
    return conf.parse()
