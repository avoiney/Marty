import os
import hashlib
import tempfile

from confiture.schema.containers import Value
from confiture.schema.types import Path

from marty.storages import DefaultStorageSchema, Storage


class FilesystemStorageSchema(DefaultStorageSchema):

    location = Value(Path())


class Filesystem(Storage):

    """ Implement a storage in a local filesystem.
    """

    INGEST_READ_SIZE = 32768
    POOL_NAME_DEPTH = 3

    config_schema = FilesystemStorageSchema()

    @property
    def location(self):
        return self.config.get('location')

    @property
    def labels(self):
        return os.path.join(self.location, 'labels')

    @property
    def pool(self):
        return os.path.join(self.location, 'pool')

    def _get_pool_dir(self, filename):
        return os.path.join(self.pool, *filename[:self.POOL_NAME_DEPTH])

    def _get_pool_name(self, filename):
        return os.path.join(self._get_pool_dir(filename), filename)

    def _get_label_name(self, name):
        return os.path.join(self.labels, name)

    def _makedirs(self, directory):
        try:
            os.makedirs(directory)
        except OSError as err:
            if err.errno != 17:
                raise  # Ignore already existing directory

    def prepare(self):
        if not os.path.exists(self.location):
            os.mkdir(self.location)
        if not os.path.exists(self.pool):
            os.mkdir(self.pool)
        if not os.path.exists(self.labels):
            os.mkdir(self.labels)

    def ingest(self, obj):
        obj_file = obj.to_file()
        size = 0
        with tempfile.NamedTemporaryFile(dir=self.location) as ftemp:
            fhash = hashlib.sha1()
            buf = True
            while buf:
                buf = obj_file.read(self.INGEST_READ_SIZE)
                fhash.update(buf)
                ftemp.write(buf)
                size += len(buf)
            # FIXME: protect this section with a lock
            hex_hash = fhash.hexdigest()
            if not self.exists(hex_hash):
                self._makedirs(self._get_pool_dir(hex_hash))
                os.link(ftemp.name, self._get_pool_name(hex_hash))
                stored_size = size
            else:
                stored_size = 0
            # FIXME: end of protected section
            return hex_hash, size, stored_size

    def list(self):
        for _, _, filename in os.walk(self.pool):
            yield from filename

    def delete(self, ref):
        os.unlink(self._get_pool_name(ref))

    def open(self, ref):
        return open(self._get_pool_name(ref), 'rb')

    def size(self, ref):
        return os.stat(self._get_pool_name(ref)).st_size

    def exists(self, filename):
        return os.path.exists(self._get_pool_name(filename))

    def read_label(self, name):
        self.check_label(name, raise_error=True)
        filename = self._get_label_name(name)
        try:
            return open(filename, 'r').read(40)
        except FileNotFoundError:
            return None

    def set_label(self, name, ref, overwrite=True):
        self.check_label(name, raise_error=True)
        filename = self._get_label_name(name)
        if os.path.exists(filename) and not overwrite:
            raise RuntimeError('Label %s already exists' % name)
        self._makedirs(os.path.dirname(filename))
        open(filename, 'w').write(ref)

    def list_labels(self):
        for dirpath, dirnames, filenames in os.walk(self.labels):
            prefix = os.path.relpath(dirpath, self.labels)
            if prefix == '.':
                prefix = ''
            for filename in filenames:
                yield os.path.join(prefix, filename)
