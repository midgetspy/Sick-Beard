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
from guessit.patterns import sep
from guessit.containers import PropertiesContainer
from guessit.patterns.numeral import numeral, parse_numeral
from guessit.date import valid_year


class GuessWeakEpisodesRexps(Transformer):
    def __init__(self):
        Transformer.__init__(self, 15)

        self.properties = PropertiesContainer(enhance=False, canonical_from_pattern=False)

        def _formater(episodeNumber):
            epnum = parse_numeral(episodeNumber)
            if not valid_year(epnum):
                if epnum > 100:
                    season, epnum = epnum // 100, epnum % 100
                    # episodes which have a season > 50 are most likely errors
                    # (Simpson is at 25!)
                    if season > 50:
                        return None
                    return {'season': season, 'episodeNumber': epnum}
                else:
                    return epnum

        self.properties.register_property(['episodeNumber', 'season'], '[0-9]{2,4}', confidence=0.6, formatter=_formater)
        self.properties.register_property('episodeNumber', '(?:episode)' + sep + '(' + numeral + ')[^0-9]', confidence=0.3)

    def supported_properties(self):
        return self.properties.get_supported_properties()

    def guess_weak_episodes_rexps(self, string, node=None, options=None):
        if node and 'episodeNumber' in node.root.info:
            return None

        properties = self.properties.find_properties(string, node)
        guess = self.properties.as_guess(properties, string)

        return guess

    def should_process(self, mtree, options=None):
        return mtree.guess.get('type', '').startswith('episode')

    def process(self, mtree, options=None):
        GuessFinder(self.guess_weak_episodes_rexps, 0.6, self.log, options).process_nodes(mtree.unidentified_leaves())
