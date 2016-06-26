from marty.commands import Command
from marty.operations.restore import restore
from marty.operations.objects import get_parent_tree


class Restore(Command):

    """ Restore a backup on the remote.
    """

    help = 'Restore a backup on the remote'

    def prepare(self):
        self._aparser.add_argument('remote')
        self._aparser.add_argument('name')
        self._aparser.add_argument('path', nargs='?', default='/')

    def run(self, args, config, storage, remotes):
        remote = remotes.get(args.remote)
        name = '%s/%s' % (args.remote, args.name)
        backup = storage.get_backup(name)
        tree = storage.get_tree(backup.root)
        tree, parent_path = get_parent_tree(storage, tree, args.path.encode('utf8'))
        restore(storage, remote, tree, parent_path)
