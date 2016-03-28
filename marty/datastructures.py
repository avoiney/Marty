import io
from collections import Counter

import humanize
import arrow
import msgpack


class MartyObjectDecodeError(RuntimeError):

    """ Error occuring when Marty object unserialization fails.
    """


class MartyObject(object):

    """ Base class for objects in a Marty store.
    """

    @classmethod
    def from_file(cls, fileobj):
        """ Instanciate the object according to provided file object.
        """
        raise NotImplementedError('from_file not implemented')

    def to_file(self):
        """ Return a file object representing the object.
        """
        raise NotImplementedError('to_file not implemented')


class Blob(MartyObject):

    """ A blob (Binary Large Object).

    This is basically a wrapper around the object file.
    """

    def __init__(self, blob=None):
        self.blob = blob

    @classmethod
    def from_file(cls, fileobj):
        blob = cls()
        blob.blob = fileobj
        return blob

    def to_file(self):
        return self.blob


class MsgPackMartyObject(MartyObject):

    """ Base class for Marty objects using MsgPack as serialization format.
    """

    @staticmethod
    def msgpack_encoder(value):
        """ Encoder used by msgpack serializer when an object is unknown.

        This hook is basically used to serialize dates in Arrow objects.
        """
        if isinstance(value, arrow.Arrow):
            value = msgpack.ExtType(1, value.isoformat().encode())
        return value

    @staticmethod
    def msgpack_ext_decoder(code, data):
        """ Decoded used by msgpack deserializer when an ext type is found.

        This hook is basically used to deserialize dates in Arrow objects.
        """
        if code == 1:
            try:
                return arrow.get(data.decode())
            except arrow.parser.ParserError:
                return arrow.Arrow.strptime(data.decode(), '%Y%m%dT%H:%M:%S.%f')
        return msgpack.ExtType(code, data)

    @classmethod
    def from_file(cls, fileobj):
        obj = cls()
        try:
            parsed = msgpack.unpackb(fileobj.read(), encoding='utf8', ext_hook=cls.msgpack_ext_decoder)
        except Exception:
            raise MartyObjectDecodeError('Error while unpacking msgpack object')
        try:
            obj.from_msgpack(parsed)
        except Exception:
            raise MartyObjectDecodeError('Error while reading msgpack object')
        return obj

    def to_file(self):
        return io.BytesIO(msgpack.packb(self.to_msgpack(), use_bin_type=True, default=self.msgpack_encoder))


class TreeItem(dict):

    """ A simple shortcut around a dict object to handle Tree item dicts.
    """

    @property
    def type(self):
        return self.get('type')

    @property
    def ref(self):
        return self.get('ref')

    @ref.setter
    def ref(self, value):
        self['ref'] = value


class Tree(MsgPackMartyObject):

    """ A tree.

    A list of items which can reference other Marty objects.
    """

    def __init__(self, items=None):
        if items is None:
            self._items = {}
        else:
            self._items = items

    def __contains__(self, name):
        return name in self._items

    def __getitem__(self, key):
        return self._items[key]

    def names(self):
        """ Returns sorted names of items.
        """
        return sorted(self._items.keys())

    def items(self):
        """ Returns a sorted pair of (name, details) of items.
        """
        return sorted(self._items.items(), key=lambda x: x[0])

    def from_msgpack(self, parsed):
        self._items = {k: TreeItem(v) for k, v in parsed}

    def to_msgpack(self):
        # Sort all dict and transform them into list in order to get
        # a distinguished output (same item list always produce the exact
        # same output once serialized).
        items = []
        for name, item in sorted(self._items.items(), key=lambda x: x[0]):
            item = list(sorted(item.items()))
            items.append((name, item))

        return items

    def add(self, name, details):
        """ Add a new item in Tree.
        """
        self._items[name] = TreeItem(details)

    def discard(self, name):
        """ Discard an item from the Tree.
        """
        try:
            del self._items[name]
        except KeyError:
            pass


def _size(*values):
    """ Print summed size humanized.
    """
    value = sum(values)
    return humanize.naturalsize(value, binary=True) if value else '-'


def _count(*values):
    """ Print summed count humanized.
    """
    value = sum(values)
    return str(value) if value else '-'


