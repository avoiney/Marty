import re

from confiture.schema.containers import Section, Value
from confiture.schema.types import String

from marty.datastructures import Blob, Tree, Backup


class DefaultStorageSchema(Section):

    _meta = {}
    type = Value(String())


class Storage(object):

    """ Base class for all storage backends.
    """

    config_schema = DefaultStorageSchema()

    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.prepare()

    def get(self, ref, type=None):
        """ Decode an object using provided type.
        """
        ref = self.resolve(ref)
        if ref is not None:
            return type.from_file(self.open(ref))
        else:
            return None

    def get_blob(self, ref):
        """ Decode a blob object from provided ref.
        """
        return self.get(ref, Blob)

    def get_tree(self, ref):
        """ Decode a tree object from provided ref.
        """
        return self.get(ref, Tree)

    def get_backup(self, ref):
        """ Decode backup object from provided ref.
        """
        return self.get(ref, Backup)

    def resolve(self, label):
        """ Resolve a label.
        """
        if self.exists(label):  # If label exists in storage, it's certainly a ref
            return label
        else:
            try:
                return self.read_label(label)
            except FileNotFoundError:
                return None

    def check_label(self, label, raise_error=False):
        """ Return True if provided label is valid.

        If raise_error is True, raise an exception if label is invalid.
        """
        if re.match('^[^./?<>\\:*|"]+(/[^./?<>\\:*|"]+)*$', label):
            return True
        else:
            if raise_error:
                raise RuntimeError('Invalid label "%s"' % label)
            else:
                return False

    def prepare(self):
        """ Prepare the storage before to use it.
        """
        pass

    def ingest(self, obj):
        """ Ingest the provided obj(ect) into the store.

        Return a tuple (ref, size, stored_size) where ref is the reference to the
        newly ingested file, size the bytes read from the file, and stored_size
        the bytes stored on the storage (after optimization/compression/chunking
        or whatever the storage implements).

        If stored_size is 0, you can assume that the file is already existing
        on the storage.
        """
        raise NotImplementedError('%s storage type does not implement ingest' % self.__class__.__name__)

    def exists(self, ref):
        """ Return True if an object with provided ref already exists in storage.
        """
        raise NotImplementedError('%s storage type does not implement exists' % self.__class__.__name__)

    def open(self, ref):
        """ Open stream to the provided object.
        """
        raise NotImplementedError('%s storage type does not implement open' % self.__class__.__name__)

    def size(self, ref):
        """ Get size of the provided object.
        """
        raise NotImplementedError('%s storage type does not implement size' % self.__class__.__name__)

    def read_label(self, name):
        """ Delete a label.
        """
        raise NotImplementedError('%s storage type does not implement read_label' % self.__class__.__name__)

    def set_label(self, name, ref, overwrite=True):
        """ Set a label on the provided ref.

        If overwrite is True, rewrite the label instead of raising an error.
        """
        raise NotImplementedError('%s storage type does not implement set_label' % self.__class__.__name__)

    def delete_label(self, name):
        """ Delete a label.
        """
        raise NotImplementedError('%s storage type does not implement delete_label' % self.__class__.__name__)
