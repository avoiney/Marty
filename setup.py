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
                                       'scheduler = marty.commands.scheduler:Scheduler'],
                    'marty.storages': ['filesystem = marty.storages.filesystem:Filesystem'],
                    'marty.remotemethods': ['local = marty.remotemethods.local:Local',
                                            'ssh = marty.remotemethods.ssh:SSH']},
      install_requires=['confiture', 'paramiko', 'arrow', 'msgpack-python', 'humanize'])
