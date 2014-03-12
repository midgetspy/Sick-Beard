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
from guessit.matcher import GuessFinder, found_property, found_guess
from guessit.containers import PropertiesContainer
from guessit.patterns import sep
from guessit.guess import Guess
from guessit.textutils import strip_brackets


class GuessReleaseGroup(Transformer):
    def __init__(self):
        Transformer.__init__(self, -190)
        self.container = PropertiesContainer(canonical_from_pattern=False)
        self._allowed_groupname_pattern = '[\w@#€£$&]'
        self._forbidden_groupname_lambda = [lambda elt: elt in ['rip', 'by', 'for', 'par', 'pour', 'bonus'],
                               lambda elt: self._is_number(elt),
                               ]
        # If the previous property in this list, the match will be considered as safe
        # and group name can contain a separator.
        self.previous_safe_properties = ['videoCodec', 'format', 'videoApi', 'audioCodec', 'audioProfile', 'videoProfile', 'audioChannels']

        self.container.sep_replace_char = '-'
        self.container.canonical_from_pattern = False
        self.container.enhance = True
        self.container.register_property('releaseGroup', self._allowed_groupname_pattern + '+')
        self.container.register_property('releaseGroup', self._allowed_groupname_pattern + '+-' + self._allowed_groupname_pattern + '+')

    def supported_properties(self):
        return self.container.get_supported_properties()

    def _is_number(self, s):
        try:
            int(s)
            return True
        except ValueError:
            return False

    def validate_group_name(self, guess):
        val = guess['releaseGroup']
        if len(val) >= 2:

            if '-' in val:
                checked_val = ""
                for elt in val.split('-'):
                    forbidden = False
                    for forbidden_lambda in self._forbidden_groupname_lambda:
                        forbidden = forbidden_lambda(elt.lower())
                        if forbidden:
                            break
                    if not forbidden:
                        if checked_val:
                            checked_val += '-'
                        checked_val += elt
                    else:
                        break
                val = checked_val
                if not val:
                    return False
                guess['releaseGroup'] = val

            forbidden = False
            for forbidden_lambda in self._forbidden_groupname_lambda:
                forbidden = forbidden_lambda(val.lower())
                if forbidden:
                    break
            if not forbidden:
                return True
        return False

    def is_leaf_previous(self, leaf, node):
        if leaf.span[1] <= node.span[0]:
            for idx in range(leaf.span[1], node.span[0]):
                if not leaf.root.value[idx] in sep:
                    return False
            return True
        return False

    def guess_release_group(self, string, node=None, options=None):
        found = self.container.find_properties(string, node, 'releaseGroup')
        guess = self.container.as_guess(found, string, self.validate_group_name, sep_replacement='-')
        validated_guess = None
        if guess:
            explicit_group_node = node.group_node()
            if explicit_group_node:
                for leaf in explicit_group_node.leaves_containing(self.previous_safe_properties):
                    if self.is_leaf_previous(leaf, node):
                        if leaf.root.value[leaf.span[1]] == '-':
                            guess.metadata().confidence = 1
                        else:
                            guess.metadata().confidence = 0.7
                        validated_guess = guess

            if not validated_guess:
                # If previous group last leaf is identified as a safe property,
                # consider the raw value as a releaseGroup
                previous_group_node = node.previous_group_node()
                if previous_group_node:
                    for leaf in previous_group_node.leaves_containing(self.previous_safe_properties):
                        if self.is_leaf_previous(leaf, node):
                            guess = Guess({'releaseGroup': node.value}, confidence=1, input=node.value, span=(0, len(node.value)))
                            if self.validate_group_name(guess):
                                node.guess = guess
                                validated_guess = guess

            if validated_guess:
                # If following group nodes have only one unidentified leaf, it belongs to the release group
                next_group_node = node

                while True:
                    next_group_node = next_group_node.next_group_node()
                    if next_group_node:
                        leaves = next_group_node.leaves()
                        if len(leaves) == 1 and not leaves[0].guess:
                            validated_guess['releaseGroup'] = validated_guess['releaseGroup'] + leaves[0].value
                            leaves[0].guess = validated_guess
                        else:
                            break
                    else:
                        break

        if validated_guess:
            # Strip brackets
            validated_guess['releaseGroup'] = strip_brackets(validated_guess['releaseGroup'])

        return validated_guess

    def process(self, mtree, options=None):
        GuessFinder(self.guess_release_group, None, self.log, options).process_nodes(mtree.unidentified_leaves())
