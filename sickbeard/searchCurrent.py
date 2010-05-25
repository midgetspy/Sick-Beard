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
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import with_statement

from sickbeard import common, db, exceptions, helpers, search
from sickbeard import logger
from sickbeard.common import * 

import datetime
import threading
import time

class CurrentSearcher():
    
    def __init__(self):
        self.lock = threading.Lock()
    
    def searchForTodaysEpisodes(self):

        self._changeMissingEpisodes()

        # make sure our lists are up to date
        sickbeard.updateMissingList()
        sickbeard.updateAiringList()
        sickbeard.updateComingList()

        with self.lock:
            
            logger.log("Beginning search for new episodes on RSS")

            foundResults = search.searchForNeededEpisodes()
            
            if not len(foundResults):
                logger.log("No needed episodes found on the RSS feeds")
            else:
                for curResult in foundResults:
                    search.snatchEpisode(curResult)
                    time.sleep(2)
                

        # update our lists to reflect any changes we just made
        sickbeard.updateMissingList()
        sickbeard.updateAiringList()
        sickbeard.updateComingList()




    def _changeMissingEpisodes(self):
        
        logger.log("Changing all old missing episodes to status MISSED")
        
        curDate = datetime.date.today().toordinal()

        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE status=" + str(UNAIRED) + " AND airdate < " + str(curDate))
        
        for sqlEp in sqlResults:
            
            try:
                show = helpers.findCertainShow(sickbeard.showList, int(sqlEp["showid"]))
            except exceptions.MultipleShowObjectsException:
                logger.log("ERROR: expected to find a single show matching " + sqlEp["showid"]) 
                return None
            
            if show == None:
                logger.log("Unable to find the show with ID "+str(sqlEp["showid"])+" in your show list! DB value was "+str(sqlEp), logger.ERROR)
                return None
            
            ep = show.getEpisode(sqlEp["season"], sqlEp["episode"])
            with ep.lock:
                if ep.show.paused:
                    ep.status = SKIPPED
                else:
                    ep.status = MISSED
                ep.saveToDB()
            

    def run(self):
        self.searchForTodaysEpisodes()