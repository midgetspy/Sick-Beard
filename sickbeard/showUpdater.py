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

import sickbeard

from sickbeard import logger
from sickbeard import exceptions
from sickbeard import ui
from sickbeard import db
from sickbeard.exceptions import ex

class ShowUpdater():

    def __init__(self):
        self.updateInterval = datetime.timedelta(hours=1)

    def run(self, force=False):

        # update at 3 AM
        updateTime = datetime.time(hour=3)

        logger.log(u"Checking update interval", logger.DEBUG)

        hourDiff = datetime.datetime.today().time().hour - updateTime.hour

        # if it's less than an interval after the update time then do an update (or if we're forcing it)
        if hourDiff >= 0 and hourDiff < self.updateInterval.seconds/3600 or force:
            logger.log(u"Doing full update on all shows")
        else:
            return

        myDB = db.DBConnection()

        piList = []

        # Shows where the last Episodes airdate is unknown, update them for 365 days (1 year) after the last known Airdate
        unknown_aired_min = (datetime.date.today() - datetime.timedelta(days=365)).toordinal()
        # Shows where the last Episodes airdate is known, update them for 90 days after the last known Airdate
        last_aired_min = (datetime.date.today() - datetime.timedelta(days=90)).toordinal()

        for curShow in sickbeard.showList:

            sqlResults = {}
            last_known_airdate = 0
            last_ep_airdate = 0

            try:
                sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? ORDER BY airdate DESC", [curShow.tvdbid])
            except:
                pass

            try:
                if sqlResults != None and len(sqlResults) > 0:
                    sortedsql = sorted(sqlResults, key=lambda x: (-x['season'], -x['episode']))
                    # get last known airdate
                    last_known_airdate = sqlResults[0]['airdate']
                    # get airdate for the last episode
                    last_ep_airdate = sortedsql[0]['airdate']
                else:
                    last_known_airdate = 0
                    last_ep_airdate = 0
            except:
                last_known_airdate = 0
                last_ep_airdate = 0

            try:

                if curShow.status != "Ended" or (last_ep_airdate <= 1 and last_known_airdate >= unknown_aired_min) or (last_ep_airdate > 1 and last_known_airdate >= last_aired_min):
                    curQueueItem = sickbeard.showQueueScheduler.action.updateShow(curShow, True) #@UndefinedVariable
                else:
                    #TODO: maybe I should still update specials?
                    logger.log(u"Not updating episodes for show "+curShow.name+" because it's marked as ended.", logger.DEBUG)
                    curQueueItem = sickbeard.showQueueScheduler.action.refreshShow(curShow, True) #@UndefinedVariable

                piList.append(curQueueItem)

            except (exceptions.CantUpdateException, exceptions.CantRefreshException), e:
                logger.log(u"Automatic update failed: " + ex(e), logger.ERROR)

        ui.ProgressIndicators.setIndicator('dailyUpdate', ui.QueueProgressIndicator("Daily Update", piList))
