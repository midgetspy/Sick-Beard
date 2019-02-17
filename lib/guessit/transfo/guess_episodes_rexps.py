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
from guessit.containers import PropertiesContainer, WeakValidator, NoValidator
from guessit.patterns.numeral import numeral, digital_numeral, parse_numeral
from re import split as re_split


class GuessEpisodesRexps(Transformer):
    def __init__(self):
        Transformer.__init__(self, 20)

        self.container = PropertiesContainer(enhance=False, canonical_from_pattern=False)

        def episode_parser(value):
            values = re_split('[a-zA-Z]', value)
            values = [x for x in values if x]
            ret = []
            for letters_elt in values:
                dashed_values = letters_elt.split('-')
                dashed_values = [x for x in dashed_values if x]
                if len(dashed_values) > 1:
                    for _ in range(0, len(dashed_values) - 1):
                        start_dash_ep = parse_numeral(dashed_values[0])
                        end_dash_ep = parse_numeral(dashed_values[1])
                        for dash_ep in range(start_dash_ep, end_dash_ep + 1):
                            ret.append(dash_ep)
                else:
                    ret.append(parse_numeral(letters_elt))
            if len(ret) > 1:
                return {None: ret[0], 'episodeList': ret}  # TODO: Should support seasonList also
            elif len(ret) > 0:
                return ret[0]
            else:
                return None

        self.container.register_property(None, r'((?:season|saison)' + sep + '?(?P<season>' + numeral + '))', confidence=1.0, formatter=parse_numeral)
        self.container.register_property(None, r'(s(?P<season>' + digital_numeral + ')[^0-9]?' + sep + '?(?P<episodeNumber>(?:e' + digital_numeral + '(?:' + sep + '?[e-]' + digital_numeral + ')*)))[^0-9]', confidence=1.0, formatter={None: parse_numeral, 'episodeNumber': episode_parser}, validator=NoValidator())
        self.container.register_property(None, r'[^0-9]((?P<season>' + digital_numeral + ')[^0-9 .-]?-?(?P<episodeNumber>(?:x' + digital_numeral + '(?:' + sep + '?[x-]' + digital_numeral + ')*)))[^0-9]', confidence=1.0, formatter={None: parse_numeral, 'episodeNumber': episode_parser})
        self.container.register_property(None, r'(s(?P<season>' + digital_numeral + '))[^0-9]', confidence=0.6, formatter=parse_numeral, validator=NoValidator())
        self.container.register_property(None, r'((?P<episodeNumber>' + digital_numeral + ')v[23])', confidence=0.6, formatter=parse_numeral)
        self.container.register_property(None, r'((?:ep)' + sep + r'(?P<episodeNumber>' + numeral + '))[^0-9]', confidence=0.7, formatter=parse_numeral)
        self.container.register_property(None, r'(e(?P<episodeNumber>' + digital_numeral + '))', confidence=0.6, formatter=parse_numeral)

        self.container.register_canonical_properties('other', 'FiNAL', 'Complete', validator=WeakValidator())

    def supported_properties(self):
        return ['episodeNumber', 'season']

    def guess_episodes_rexps(self, string, node=None, options=None):
        found = self.container.find_properties(string, node)
        return self.container.as_guess(found, string)

    def should_process(self, mtree, options=None):
        return mtree.guess.get('type', '').startswith('episode')

    def process(self, mtree, options=None):
        GuessFinder(self.guess_episodes_rexps, None, self.log, options).process_nodes(mtree.unidentified_leaves())
