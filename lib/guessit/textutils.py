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

from guessit import s
from guessit.patterns import sep
import functools
import unicodedata
import re

# string-related functions


def normalize_unicode(s):
    return unicodedata.normalize('NFC', s)


def strip_brackets(s):
    if not s:
        return s

    if ((s[0] == '[' and s[-1] == ']') or
        (s[0] == '(' and s[-1] == ')') or
        (s[0] == '{' and s[-1] == '}')):
        return s[1:-1]

    return s


_dotted_rexp = re.compile(r'(?:\W|^)(([A-Za-z]\.){2,}[A-Za-z]\.?)')


def clean_string(st):
    for c in sep:
        # do not remove certain chars
        if c in ['-', ',']:
            continue

        if c == '.':
            # we should not remove the dots for acronyms and such
            dotted = _dotted_rexp.search(st)
            if dotted:
                s = dotted.group(1)
                exclude_begin, exclude_end = dotted.span(1)

                st = (st[:exclude_begin].replace(c, ' ') +
                      st[exclude_begin:exclude_end] +
                      st[exclude_end:].replace(c, ' '))
                continue

        st = st.replace(c, ' ')

    parts = st.split()
    result = ' '.join(p for p in parts if p != '')

    # now also remove dashes on the outer part of the string
    while result and result[0] in '-':
        result = result[1:]
    while result and result[-1] in '-':
        result = result[:-1]

    return result


_words_rexp = re.compile('\w+', re.UNICODE)


def find_words(s):
    return _words_rexp.findall(s.replace('_', ' '))


def reorder_title(title, articles=('the',), separators=(',', ', ')):
    ltitle = title.lower()
    for article in articles:
        for separator in separators:
            suffix = separator + article
            if ltitle[-len(suffix):] == suffix:
                return title[-len(suffix) + len(separator):] + ' ' + title[:-len(suffix)]
    return title


def str_replace(string, pos, c):
    return string[:pos] + c + string[pos + 1:]


def str_fill(string, region, c):
    start, end = region
    return string[:start] + c * (end - start) + string[end:]


