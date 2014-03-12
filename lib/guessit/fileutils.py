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

from guessit import s, u
import os.path
import zipfile
import io


def split_path(path):
    r"""Splits the given path into the list of folders and the filename (or the
    last folder if you gave it a folder path.

    If the given path was an absolute path, the first element will always be:
     - the '/' root folder on Unix systems
     - the drive letter on Windows systems (eg: r'C:\')
     - the mount point '\\' on Windows systems (eg: r'\\host\share')

    >>> s(split_path('/usr/bin/smewt'))
    ['/', 'usr', 'bin', 'smewt']

    >>> s(split_path('relative_path/to/my_folder/'))
    ['relative_path', 'to', 'my_folder']

    """
    result = []
    while True:
        head, tail = os.path.split(path)

        if not head and not tail:
            return result

        if not tail and head == path:
            # Make sure we won't have an infinite loop.
            result = [head] + result
            return result

        # we just split a directory ending with '/', so tail is empty
        if not tail:
            path = head
            continue

        # otherwise, add the last path fragment and keep splitting
        result = [tail] + result
        path = head


def file_in_same_dir(ref_file, desired_file):
    """Return the path for a file in the same dir as a given reference file.

    >>> s(file_in_same_dir('~/smewt/smewt.db', 'smewt.settings')) == os.path.normpath('~/smewt/smewt.settings')
    True

    """
    return os.path.join(*(split_path(ref_file)[:-1] + [desired_file]))


def load_file_in_same_dir(ref_file, filename):
    """Load a given file. Works even when the file is contained inside a zip."""
    path = split_path(ref_file)[:-1] + [filename]

    for i, p in enumerate(path):
        if p.endswith('.zip'):
            zfilename = os.path.join(*path[:i + 1])
            zfile = zipfile.ZipFile(zfilename)
            return zfile.read('/'.join(path[i + 1:]))

    return u(io.open(os.path.join(*path), encoding='utf-8').read())
