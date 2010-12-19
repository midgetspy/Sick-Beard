import unittest

import sys, os.path
sys.path.append(os.path.abspath('..'))

from sickbeard import sceneHelpers, common

class SceneTests(unittest.TestCase):
    
    def _test_sceneToNormalShowNames(self, name, expected):
        result = sceneHelpers.sceneToNormalShowNames(name)
        self.assertTrue(len(set(expected).intersection(set(result))) == len(expected))

        dot_result = sceneHelpers.sceneToNormalShowNames(name.replace(' ','.'))
        dot_expected = [x.replace(' ','.') for x in expected]
        self.assertTrue(len(set(dot_expected).intersection(set(dot_result))) == len(dot_expected))
        
    def _test_allPossibleShowNames(self, name, tvdbid=0, tvrname=None, expected=[]):
        
        class Show:
            def __init__(self, name, tvdbid, tvrname):
                self.name = name
                self.tvdbid = tvdbid
                self.tvrname = tvrname
        
        
        result = sceneHelpers.allPossibleShowNames(Show(name, tvdbid, tvrname))
        self.assertTrue(len(set(expected).intersection(set(result))) == len(expected))

    def _test_filterBadReleases(self, name, expected):
        result = sceneHelpers.filterBadReleases(name)
        self.assertEqual(result, expected)

    def test_sceneToNormalShowNames(self):
        self._test_sceneToNormalShowNames('Show Name 2010', ['Show Name 2010', 'Show Name (2010)'])
        self._test_sceneToNormalShowNames('Show Name US', ['Show Name US', 'Show Name (US)'])
        self._test_sceneToNormalShowNames('Show Name AU', ['Show Name AU', 'Show Name (AU)'])
        self._test_sceneToNormalShowNames('Show Name CA', ['Show Name CA', 'Show Name (CA)'])
        self._test_sceneToNormalShowNames('Show and Name', ['Show and Name', 'Show & Name'])
        self._test_sceneToNormalShowNames('Show and Name 2010', ['Show and Name 2010', 'Show & Name 2010', 'Show and Name (2010)', 'Show & Name (2010)'])
        self._test_sceneToNormalShowNames('show name us', ['show name us', 'show name (us)'])
        self._test_sceneToNormalShowNames('Show And Name', ['Show And Name', 'Show & Name'])
        
        # failure cases
        self._test_sceneToNormalShowNames('Show Name 90210', ['Show Name 90210'])
        self._test_sceneToNormalShowNames('Show Name YA', ['Show Name YA'])

    def test_allPossibleShowNames(self):
        common.sceneExceptions[-1] = ['Exception Test']
        common.countryList['Full Country Name'] = 'FCN'
        
        self._test_allPossibleShowNames('Show Name', expected=['Show Name'])
        self._test_allPossibleShowNames('Show Name', -1, expected=['Show Name', 'Exception Test'])
        self._test_allPossibleShowNames('Show Name', tvrname='TVRage Name', expected=['Show Name', 'TVRage Name'])
        self._test_allPossibleShowNames('Show Name FCN', expected=['Show Name FCN', 'Show Name (Full Country Name)'])
        self._test_allPossibleShowNames('Show Name (FCN)', expected=['Show Name (FCN)', 'Show Name (Full Country Name)'])
        self._test_allPossibleShowNames('Show Name Full Country Name', expected=['Show Name Full Country Name', 'Show Name (FCN)'])
        self._test_allPossibleShowNames('Show Name (Full Country Name)', expected=['Show Name (Full Country Name)', 'Show Name (FCN)'])
        self._test_allPossibleShowNames('Show Name (FCN)', -1, 'TVRage Name', expected=['Show Name (FCN)', 'Show Name (Full Country Name)', 'Exception Test', 'TVRage Name'])

    def test_filterBadReleases(self):
        
        self._test_filterBadReleases('Show.S02.German.Stuff-Grp', False)
        self._test_filterBadReleases('Show.S02.Some.German.Stuff-Grp', False)
        self._test_filterBadReleases('German.Show.S02.Some.Stuff-Grp', True)
        self._test_filterBadReleases('Show.S02.This.Is.German', False)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        suite = unittest.TestLoader().loadTestsFromName('scene_helpers_tests.SceneTests.test_'+sys.argv[1])
    else:
        suite = unittest.TestLoader().loadTestsFromTestCase(SceneTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
