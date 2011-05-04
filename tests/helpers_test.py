import datetime
import unittest

import sys, os.path
sys.path.append(os.path.abspath('..'))
sys.path.append(os.path.abspath('../lib'))

import sickbeard # we need to import this so we can override the SYS_ENCODING which is needed by the parser
from sickbeard import helpers, scene_exceptions

DEBUG = VERBOSE = False
sickbeard.SYS_ENCODING = "UTF-8"
sickbeard.QUALITY_DEFAULT = 4
sickbeard.SEASON_FOLDERS_DEFAULT = 0


class DumyTVShow(object):
    name = ""
    tvdbid = 0
    
    def __init__(self, id, name, anime):
        self.name = name
        self.tvdbid = id
        self.anime = anime
    
    def is_anime(self):
        return self.anime


showDict = {DumyTVShow(1,"Dance in the Vampire Bund",True):"[SFW-Chihiro] Dance in the Vampire Bund - 12 [1920x1080 Blu-ray FLAC][2F6DBC66].mkv",
            DumyTVShow(2,"Infinite Stratos",True):"[Stratos-Subs]_Infinite_Stratos_-_12_(1280x720_H.264_AAC)_[379759DB]",
            DumyTVShow(3,"Blue Exorcist",True):"[Stratos-Subs]_Ao no Exorcist_-_12_(1280x720)_[379759DB]",
            DumyTVShow(4,"Dexter",True):"Dexter S05E07 1080p HDTV DD5.1 H.264",
            }
showList =[x for x,y in showDict.items()]

showExceptions = {2:["IS"]
                  }

def dummy_get_scene_exceptions(id):
    try:
        return showExceptions[id]
    except:
        return []
    
scene_exceptions.get_scene_exceptions = dummy_get_scene_exceptions

def generator_get_tvdbid(show,name,list):
    def test(self):
        result = helpers.get_tvdbid(show.name,list, False)
        self.assertEqual(result, show.tvdbid)
    return test

def generator_parse_result_wrapper(show,name,list):
    def test(self):
        result = helpers.parse_result_wrapper(None, name, list, False)
        self.assertEqual(result.series_name , show.name)
    return test


class HelperTests(unittest.TestCase):
    def setUP(self):
        pass
      
for show,name in showDict.items():
    test_name = 'test_get_tvdbid_%s' % show.tvdbid
    test = generator_get_tvdbid(show, name, showList)
    setattr(HelperTests, test_name, test)

for show,name in showDict.items():
    test_name = 'test_parse_result_wrapper_%s' % show.tvdbid
    test = generator_parse_result_wrapper(show, name, showList)
    setattr(HelperTests, test_name, test)

if __name__ == '__main__':

    suite = unittest.TestLoader().loadTestsFromTestCase(HelperTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
