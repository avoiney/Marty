from setuptools import setup, find_packages
import os

version = '1'

base = os.path.dirname(__file__)

setup(name='marty',
      version=version,
      description=('An efficient backup tool inspired by Git, saving your '
                   'bandwidth and providing global deduplication at file level.'),
      long_description=open(os.path.join(base, 'README.rst')).read(),
      classifiers=['Development Status :: 4 - Beta',
                   'License :: OSI Approved :: MIT License',
                   'Operating System :: OS Independent'],
      keywords='marty backup git deduplication',
      author='Antoine Millet',
      author_email='antoine@inaps.org',
      url='https://github.com/NaPs/Marty',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      scripts=['bin/marty'],
      entry_points={'marty.commands': ['backup = marty.commands.backup:Backup',
                                       'gc = marty.commands.gc:Gc',
                                       'show-tree = marty.commands.show:ShowTree',
                                       'show-backup = marty.commands.show:ShowBackup',
                                       'export = marty.commands.export:Export',
                                       'scheduler = marty.commands.scheduler:Scheduler',
                                       'remotes = marty.commands.remotes:Remotes',
                                       'list = marty.commands.list:List',
                                       'tree = marty.commands.show:RecursivelyShowTree',
                                       'restore = marty.commands.restore:Restore',
                                       'check = marty.commands.check:Check',
                                       'mount = marty.commands.mount:Mount',
                                       'explore = marty.commands.mount:Explore',
                                       'diff = marty.commands.diff:Diff'],
                    'marty.storages': ['filesystem = marty.storages.filesystem:Filesystem'],
                    'marty.remotemethods': ['local = marty.remotemethods.local:Local',
                                            'ssh = marty.remotemethods.ssh:SSH',
                                            'mikrotik = marty.remotemethods.ssh:Mikrotik']},
      install_requires=['confiture', 'paramiko', 'arrow', 'msgpack-python', 'humanize', 'llfuse'])
