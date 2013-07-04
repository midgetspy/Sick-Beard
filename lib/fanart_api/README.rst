=================================
Python interface to fanart.tv API
=================================

.. image:: https://api.travis-ci.org/z4r/python-fanart.png?branch=master
   :target: http://travis-ci.org/z4r/python-fanart

.. image:: https://coveralls.io/repos/z4r/python-fanart/badge.png?branch=master
    :target: https://coveralls.io/r/z4r/python-fanart
    
.. image:: https://pypip.in/v/python-fanart/badge.png
   :target: https://crate.io/packages/python-fanart/

.. image:: https://pypip.in/d/python-fanart/badge.png
   :target: https://crate.io/packages/python-fanart/

This package provides a module to interface with the `fanart.tv`_ API.

.. contents::
    :local:

.. _installation:

Installation
============
Using pip::

    $ pip install git+https://github.com/z4r/python-fanart

.. _summary:

FANART API Summary
==================

Low Level
---------

::

    from fanart.core import Request
    import fanart
    request = Request(
        apikey = '<YOURAPIKEY>',
        id = '24e1b53c-3085-4581-8472-0b0088d2508c',
        ws = fanart.WS.MUSIC,
        type = fanart.TYPE.ALL,
        sort = fanart.SORT.POPULAR,
        limit = fanart.LIMIT.ALL,
    )
    print request.response()


Music
-----

::

    import os
    os.environ.setdefault('FANART_APIKEY', '<YOURAPIKEY>')
    import requests

    from fanart.music import Artist

    artist = Artist.get(id = '24e1b53c-3085-4581-8472-0b0088d2508c')
    print artist.name
    print artist.mbid
    for album in artist.albums:
        for cover in album.covers:
            print 'Saving: %s' % cover
            _, ext = os.path.splitext(cover.url)
            filepath = os.path.join(path, '%d%s' % (cover.id, ext))
            with open(filepath, 'wb') as fp:
                fp.write(cover.content())

Movie
-----

::

    import os
    os.environ.setdefault('FANART_APIKEY', '<YOURAPIKEY>')

    from fanart.movie import Movie

    movie = Movie.get(id = '70160')


TV Shows
--------

::

    import os
    os.environ.setdefault('FANART_APIKEY', '<YOURAPIKEY>')

    from fanart.tv import TvShow

    tvshow = TvShow.get(id = '80379')

.. _license:

License
=======

This software is licensed under the ``Apache License 2.0``. See the ``LICENSE``
file in the top distribution directory for the full license text.

.. _references:

References
==========
* `fanart.tv`_

.. _fanart.tv: http://fanart.tv/
