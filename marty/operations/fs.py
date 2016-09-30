import itertools
import errno
import stat
import os
import multiprocessing

import llfuse


class MartyFSHandler(llfuse.Operations):

    """ Fuse FS for a Marty Tree.
    """

    DEFAULT_MODE = 0o555
    DEFAULT_UID = 0
    DEFAULT_GID = 0

    def __init__(self, storage, root_tree):
        super(MartyFSHandler, self).__init__()
        self.storage = storage
        self.inodes = {}
        self.fd = {}
        self.inodes_index = itertools.count(llfuse.ROOT_INODE)
        self.fd_index = itertools.count()

        # First item registered will be the root tree
        self._register_item({'type': 'tree',
                             'tree': root_tree,
                             'mode': MartyFSHandler.DEFAULT_MODE,
                             'uid': MartyFSHandler.DEFAULT_UID,
                             'gid': MartyFSHandler.DEFAULT_GID})

    def _register_item(self, item):
        inode = next(self.inodes_index)

        if item.get('type') == 'tree' and 'ref' in item:
            item['tree'] = self.storage.get_tree(item['ref'])

        self.inodes[inode] = item

        return inode

    def _get_blob(self, item):
        return self.storage.get_blob(item['ref'])

    def getattr(self, inode, ctx=None):
        attrs = self.inodes.get(inode)
        if attrs is None:
            raise llfuse.FUSEError(errno.ENOENT)  # FIXME

        if attrs.get('type') == 'tree':
            mode_filetype = stat.S_IFDIR
        elif attrs.get('type') == 'blob':
            mode_filetype = stat.S_IFREG
        elif attrs.get('filetype') == 'link':
            mode_filetype = stat.S_IFLNK
        elif attrs.get('filetype') == 'fifo':
            mode_filetype = stat.S_IFIFO
        else:
            raise llfuse.FUSEError(errno.ENOENT)  # FIXME

        entry = llfuse.EntryAttributes()
        entry.st_mode = mode_filetype | attrs.get('mode', MartyFSHandler.DEFAULT_MODE)

        if attrs.get('type') == 'blob' and 'ref' in attrs:
            entry.st_size = self.storage.size(attrs['ref'])
        else:
            entry.st_size = 0

        stamp = int(1438467123.985654 * 1e9)
        entry.st_atime_ns = stamp
        entry.st_ctime_ns = stamp
        entry.st_mtime_ns = stamp
        entry.st_gid = 0
        entry.st_uid = 0
        entry.st_ino = inode

        return entry

    def lookup(self, parent_inode, name, ctx=None):
        attrs = self.inodes.get(parent_inode)
        if attrs is None:
            raise llfuse.FUSEError(errno.ENOENT)
        elif attrs['type'] != 'tree':
            raise llfuse.FUSEError(errno.ENOENT)
        elif name not in attrs['tree']:
            raise llfuse.FUSEError(errno.ENOENT)

        if 'inode' not in attrs['tree'][name]:
            inode = self._register_item(attrs['tree'][name])
            attrs['tree'][name]['inode'] = inode

        return self.getattr(attrs['tree'][name]['inode'])

    def opendir(self, inode, ctx):
        return inode

    def readdir(self, fh, offset):
        # fh is actually the inode number for directories
        attrs = self.inodes.get(fh)
        if attrs is None:
            raise llfuse.FUSEError(errno.ENOENT)
        elif attrs['type'] != 'tree':
            raise llfuse.FUSEError(errno.ENOENT)

        for i, (name, item) in enumerate(attrs['tree'].items()):
            if offset > i:
                continue

            if 'inode' not in item:
                inode = self._register_item(item)
                item['inode'] = inode

            yield (name, self.getattr(item['inode']), i + 1)

    def readlink(self, inode, ctx):
        attrs = self.inodes.get(inode)
        if 'link' not in attrs:
            raise llfuse.FUSEError(errno.ENOENT)

        return attrs['link']

    def open(self, inode, flags, ctx):
        attrs = self.inodes.get(inode)
        if attrs.get('type', None) != 'blob':
            raise llfuse.FUSEError(errno.ENOENT)

        fh = next(self.fd_index)
        self.fd[fh] = self._get_blob(attrs).to_file()

        return fh

    def read(self, fh, offset, size):
        fobj = self.fd[fh]
        fobj.seek(offset, os.SEEK_SET)
        return fobj.read(size)

    def release(self, fh):
        if fh in self.fd:
            self.fd[fh].close()
            del self.fd[fh]


class MartyFS(object):

    def __init__(self, storage, root_tree, mountpoint):
        self.storage = storage
        self.root_tree = root_tree
        self.mountpoint = mountpoint
        self.llfuse_worker = None

    def _llfuse_worker(self, fs, mountpoint, init_event):
        fuse_options = set(llfuse.default_options)
        fuse_options.add('fsname=marty')
        llfuse.init(fs, mountpoint, fuse_options)
        init_event.set()
        try:
            llfuse.main(workers=1)
        finally:
            llfuse.close()

    def mount(self):
        if self.llfuse_worker is None:
            marty_fs = MartyFSHandler(self.storage, self.root_tree)
            init_event = multiprocessing.Event()
            self.llfuse_worker = multiprocessing.Process(target=self._llfuse_worker,
                                                         args=(marty_fs, self.mountpoint, init_event))
            self.llfuse_worker.start()
            init_event.wait()
        else:
            raise RuntimeError('Filesystem already mounted')

    def umount(self):
        if self.llfuse_worker is not None:
            self.llfuse_worker.terminate()
            self.llfuse_worker.join()
        else:
            raise RuntimeError('Filesystem is not mounted')
