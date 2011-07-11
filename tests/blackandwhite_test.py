# coding=UTF-8
import unittest
import test_lib as test

import sys, os.path
sys.path.append(os.path.abspath('..'))
sys.path.append(os.path.abspath('../lib'))

from sickbeard.blackandwhitelist import *
from sickbeard.name_parser.parser import ParseResult


class BlackAndWhiteListTests(test.SickbeardTestDBCase):

    def setUp(self):
        super(BlackAndWhiteListTests, self).setUp()
    
    def tearDown(self):
        super(BlackAndWhiteListTests, self).tearDown()
        
    def test_insert(self):
        bwl = BlackAndWhiteList(1337)
        bwl.add_black_keyword("global", "german")

    def test_add(self):
        bwl = BlackAndWhiteList(1337)
        bwl.add_black_keyword("global", "german")
        bwl.add_black_keyword("global", "italian")
        self.assertEqual(bwl.blackDict["global"],["german","italian"])
        
    def test_set_for(self):
        bwl = BlackAndWhiteList(1337)
        bwl.set_black_keywords_for("global", ["german", "italian"])
        bwl.set_black_keywords_for("release_group", ["taka", "horrible"])
        
        self.assertEqual(bwl.blackDict["global"],["german","italian"])
        
        
    def test_white_success(self):
        bwl = BlackAndWhiteList(1337)
        bwl.set_white_keywords_for("release_group", ["SGKK"])
        
        result = ParseResult("[SGKK] Bleach - 326 (1280x720 h264 AAC) [3E33616B]")
        result.name = result.original_name
        result.release_group = "SGKK"
        
        self.assertTrue(bwl.is_valid_for_white(result))
        
    def test_white_success_multi(self):
        bwl = BlackAndWhiteList(1337)
        bwl.set_white_keywords_for("release_group", ["taka","SGKK"])
        
        result = ParseResult("[SGKK] Bleach - 326 (1280x720 h264 AAC) [3E33616B]",release_group="SGKK")
        result.name = result.original_name
        
        self.assertTrue(bwl.is_valid_for_white(result))
        
    def test_white_fail(self):
        bwl = BlackAndWhiteList(1337)
        bwl.set_white_keywords_for("global", ["SGKK"])
        
        result = ParseResult("[taka] Bleach - 326 (1280x720 h264 AAC) [3E33616B]",release_group="taka")
        result.name = result.original_name
        
        self.assertFalse(bwl.is_valid_for_white(result)) 
        
    def test_white_fail_no_group(self):
        bwl = BlackAndWhiteList(1337)
        bwl.set_white_keywords_for("release_group", ["taka","SGKK"])
        
        result = ParseResult("[SGKK] Bleach - 326 (1280x720 h264 AAC) [3E33616B]")
        result.name = result.original_name
        
        self.assertFalse(bwl.is_valid_for_white(result))
        
    def test_black_success(self):
        bwl = BlackAndWhiteList(1337)
        bwl.set_black_keywords_for("global", ["taka"])
        
        result = ParseResult("[SGKK] Bleach - 326 (1280x720 h264 AAC) [3E33616B]",release_group="SGKK")
        result.name = result.original_name
        
        self.assertTrue(bwl.is_valid_for_black(result))
        
    def test_black_success_no_group(self):
        bwl = BlackAndWhiteList(1337)
        bwl.set_black_keywords_for("release_group", ["taka"])
        
        result = ParseResult("[SGKK] Bleach - 326 (1280x720 h264 AAC) [3E33616B]",release_group="SGKK")
        result.name = result.original_name
        
        self.assertTrue(bwl.is_valid_for_black(result))
        
    def test_black_fail(self):
        bwl = BlackAndWhiteList(1337)
        bwl.set_black_keywords_for("global", ["SGKK"])
        
        result = ParseResult("[SGKK] Bleach - 326 (1280x720 h264 AAC) [3E33616B]",release_group="SGKK")
        result.name = result.original_name
        
        self.assertFalse(bwl.is_valid_for_black(result))
        
    def test_blackandwhite_success(self):
        
        bwl = BlackAndWhiteList(1337)
        bwl.set_black_keywords_for("global", ["taka"])
        bwl.set_white_keywords_for("global", ["SGKK"])
        
        result = ParseResult("[SGKK] Bleach - 326 (1280x720 h264 AAC) [3E33616B]",release_group="SGKK")
        result.name = result.original_name
        
        self.assertTrue(bwl.is_valid_for_black(result))
             

    def test_blackandwhite_success_multi(self):
        
        bwl = BlackAndWhiteList(1337)
        bwl.set_black_keywords_for("global", ["gg","horrible"])
        bwl.set_white_keywords_for("global", ["taka","SGKK"])
        
        result = ParseResult("[SGKK] Bleach - 326 (1280x720 h264 AAC) [3E33616B]",release_group="SGKK")
        result.name = result.original_name
        
        self.assertTrue(bwl.is_valid_for_black(result))
        
    def test_blackandwhite_fail(self):
        
        bwl = BlackAndWhiteList(1337)
        bwl.set_black_keywords_for("global", ["taka"])
        bwl.set_white_keywords_for("global", ["SGKK"])
        
        result = ParseResult("[taka] Bleach - 326 (1280x720 h264 AAC) [3E33616B]",release_group="taka")
        result.name = result.original_name
        
        self.assertFalse(bwl.is_valid_for_black(result))
        
    
if __name__ == '__main__':
    print "=================="
    print "STARTING - Black and White List TESTS"
    print "=================="
    print "######################################################################"
    suite = unittest.TestLoader().loadTestsFromTestCase(BlackAndWhiteListTests)
    unittest.TextTestRunner(verbosity=2).run(suite)