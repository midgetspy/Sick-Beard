#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
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

digital_numeral = '\d{1,3}'

roman_numeral = "(?=[MCDLXVI]+)M{0,4}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})"

english_word_numeral_list = [
  'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
  'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty'
]

french_word_numeral_list = [
  'zéro', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf', 'dix',
  'onze', 'douze', 'treize', 'quatorze', 'quinze', 'seize', 'dix-sept', 'dix-huit', 'dix-neuf', 'vingt'
]

french_alt_word_numeral_list = [
  'zero', 'une', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf', 'dix',
  'onze', 'douze', 'treize', 'quatorze', 'quinze', 'seize', 'dixsept', 'dixhuit', 'dixneuf', 'vingt'
]


def __build_word_numeral(*args, **kwargs):
    re = None
    for word_list in args:
        for word in word_list:
            if not re:
                re = '(?:(?=\w+)'
            else:
                re += '|'
            re += word
    re += ')'
    return re

word_numeral = __build_word_numeral(english_word_numeral_list, french_word_numeral_list, french_alt_word_numeral_list)

numeral = '(?:' + digital_numeral + '|' + roman_numeral + '|' + word_numeral + ')'

__romanNumeralMap = (
                   ('M', 1000),
                   ('CM', 900),
                   ('D', 500),
                   ('CD', 400),
                   ('C', 100),
                   ('XC', 90),
                   ('L', 50),
                   ('XL', 40),
                   ('X', 10),
                   ('IX', 9),
                   ('V', 5),
                   ('IV', 4),
                   ('I', 1)
                   )

__romanNumeralPattern = re.compile('^' + roman_numeral + '$')


def __parse_roman(value):
    """convert Roman numeral to integer"""
    if not __romanNumeralPattern.search(value):
        raise ValueError('Invalid Roman numeral: %s' % value)

    result = 0
    index = 0
    for numeral, integer in __romanNumeralMap:
        while value[index:index + len(numeral)] == numeral:
            result += integer
            index += len(numeral)
    return result


def __parse_word(value):
    """Convert Word numeral to integer"""
    for word_list in [english_word_numeral_list, french_word_numeral_list, french_alt_word_numeral_list]:
        try:
            return word_list.index(value)
        except ValueError:
            pass
    raise ValueError


_clean_re = re.compile('[^\d]*(\d+)[^\d]*')


def parse_numeral(value, int_enabled=True, roman_enabled=True, word_enabled=True, clean=True):
    """Parse a numeric value into integer.

    input can be an integer as a string, a roman numeral or a word

    :param value: Value to parse. Can be an integer, roman numeral or word.
    :type value: string

    :return: Numeric value, or None if value can't be parsed
    :rtype: int
    """
    if int_enabled:
        try:
            if clean:
                match = _clean_re.match(value)
                if match:
                    clean_value = match.group(1)
                    return int(clean_value)
            return int(value)
        except ValueError:
            pass
    if roman_enabled:
        try:
            if clean:
                for word in value.split():
                    try:
                        return __parse_roman(word)
                    except ValueError:
                        pass
            return __parse_roman(value)
        except ValueError:
            pass
    if word_enabled:
        try:
            if clean:
                for word in value.split():
                    try:
                        return __parse_word(word)
                    except ValueError:
                        pass
            return __parse_word(value)
        except ValueError:
            pass
    raise ValueError('Invalid numeral: ' + value)
