#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2013 Nicolas Wack <wackou@gmail.com>
# Copyright (c) 2013 Rémi Alvergnat <toilal.dev@gmail.com>
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

import re

from guessit import base_text_type

group_delimiters = ['()', '[]', '{}']

# separator character regexp
sep = r'[][,)(}:{+ /\._-]'  # regexp art, hehe :D

_dash = '-'
_psep = '[\W_]?'


def build_or_pattern(patterns):
    """Build a or pattern string from a list of possible patterns
    """
    or_pattern = ''
    for pattern in patterns:
        if not or_pattern:
            or_pattern += '(?:'
        else:
            or_pattern += '|'
        or_pattern += ('(?:%s)' % pattern)
    or_pattern += ')'
    return or_pattern


def compile_pattern(pattern, enhance=True):
    """Compile and enhance a pattern

    :param pattern: Pattern to compile (regexp).
    :type pattern: string

    :param pattern: Enhance pattern before compiling.
    :type pattern: string

    :return: The compiled pattern
    :rtype: regular expression object
    """
    return re.compile(enhance_pattern(pattern) if enhance else pattern, re.IGNORECASE)


def enhance_pattern(pattern):
    """Enhance pattern to match more equivalent values.

    '-' are replaced by '[\W_]?', which matches more types of separators (or none)

    :param pattern: Pattern to enhance (regexp).
    :type pattern: string

    :return: The enhanced pattern
    :rtype: string
    """
    return pattern.replace(_dash, _psep)
