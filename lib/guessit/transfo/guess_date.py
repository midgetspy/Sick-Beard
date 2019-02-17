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

from guessit.plugins.transformers import Transformer
from guessit.matcher import GuessFinder
from guessit.date import search_date


class GuessDate(Transformer):
    def __init__(self):
        Transformer.__init__(self, 50)

    def supported_properties(self):
        return ['date']

    def guess_date(self, string, node=None, options=None):
        date, span = search_date(string)
        if date:
            return {'date': date}, span
        else:
            return None, None

    def process(self, mtree, options=None):
        GuessFinder(self.guess_date, 1.0, self.log, options).process_nodes(mtree.unidentified_leaves())
