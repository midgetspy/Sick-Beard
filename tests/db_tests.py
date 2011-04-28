# coding=UTF-8
import unittest
import test_lib as test

import sys, os.path
sys.path.append(os.path.abspath('..'))
sys.path.append(os.path.abspath('../lib'))


        
class DBBasicTests(test.SickbeardTestDBCase):

    def setUp(self):
        super(DBBasicTests, self).setUp()
        self.db = test.db.DBConnection()
        
    def test_select(self):
        self.db.select("SELECT * FROM tv_episodes WHERE showid = ? AND location != ''", [0000])

    
if __name__ == '__main__':
    print "=================="
    print "STARTING - DB TESTS"
    print "=================="
    print "######################################################################"
    suite = unittest.TestLoader().loadTestsFromTestCase(DBBasicTests)
    unittest.TextTestRunner(verbosity=2).run(suite)