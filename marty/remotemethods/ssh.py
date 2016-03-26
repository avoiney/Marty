import os
import stat
import inspect

import paramiko
from confiture.schema.containers import Value
from confiture.schema.types import String, Boolean

from marty.remotemethods import DefaultRemoteMethodSchema, RemoteMethod, RemoteOperationError
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


class BaseSSHRemoteMethodSchema(DefaultRemoteMethodSchema):

    server = Value(String(), default=None)
    login = Value(String(), default='root')
    password = Value(String(), default=None)
    ssh_key = Value(String(), default=None)
    enable_ssh_agent = Value(Boolean(), default=True)
    enable_user_ssh_key = Value(Boolean(), default=True)
    enable_compression = Value(Boolean(), default=False)


class BaseSSH(RemoteMethod):

    """ Base class for SSH remote.
    """

    config_schema = BaseSSHRemoteMethodSchema()

    def initialize(self):
        self._ssh = paramiko.client.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
        server = self.config.get('server')
        if server is None:
            server = self.name
        try:
            self._ssh.connect(server,
                              username=self.config.get('login'),
                              password=self.config.get('password'),
                              allow_agent=self.config.get('enable_ssh_agent'),
                              key_filename=self.config.get('ssh_key'),
                              look_for_keys=self.config.get('enable_user_ssh_key'),
                              compress=self.config.get('enable_compression'))
        except paramiko.ssh_exception.SSHException as err:
            raise RemoteOperationError('SSH: %s' % err)

    def shutdown(self):
        self._ssh.close()


class SSHRemoteMethodSchema(BaseSSHRemoteMethodSchema):

    root = Value(String(), default='/')


class SSH(BaseSSH):

    """ SSH remote.
    """

    config_schema = SSHRemoteMethodSchema()

    def initialize(self):
        super().initialize()
        self._sftp = self._ssh.open_sftp()

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


class MikrotikLogin(String):

    def validate(self, value):
        return value + '+e'


class MikorikRemoteMethodSchema(BaseSSHRemoteMethodSchema):

    login = Value(MikrotikLogin(), default='admin+e')


class Mikrotik(BaseSSH):

    """ Mikrotik through SSH remote.
    """

    MikorikRemoteMethodSchema = SSHRemoteMethodSchema()

    def get_tree(self, path):
        tree = Tree()
        tree.add(b'export', {'type': 'blob'})
        return tree

    def get_blob(self, path):
        if path == b'/export':
            stdin, stdout, stderr = self._ssh.exec_command('/export')
            stdout.readline()  # Skip the first line containing a timestamp
            return Blob(blob=stdout)

    def checksum(self, path):
        return None

    def newer(self, attr_new, attr_old):
        return False
