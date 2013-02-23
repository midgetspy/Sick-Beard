# coding=UTF-8
# Author: Daniel Hobe <hobe@gmail.com>
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

import os
import unittest
import test_lib as test

import sickbeard
from sickbeard import tvcache
from sickbeard.providers import newznab
from sickbeard.db_peewee import *

TESTDIR = os.path.abspath('.')

def mock_getUrl(*args, **kwargs):
    return open(
        os.path.join(TESTDIR, 'fixtures/lolo_rss_fixture.txt')).read()

class TvcacheTests(test.SickbeardTestDBCase):
    def test_setup(self):
        n = newznab.NewznabProvider('testing', 'http://lolo.sickbeard.com/')
        n.getURL = mock_getUrl
        results = n.searchRSS()
        self.assertEqual(17, ProviderCache.select().count())
        n.cache._clearCache()
        self.assertEqual(0, ProviderCache.select().count())


if __name__ == '__main__':

    print "=================="
    print "STARTING - tvcache TESTS"
    print "=================="
    print "######################################################################"
    unittest.main()
