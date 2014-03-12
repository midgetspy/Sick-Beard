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
from guessit.country import Country
from guessit import Guess


class GuessCountry(Transformer):
    def __init__(self):
        Transformer.__init__(self, -170)
        # list of common words which could be interpreted as countries, but which
        # are far too common to be able to say they represent a country
        self.country_common_words = frozenset(['bt', 'bb'])

    def supported_properties(self):
        return ['country']

    def should_process(self, mtree, options=None):
        options = options or {}
        return 'nocountry' not in options.keys()

    def process(self, mtree, options=None):
        for node in mtree.unidentified_leaves():
            if len(node.node_idx) == 2:
                c = node.value[1:-1].lower()
                if c in self.country_common_words:
                    continue

                # only keep explicit groups (enclosed in parentheses/brackets)
                if not node.is_explicit():
                    continue

                try:
                    country = Country(c, strict=True)
                except ValueError:
                    continue

                node.guess = Guess(country=country, confidence=1.0, input=node.value, span=node.span)

    def post_process(self, mtree, options=None, *args, **kwargs):
        # if country is in the guessed properties, make it part of the series name
        series_leaves = mtree.leaves_containing('series')
        country_leaves = mtree.leaves_containing('country')

        if series_leaves and country_leaves:
            country_leaf = country_leaves[0]
            for serie_leaf in series_leaves:
                serie_leaf.guess['series'] += ' (%s)' % country_leaf.guess['country'].alpha2.upper()
            #result['series'] += ' (%s)' % result['country'].alpha2.upper()
