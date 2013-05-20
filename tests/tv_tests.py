# coding=UTF-8
# Author: Dennis Lutter <lad1337@gmail.com>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import test_lib as test

import sickbeard
from sickbeard.tv import TVEpisode, TVShow


class TVShowTests(test.SickbeardTestDBCase):

    def setUp(self):
        super(TVShowTests, self).setUp()
        sickbeard.showList = []

    def test_init_tvdbid(self):
        show = TVShow(0001, "en")
        self.assertEqual(show.tvdbid, 0001)

    def test_change_tvdbid(self):
        show = TVShow(0001, "en")
        show.name = "show name"
        show.tvrname = "show name"
        show.network = "cbs"
        show.genre = "crime"
        show.runtime = 40
        show.status = "5"
        show.airs = "monday"
        show.startyear = 1987

        show.saveToDB()
        show.loadFromDB(skipNFO=True)

        show.tvdbid = 0002
        show.saveToDB()
        show.loadFromDB(skipNFO=True)

        self.assertEqual(show.tvdbid, 0002)

    def test_set_name(self):
        show = TVShow(0001, "en")
        show.name = "newName"
        show.saveToDB()
        show.loadFromDB(skipNFO=True)
        self.assertEqual(show.name, "newName")


class TVEpisodeTests(test.SickbeardTestDBCase):

    def setUp(self):
        super(TVEpisodeTests, self).setUp()
        sickbeard.showList = []

    def test_init_empty_db(self):
        show = TVShow(0001, "en")
        ep = TVEpisode(show, 1, 1)
        ep.name = "asdasdasdajkaj"
        ep.saveToDB()
        ep.loadFromDB(1, 1)
        self.assertEqual(ep.name, "asdasdasdajkaj")


class TVTests(test.SickbeardTestDBCase):

    def setUp(self):
        super(TVTests, self).setUp()
        sickbeard.showList = []

    def test_getEpisode(self):
        show = TVShow(0001, "en")
        show.name = "show name"
        show.tvrname = "show name"
        show.network = "cbs"
        show.genre = "crime"
        show.runtime = 40
        show.status = "5"
        show.airs = "monday"
        show.startyear = 1987
        show.saveToDB()
        sickbeard.showList = [show]
        #TODO: implement


if __name__ == '__main__':
    print "=================="
    print "STARTING - TV TESTS"
    print "=================="
    print "######################################################################"
    suite = unittest.TestLoader().loadTestsFromTestCase(TVShowTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
    print "######################################################################"
    suite = unittest.TestLoader().loadTestsFromTestCase(TVEpisodeTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
    print "######################################################################"
    suite = unittest.TestLoader().loadTestsFromTestCase(TVTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
