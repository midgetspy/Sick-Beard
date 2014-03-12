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

from __future__ import absolute_import, division, print_function, \
    unicode_literals

from guessit.patterns import _psep
from guessit.containers import PropertiesContainer
from guessit.plugins.transformers import Transformer
from guessit.matcher import GuessFinder
from guessit.patterns.numeral import parse_numeral


class GuessVideoRexps(Transformer):
    def __init__(self):
        Transformer.__init__(self, 25)

        self.container = PropertiesContainer(canonical_from_pattern=False)

        self.container.register_property(None, 'cd' + _psep + '(?P<cdNumber>[0-9])(?:' + _psep + 'of' + _psep + '(?P<cdNumberTotal>[0-9]))?', confidence=1.0, enhance=False, global_span=True, formatter=parse_numeral)
        self.container.register_property('cdNumberTotal', '([1-9])' + _psep + 'cds?', confidence=0.9, enhance=False, formatter=parse_numeral)

        self.container.register_property('bonusNumber', 'x([0-9]{1,2})', enhance=False, global_span=True, formatter=parse_numeral)

        self.container.register_property('filmNumber', 'f([0-9]{1,2})', enhance=False, global_span=True, formatter=parse_numeral)

        self.container.register_property('edition', 'collector', 'collector-edition', 'edition-collector', canonical_form='Collector Edition')
        self.container.register_property('edition', 'special-edition', 'edition-special', canonical_form='Special Edition')
        self.container.register_property('edition', 'criterion', 'criterion-edition', 'edition-criterion', canonical_form='Criterion Edition')
        self.container.register_property('edition', 'deluxe', 'cdeluxe-edition', 'edition-deluxe', canonical_form='Deluxe Edition')
        self.container.register_property('edition', 'director\'?s?-cut', 'director\'?s?-cut-edition', 'edition-director\'?s?-cut', canonical_form='Director\'s cut')

    def supported_properties(self):
        return self.container.get_supported_properties()

    def guess_video_rexps(self, string, node=None, options=None):
        found = self.container.find_properties(string, node)
        return self.container.as_guess(found, string)

    def process(self, mtree, options=None):
        GuessFinder(self.guess_video_rexps, None, self.log, options).process_nodes(mtree.unidentified_leaves())
