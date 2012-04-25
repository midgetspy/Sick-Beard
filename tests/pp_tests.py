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
import test_lib

import sys, os.path

from sickbeard.postProcessor import PostProcessor
import sickbeard
from sickbeard.tv import TVEpisode, TVShow
import sickbeard.common as c

from snatch_tests import tests

class PPInitTests(unittest.TestCase):

    def setUp(self):
        self.pp = PostProcessor(test_lib.FILEPATH)

    def test_init_file_name(self):
        self.assertEqual(self.pp.file_name, test_lib.FILENAME)

    def test_init_folder_name(self):
        self.assertEqual(self.pp.folder_name, test_lib.SHOWNAME)


class PPPrivateTests(test_lib.SickbeardTestDBCase):


    def setUp(self):
        super(PPPrivateTests, self).setUp()

        sickbeard.showList = [TVShow(0000), TVShow(0001)]

        self.pp = PostProcessor(test_lib.FILEPATH)
        self.show_obj = TVShow(0002)

        self.db = test_lib.db.DBConnection()
        newValueDict = {"tvdbid": 1002,
                        "name": test_lib.SHOWNAME,
                        "description": "description",
                        "airdate": 1234,
                        "hasnfo": 1,
                        "hastbn": 1,
                        "status": 404,
                        "location": test_lib.FILEPATH}
        controlValueDict = {"showid": 0002,
                            "season": test_lib.SEASON,
                            "episode": test_lib.EPISODE}

        # use a custom update/insert method to get the data into the DB
        self.db.upsert("tv_episodes", newValueDict, controlValueDict)

        self.ep_obj = TVEpisode(self.show_obj, test_lib.SEASON, test_lib.EPISODE, test_lib.FILEPATH)

    def test__find_ep_destination_folder(self):
        self.show_obj.location = test_lib.FILEDIR
        self.ep_obj.show.seasonfolders = 1
        sickbeard.SEASON_FOLDERS_FORMAT = 'Season %02d'
        calculatedPath = self.pp._find_ep_destination_folder(self.ep_obj)
        ecpectedPath = os.path.join(test_lib.FILEDIR, "Season 0" + str(test_lib.SEASON))
        self.assertEqual(calculatedPath, ecpectedPath)


class PPBasicTests(test_lib.SickbeardTestDBCase):

    filePath = ''
    showDir = ''

    def tearDown(self):
        if self.showDir:
            test_lib.tearDown_test_show_dir(self.showDir)
        if self.filePath:
            test_lib.tearDown_test_episode_file(os.path.dirname(self.filePath))

        test_lib.SickbeardTestDBCase.tearDown(self)


def test_generator(tvdbdid, show_name, curData):

    def test(self):

        self.showDir = test_lib.setUp_test_show_dir(show_name)
        self.filePath = test_lib.setUp_test_episode_file(None, curData["b"]+".mkv")

        show = TVShow(tvdbdid)
        show.name = show_name
        show.quality = curData["q"]
        show.location = self.showDir
        if curData["anime"]:
            show.anime = 1
        show.saveToDB()
        sickbeard.showList.append(show)

        for epNumber in curData["e"]:
            episode = TVEpisode(show, curData["s"], epNumber)
            episode.status = c.WANTED
            if "ab" in curData:
                episode.absolute_number = curData["ab"]
            episode.saveToDB()

        pp = PostProcessor(self.filePath)
        self.assertTrue(pp.process())
    return test


# create the test methods
tvdbdid = 1
for name, curData in tests.items(): # we use the tests from snatch_tests.py
    if not curData["a"]:
        continue
    fname = name.replace(' ', '_')
    test_name = 'test_pp_%s_%s' % (fname, tvdbdid)

    test = test_generator(tvdbdid, name, curData)
    setattr(PPBasicTests, test_name, test)
    tvdbdid += 1

if __name__ == '__main__':
    print "=================="
    print "STARTING - PostProcessor TESTS"
    print "=================="
    print "######################################################################"
    suite = unittest.TestLoader().loadTestsFromTestCase(PPInitTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
    print "######################################################################"
    suite = unittest.TestLoader().loadTestsFromTestCase(PPPrivateTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
    print "######################################################################"
    suite = unittest.TestLoader().loadTestsFromTestCase(PPBasicTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
