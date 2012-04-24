import datetime
import unittest
import test_lib as test

import sys, os.path
from sickbeard.tv import TVShow
sys.path.append(os.path.abspath('..'))
sys.path.append(os.path.abspath('../lib'))

import sickbeard # we need to import this so we can override the SYS_ENCODING which is needed by the parser
from sickbeard import helpers, scene_exceptions


DEBUG = VERBOSE = False
sickbeard.SYS_ENCODING = "UTF-8"
sickbeard.QUALITY_DEFAULT = 4
sickbeard.SEASON_FOLDERS_DEFAULT = 0


# warning: uses real data !!
testCases = {1:["Dance in the Vampire Bund",True,"Dance in the Vampire Bund"],
            248035:["Blue Exorcist",True,"Ao no Exorcist"],
            4:["Dexter",False,"Dexter"],
            }

class HelperTests(test.SickbeardTestDBCase):
    
    def setUp(self):
        super(HelperTests, self).setUp()
        sickbeard.scene_exceptions.retrieve_exceptions()

def _generator_get_tvdbid(tvdb_id, data):
    def test(self):
        show = TVShow(tvdb_id)
        show.name = data[0]
        if data[1]:
            show.anime = 1
        show.saveToDB()
        showList = [show]
        sceneName = data[2]
        result = helpers.get_tvdbid(sceneName, showList, False)
        self.assertEqual(result, show.tvdbid)
    return test

for tvdb_id, data in testCases.items():
    
    test_name = 'test_get_tvdbid_%s' % tvdb_id
    test = _generator_get_tvdbid(tvdb_id, data)
    setattr(HelperTests, test_name, test)

if __name__ == '__main__':

    suite = unittest.TestLoader().loadTestsFromTestCase(HelperTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
