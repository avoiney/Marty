import os
import stat
import inspect

import paramiko
from confiture.schema.containers import Value
from confiture.schema.types import String

from marty.remotemethods import DefaultRemoteMethodSchema, RemoteMethod
from marty.datastructures import Tree, Blob


# Monkey-patch Paramiko in order to provide a listdir function that works
# with bytes instead of unicode strings:

def listdir_attr_b(self, path=b'.'):
    path = self._adjust_cwd(path)
    self._log(paramiko.common.DEBUG, 'listdir(%r)' % path)
    t, msg = self._request(paramiko.sftp.CMD_OPENDIR, path)
    if t != paramiko.sftp.CMD_HANDLE:
        raise paramiko.sftp.SFTPError('Expected handle')
    handle = msg.get_binary()
    filelist = []
    while True:
        try:
            t, msg = self._request(paramiko.sftp.CMD_READDIR, handle)
        except EOFError:
            # done with handle
            break
        if t != paramiko.sftp.CMD_NAME:
            raise paramiko.sftp.SFTPError('Expected name response')
        count = msg.get_int()
        for i in range(count):
            filename = msg.get_string()
            longname = msg.get_string()
            attr = paramiko.sftp_attr.SFTPAttributes._from_msg(msg, filename, longname)
            if (filename != b'.') and (filename != b'..'):
                filelist.append(attr)
    self._request(paramiko.sftp.CMD_CLOSE, handle)
    return filelist
paramiko.SFTPClient.listdir_attr_b = listdir_attr_b

# End of monkey-path

CHECKSUM_LOOP = 'sh -c \'while read filename; do sha1sum "$filename" || echo "failed"; done;\''


class SSHRemoteMethodSchema(DefaultRemoteMethodSchema):

    root = Value(String(), default='/')
    server = Value(String())
    login = Value(String(), default='root')
    password = Value(String())


class SSH(RemoteMethod):

    """ SSH remote.
    """

    config_schema = SSHRemoteMethodSchema()

    def initialize(self):
        self._ssh = paramiko.client.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
        self._ssh.connect(self.config.get('server'),
                          username=self.config.get('login'),
                          password=self.config.get('password'),
                          allow_agent=False,
                          compress=False,
                          look_for_keys=False)
        transport = self._ssh.get_transport()
        # transport.window_size = 2147483647
        # transport.packetizer.REKEY_BYTES = pow(2, 40)
        # transport.packetizer.REKEY_PACKETS = pow(2, 40)
        self._sftp = paramiko.SFTPClient.from_transport(transport)

        # Launch the checksum computing loop:
        self._checksum_stdin, self._checksum_stdout, _ = self._ssh.exec_command(CHECKSUM_LOOP)
        # Workaround because Paramiko open stdout as text mode and not binary:
        self._checksum_stdout._set_mode('rb')

    @property
    def root(self):
        return self.config.get('root').encode('utf-8')

    def get_tree(self, path):
        path = path.lstrip(os.sep.encode('utf-8'))
        directory = os.path.join(self.root, path)
        tree = Tree()
        directory_items = self._sftp.listdir_attr_b(directory)

        for fattr in directory_items:
            filename = fattr.filename
            item = {}
            if stat.S_ISREG(fattr.st_mode):
                item['type'] = 'blob'
                item['filetype'] = 'regular'
            elif stat.S_ISDIR(fattr.st_mode):
                item['type'] = 'tree'
                item['filetype'] = 'directory'
            elif stat.S_ISLNK(fattr.st_mode):
                item['filetype'] = 'link'
                item['link'] = self._sftp.readlink(os.path.join(directory, filename))
            elif stat.S_ISFIFO(fattr.st_mode):
                item['filetype'] = 'fifo'
            else:
                continue  # FIXME: Warn
            fmode = fattr.st_mode & (stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO | stat.S_ISVTX)

            item['uid'] = fattr.st_uid
            item['gid'] = fattr.st_gid
            item['mode'] = fmode
            item['mtime'] = int(fattr.st_mtime)
            item['size'] = fattr.st_size

            tree.add(filename, item)
        return tree

    def get_blob(self, path):
        path = path.lstrip(os.sep.encode('utf-8'))
        fullname = os.path.join(self.root, path)
        remote_file = self._sftp.open(fullname, 'r')
        # Call prefetch, backward compatibility between Paramiko <1.16 and 1.16+:
        if 'file_size' in inspect.signature(remote_file.prefetch).parameters:
            remote_file.prefetch(remote_file.stat().st_size)
        else:
            remote_file.prefetch()
        blob = Blob(blob=remote_file)
        return blob

    def checksum(self, path):
        path = path.lstrip(os.sep.encode('utf-8'))
        fullname = os.path.join(self.root, path)
        self._checksum_stdin.write(fullname + b'\n')
        output = self._checksum_stdout.readline().strip()

        if output == 'failed':
            return None
        else:
            return output.split(b' ', 1)[0].strip().decode()

    def newer(self, attr_new, attr_old):
        return attr_new.get('mtime', 0) != attr_old.get('mtime', 0)
