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

import datetime
import unittest
import test_lib as test
from sickbeard.db_peewee import *
from sickbeard import webserve

class WebserveTests(test.SickbeardTestDBCase):
    def test_ComingEpisodes(self):
        self.loadFixtures()
        t = TvShow().select().first()
        t.status = 'Continuing'
        t.save()
        e = TvEpisode.select().where(TvEpisode.name=='An Enemy of Fate').get()
        e.airdate = (datetime.date.today() + datetime.timedelta(days=3)).toordinal()
        e.save()

        w = webserve.WebInterface()
        w.comingEpisodes()


if __name__ == '__main__':

    print "=================="
    print "STARTING - Webserve TESTS"
    print "=================="
    print "######################################################################"
    unittest.main()
