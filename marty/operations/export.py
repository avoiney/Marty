import os
import tarfile
import shutil
import functools

import humanize

from marty.operations.objects import walk_tree
from marty.printer import printer


def export_tar(tree, storage, output, compression=None):
    """ Export a tree in tar format.
    """

    mode = 'w'

    if compression in ('gz', 'bz2', 'xz'):
        mode += ':' + compression

    with tarfile.open(output, mode) as tar:
        for fullname, item in walk_tree(storage, tree):
            payload = None
            info = tarfile.TarInfo()
            info.name = fullname.decode('utf-8', 'ignore')

            if item.type == 'blob':
                payload = storage.get_blob(item.ref).blob
                info.type = tarfile.REGTYPE
                info.size = item['size']
                printer.verbose('Adding to {out}: <b>{fn}</b> ({size})',
                                out=output,
                                fn=fullname.decode('utf-8', errors='ignore'),
                                size=humanize.naturalsize(item['size'], binary=True))
            elif item.type == 'tree':
                info.type = tarfile.DIRTYPE
                printer.verbose('Adding to {out}: <b>{fn}</b> (directory)',
                                out=output,
                                fn=fullname.decode('utf-8', errors='ignore'))
            else:
                if item['filetype'] == 'link':
                    info.type = tarfile.SYMTYPE
                    info.linkname = item['link']
                    printer.verbose('Adding to {out}: <b>{fn}</b> (link to {link})',
                                    out=output,
                                    fn=fullname.decode('utf-8', errors='ignore'),
                                    link=item['link'])

                elif item['filetype'] == 'fifo':
                    info.type = tarfile.FIFOTYPE
                    printer.verbose('Adding to {out}: <b>{fn}</b> (fifo)',
                                    out=output,
                                    fn=fullname.decode('utf-8', errors='ignore'))
                else:
                    continue  # Ignore unknown file types

            # Set optional attributes:
            info.mode = item.get('mode')
            info.uid = item.get('uid')
            info.gid = item.get('gid')
            info.mtime = item.get('mtime')

            # Add the item into the tar file:
            tar.addfile(info, payload)


def export_directory(tree, storage, output):
    """ Export a tree in a directory.
    """

    os.mkdir(output)

    for fullname, item in walk_tree(storage, tree):
        outfullname = os.path.join(output.encode('utf-8'), fullname.lstrip(b'/'))

        if item.type == 'blob':
            blob = storage.get_blob(item.ref).blob
            with open(outfullname, 'wb') as fout:
                shutil.copyfileobj(blob, fout)
            printer.verbose('Exporting to {out}: <b>{fn}</b> ({size})',
                            out=output,
                            fn=fullname.decode('utf-8', errors='replace'),
                            size=humanize.naturalsize(item['size'], binary=True))
        elif item.type == 'tree':
            os.mkdir(outfullname)
            printer.verbose('Exporting to {out}: <b>{fn}</b> (directory)',
                            out=output,
                            fn=fullname.decode('utf-8', errors='replace'))
        else:
            if item['filetype'] == 'link':
                os.symlink(item['link'], outfullname)
                printer.verbose('Exporting to {out}: <b>{fn}</b> (link to {link})',
                                out=output,
                                fn=fullname.decode('utf-8', errors='replace'),
                                link=item['link'])

            elif item['filetype'] == 'fifo':
                os.mkfifo(outfullname)
                printer.verbose('Exporting to {out}: <b>{fn}</b> (fifo)',
                                out=output,
                                fn=fullname.decode('utf-8', errors='replace'))
            else:
                continue  # Ignore unknown file types

        try:
            if 'mode' in item:
                try:
                    os.chmod(outfullname, item['mode'], follow_symlinks=False)
                except SystemError:
                    pass  # Workaround follow_symlinks not implemented in Python 3.5 (bug?)
            if 'uid' in item or 'gid' in item:
                os.chown(outfullname, item.get('uid', -1), item.get('gid', -1), follow_symlinks=False)
        except PermissionError:
            printer.p('<color fg=yellow><b>Warning:</b> unable to set attributes on {fn}</color>',
                      fn=fullname.decode('utf-8', errors='replace'))


EXPORT_FORMATS = {'tar': export_tar,
                  'targz': functools.partial(export_tar, compression='gz'),
                  'tarbz2': functools.partial(export_tar, compression='bz2'),
                  'tarxz': functools.partial(export_tar, compression='xz'),
                  'dir': export_directory}
