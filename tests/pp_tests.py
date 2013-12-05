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

import random
import unittest

import test_lib as test

import sys, os.path, os, shutil

from sickbeard.postProcessor import PostProcessor

import sickbeard
from sickbeard.tv import TVEpisode, TVShow
from sickbeard.processTV import processDir

def init_shows():
    show = TVShow(3)
    show.name = test.SHOWNAME
    show.location = test.SHOWDIR
    show.saveToDB()

    sickbeard.showList = [show]
    ep = TVEpisode(show, test.SEASON, test.EPISODE)
    ep.name = "some ep name"
    ep.saveToDB()
    return (show, ep)

class PPInitTests(unittest.TestCase):

    def setUp(self):
        self.pp = PostProcessor(test.FILEPATH)

    def test_init_file_name(self):
        self.assertEqual(self.pp.file_name, test.FILENAME)

    def test_init_folder_name(self):
        self.assertEqual(self.pp.folder_name, test.SHOWNAME)


class PPPrivateTests(test.SickbeardTestDBCase):


    def setUp(self):
        super(PPPrivateTests, self).setUp()

        sickbeard.showList = [TVShow(0000), TVShow(0001)]

        self.pp = PostProcessor(test.FILEPATH)
        self.show_obj = TVShow(0002)

        self.db = test.db.DBConnection()
        newValueDict = {"tvdbid": 1002,
                        "name": test.SHOWNAME,
                        "description": "description",
                        "airdate": 1234,
                        "hasnfo": 1,
                        "hastbn": 1,
                        "status": 404,
                        "location": test.FILEPATH}
        controlValueDict = {"showid": 0002,
                            "season": test.SEASON,
                            "episode": test.EPISODE}

        # use a custom update/insert method to get the data into the DB
        self.db.upsert("tv_episodes", newValueDict, controlValueDict)

        self.ep_obj = TVEpisode(self.show_obj, test.SEASON, test.EPISODE, test.FILEPATH)

    def test__find_ep_destination_folder(self):
        self.show_obj.location = test.FILEDIR
        self.ep_obj.show.seasonfolders = 1
        sickbeard.SEASON_FOLDERS_FORMAT = 'Season %02d'
        calculatedPath = self.pp._find_ep_destination_folder(self.ep_obj)
        ecpectedPath = os.path.join(test.FILEDIR, "Season 0" + str(test.SEASON))
        self.assertEqual(calculatedPath, ecpectedPath)

    def test_do_not_delete_tv_download_dir(self):
        TEST_DOWNLOAD_DIR = u"tv_download_dir"
        TEST_DOWNLOAD_DIR_LINK = u"tv_download_dir_link"
        TEST_NEW_EP_FILE = u"show name - s01e010.mkv"

        (show, ep) = init_shows()

        old_download_dir = sickbeard.TV_DOWNLOAD_DIR
        sickbeard.TV_DOWNLOAD_DIR = TEST_DOWNLOAD_DIR_LINK
        if(os.path.exists(TEST_DOWNLOAD_DIR_LINK)):
            os.remove(TEST_DOWNLOAD_DIR_LINK)
        if(os.path.exists(TEST_DOWNLOAD_DIR)):
            shutil.rmtree(TEST_DOWNLOAD_DIR)
        os.mkdir(TEST_DOWNLOAD_DIR)
        os.symlink(TEST_DOWNLOAD_DIR, TEST_DOWNLOAD_DIR_LINK)
        open(os.path.join(TEST_DOWNLOAD_DIR_LINK, TEST_NEW_EP_FILE), "a").close()
        processDir(TEST_DOWNLOAD_DIR_LINK)

        sickbeard.TV_DOWNLOAD_DIR = old_download_dir
        self.assertTrue(os.path.exists(TEST_DOWNLOAD_DIR))

        shutil.rmtree(TEST_DOWNLOAD_DIR)
        os.remove(TEST_DOWNLOAD_DIR_LINK)

class PPBasicTests(test.SickbeardTestDBCase):

    def test_process(self):
        (show, ep) = init_shows()

        pp = PostProcessor(test.FILEPATH)
        self.assertTrue(pp.process())


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
