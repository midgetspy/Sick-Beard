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

from collections import defaultdict

import unittest
import test_lib as test
from sickbeard import helpers
from sickbeard.db_peewee import *
import sickbeard

class HelpersTests(test.SickbeardTestDBCase):

    def test_searchDBForShow(self):
        self.assertIsNone(helpers.searchDBForShow('Testing Show'))
        TvShow(tvdb_id=1, show_name='Testing Show').save(force_insert=True)
        self.assertIsNotNone(helpers.searchDBForShow('Testing Show'))


if __name__ == '__main__':

    print "=================="
    print "STARTING - Config TESTS"
    print "=================="
    print "######################################################################"
    unittest.main()
