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
        sqlResults = TvShow.select(
            TvShow.show_id, peewee.fn.Count(TvShow.tvdb_id)
        ).group_by(TvShow.tvdb_id).having(
            peewee.fn.Count(TvShow.tvdb_id) > 1
        )

        for cur_duplicate in sqlResults:
            logger.log(u"Duplicate show detected! tvdb_id: " + str(cur_duplicate.tvdb_id) + u" count: " + str(cur_duplicate.count), logger.DEBUG)

            cur_dupe_results = TvShow.select().where(TvShow.tvdb_id == cur_duplicate.tvdb_id).limit(cur_duplicate.count - 1)

            for cur_dupe_id in cur_dupe_results:
                logger.log(u"Deleting duplicate show with tvdb_id: " + str(cur_dupe_id.tvdb_id) + u" show_id: " + str(cur_dupe_id.show_id))
                cur_dupe_id.delete_instance()

        else:
            logger.log(u"No duplicate show, check passed")

    def fix_duplicate_episodes(self):

        sqlResults = TvEpisode.select(TvEpisode, peewee.fn.Count(TvEpisode.show)).group_by(
            TvEpisode.show, TvEpisode.season, TvEpisode.episode
        ).having(
            peewee.fn.Count(TvEpisode.show) > 1
        )

        for cur_duplicate in sqlResults:
            logger.log(u"Duplicate episode detected! showid: " + str(cur_duplicate.show) + u" season: "+str(cur_duplicate.season) + u" episode: "+str(cur_duplicate.episode) + u" count: " + str(cur_duplicate.count), logger.DEBUG)

            cur_dupe_results = TvEpisode.select().where(
                (TvEpisode.show == cur_duplicate.show) &
                (TvEpisode.season == cur_duplicate.season) &
                (TvEpisode.episode == cur_duplicate.episode)
            ).order_by(TvEpisode.episode_id.desc()).limit(cur_duplicate.count-1)

            for cur_dupe_id in cur_dupe_results:
                logger.log(u"Deleting duplicate episode with episode_id: " + str(cur_dupe_id.episode_id))
                cur_dupe_id.delete_instance()

        else:
            logger.log(u"No duplicate episode, check passed")

    def fix_orphan_episodes(self):
        sqlResults = TvEpisode.select(TvEpisode, TvShow).where(
            TvShow.tvdb_id == None
        ).join(TvShow)

        for cur_orphan in sqlResults:
            logger.log(u"Orphan episode detected! episode_id: " + str(cur_orphan.episode_id) + " showid: " + str(cur_orphan.show.tvdb_id), logger.DEBUG)
            logger.log(u"Deleting orphan episode with episode_id: "+str(cur_orphan.episode_id))
            cur_orphan.delete_instance()

        else:
            logger.log(u"No orphan episode, check passed")

# ======================
# = Main DB Migrations =
# ======================
# Add new migrations at the bottom of the list; subclass the previous migration.

class InitialSchema (db.SchemaUpgrade):
    tables = [TvShow, TvEpisode, Info, History]
    def test(self):
        for table in self.tables:
            if not table.table_exists():
                return False
        return True

    def execute(self):
        with maindb.transaction():
            for table in self.tables:
                table.create_table()
