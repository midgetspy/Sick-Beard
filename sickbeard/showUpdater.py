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

        piList = []
        graceperiod = datetime.timedelta(days=30)

        def lookup_latest(cur_tvdbid):
            myDB = db.DBConnection()

            sqlResults = None
            latest_aired = False
            next_upcoming = False

            # get latest aired episode to compare against today-graceperiod and today+graceperiod
            try:
                sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND season > '0' AND airdate > '1' AND status > '1' ORDER BY airdate DESC LIMIT 1", [cur_tvdbid])
            except:
                pass
            if sqlResults is not None and len(sqlResults) > 0:
                latest_aired = (sqlResults[0]['airdate'] >= (datetime.date.today() - graceperiod).toordinal() and sqlResults[0]['airdate'] <= (datetime.date.today() + graceperiod).toordinal())

            # get next upcoming UNAIRED episode to compare against today+graceperiod
            try:
                sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND season > '0' AND airdate > '1' AND status = '1' ORDER BY airdate ASC LIMIT 1", [cur_tvdbid])
            except:
                pass
            if sqlResults is not None and len(sqlResults) > 0:
                next_upcoming = (sqlResults[0]['airdate'] <= (datetime.date.today() + graceperiod).toordinal())

            # get last backlog date to compare against
            try:
                sqlResults = myDB.select("SELECT * FROM info")
            except:
                pass
            if sqlResults is not None and len(sqlResults) > 0:
                # if it is time for the full backlog, then just bypass 'ended' check
                if (sqlResults[0]['last_backlog'] <= (datetime.date.today() - datetime.timedelta(days=20)).toordinal()):
                    latest_aired = True

            myDB.connection.close()

            return (latest_aired, next_upcoming)

        for curShow in sickbeard.showList:

            try:

                if curShow.status != "Ended":
                    curQueueItem = sickbeard.showQueueScheduler.action.updateShow(curShow, True)  # @UndefinedVariable
                else:
                    # run logic against the current show latest aired and next unaired data to see if we should bypass 'ended' status
                    latest_aired, next_upcoming = lookup_latest(curShow.tvdbid)
                    # if either check is True then we go ahead and update, otherwise just refresh
                    if latest_aired or next_upcoming:
                        curQueueItem = sickbeard.showQueueScheduler.action.updateShow(curShow, True)  # @UndefinedVariable
                    else:
                        logger.log(u"Not updating episodes for show " + curShow.name + " because it's marked as ended and last/next episode is not within the grace period.", logger.DEBUG)
                        curQueueItem = sickbeard.showQueueScheduler.action.refreshShow(curShow, True)  # @UndefinedVariable

                piList.append(curQueueItem)

            except (exceptions.CantUpdateException, exceptions.CantRefreshException), e:
                logger.log(u"Automatic update failed: " + ex(e), logger.ERROR)

        ui.ProgressIndicators.setIndicator('dailyUpdate', ui.QueueProgressIndicator("Daily Update", piList))
