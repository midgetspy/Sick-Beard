import unittest

import sys
import os.path
sys.path.append(os.path.abspath('..'))

from sickbeard import config


class QualityTests(unittest.TestCase):

    def test_clean_url(self):
        self.assertEqual(config.clean_url("https://subdomain.domain.tld/endpoint"), "https://subdomain.domain.tld/endpoint")
        self.assertEqual(config.clean_url("google.com/xml.rpc"), "http://google.com/xml.rpc")
        self.assertEqual(config.clean_url("google.com"), "http://google.com/")
        self.assertEqual(config.clean_url("http://www.example.com/folder/"), "http://www.example.com/folder/")

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(QualityTests)
    unittest.TextTestRunner(verbosity=2).run(suite)
