# Author: Nic Wolfe <nic@wolfeden.ca>
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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import sickbeard
import os.path
from lib import peewee

from sickbeard import db, common, helpers, logger
from sickbeard.providers.generic import GenericProvider
from sickbeard.db_peewee import *

from sickbeard import encodingKludge as ek
from sickbeard.name_parser.parser import NameParser, InvalidNameException 

class MainSanityCheck(db.DBSanityCheck):

    def check(self):
        self.fix_duplicate_shows()
        self.fix_duplicate_episodes()
        self.fix_orphan_episodes()

    def fix_duplicate_shows(self):

        sqlResults = self.connection.select("SELECT show_id, tvdb_id, COUNT(tvdb_id) as count FROM tv_shows GROUP BY tvdb_id HAVING count > 1")

        for cur_duplicate in sqlResults:

            logger.log(u"Duplicate show detected! tvdb_id: " + str(cur_duplicate["tvdb_id"]) + u" count: " + str(cur_duplicate["count"]), logger.DEBUG)

            cur_dupe_results = self.connection.select("SELECT show_id, tvdb_id FROM tv_shows WHERE tvdb_id = ? LIMIT ?",
                                           [cur_duplicate["tvdb_id"], int(cur_duplicate["count"])-1]
                                           )

            for cur_dupe_id in cur_dupe_results:
                logger.log(u"Deleting duplicate show with tvdb_id: " + str(cur_dupe_id["tvdb_id"]) + u" show_id: " + str(cur_dupe_id["show_id"]))
                self.connection.action("DELETE FROM tv_shows WHERE show_id = ?", [cur_dupe_id["show_id"]])

        else:
            logger.log(u"No duplicate show, check passed")

    def fix_duplicate_episodes(self):

        sqlResults = self.connection.select("SELECT showid, season, episode, COUNT(showid) as count FROM tv_episodes GROUP BY showid, season, episode HAVING count > 1")

        for cur_duplicate in sqlResults:

            logger.log(u"Duplicate episode detected! showid: " + str(cur_duplicate["showid"]) + u" season: "+str(cur_duplicate["season"]) + u" episode: "+str(cur_duplicate["episode"]) + u" count: " + str(cur_duplicate["count"]), logger.DEBUG)

            cur_dupe_results = self.connection.select("SELECT episode_id FROM tv_episodes WHERE showid = ? AND season = ? and episode = ? ORDER BY episode_id DESC LIMIT ?",
                                           [cur_duplicate["showid"], cur_duplicate["season"], cur_duplicate["episode"], int(cur_duplicate["count"])-1]
                                           )

            for cur_dupe_id in cur_dupe_results:
                logger.log(u"Deleting duplicate episode with episode_id: " + str(cur_dupe_id["episode_id"]))
                self.connection.action("DELETE FROM tv_episodes WHERE episode_id = ?", [cur_dupe_id["episode_id"]])

        else:
            logger.log(u"No duplicate episode, check passed")

    def fix_orphan_episodes(self):

        sqlResults = self.connection.select("SELECT episode_id, showid, tv_shows.tvdb_id FROM tv_episodes LEFT JOIN tv_shows ON tv_episodes.showid=tv_shows.tvdb_id WHERE tv_shows.tvdb_id is NULL")

        for cur_orphan in sqlResults:
            logger.log(u"Orphan episode detected! episode_id: " + str(cur_orphan["episode_id"]) + " showid: " + str(cur_orphan["showid"]), logger.DEBUG)
            logger.log(u"Deleting orphan episode with episode_id: "+str(cur_orphan["episode_id"]))
            self.connection.action("DELETE FROM tv_episodes WHERE episode_id = ?", [cur_orphan["episode_id"]])

        else:
            logger.log(u"No orphan episode, check passed")

# ======================
# = Main DB Migrations =
# ======================
# Add new migrations at the bottom of the list; subclass the previous migration.

class InitialSchema (db.SchemaUpgrade):
    def test(self):
        return self.hasTable("tv_shows")

    def execute(self):
        tables = [TvShow, TvEpisode, Info, History]
        with maindb.transaction():
            for table in tables:
                table.create_table()
