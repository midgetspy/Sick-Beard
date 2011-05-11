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


showDict = {1:["Dance in the Vampire Bund",True,"Dance in the Vampire Bund"],
            2:["Infinite Stratos",True,"IS",True],
            3:["Blue Exorcist",True,"Ao no Exorcist"],
            4:["Dexter",True,"Dexter"],
            
            
            }

showExceptions = {2:["IS"],
                  3:["Ao no Exorcist"]
                  }

showList =[DumyTVShow(x,y[0],y[1]) for x,y in showDict.items()]

def dummy_get_scene_exceptions(id):
    try:
        return showExceptions[id]
    except:
        return []
    
scene_exceptions.get_scene_exceptions = dummy_get_scene_exceptions

def generator_get_tvdbid(show,sceneName,list):
    def test(self):
        result = helpers.get_tvdbid(sceneName,list, False)
        self.assertEqual(result, show.tvdbid)
    return test

class HelperTests(unittest.TestCase):
    def setUP(self):
        pass
      
for show in showList:
    sceneName = showDict[show.tvdbid][2]
    test_name = 'test_get_tvdbid_%s' % show.tvdbid
    test = generator_get_tvdbid(show, sceneName, showList)
    setattr(HelperTests, test_name, test)

if __name__ == '__main__':

    suite = unittest.TestLoader().loadTestsFromTestCase(HelperTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
