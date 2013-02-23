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

import unittest
import test_lib as test
from sickbeard import name_cache
from sickbeard.db_peewee import *

class NameCacheTests(test.SickbeardTestDBCase):

    def test_addNameToCache(self):
        self.assertEqual(
            SceneName.select().where(SceneName.name == 'foo').count(),
            0
        )
        name_cache.addNameToCache('foo', 1)
        self.assertEqual(
            SceneName.select().where(SceneName.name == 'foo').count(),
            1
        )

    def test_retrieveNameFromCache(self):
        self.assertEqual(
            SceneName.select().where(SceneName.name == 'foo').count(),
            0
        )
        self.assertIsNone(name_cache.retrieveNameFromCache('foo'))
        name_cache.addNameToCache('foo', 1)
        self.assertIsNotNone(name_cache.retrieveNameFromCache('foo'))

    def test_clearCache(self):
        name_cache.addNameToCache('foo', 0)
        self.assertIsNotNone(name_cache.retrieveNameFromCache('foo'))
        name_cache.clearCache()
        self.assertIsNone(name_cache.retrieveNameFromCache('foo'))

if __name__ == '__main__':

    print "=================="
    print "STARTING - Name Cache TESTS"
    print "=================="
    print "######################################################################"
    unittest.main()

