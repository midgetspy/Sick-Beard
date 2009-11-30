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



import datetime
import sqlite3
import threading
import time
import traceback

from sickbeard import db, exceptions, helpers, search, scheduler
from sickbeard.logging import *
from sickbeard.common import *

class BacklogSearchScheduler(scheduler.Scheduler):

    def forceSearch(self):
        self.action._set_lastBacklog(1)
        self.lastRun = datetime.datetime.fromordinal(1)
        

class BacklogSearcher:

    def __init__(self):
        
        self._lastBacklog = self._get_lastBacklog()
        self.cycleTime = 3
        self.lock = threading.Lock()
        self.amActive = False

    def searchBacklog(self):
        
        if self.amActive == True:
            Logger().log("Backlog is still running, not starting it again", DEBUG)
            return
        
        self.amActive = True
        
        self._get_lastBacklog()
        
        curDate = datetime.date.today().toordinal()
        
        if curDate - self._lastBacklog >= self.cycleTime:
            
            Logger().log("Searching the database for a list of backlogged episodes to download")
            
            myDB = db.DBConnection()
            sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE status IN (" + str(BACKLOG) + ", " + str(DISCBACKLOG) + ")")
            
            if sqlResults == None or len(sqlResults) == 0:
                Logger().log("No episodes were found in the backlog")
                self._set_lastBacklog(curDate)
                self.amActive = False
                return
            
            for sqlEp in sqlResults:
                
                try:
                    show = helpers.findCertainShow(sickbeard.showList, int(sqlEp["showid"]))
                except exceptions.MultipleShowObjectsException:
                    Logger().log("ERROR: expected to find a single show matching " + sqlEp["showid"], ERROR) 
                    continue

                if show.paused:
                    Logger().log("Show is currently paused, skipping search")
                    continue
                                
                curEp = show.getEpisode(sqlEp["season"], sqlEp["episode"])
                
                Logger().log("Found backlog episode: " + curEp.prettyName(), DEBUG)
            
                foundNZBs = search.findEpisode(curEp)
                
                if len(foundNZBs) == 0:
                    Logger().log("Unable to find NZB for " + curEp.prettyName())
                
                else:
                    # just use the first result for now
                    search.snatchEpisode(foundNZBs[0])
                    
            self._set_lastBacklog(curDate)
            
        self.amActive = False
            
    
    
    def _searchBacklogForEp(self, curEp):
    
        foundNZBs = search.findEpisode(curEp)
        
        if len(foundNZBs) == 0:
            Logger().log("Unable to find NZB for " + curEp.prettyName())
        
        else:
            # just use the first result for now
            search.snatchEpisode(foundNZBs[0])

    
    def _get_lastBacklog(self):
    
        Logger().log("Retrieving the last check time from the DB", DEBUG)
        
        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM info")
        
        if len(sqlResults) == 0:
            lastBacklog = 1
        elif sqlResults[0]["last_backlog"] == None or sqlResults[0]["last_backlog"] == "":
            lastBacklog = 1
        else:
            lastBacklog = int(sqlResults[0]["last_backlog"])
    
        self._lastBacklog = lastBacklog
        return self._lastBacklog
    
    
    def _set_lastBacklog(self, when):
    
        Logger().log("Setting the last backlog in the DB to " + str(when), DEBUG)
        
        myDB = db.DBConnection()
        myDB.action("UPDATE info SET last_backlog=" + str(when))
        

    def run(self):
        self.searchBacklog()