def levenshtein(a, b):
    if not a:
        return len(b)
    if not b:
        return len(a)

    m = len(a)
    n = len(b)
    d = []
    for i in range(m + 1):
        d.append([0] * (n + 1))

    for i in range(m + 1):
        d[i][0] = i

    for j in range(n + 1):
        d[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                cost = 0
            else:
                cost = 1

            d[i][j] = min(d[i - 1][j] + 1,  # deletion
                          d[i][j - 1] + 1,  # insertion
                          d[i - 1][j - 1] + cost  # substitution
                          )

    return d[m][n]


# group-related functions

def find_first_level_groups_span(string, enclosing):
    """Return a list of pairs (start, end) for the groups delimited by the given
    enclosing characters.
    This does not return nested groups, ie: '(ab(c)(d))' will return a single group
    containing the whole string.

    >>> find_first_level_groups_span('abcd', '()')
    []

    >>> find_first_level_groups_span('abc(de)fgh', '()')
    [(3, 7)]

    >>> find_first_level_groups_span('(ab(c)(d))', '()')
    [(0, 10)]

    >>> find_first_level_groups_span('ab[c]de[f]gh(i)', '[]')
    [(2, 5), (7, 10)]
    """
    opening, closing = enclosing
    depth = []  # depth is a stack of indices where we opened a group
    result = []
    for i, c, in enumerate(string):
        if c == opening:
            depth.append(i)
        elif c == closing:
            try:
                start = depth.pop()
                end = i
                if not depth:
                    # we emptied our stack, so we have a 1st level group
                    result.append((start, end + 1))
            except IndexError:
                # we closed a group which was not opened before
                pass

    return result


def split_on_groups(string, groups):
    """Split the given string using the different known groups for boundaries.
    >>> s(split_on_groups('0123456789', [ (2, 4) ]))
    ['01', '23', '456789']

    >>> s(split_on_groups('0123456789', [ (2, 4), (4, 6) ]))
    ['01', '23', '45', '6789']

    >>> s(split_on_groups('0123456789', [ (5, 7), (2, 4) ]))
    ['01', '23', '4', '56', '789']

    """
    if not groups:
        return [string]

    boundaries = sorted(set(functools.reduce(lambda l, x: l + list(x), groups, [])))
    if boundaries[0] != 0:
        boundaries.insert(0, 0)
    if boundaries[-1] != len(string):
        boundaries.append(len(string))

    groups = [string[start:end] for start, end in zip(boundaries[:-1],
                                                       boundaries[1:])]

    return [g for g in groups if g]  # return only non-empty groups


def find_first_level_groups(string, enclosing, blank_sep=None):
    """Return a list of groups that could be split because of explicit grouping.
    The groups are delimited by the given enclosing characters.

    You can also specify if you want to blank the separator chars in the returned
    list of groups by specifying a character for it. None means it won't be replaced.

    This does not return nested groups, ie: '(ab(c)(d))' will return a single group
    containing the whole string.

    >>> s(find_first_level_groups('', '()'))
    ['']

    >>> s(find_first_level_groups('abcd', '()'))
    ['abcd']

    >>> s(find_first_level_groups('abc(de)fgh', '()'))
    ['abc', '(de)', 'fgh']

    >>> s(find_first_level_groups('(ab(c)(d))', '()', blank_sep = '_'))
    ['_ab(c)(d)_']

    >>> s(find_first_level_groups('ab[c]de[f]gh(i)', '[]'))
    ['ab', '[c]', 'de', '[f]', 'gh(i)']

    >>> s(find_first_level_groups('()[]()', '()', blank_sep = '-'))
    ['--', '[]', '--']

    """
    groups = find_first_level_groups_span(string, enclosing)
    if blank_sep:
        for start, end in groups:
            string = str_replace(string, start, blank_sep)
            string = str_replace(string, end - 1, blank_sep)

    return split_on_groups(string, groups)


_camel_word2_set = set(('is', 'to',))
_camel_word3_set = set(('the',))


def _camel_split_and_lower(string, i):
        """Retrieves a tuple (need_split, need_lower)

        need_split is True if this char is a first letter in a camelCasedString.
        need_lower is True if this char should be lowercased.
        """

        def islower(c):
            return c.isalpha() and not c.isupper()

        previous_char2 = string[i - 2] if i > 1 else None
        previous_char = string[i - 1] if i > 0 else None
        char = string[i]
        next_char = string[i + 1] if i + 1 < len(string) else None
        next_char2 = string[i + 2] if i + 2 < len(string) else None

        char_upper = char.isupper()
        char_lower = islower(char)

        # previous_char2_lower = islower(previous_char2) if previous_char2 else False
        previous_char2_upper = previous_char2.isupper() if previous_char2 else False

        previous_char_lower = islower(previous_char) if previous_char else False
        previous_char_upper = previous_char.isupper() if previous_char else False

        next_char_upper = next_char.isupper() if next_char else False
        next_char_lower = islower(next_char) if next_char else False

        next_char2_upper = next_char2.isupper() if next_char2 else False
        # next_char2_lower = islower(next_char2) if next_char2 else False

        mixedcase_word = (previous_char_upper and char_lower and next_char_upper) or \
                        (previous_char_lower and char_upper and next_char_lower and next_char2_upper) or \
                        (previous_char2_upper and previous_char_lower and char_upper)
        if mixedcase_word:
            word2 = (char + next_char).lower() if next_char else None
            word3 = (char + next_char + next_char2).lower() if next_char and next_char2 else None
            word2b = (previous_char2 + previous_char).lower() if previous_char2 and previous_char else None
            if word2 in _camel_word2_set or word2b in _camel_word2_set or word3 in _camel_word3_set:
                mixedcase_word = False

        uppercase_word = previous_char_upper and char_upper and next_char_upper or (char_upper and next_char_upper and next_char2_upper)

        need_split = char_upper and previous_char_lower and not mixedcase_word

        if not need_split:
            previous_char_upper = string[i - 1].isupper() if i > 0 else False
            next_char_lower = (string[i + 1].isalpha() and not string[i + 1].isupper()) if i + 1 < len(string) else False
            need_split = char_upper and previous_char_upper and next_char_lower
            uppercase_word = previous_char_upper and not next_char_lower

        need_lower = not uppercase_word and not mixedcase_word and need_split

        return (need_split, need_lower)


def is_camel(string):
    """
    >>> is_camel('dogEATDog')
    True
    >>> is_camel('DeathToCamelCase')
    True
    >>> is_camel('death_to_camel_case')
    False
    >>> is_camel('TheBest')
    True
    >>> is_camel('The Best')
    False
    """
    for i in range(0, len(string)):
        need_split, _ = _camel_split_and_lower(string, i)
        if need_split:
            return True
    return False


def from_camel(string):
    """
    >>> from_camel('dogEATDog') == 'dog EAT dog'
    True
    >>> from_camel('DeathToCamelCase') == 'Death to camel case'
    True
    >>> from_camel('TheBest') == 'The best'
    True
    >>> from_camel('MiXedCaSe is not camelCase') == 'MiXedCaSe is not camel case'
    True
    """
    if not string:
        return string
    pieces = []

    for i in range(0, len(string)):
        char = string[i]
        need_split, need_lower = _camel_split_and_lower(string, i)
        if need_split:
            pieces.append(' ')

        if need_lower:
            pieces.append(char.lower())
        else:
            pieces.append(char)
    return ''.join(pieces)
