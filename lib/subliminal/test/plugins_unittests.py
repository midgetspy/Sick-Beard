#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Subliminal - Subtitles, faster than your thoughts
# Copyright (c) 2011 Antoine Bertin <diaoulael@gmail.com>
#
# Subliminal is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import unittest
import logging
import os


logging.basicConfig(level=logging.DEBUG, format='%(name)-24s %(levelname)-8s %(message)s')
if not os.path.exists('/tmp/subliminal/cache'):
    os.mkdir('/tmp/subliminal/cache')
config = {'multi': True, 'cache_dir': '/tmp/subliminal/cache', 'subtitlesource_key': '', 'force': False}


class Addic7edListTestCase1(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import Addic7ed
        plugin = Addic7ed(config)
        results = plugin.list(["The.Big.Bang.Theory.S03E13.HDTV.XviD-2HD.mkv"], ["en", "fr"])
        print results
        assert len(results) > 0


class Addic7edListTestCase2(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import Addic7ed
        plugin = Addic7ed(config)
        results = plugin.list(["Dexter.S05E02.720p.HDTV.x264-IMMERSE.mkv"], ["en", "fr"])
        print results
        assert len(results) > 0


class Addic7edDownloadTestCase(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import Addic7ed
        plugin = Addic7ed(config)
        results = plugin.download(plugin.list(["/tmp/The.Big.Bang.Theory.S03E13.HDTV.XviD-2HD.mkv"], ["en", "fr"])[0])
        print results
        assert len(results) > 0


class BierDopjeListTestCase(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import BierDopje
        plugin = BierDopje(config)
        results = plugin.list(["The.Big.Bang.Theory.S03E13.HDTV.XviD-2HD.mkv"], ["en", "fr"])
        print results
        assert len(results) > 0


class BierDopjeListExceptionTestCase(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import BierDopje
        plugin = BierDopje(config)
        results = plugin.list(["The.Office.US.S07E08.Viewing.Party.HDTV.XviD-FQM.[VTV].avi"], ["en", "fr"])
        print results
        assert len(results) > 0


class BierDopjeListTestCase(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import BierDopje
        plugin = BierDopje(config)
        results = plugin.list(["The.Big.Bang.Theory.S03E13.HDTV.XviD-2HD.mkv"], ["en", "fr"])
        print results
        assert len(results) > 0


class OpenSubtitlesQueryTestCase(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import OpenSubtitles
        plugin = OpenSubtitles()
        results = plugin.query('Night.Watch.2004.CD1.DVDRiP.XViD-FiCO.avi', moviehash="09a2c497663259cb", bytesize="733589504")  # http://trac.opensubtitles.org/projects/opensubtitles/wiki/XMLRPC
        print results
        assert len(results) > 0


class OpenSubtitlesQueryNoHashTestCase(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import OpenSubtitles
        plugin = OpenSubtitles()
        results = plugin.query('Night.Watch.2004.CD1.DVDRiP.XViD-FiCO.avi', languages=['en', 'fr'])  # http://trac.opensubtitles.org/projects/opensubtitles/wiki/XMLRPC
        print results
        assert len(results) > 0


class OpenSubtitlesListTestCase(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import OpenSubtitles
        plugin = OpenSubtitles()
        results = plugin.download(plugin.query('/tmp/Night.Watch.2004.CD1.DVDRiP.XViD-FiCO.avi', moviehash="09a2c497663259cb", bytesize="733589504")[0])  # http://trac.opensubtitles.org/projects/opensubtitles/wiki/XMLRPC
        assert len(results) > 0


class SubtitulosListTestCase(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import Subtitulos
        plugin = Subtitulos()
        results = plugin.list(["The.Big.Bang.Theory.S03E13.HDTV.XviD-2HD.mkv"], ['en', 'fr'])
        print results
        assert len(results) > 0


class SubtitulosDownloadTestCase(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import Subtitulos
        plugin = Subtitulos()
        results = plugin.download(plugin.list(["/tmp/The.Big.Bang.Theory.S03E13.HDTV.XviD-2HD.mkv"], ['en', 'fr'])[0])
        print results
        assert len(results) > 0


class TheSubDBQueryTestCase(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import TheSubDB
        plugin = TheSubDB()
        results = plugin.query("test.mkv", "edc1981d6459c6111fe36205b4aff6c2")
        print results
        assert len(results) > 0


class TheSubDBDownloadTestCase(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import TheSubDB
        plugin = TheSubDB()
        results = plugin.download(plugin.query("/tmp/test.mkv", "edc1981d6459c6111fe36205b4aff6c2")[0])
        print results
        assert len(results) > 0


class SubsWikiListTestCase(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import SubsWiki
        plugin = SubsWiki()
        results = plugin.list(["The.Big.Bang.Theory.S03E13.HDTV.XviD-2HD.mkv"], ['en', 'es'])
        print results
        assert len(results) > 0


class SubsWikiDownloadTestCase(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import SubsWiki
        plugin = SubsWiki()
        results = plugin.download(plugin.list(["/tmp/The.Big.Bang.Theory.S03E13.HDTV.XviD-2HD.mkv"], ['en', 'es'])[0])
        print results
        assert len(results) > 0
'''
class PodnapisiQueryTestCase(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import Podnapisi
        plugin = Podnapisi()
        results = plugin.query('09a2c497663259cb', ["en", "fr"])
        print results
        assert len(results) > 5


class SubSceneListTestCase(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import SubScene
        plugin = SubScene()
        results = plugin.list(["Dexter.S04E01.HDTV.XviD-NoTV.avi"], ['en', 'fr'])
        print results
        assert len(results) > 0, "No result could be found for Dexter.S04E01.HDTV.XviD-NoTV.avi and no languages"


class SubSceneDownloadTestCase(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import SubScene
        plugin = SubScene()
        results = plugin.download(plugin.list(["Dexter.S04E01.HDTV.XviD-NoTV.avi"], ['en', 'fr'])[0])
        print results
        assert len(results) > 0, "No result could be found for Dexter.S04E01.HDTV.XviD-NoTV.avi and no languages"


class SubtitleSourceListTestCase(unittest.TestCase):
    def runTest(self):
        from subliminal.plugins import SubtitleSource
        plugin = SubtitleSource()
        results = plugin.list(["PrisM-Inception.2010"], ['en', 'fr'])
        print results
        assert len(results) > 0, "No result could be found for PrisM-Inception.2010"
'''


if __name__ == "__main__":
    unittest.main()
