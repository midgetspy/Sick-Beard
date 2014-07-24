# coding=UTF-8
# Author: Daniel Hobe <hobeonekenobi@gmail.com>
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

import datetime
import unittest
import test_lib as test
import mox
import cptestcase
import cherrypy

import sickbeard
from sickbeard import tv
from sickbeard import webserve, scheduler, searchBacklog


def setUpModule():
    cherrypy.tree.mount(webserve.WebInterface(), '/')
    cherrypy.engine.start()
setup_module = setUpModule


def tearDownModule():
    cherrypy.engine.exit()
teardown_module = tearDownModule


class WebserveTests(test.SickbeardTestDBCase, cptestcase.BaseCherryPyTestCase):
    def setUp(self):
        test.SickbeardTestDBCase.setUp(self)
        sickbeard.USE_API = True
        sickbeard.API_KEY = 'testing'
        sickbeard.COMING_EPS_SORT = 'date'
        self.mox = mox.Mox()
        mock_sched = self.mox.CreateMock(scheduler.Scheduler)
        mock_sched.timeLeft().AndReturn('')
        mock_backlog_sched = self.mox.CreateMock(
            searchBacklog.BacklogSearchScheduler)
        mock_backlog_sched.nextRun().AndReturn(datetime.datetime.today())
        sickbeard.currentSearchScheduler = mock_sched
        sickbeard.backlogSearchScheduler = mock_backlog_sched

    def tearDown(self):
        test.SickbeardTestDBCase.tearDown(self)
        self.mox.UnsetStubs()

    def test_ComingEpisodes(self):
        self.loadFixtures()
        s = tv.TVShow(82066)
        e = tv.TVEpisode(s, 5, 13)
        e.loadFromDB(5, 13)
        e.airdate = (datetime.date.today() +
                     datetime.timedelta(days=3))
        e.saveToDB(forceSave=True)

        self.mox.ReplayAll()
        response = self.request('/comingEpisodes/')
        self.assertEqual(response.output_status, '200 OK')
        self.assertIn('5x13 - An Enemy of Fate', response.body[0])

    def test_Api(self):
        response = self.request('/api/testing/', cmd='logs', min_level='debug')
        self.assertIn('success', response.body[0])

    def test_future_Api(self):
        response = self.request('/api/testing/', cmd='future')
        self.assertIn('success', response.body[0])

    def test_history_Api(self):
        self.loadFixtures()
        response = self.request('/api/testing/', cmd='history', debug=1)
        self.assertIn('Fringe', response.body[0])
        response = self.request('/api/testing/', cmd='history',
                                limit=100, debug=1)
        self.assertIn('Fringe', response.body[0])

    def test_exceptions_Api(self):
        self.loadFixtures()
        response = self.request('/api/testing/', cmd='exceptions')
        self.assertIn('success', response.body[0])

        sickbeard.showList = [tv.TVShow(82066)]
        response = self.request('/api/testing/',
                                cmd='exceptions', tvdbid='82066', debug=1)
        self.assertIn('success', response.body[0])

    def test_show_season_list_api(self):
        self.loadFixtures()
        sickbeard.showList = [tv.TVShow(82066)]
        response = self.request('/api/testing/',
                                cmd='show.seasonlist',
                                tvdbid=82066,
                                debug=1)
        self.assertIn('success', response.body[0])

    def test_show_seasons(self):
        self.loadFixtures()
        sickbeard.showList = [tv.TVShow(82066)]
        response = self.request('/api/testing/',
                                cmd='show.seasons',
                                tvdbid=82066,
                                debug=1)
        self.assertIn('success', response.body[0])

        response = self.request('/api/testing/',
                                cmd='show.seasons',
                                tvdbid=82066,
                                season=5,
                                debug=1)
        self.assertIn('success', response.body[0])

    def test_show_stats(self):
        self.loadFixtures()
        sickbeard.showList = [tv.TVShow(82066)]
        response = self.request('/api/testing/',
                                cmd='show.stats',
                                tvdbid=82066,
                                debug=1)
        self.assertIn('success', response.body[0])

    def test_shows_stats(self):
        self.loadFixtures()
        sickbeard.showList = [tv.TVShow(82066)]
        response = self.request('/api/testing/',
                                cmd='shows.stats',
                                debug=1)
        self.assertIn('success', response.body[0])
        self.assertIn('"ep_total": 1', response.body[0])


if __name__ == '__main__':

    print "=================="
    print "STARTING - Webserve TESTS"
    print "=================="
    print "###################################################################"
    unittest.main()
