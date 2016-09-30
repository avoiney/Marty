import os
import stat
import hashlib
import shutil

from confiture.schema.containers import Value
from confiture.schema.types import Path

from marty.remotemethods import DefaultRemoteMethodSchema, RemoteMethod, RemoteOperationError
from marty.datastructures import Tree, Blob


class LocalRemoteMethodSchema(DefaultRemoteMethodSchema):

    root = Value(Path(), default='/')


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

    def put_tree(self, tree, path):
        path = path.lstrip(os.sep.encode('utf-8'))
        directory = os.path.join(self.root, path)
        for name, item in tree.items():
            fullname = os.path.join(directory, name)
            try:
                fstat = os.lstat(fullname)
            except FileNotFoundError:
                fstat = None

            # Create the file itself according to its type:
            if item.get('filetype') == 'regular':
                if fstat is not None and not stat.S_ISREG(fstat.st_mode):
                    raise RemoteOperationError('%s already exists and not a regular file' % fullname)
                else:
                    try:
                        with open(fullname, 'a'):
                            pass
                    except OSError as err:
                        raise RemoteOperationError(err.strerror)
            elif item.get('filetype') == 'directory':
                try:
                    os.mkdir(fullname)
                except FileExistsError:
                    if stat.S_ISDIR(fstat.st_mode):
                        pass  # Ignore already existing directory
                    else:
                        raise RemoteOperationError('%s already exists and not a directory' % fullname)
                except OSError as err:
                    raise RemoteOperationError(err.strerror)
            elif item.get('filetype') == 'link':
                if 'link' in item:
                    try:
                        if fstat is not None:
                            if stat.S_ISLNK(fstat.st_mode):
                                os.unlink(fullname)
                            else:
                                raise RemoteOperationError('%s already exists and not a link' % fullname)
                        os.symlink(item['link'], fullname)
                    except OSError as err:
                        raise RemoteOperationError(err.strerror)
            elif item.get('filetype') == 'fifo':
                try:
                    os.mkfifo(fullname)
                except FileExistsError:
                    if stat.S_ISFIFO(fstat.st_mode):
                        pass  # Ignore already existing FIFO file
                    else:
                        raise RemoteOperationError('%s already exists and not a FIFO file' % fullname)
                except OSError as err:
                    raise RemoteOperationError(err.strerror)
            else:
                pass  # Ignore unknown file types

            # Set files metadata:
            os.chown(fullname, item.get('uid', -1), item.get('gid', -1), follow_symlinks=False)
            if 'mode' in item:
                try:
                    os.chmod(fullname, item['mode'], follow_symlinks=False)
                except SystemError:
                    pass  # Workaround follow_symlinks not implemented in Python 3.5 (bug?)

    def get_blob(self, path):
        path = path.lstrip(os.sep.encode('utf-8'))
        try:
            blob = Blob(blob=open(os.path.join(self.root, path), 'rb'))
        except OSError as err:
            raise RemoteOperationError(err.strerror)
        return blob

    def put_blob(self, blob, path):
        path = path.lstrip(os.sep.encode('utf-8'))
        fullname = os.path.join(self.root, path)
        try:
            shutil.copyfileobj(blob.to_file(), open(fullname, 'wb'))
        except OSError as err:
            raise RemoteOperationError(err.strerror)

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
