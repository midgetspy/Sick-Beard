import unittest

import sys, os.path
sys.path.append(os.path.abspath('..'))

from sickbeard import sceneHelpers

class SceneTests(unittest.TestCase):
    
    def _test_sceneToNormalShowNames(self, name, expected):
        result = sceneHelpers.sceneToNormalShowNames(name)
        self.assertTrue(len(set(expected).intersection(set(result))) == len(expected))

        dot_result = sceneHelpers.sceneToNormalShowNames(name.replace(' ','.'))
        dot_expected = [x.replace(' ','.') for x in expected]
        self.assertTrue(len(set(dot_expected).intersection(set(dot_result))) == len(dot_expected))
        
            
    def test_sceneToNormalShowNames(self):
        self._test_sceneToNormalShowNames('Show Name 2010', ['Show Name 2010', 'Show Name (2010)'])
        self._test_sceneToNormalShowNames('Show Name US', ['Show Name US', 'Show Name (US)'])
        self._test_sceneToNormalShowNames('Show Name AU', ['Show Name AU', 'Show Name (AU)'])
        self._test_sceneToNormalShowNames('Show Name CA', ['Show Name CA', 'Show Name (CA)'])
        self._test_sceneToNormalShowNames('Show and Name', ['Show and Name', 'Show & Name'])
        self._test_sceneToNormalShowNames('Show and Name 2010', ['Show and Name 2010', 'Show & Name 2010', 'Show and Name (2010)', 'Show & Name (2010)'])
        
        # failure cases
        self._test_sceneToNormalShowNames('Show Name 90210', ['Show Name 90210'])
        self._test_sceneToNormalShowNames('Show Name YA', ['Show Name YA'])

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(SceneTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
