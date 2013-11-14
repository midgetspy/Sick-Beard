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

import datetime
import os

import sickbeard

from sickbeard import logger
from sickbeard import exceptions
from sickbeard import ui
from sickbeard.exceptions import ex
from sickbeard import encodingKludge as ek
from sickbeard import db

class ShowUpdater():

    def __init__(self):
        self.updateInterval = datetime.timedelta(hours=1)

    def run(self, force=False):

        # update at 3 AM
        updateTime = datetime.time(hour=3)

        logger.log(u"Checking update interval", logger.DEBUG)

        hourDiff = datetime.datetime.today().time().hour - updateTime.hour

        # if it's less than an interval after the update time then do an update (or if we're forcing it)
        if hourDiff >= 0 and hourDiff < self.updateInterval.seconds / 3600 or force:
            logger.log(u"Doing full update on all shows")
        else:
            return

        if sickbeard.CACHE_DIR:
            cache_dir = sickbeard.TVDB_API_PARMS['cache']
            logger.log(u"Trying to clean cache folder " + cache_dir)

            # Does our cache_dir exists
            if not ek.ek(os.path.isdir, cache_dir):
                logger.log(u"Can't clean " + cache_dir + " if it doesn't exist", logger.WARNING)
            else:
                now = datetime.datetime.now()
                max_age = datetime.timedelta(hours=12)
                # Get all our cache files
                cache_files = ek.ek(os.listdir, cache_dir)

                for cache_file in cache_files:
                    cache_file_path = ek.ek(os.path.join, cache_dir, cache_file)

                    if ek.ek(os.path.isfile, cache_file_path):
                        cache_file_modified = datetime.datetime.fromtimestamp(ek.ek(os.path.getmtime, cache_file_path))

                        if now - cache_file_modified > max_age:
                            try:
                                ek.ek(os.remove, cache_file_path)
                            except OSError, e:
                                logger.log(u"Unable to clean " + cache_dir + ": " + repr(e) + " / " + str(e), logger.WARNING)
                                break

        def should_update(curShow, update_date=datetime.date.today()):

            # if show is not 'Ended' always update
            if curShow.status == 'Continuing':
                return True

            # run logic against the current show latest aired and next unaired data to see if we should bypass 'Ended' status
            cur_tvdbid = curShow.tvdbid

            graceperiod = datetime.timedelta(days=30)

            myDB = db.DBConnection()
            last_airdate = datetime.date.fromordinal(1)

            # get latest aired episode to compare against today - graceperiod and today + graceperiod
            sql_result = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND season > '0' AND airdate > '1' AND status > '1' ORDER BY airdate DESC LIMIT 1", [cur_tvdbid])

            if sql_result:
                last_airdate = datetime.date.fromordinal(sql_result[0]['airdate'])
                if last_airdate >= (update_date - graceperiod) and last_airdate <= (update_date + graceperiod):
                    return True

            # get next upcoming UNAIRED episode to compare against today + graceperiod
            sql_result = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND season > '0' AND airdate > '1' AND status = '1' ORDER BY airdate ASC LIMIT 1", [cur_tvdbid])

            if sql_result:
                next_airdate = datetime.date.fromordinal(sql_result[0]['airdate'])
                if next_airdate <= (update_date + graceperiod):
                    return True

            return False

        piList = []

        for curShow in sickbeard.showList:

            try:

                # if should_update check returns True then update, otherwise just refresh
                if should_update(curShow):
                    curQueueItem = sickbeard.showQueueScheduler.action.updateShow(curShow, True)  # @UndefinedVariable
                else:
                    logger.log(u"Not updating episodes for show " + curShow.name + " because it's marked as ended and last/next episode is not within the grace period.", logger.DEBUG)
                    curQueueItem = sickbeard.showQueueScheduler.action.refreshShow(curShow, True)  # @UndefinedVariable

                piList.append(curQueueItem)

            except (exceptions.CantUpdateException, exceptions.CantRefreshException), e:
                logger.log(u"Automatic update failed: " + ex(e), logger.ERROR)

        ui.ProgressIndicators.setIndicator('dailyUpdate', ui.QueueProgressIndicator("Daily Update", piList))
