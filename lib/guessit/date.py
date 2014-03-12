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

import datetime
import re
import math


_dsep = r'[-/ \.]'
_date_rexps = [re.compile(
        # 20010823
        r'[^0-9]' +
        r'(?P<year>[0-9]{4})' +
        r'(?P<month>[0-9]{2})' +
        r'(?P<day>[0-9]{2})' +
        r'[^0-9]'),

        # 2001-08-23
        re.compile(r'[^0-9]' +
        r'(?P<year>[0-9]{4})' + _dsep +
        r'(?P<month>[0-9]{2})' + _dsep +
        r'(?P<day>[0-9]{2})' +
        r'[^0-9]'),

        # 23-08-2001
        re.compile(r'[^0-9]' +
        r'(?P<day>[0-9]{2})' + _dsep +
        r'(?P<month>[0-9]{2})' + _dsep +
        r'(?P<year>[0-9]{4})' +
        r'[^0-9]'),

        # 23-08-01
        re.compile(r'[^0-9]' +
        r'(?P<day>[0-9]{2})' + _dsep +
        r'(?P<month>[0-9]{2})' + _dsep +
        r'(?P<year>[0-9]{2})' +
        r'[^0-9]'),
        ]


def valid_year(year, today=None):
    """Check if number is a valid year"""
    if not today:
        today = datetime.date.today()
    return 1920 < year < today.year + 5


def search_year(string):
    """Looks for year patterns, and if found return the year and group span.

    Assumes there are sentinels at the beginning and end of the string that
    always allow matching a non-digit delimiting the date.

    Note this only looks for valid production years, that is between 1920
    and now + 5 years, so for instance 2000 would be returned as a valid
    year but 1492 would not.

    >>> search_year(' in the year 2000... ')
    (2000, (13, 17))

    >>> search_year(' they arrived in 1492. ')
    (None, None)
    """
    match = re.search(r'[^0-9]([0-9]{4})[^0-9]', string)
    if match:
        year = int(match.group(1))
        if valid_year(year):
            return (year, match.span(1))

    return (None, None)


def search_date(string):
    """Looks for date patterns, and if found return the date and group span.

    Assumes there are sentinels at the beginning and end of the string that
    always allow matching a non-digit delimiting the date.

    Year can be defined on two digit only. It will return the nearest possible
    date from today.

    >>> search_date(' This happened on 2002-04-22. ')
    (datetime.date(2002, 4, 22), (18, 28))

    >>> search_date(' And this on 17-06-1998. ')
    (datetime.date(1998, 6, 17), (13, 23))

    >>> search_date(' no date in here ')
    (None, None)
    """

    today = datetime.date.today()
    for drexp in _date_rexps:
        match = re.search(drexp, string)
        if match:
            d = match.groupdict()
            year, month, day = int(d['year']), int(d['month']), int(d['day'])
            # years specified as 2 digits should be adjusted here
            if year < 100:
                if year > (today.year % 100) + 5:
                    year = 1900 + year
                else:
                    year = 2000 + year

            date = None
            try:
                date = datetime.date(year, month, day)
            except ValueError:
                try:
                    date = datetime.date(year, day, month)
                except ValueError:
                    pass

            if date is None:
                continue

            # check date plausibility
            if not valid_year(date.year, today=today):
                continue

            # looks like we have a valid date
            # note: span is  [+1,-1] because we don't want to include the
            # non-digit char
            start, end = match.span()
            return (date, (start + 1, end - 1))

    return None, None
