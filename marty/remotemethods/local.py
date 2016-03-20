import os
import stat
import hashlib

from confiture.schema.containers import Value
from confiture.schema.types import String

from marty.remotemethods import DefaultRemoteMethodSchema, RemoteMethod, RemoteOperationError
from marty.datastructures import Tree, Blob


class LocalRemoteMethodSchema(DefaultRemoteMethodSchema):

    root = Value(String(), default='/')


class Local(RemoteMethod):

    """ Local remote.
    """

    config_schema = LocalRemoteMethodSchema()

    @property
    def root(self):
        return self.config.get('root').encode('utf-8')

    def get_tree(self, path):
        path = path.lstrip(os.sep.encode('utf-8'))
        directory = os.path.join(self.root, path)
        tree = Tree()
        try:
            directory_items = os.listdir(directory)
        except OSError as err:
            raise RemoteOperationError(err.strerror)

        for filename in directory_items:
            assert isinstance(filename, bytes)
            item = {}
            fullname = os.path.join(directory, filename)
            fstat = os.lstat(fullname)
            if stat.S_ISREG(fstat.st_mode):
                item['type'] = 'blob'
                item['filetype'] = 'regular'
            elif stat.S_ISDIR(fstat.st_mode):
                item['type'] = 'tree'
                item['filetype'] = 'directory'
            elif stat.S_ISLNK(fstat.st_mode):
                item['filetype'] = 'link'
                item['link'] = os.readlink(os.path.join(directory, filename))
            elif stat.S_ISFIFO(fstat.st_mode):
                item['filetype'] = 'fifo'
            else:
                continue  # FIXME: Warn
            fmode = fstat.st_mode & (stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO | stat.S_ISVTX)

            item['uid'] = fstat.st_uid
            item['gid'] = fstat.st_gid
            item['mode'] = fmode
            item['atime'] = int(fstat.st_atime)
            item['mtime'] = int(fstat.st_mtime)
            item['ctime'] = int(fstat.st_ctime)
            item['size'] = fstat.st_size

            tree.add(filename, item)
        return tree

    def get_blob(self, path):
        path = path.lstrip(os.sep.encode('utf-8'))
        try:
            blob = Blob(blob=open(os.path.join(self.root, path), 'rb'))
        except OSError as err:
            raise RemoteOperationError(err.strerror)
        return blob

    def checksum(self, path):
        path = path.lstrip(os.sep.encode('utf-8'))
        filename = os.path.join(self.root, path)
        filehash = hashlib.sha1()
        try:
            with open(filename, 'rb') as fhash:
                buf = True
                while buf:
                    buf = fhash.read(8192)
                    filehash.update(buf)
        except OSError as err:
            raise RemoteOperationError(err.strerror)
        return filehash.hexdigest()

    def newer(self, attr_new, attr_old):
        return attr_new.get('mtime', 0) != attr_old.get('mtime', 0)
