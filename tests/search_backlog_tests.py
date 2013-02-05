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
from sickbeard import searchBacklog
from sickbeard.db_peewee import *

class SearchBacklogTests(test.SickbeardTestDBCase):

    def test_get_season_segments(self):
        self.loadFixtures()
        t = TvShow.select().where(TvShow.show_name == 'Fringe').get()
        e = t.episodes.where(TvEpisode.season == 5).first()
        e.airdate = datetime.date(2010, 1, 1).toordinal()
        e.save()

        b = searchBacklog.BacklogSearcher()
        result = b._get_season_segments(t.tvdb_id, datetime.date(2000, 1, 1))
        self.assertEqual(result, [e.season])

    def test_get_air_by_date_segments(self):
        self.loadFixtures()
        t = TvShow.select().where(TvShow.show_name == 'Fringe').get()
        e = t.episodes.where(TvEpisode.season == 5).first()
        e.airdate = datetime.date(2010, 1, 1).toordinal()
        e.save()

        b = searchBacklog.BacklogSearcher()
        result = b._get_air_by_date_segments(
            t.tvdb_id, datetime.date(2000, 1, 1)
        )
        self.assertEqual(result, [(82066, '2010-01')])

    def test_set_lastBacklog(self):
        Info.delete()
        b = searchBacklog.BacklogSearcher()
        result = b._set_lastBacklog(23)
        i = Info.select().first()
        self.assertEqual(i.last_backlog, 23)


if __name__ == '__main__':

    print "=================="
    print "STARTING - SearchBacklog TESTS"
    print "=================="
    print "######################################################################"
    unittest.main()
