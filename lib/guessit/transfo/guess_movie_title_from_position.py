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
from guessit.matcher import found_property
from guessit import u


class GuessMovieTitleFromPosition(Transformer):
    def __init__(self):
        Transformer.__init__(self, -200)

    def supported_properties(self):
        return ['title']

    def should_process(self, mtree, options=None):
        options = options or {}
        return not options.get('skip_title') and not mtree.guess.get('type', '').startswith('episode')

    def process(self, mtree, options=None):
        """
        try to identify the remaining unknown groups by looking at their
        position relative to other known elements
        """
        basename = mtree.node_at((-2,))
        all_valid = lambda leaf: len(leaf.clean_value) > 0
        basename_leftover = basename.unidentified_leaves(valid=all_valid)

        try:
            folder = mtree.node_at((-3,))
            folder_leftover = folder.unidentified_leaves()
        except ValueError:
            folder = None
            folder_leftover = []

        self.log.debug('folder: %s' % u(folder_leftover))
        self.log.debug('basename: %s' % u(basename_leftover))

        # specific cases:
        # if we find the same group both in the folder name and the filename,
        # it's a good candidate for title
        if (folder_leftover and basename_leftover and
            folder_leftover[0].clean_value == basename_leftover[0].clean_value):

            found_property(folder_leftover[0], 'title', confidence=0.8)
            return

        # specific cases:
        # if the basename contains a number first followed by an unidentified
        # group, and the folder only contains 1 unidentified one, then we have
        # a series
        # ex: Millenium Trilogy (2009)/(1)The Girl With The Dragon Tattoo(2009).mkv
        try:
            series = folder_leftover[0]
            filmNumber = basename_leftover[0]
            title = basename_leftover[1]

            basename_leaves = basename.leaves()

            num = int(filmNumber.clean_value)

            self.log.debug('series: %s' % series.clean_value)
            self.log.debug('title: %s' % title.clean_value)
            if (series.clean_value != title.clean_value and
                series.clean_value != filmNumber.clean_value and
                basename_leaves.index(filmNumber) == 0 and
                basename_leaves.index(title) == 1):

                found_property(title, 'title', confidence=0.6)
                found_property(series, 'filmSeries', confidence=0.6)
                found_property(filmNumber, 'filmNumber', num, confidence=0.6)
            return
        except Exception:
            pass

        # specific cases:
        #  - movies/tttttt (yyyy)/tttttt.ccc
        try:
            if mtree.node_at((-4, 0)).value.lower() == 'movies':
                folder = mtree.node_at((-3,))

                # Note:too generic, might solve all the unittests as they all
                # contain 'movies' in their path
                #
                # if containing_folder.is_leaf() and not containing_folder.guess:
                #    containing_folder.guess =
                #        Guess({ 'title': clean_string(containing_folder.value) },
                #              confidence=0.7)

                year_group = folder.first_leaf_containing('year')
                groups_before = folder.previous_unidentified_leaves(year_group)

                found_property(groups_before[0], 'title', confidence=0.8)
                return

        except Exception:
            pass

        # if we have either format or videoCodec in the folder containing the file
        # or one of its parents, then we should probably look for the title in
        # there rather than in the basename
        try:
            props = mtree.previous_leaves_containing(mtree.children[-2],
                                                     ['videoCodec', 'format',
                                                       'language'])
        except IndexError:
            props = []

        if props:
            group_idx = props[0].node_idx[0]
            if all(g.node_idx[0] == group_idx for g in props):
                # if they're all in the same group, take leftover info from there
                leftover = mtree.node_at((group_idx,)).unidentified_leaves()

                if leftover:
                    found_property(leftover[0], 'title', confidence=0.7)
                    return

        # look for title in basename if there are some remaining unidentified
        # groups there
        if basename_leftover:
            # if basename is only one word and the containing folder has at least
            # 3 words in it, we should take the title from the folder name
            # ex: Movies/Alice in Wonderland DVDRip.XviD-DiAMOND/dmd-aw.avi
            # ex: Movies/Somewhere.2010.DVDRip.XviD-iLG/i-smwhr.avi  <-- TODO: gets caught here?
            if (basename_leftover[0].clean_value.count(' ') == 0 and
                folder_leftover and
                folder_leftover[0].clean_value.count(' ') >= 2):

                found_property(folder_leftover[0], 'title', confidence=0.7)
                return

            # if there are only many unidentified groups, take the first of which is
            # not inside brackets or parentheses.
            # ex: Movies/[阿维达].Avida.2006.FRENCH.DVDRiP.XViD-PROD.avi
            if basename_leftover[0].is_explicit():
                for basename_leftover_elt in basename_leftover:
                    if not basename_leftover_elt.is_explicit():
                        found_property(basename_leftover_elt, 'title', confidence=0.8)
                        return

            # if all else fails, take the first remaining unidentified group in the
            # basename as title
            found_property(basename_leftover[0], 'title', confidence=0.6)
            return

        # if there are no leftover groups in the basename, look in the folder name
        if folder_leftover:
            found_property(folder_leftover[0], 'title', confidence=0.5)
            return

        # if nothing worked, look if we have a very small group at the beginning
        # of the basename
        basename = mtree.node_at((-2,))
        basename_leftover = basename.unidentified_leaves(valid=lambda leaf: True)
        if basename_leftover:
            found_property(basename_leftover[0], 'title', confidence=0.4)
            return
