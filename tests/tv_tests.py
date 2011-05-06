# coding=UTF-8
import random
import unittest

import test_lib as test

import sys, os.path
sys.path.append(os.path.abspath('..'))
sys.path.append(os.path.abspath('../lib'))

import sickbeard
from sickbeard.tv import TVEpisode,TVShow
from sickbeard import exceptions


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
        self.assertRaises(exceptions.EpisodeNotFoundException, TVEpisode, show, test.SEASON, test.EPISODE)

class TVTests(test.SickbeardTestDBCase):
    
    def setUp(self):
        super(TVEpisodeTests, self).setUp()
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
        
        
        
        
        pass 






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
    

