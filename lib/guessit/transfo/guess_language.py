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

from guessit.language import search_language, subtitle_prefixes, subtitle_suffixes
from guessit.patterns.extension import subtitle_exts
from guessit.textutils import clean_string, find_words
from guessit.plugins.transformers import Transformer
from guessit.matcher import GuessFinder


class GuessLanguage(Transformer):
    def __init__(self):
        Transformer.__init__(self, 30)

    def supported_properties(self):
        return ['language', 'subtitleLanguage']

    def guess_language(self, string, node=None, options=None):
        guess = search_language(string)
        return guess

    def _skip_language_on_second_pass(self, mtree, node):
        """Check if found node is a valid language node, or if it's a false positive.

        :param mtree: Tree detected on first pass.
        :type mtree: :class:`guessit.matchtree.MatchTree`
        :param node: Node that contains a language Guess
        :type node: :class:`guessit.matchtree.MatchTree`

        :return: True if a second pass skipping this node is required
        :rtype: bool
        """
        unidentified_starts = {}
        unidentified_ends = {}

        property_starts = {}
        property_ends = {}

        title_starts = {}
        title_ends = {}

        for unidentified_node in mtree.unidentified_leaves():
            unidentified_starts[unidentified_node.span[0]] = unidentified_node
            unidentified_ends[unidentified_node.span[1]] = unidentified_node

        for property_node in mtree.leaves_containing('year'):
            property_starts[property_node.span[0]] = property_node
            property_ends[property_node.span[1]] = property_node

        for title_node in mtree.leaves_containing(['title', 'series']):
            title_starts[title_node.span[0]] = title_node
            title_ends[title_node.span[1]] = title_node

        return node.span[0] in title_ends.keys() and (node.span[1] in unidentified_starts.keys() or node.span[1] + 1 in property_starts.keys()) or\
                node.span[1] in title_starts.keys() and (node.span[0] == 0 or node.span[0] in unidentified_ends.keys() or node.span[0] in property_ends.keys())

    def second_pass_options(self, mtree, options=None):
        m = mtree.matched()
        to_skip_language_nodes = []

        for lang_key in ('language', 'subtitleLanguage'):
            langs = {}
            lang_nodes = set(n for n in mtree.leaves_containing(lang_key))

            for lang_node in lang_nodes:
                lang = lang_node.guess.get(lang_key, None)
                if self._skip_language_on_second_pass(mtree, lang_node):
                    # Language probably split the title. Add to skip for 2nd pass.

                    # if filetype is subtitle and the language appears last, just before
                    # the extension, then it is likely a subtitle language
                    parts = clean_string(lang_node.root.value).split()
                    if (m.get('type') in ['moviesubtitle', 'episodesubtitle'] and
                        (parts.index(lang_node.value) == len(parts) - 2)):
                        continue

                    to_skip_language_nodes.append(lang_node)
                elif not lang in langs:
                    langs[lang] = lang_node
                else:
                    # The same language was found. Keep the more confident one,
                    # and add others to skip for 2nd pass.
                    existing_lang_node = langs[lang]
                    to_skip = None
                    if (existing_lang_node.guess.confidence('language') >=
                        lang_node.guess.confidence('language')):
                        # lang_node is to remove
                        to_skip = lang_node
                    else:
                        # existing_lang_node is to remove
                        langs[lang] = lang_node
                        to_skip = existing_lang_node
                    to_skip_language_nodes.append(to_skip)

        if to_skip_language_nodes:
            return {'skip_nodes': to_skip_language_nodes}
        return None

    def should_process(self, mtree, options=None):
        options = options or {}
        return 'nolanguage' not in options

    def process(self, mtree, options=None):
        GuessFinder(self.guess_language, None, self.log, options).process_nodes(mtree.unidentified_leaves())

    def promote_subtitle(self, node):
        node.guess.set('subtitleLanguage', node.guess['language'],
                       confidence=node.guess.confidence('language'))
        del node.guess['language']

    def post_process(self, mtree, options=None):
        # 1- try to promote language to subtitle language where it makes sense
        for node in mtree.nodes():
            if 'language' not in node.guess:
                continue

            # - if we matched a language in a file with a sub extension and that
            #   the group is the last group of the filename, it is probably the
            #   language of the subtitle
            #   (eg: 'xxx.english.srt')
            if (mtree.node_at((-1,)).value.lower() in subtitle_exts and
                node == mtree.leaves()[-2]):
                self.promote_subtitle(node)

            # - if we find in the same explicit group
            # a subtitle prefix before the language,
            # or a subtitle suffix after the language,
            # then upgrade the language
            explicit_group = mtree.node_at(node.node_idx[:2])
            group_str = explicit_group.value.lower()

            for sub_prefix in subtitle_prefixes:
                if (sub_prefix in find_words(group_str) and
                    0 <= group_str.find(sub_prefix) < (node.span[0] - explicit_group.span[0])):
                    self.promote_subtitle(node)

            for sub_suffix in subtitle_suffixes:
                if (sub_suffix in find_words(group_str) and
                    (node.span[0] - explicit_group.span[0]) < group_str.find(sub_suffix)):
                    self.promote_subtitle(node)

            # - if a language is in an explicit group just preceded by "st",
            #   it is a subtitle language (eg: '...st[fr-eng]...')
            try:
                idx = node.node_idx
                previous = mtree.node_at((idx[0], idx[1] - 1)).leaves()[-1]
                if previous.value.lower()[-2:] == 'st':
                    self.promote_subtitle(node)
            except IndexError:
                pass