class Backup(MsgPackMartyObject):

    """ A backup.

    Represents a backup with its attributes, statistics and error log.
    """

    def __init__(self, root=None, parent=None, stats=None, errors=None, start_date=None, end_date=None):
        self.root = root
        self.parent = parent
        self.stats = stats if stats is not None else Counter()
        self.errors = errors if errors is not None else {}
        self.start_date = start_date
        self.end_date = end_date

    def __enter__(self):
        self.start()

    def __exit__(self, type, value, traceback):
        self.end()

    @property
    def duration(self):
        return self.end_date - self.start_date

    def start(self):
        """ Set the start date of backup to now.
        """
        self.start_date = arrow.now()

    def end(self):
        """ Set the end date of backup to now.
        """
        self.end_date = arrow.now()

    def from_msgpack(self, parsed):
        self.root = parsed['root']
        self.parent = parsed['parent']
        self.stats = parsed['stats']
        self.errors = parsed['errors']
        self.start_date = parsed['start_date']
        self.end_date = parsed['end_date']

    def to_msgpack(self):
        return {'root': self.root,
                'parent': self.parent,
                'stats': self.stats,
                'errors': self.errors,
                'start_date': self.start_date,
                'end_date': self.end_date}

    def stats_table(self):
        """ Export a statistics table of the Backup.

        Output is basically displayed using printer.table.
        """
        table = [('',
                  '<b>blob</b>',
                  '<b>tree</b>',
                  '<b>total</b>'),
                 ('<b>New objects</b>',
                  _count(self.stats.get('new-blob', 0)),
                  _count(self.stats.get('new-tree', 0)),
                  _count(self.stats.get('new-blob', 0),
                         self.stats.get('new-tree', 0))),
                 ('<b>Data size</b>',
                  _size(self.stats.get('new-blob-size', 0)),
                  _size(self.stats.get('new-tree-size', 0)),
                  _size(self.stats.get('new-blob-size', 0),
                        self.stats.get('new-tree-size', 0))),
                 ('<b>Stored size</b>',
                  _size(self.stats.get('new-blob-stored-size', 0)),
                  _size(self.stats.get('new-tree-stored-size', 0)),
                  _size(self.stats.get('new-blob-stored-size', 0),
                        self.stats.get('new-tree-stored-size', 0))),
                 ('',) * 4,
                 ('<b>Reused objects</b>',
                  _count(self.stats.get('reused-blob', 0)),
                  _count(self.stats.get('reused-tree', 0)),
                  _count(self.stats.get('reused-blob', 0),
                         self.stats.get('reused-tree', 0))),
                 ('<b>Reused size</b>',
                  _size(self.stats.get('reused-blob-size', 0)),
                  _size(self.stats.get('reused-tree-size', 0)),
                  _size(self.stats.get('reused-blob-size', 0),
                        self.stats.get('reused-tree-size', 0))),
                 ('',) * 4,
                 ('<b>Skipped</b>',
                  _count(self.stats.get('skipped-blob', 0)),
                  '-',
                  _count(self.stats.get('skipped-blob', 0))),
                 ('<b>Skipped size</b>',
                  _size(self.stats.get('skipped-blob-size', 0)),
                  '-',
                  _size(self.stats.get('skipped-blob-size', 0))),
                 ('',) * 4,
                 ('<b>Total</b>',
                  _count(self.stats.get('new-blob', 0),
                         self.stats.get('reused-blob', 0),
                         self.stats.get('skipped-blob', 0)),
                  _count(self.stats.get('new-tree', 0),
                         self.stats.get('reused-tree', 0)),
                  _count(self.stats.get('new-blob', 0),
                         self.stats.get('reused-blob', 0),
                         self.stats.get('skipped-blob', 0),
                         self.stats.get('new-tree', 0),
                         self.stats.get('reused-tree', 0))),
                 ('<b>Total size</b>',
                  _size(self.stats.get('new-blob-size', 0),
                        self.stats.get('reused-blob-size', 0),
                        self.stats.get('skipped-blob-size', 0)),
                  _size(self.stats.get('new-tree-size', 0),
                        self.stats.get('reused-tree-size', 0)),
                  _size(self.stats.get('new-blob-size', 0),
                        self.stats.get('reused-blob-size', 0),
                        self.stats.get('skipped-blob-size', 0),
                        self.stats.get('new-tree-size', 0),
                        self.stats.get('reused-tree-size', 0)))]
        return table
