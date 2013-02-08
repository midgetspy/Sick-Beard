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
from sickbeard.db_peewee import *
from lib import peewee

class DBPeeweeTests(test.SickbeardTestDBCase):

    def setUp(self):
        super(DBPeeweeTests, self).setUp()
        self.loadFixtures()

    def testHasMany(self):
      t = TvShow.select().where(TvShow.show_name == 'Fringe').get()
      self.assertEqual(t.episodes.count(), 5)
      for ep in t.episodes:
        self.assertEqual(ep.show.show_name, t.show_name)

    def testCountThenGet(self):
      t = TvShow.select()
      self.assertEqual(t.count(), 1)
      show = t.get()
      self.assertEqual(show.show_name, 'Fringe')

    def testNotFound(self):
      self.assertRaises(peewee.DoesNotExist,
          TvShow.select().where(TvShow.show_name == 'NotExist').get)

    def testSelectByShow(self):
      t = TvShow.select().get()
      q = TvEpisode.select().join(TvShow).where(TvShow.tvdb_id == t.tvdb_id)
      self.assertEqual(q.count(), 5)

    def testMultiWhereClauses(self):
      # You can chain multiple where clauses but they don't modify the object
      # you call it on, they return a clone.  Thus the query = query.where()
      query = TvEpisode.select(TvEpisode.name)
      query.where(TvEpisode.name == 'foo')
      query = query.where(TvEpisode.location == '')
      sql = query.sql()[0]
      self.assertIn('location', sql)

    def testNextEpisodeSelection(self):
        print [e.name for e in TvEpisode.select(TvEpisode, peewee.fn.Min(TvEpisode.airdate).alias('test'), TvShow).where(
            (TvEpisode.airdate > 733770)
        ).join(TvShow).order_by(
            TvEpisode.airdate.desc()
        )]

    def test_data_as_dict(self):
        t = TvEpisode.select().get()
        d = t.to_dict()
        self.assertIn('showid', d)


if __name__ == '__main__':

    print "=================="
    print "STARTING - DB PeeWee TESTS"
    print "=================="
    print "######################################################################"
    unittest.main()
