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
from sickbeard import ui
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
        
        self._resetPI()
        
    def _resetPI(self):
        self.percentDone = 0
        self.currentSearchInfo = {'title': 'Initializing'}

    def getProgressIndicator(self):
        if self.amActive:
            return ui.ProgressIndicator(self.percentDone, self.currentSearchInfo)
        else:
            return None

    def searchBacklog(self):

        if self.amActive == True:
            logger.log("Backlog is still running, not starting it again", logger.DEBUG)
            return
        
        self.amActive = True
        
        self._get_lastBacklog()
        
        curDate = datetime.date.today().toordinal()
        
        if not curDate - self._lastBacklog >= self.cycleTime:
            return

        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT DISTINCT(season), showid FROM tv_episodes eps, tv_shows shows WHERE season != 0 AND eps.showid = shows.tvdb_id AND shows.paused = 0")

        totalSeasons = float(len(sqlResults))
        numSeasonsDone = 0.0

        # go through every show and see if it needs any episodes
        for curShow in sickbeard.showList:

            if curShow.paused:
                continue

            logger.log("Checking backlog for show "+curShow.name)

            anyQualities, bestQualities = Quality.splitQuality(curShow.quality)
            
            sqlResults = myDB.select("SELECT DISTINCT(season) as season FROM tv_episodes WHERE showid = ? AND season > 0", [curShow.tvdbid])

            for curSeasonResult in sqlResults:
                curSeason = int(curSeasonResult["season"])

                logger.log("Seeing if we need any episodes from "+curShow.name+" season "+str(curSeason))
                self.currentSearchInfo = {'title': curShow.name + " Season "+str(curSeason)}

                # see if there is anything in this season worth searching for
                wantSeason = False
                statusResults = myDB.select("SELECT status FROM tv_episodes WHERE showid = ? AND season = ?", [curShow.tvdbid, curSeason])
                for curStatusResult in statusResults:
                    curCompositeStatus = int(curStatusResult["status"])
                    curStatus, curQuality = Quality.splitCompositeStatus(curCompositeStatus)
                    
                    if bestQualities:
                        highestBestQuality = max(bestQualities)
                    else:
                        highestBestQuality = 0
                    
                    # if we need a better one then say yes
                    if (curStatus in (DOWNLOADED, SNATCHED) and curQuality < highestBestQuality) or curStatus == WANTED:
                        wantSeason = True
                        break

                if not wantSeason:
                    logger.log("Nothing in season "+str(curSeason)+" needs to be downloaded, skipping this season", logger.DEBUG)
                    continue
                
                results = search.findSeason(curShow, curSeason)
                
                for curResult in results:
                    search.snatchEpisode(curResult)
                    time.sleep(5)
                
                numSeasonsDone += 1.0
                self.percentDone = (numSeasonsDone / totalSeasons) * 100.0

        self._set_lastBacklog(curDate)
            
        self.amActive = False
        self._resetPI()


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