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



from sickbeard import common, db, exceptions, helpers, search
from sickbeard.logging import *
from sickbeard.common import * 

import datetime
import sqlite3
import threading
import time
import traceback

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
    
            Logger().log("Beginning search for todays episodes", DEBUG)
    
            epList = sickbeard.missingList + sickbeard.airingList
            
            if epList == None or len(epList) == 0:
                Logger().log("No episodes were found to download")
                return
            
            for curEp in epList:
                
                if curEp.show.paused:
                    Logger().log("Show "+curEp.show.name + " is currently paused, skipping search")
                    continue
                
                foundEpisodes = search.findEpisode(curEp)
                
                if len(foundEpisodes) == 0:
                    Logger().log("Unable to find download for " + curEp.prettyName())
                else:
                    # just use the first result for now
                    search.snatchEpisode(foundEpisodes[0])
                    
                time.sleep(3)

        # update our lists to reflect any changes we just made
        sickbeard.updateMissingList()
        sickbeard.updateAiringList()
        sickbeard.updateComingList()




    def _changeMissingEpisodes(self):
        
        Logger().log("Changing all old missing episodes to status MISSED")
        
        curDate = datetime.date.today().toordinal()

        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE status=" + str(UNAIRED) + " AND airdate < " + str(curDate))
        
        for sqlEp in sqlResults:
            
            try:
                show = helpers.findCertainShow(sickbeard.showList, int(sqlEp["showid"]))
            except exceptions.MultipleShowObjectsException:
                Logger().log("ERROR: expected to find a single show matching " + sqlEp["showid"]) 
                return None
            
            if show == None:
                Logger().log("Unable to find the show with ID "+str(sqlEp["showid"])+" in your show list! DB value was "+sqlEp, ERROR)
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