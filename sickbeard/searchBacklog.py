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

import datetime
import threading
import time

from sickbeard import db, exceptions, helpers, search, scheduler
from sickbeard import logger
from sickbeard.common import *

class BacklogSearchScheduler(scheduler.Scheduler):

    def forceSearch(self):
        self.action._set_lastBacklog(1)
        self.lastRun = datetime.datetime.fromordinal(1)
        
    def nextRun(self):
        if self.action._lastBacklog <= 1:
            return datetime.date.today()
        else:
            return datetime.date.fromordinal(self.action._lastBacklog + self.action.cycleTime)

class BacklogSearcher:

    def __init__(self):
        
        self._lastBacklog = self._get_lastBacklog()
        self.cycleTime = 3
        self.lock = threading.Lock()
        self.amActive = False

    def searchBacklog(self):
        
        if self.amActive == True:
            logger.log("Backlog is still running, not starting it again", logger.DEBUG)
            return
        
        self.amActive = True
        
        self._get_lastBacklog()
        
        curDate = datetime.date.today().toordinal()
        
        if curDate - self._lastBacklog >= self.cycleTime:
            
            logger.log("Searching the database for a list of backlogged episodes to download")
            
            myDB = db.DBConnection()
            sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE status IN (" + str(BACKLOG) + ", " + str(DISCBACKLOG) + ")")
            
            if sqlResults == None or len(sqlResults) == 0:
                logger.log("No episodes were found in the backlog")
                self._set_lastBacklog(curDate)
                self.amActive = False
                return
            
            for sqlEp in sqlResults:
                
                try:
                    show = helpers.findCertainShow(sickbeard.showList, int(sqlEp["showid"]))
                except exceptions.MultipleShowObjectsException:
                    logger.log("ERROR: expected to find a single show matching " + sqlEp["showid"], logger.ERROR) 
                    continue

                curEp = show.getEpisode(sqlEp["season"], sqlEp["episode"])
                
                logger.log("Found backlog episode: " + curEp.prettyName(True), logger.DEBUG)
            
                foundResult = search.findEpisode(curEp)
                
                if not foundResult:
                    logger.log("Unable to find NZB for " + curEp.prettyName(True))
                
                else:
                    # just use the first result for now
                    search.snatchEpisode(foundResult, SNATCHED_BACKLOG)

                time.sleep(10)
                    
            self._set_lastBacklog(curDate)
            
        self.amActive = False
            
    
    
    def _searchBacklogForEp(self, curEp):
    
        foundResult = search.findEpisode(curEp)
        
        if not foundResult:
            logger.log("Unable to find NZB for " + curEp.prettyName(True))
        
        else:
            # just use the first result for now
            search.snatchEpisode(foundResult)

    
    def _get_lastBacklog(self):
    
        logger.log("Retrieving the last check time from the DB", logger.DEBUG)
        
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
    
        logger.log("Setting the last backlog in the DB to " + str(when), logger.DEBUG)
        
        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM info")

        if len(sqlResults) == 0:
            myDB.action("INSERT INTO info (last_backlog, last_TVDB) VALUES (?,?)", [str(when), 0])
        else:
            myDB.action("UPDATE info SET last_backlog=" + str(when))
        

    def run(self):
        self.searchBacklog()