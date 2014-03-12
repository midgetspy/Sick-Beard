#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2013 Nicolas Wack <wackou@gmail.com>
#
# GuessIt is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# GuessIt is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import absolute_import, division, print_function, unicode_literals

import pkg_resources
from .__version__ import __version__

__all__ = ['Guess', 'Language',
           'guess_file_info', 'guess_video_info',
           'guess_movie_info', 'guess_episode_info']


# Do python3 detection before importing any other module, to be sure that
# it will then always be available
# with code from http://lucumr.pocoo.org/2011/1/22/forwards-compatible-python/
import sys
if sys.version_info[0] >= 3:  # pragma: no cover
    PY2, PY3 = False, True
    unicode_text_type = str
    native_text_type = str
    base_text_type = str

    def u(x):
        return str(x)

    def s(x):
        return x

    class UnicodeMixin(object):
        __str__ = lambda x: x.__unicode__()
    import binascii

    def to_hex(x):
        return binascii.hexlify(x).decode('utf-8')

else:   # pragma: no cover
    PY2, PY3 = True, False
    __all__ = [str(s) for s in __all__]  # fix imports for python2
    unicode_text_type = unicode
    native_text_type = str
    base_text_type = basestring

    def u(x):
        if isinstance(x, str):
            return x.decode('utf-8')
        if isinstance(x, list):
            return [u(s) for s in x]
        return unicode(x)

    def s(x):
        if isinstance(x, unicode):
            return x.encode('utf-8')
        if isinstance(x, list):
            return [s(y) for y in x]
        if isinstance(x, tuple):
            return tuple(s(y) for y in x)
        if isinstance(x, dict):
            return dict((s(key), s(value)) for key, value in x.items())
        return x

    class UnicodeMixin(object):
        __str__ = lambda x: unicode(x).encode('utf-8')

    def to_hex(x):
        return x.encode('hex')

    range = xrange


from guessit.guess import Guess, merge_all
from guessit.language import Language
from guessit.matcher import IterativeMatcher
from guessit.textutils import clean_string, is_camel, from_camel
import os.path
import logging
import json

log = logging.getLogger(__name__)


class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# let's be a nicely behaving library
h = NullHandler()
log.addHandler(h)


def _guess_filename(filename, options=None, **kwargs):
    mtree = _build_filename_mtree(filename, options=options, **kwargs)
    _add_camel_properties(mtree, options=options)
    return mtree.matched()


def _build_filename_mtree(filename, options=None, **kwargs):
    mtree = IterativeMatcher(filename, options=options, **kwargs)
    second_pass_options = mtree.second_pass_options
    if second_pass_options:
        log.info("Running 2nd pass")
        merged_options = dict(options)
        merged_options.update(second_pass_options)
        mtree = IterativeMatcher(filename, options=merged_options, **kwargs)
    return mtree


def _add_camel_properties(mtree, options=None, **kwargs):
    prop = 'title' if mtree.matched().get('type') != 'episode' else 'series'
    value = mtree.matched().get(prop)
    _guess_camel_string(mtree, value, options=options, skip_title=False, **kwargs)

    for leaf in mtree.match_tree.unidentified_leaves():
        value = leaf.value
        _guess_camel_string(mtree, value, options=options, skip_title=True, **kwargs)


def _guess_camel_string(mtree, string, options=None, skip_title=False, **kwargs):
    if string and is_camel(string):
        log.info('"%s" is camel cased. Try to detect more properties.' % (string,))
        uncameled_value = from_camel(string)
        camel_tree = _build_filename_mtree(uncameled_value, options=options, name_only=True, skip_title=skip_title, **kwargs)
        if len(camel_tree.matched()) > 0:
            # Title has changed.
            mtree.matched().update(camel_tree.matched())
            return True
    return False


def guess_file_info(filename, info=None, options=None, **kwargs):
    """info can contain the names of the various plugins, such as 'filename' to
    detect filename info, or 'hash_md5' to get the md5 hash of the file.

    >>> testfile = os.path.join(os.path.dirname(__file__), 'test/dummy.srt')
    >>> g = guess_file_info(testfile, info = ['hash_md5', 'hash_sha1'])
    >>> g['hash_md5'], g['hash_sha1']
    ('64de6b5893cac24456c46a935ef9c359', 'a703fc0fa4518080505809bf562c6fc6f7b3c98c')
    """
    info = info or 'filename'
    options = options or {}

    result = []
    hashers = []

    # Force unicode as soon as possible
    filename = u(filename)

    if isinstance(info, base_text_type):
        info = [info]

    for infotype in info:
        if infotype == 'filename':
            result.append(_guess_filename(filename, options, **kwargs))

        elif infotype == 'hash_mpc':
            from guessit.hash_mpc import hash_file
            try:
                result.append(Guess({infotype: hash_file(filename)},
                                    confidence=1.0))
            except Exception as e:
                log.warning('Could not compute MPC-style hash because: %s' % e)

        elif infotype == 'hash_ed2k':
            from guessit.hash_ed2k import hash_file
            try:
                result.append(Guess({infotype: hash_file(filename)},
                                    confidence=1.0))
            except Exception as e:
                log.warning('Could not compute ed2k hash because: %s' % e)

        elif infotype.startswith('hash_'):
            import hashlib
            hashname = infotype[5:]
            try:
                hasher = getattr(hashlib, hashname)()
                hashers.append((infotype, hasher))
            except AttributeError:
                log.warning('Could not compute %s hash because it is not available from python\'s hashlib module' % hashname)

        else:
            log.warning('Invalid infotype: %s' % infotype)

    # do all the hashes now, but on a single pass
    if hashers:
        try:
            blocksize = 8192
            hasherobjs = dict(hashers).values()

            with open(filename, 'rb') as f:
                chunk = f.read(blocksize)
                while chunk:
                    for hasher in hasherobjs:
                        hasher.update(chunk)
                    chunk = f.read(blocksize)

            for infotype, hasher in hashers:
                result.append(Guess({infotype: hasher.hexdigest()},
                                    confidence=1.0))
        except Exception as e:
            log.warning('Could not compute hash because: %s' % e)

    result = merge_all(result)

    return result


def guess_video_info(filename, info=None, options=None, **kwargs):
    return guess_file_info(filename, info=info, options=options, type='video', **kwargs)


def guess_movie_info(filename, info=None, options=None, **kwargs):
    return guess_file_info(filename, info=info, options=options, type='movie', **kwargs)


def guess_episode_info(filename, info=None, options=None, **kwargs):
    return guess_file_info(filename, info=info, options=options, type='episode', **kwargs)
