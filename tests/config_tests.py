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
from sickbeard import config
from sickbeard.db_peewee import *
import sickbeard

class ConfigMigratorTests(test.SickbeardTestDBCase):

    def test_migrate_v1(self):
        fake_cfg = defaultdict(dict)
        fake_cfg['General']['config_version'] = 0
        fake_cfg['General']['naming_dates'] = 0
        fake_cfg['General']['naming_multi_ep_type'] = 1
        fake_cfg['General']['season_folders_format'] = 'Season %02d'

        t = TvShow(tvdb_id=1, flatten_folders=False)
        t.save(force_insert=True)

        c = config.ConfigMigrator(fake_cfg)
        c._migrate_v1()

        self.assertTrue(sickbeard.NAMING_PATTERN.startswith('Season %0S'))

        TvShow.delete().execute()
        t = TvShow(tvdb_id=1, flatten_folders=True)
        t.save(force_insert=True)
        c._migrate_v1()

        self.assertEqual(
                TvShow.select().where(TvShow.flatten_folders == False).count(),
                0)


if __name__ == '__main__':

    print "=================="
    print "STARTING - Config TESTS"
    print "=================="
    print "######################################################################"
    unittest.main()
