Marty
=====

An efficient backup tool inspired by Git, saving your bandwidth and providing
global deduplication at file level.


Legal
-----

Marty is released under MIT license, copyright 2016 Antoine Millet.


Contribute
----------

You can send your pull-request for Marty through Github:

    https://github.com/NaPs/Marty

I also accept well formatted git patches sent by email.

Feel free to contact me for any question/suggestion/patch: <antoine@inaps.org>.


Tutorial
--------

This tutorial is a quick introduction guide to Marty. We will install it, make
a few backups and restore a backup.

Installation
^^^^^^^^^^^^

Marty depends on:

- confiture
- paramiko
- arrow
- msgpack-python
- humanize

Marty can be installed via setuptools with the following command: ::

    python setup.py install


Configuration
^^^^^^^^^^^^^

By default Marty will look for its configuration at: ::

    /etc/marty.conf

But you can also put your configuration anywhere else and pass it in the
command line: ::

    marty -c /path/to/configuration.conf command

We will start with a simple configuration as example: ::

    storage {
        type = 'filesystem'
        location = '/tmp/marty'
    }

    scheduler {
    }

    remotes {
        remote 'photos' {
            method = 'local'
            root = '/tmp/photos'
        }
    }

The ``storage`` section tells Marty to store backups in the ``/tmp/marty`` folder
of the local ``filesystem``.

The ``scheduler`` section won't be covered in this tutorial.

The ``remotes`` section specifies what is to be backed up. Here we have only one item
which is a local directory. We could also add a remote SSH directory with the
'ssh' method.


Work with backups
^^^^^^^^^^^^^^^^^

First we can list all available backups: ::

    $ marty list
     NAME START DATE DURATION

    Flags: P have parent, E - have errors, O orphan backup

Unsurprisingly, none is available. Let's make one: ::

    $ marty backup photos
    Duration: 0:00:00.035775
    Root: 4febe17fd4ae2ff867263fcc4c6f1c625fd67ec9

    $ marty list
     NAME                       START DATE          DURATION
     photos/2016-06-14_13-00-22 14/06/2016 13:00:22 0:00:00.035775
     photos/latest              14/06/2016 13:00:22 0:00:00.035775

We have now 2 backups, one is named by the creation time and date. The other is
an automatic reference to the latest created backup for the given ``remote``.

We can also specify our own names: ::

    $ marty backup photos wonderful_day
    Duration: 0:00:00.017411
    Root: a2b17b0770d40f61cf5aa6c6f6bb7235ded777e5

    $ marty list
     NAME                       START DATE          DURATION
     photos/2016-06-14_13-00-22 14/06/2016 13:00:22 0:00:00.035775
     photos/latest              14/06/2016 13:02:32 0:00:00.017411
     photos/wonderful_day       14/06/2016 13:02:32 0:00:00.017411

    Flags: P have parent, E - have errors, O orphan backup

Let's look at what is inside one of the backups: ::

    $ marty show-tree photos/latest
    NAME                  TYPE REF                                      ATTRIBUTES
    chat1.jpg             blob 0e51cbfaa58ec7dd483bb20067f42aa07557d846 filetype:regular mode:420 uid:1000 gid:1000 atime:1465902022 mtime:1465901781 ctime:1465901802 size:37454
    chat2.jpg             blob d9002fc8a485f8879819a4b53ca8691bff6d9a19 filetype:regular mode:420 uid:1000 gid:1000 atime:1465902022 mtime:1465901781 ctime:1465901805 size:98886
    poney_aquatique_1.jpg blob 5fb45355be5c176b1d0a72e75581e907bd3b7355 filetype:regular mode:420 uid:1000 gid:1000 atime:1465902022 mtime:1465901781 ctime:1465901862 size:117070
    poney_aquatique_2.jpg blob aaea807913df7fec4b55670f5a98e6a147214dc3 filetype:regular mode:420 uid:1000 gid:1000 atime:1465902022 mtime:1465901781 ctime:1465901858 size:94474
    poney_aquatique_3.jpg blob c5278b8f36faa0acdae191348f38b9f4d0e0368a filetype:regular mode:420 uid:1000 gid:1000 atime:1465902022 mtime:1465901781 ctime:1465901867 size:6749184

We can now restore a backup on an arbitrary folder: ::

    $ marty export photos/latest /tmp/restore/

    $ ls /tmp/restore
    chat1.jpg  chat2.jpg  poney_aquatique_1.jpg  poney_aquatique_2.jpg  poney_aquatique_3.jpg

Or we can create a tarball with a given backup: ::

    $ marty export -f tarbz2 photos/latest backup.tar.bz2

    $ tar jtvf backup.tar.bz2
    -rw-r--r-- 1000/1000     37454 2016-06-14 12:56 /chat1.jpg
    -rw-r--r-- 1000/1000     98886 2016-06-14 12:56 /chat2.jpg
    -rw-r--r-- 1000/1000        37 2016-06-14 13:12 /notes.txt
    -rw-r--r-- 1000/1000    117070 2016-06-14 12:56 /poney_aquatique_1.jpg
    -rw-r--r-- 1000/1000     94474 2016-06-14 12:56 /poney_aquatique_2.jpg
    -rw-r--r-- 1000/1000   6749184 2016-06-14 12:56 /poney_aquatique_3.jpg
