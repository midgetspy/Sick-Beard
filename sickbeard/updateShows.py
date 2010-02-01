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
import urllib2
import sqlite3
import traceback

import sickbeard

from sickbeard import db

from sickbeard import exceptions
from sickbeard import logger

from lib.BeautifulSoup import BeautifulStoneSoup
from lib.tvdb_api import tvdb_api, tvdb_exceptions

class ShowUpdateQueue():

    def __init__(self):
        
        self.updateQueue = []
        self.updateThread = None
        
        self.currentlyUpdating = None

    def isBeingUpdated(self, show):
        return show == self.currentlyUpdating

    def isInQueue(self, show):
        return show in [x.show for x in self.updateQueue]

    def addShowToQueue(self, show, force=False):
        self.updateQueue.append(SingleShowUpdater(show, force))

    def _doUpdateShow(self):

        # only start a new add task if one isn't already going
        if self.updateThread == None or self.updateThread.isAlive() == False:

            if self.currentlyUpdating != None:
                self.currentlyUpdating = None

            # if there's something in the queue then run it in a thread and take it out of the queue
            if len(self.updateQueue) > 0:
                logger.log("Starting new update task for show " + self.updateQueue[0].show.name)
                self.updateThread = threading.Thread(None, self.updateQueue[0].doUpdate, "UPDATESHOW-"+str(self.updateQueue[0].show.tvdbid))
                self.updateThread.start()
                self.currentlyUpdating = self.updateQueue[0].show
                del self.updateQueue[0]

    def run(self):
        self._doUpdateShow()


class SingleShowUpdater():
    
    def __init__(self, show, force=False):
        self.show = show
        self.force = force

    def doUpdate(self):
        su = ShowUpdater()
        logger.log("Updating single show "+self.show.name)
        su.updateShowFromTVDB(self.show, self.force)


class ShowUpdater():

    def __init__(self):
        self._lastTVDB = 0

    def _getUpdatedShows(self, timestamp=None):
        
        if timestamp == None:
            timestamp = self._lastTVDB
        
        if timestamp < 1:
            return (0, None, None)
        
        url = 'http://www.thetvdb.com/api/Updates.php?type=all&time=' + str(timestamp)
        
        try:
            urlObj = urllib2.urlopen(url, timeout=180)
        except IOError, e:
            logger.log("Unable to retrieve updated shows, assuming everything needs updating: " + str(e), logger.ERROR)
            return (0, None, None)
        
        soup = BeautifulStoneSoup(urlObj)
        
        newTime = int(soup.time.string)
        
        updatedSeries = []
        updatedEpisodes = []
        
        for curSeries in soup.findAll('series'):
            updatedSeries.append(int(curSeries.string))
            
        for curEpisode in soup.findAll('episode'):
            updatedEpisodes.append(int(curEpisode.string))
            
        return (newTime, updatedSeries, updatedEpisodes)

    def _get_lastTVDB(self):
    
        logger.log("Retrieving the last TVDB update time from the DB", logger.DEBUG)
        
        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM info")
        
        if len(sqlResults) == 0:
            lastTVDB = 0
        elif sqlResults[0]["last_tvdb"] == None or sqlResults[0]["last_tvdb"] == "":
            lastTVDB = 0
        else:
            lastTVDB = int(sqlResults[0]["last_tvdb"])
    
        logger.log("Last TVDB update changed from " + str(self._lastTVDB) + " to " + str(lastTVDB), logger.DEBUG)
        
        self._lastTVDB = lastTVDB
        
        return self._lastTVDB
    
    
    def _set_lastTVDB(self, when):
    
        logger.log("Setting the last TVDB update in the DB to " + str(int(when)), logger.DEBUG)
        
        myDB = db.DBConnection()

        sqlResults = myDB.select("SELECT * FROM info")

        if len(sqlResults) == 0:
            myDB.action("INSERT INTO info (last_backlog, last_TVDB) VALUES (?,?)", [1, str(when)])
        else:
            myDB.action("UPDATE info SET last_tvdb=" + str(int(when)))

    def _getNewestDBEpisode(self, show):
        
        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid="+str(show.tvdbid)+" AND tvdbid != -1 ORDER BY airdate DESC LIMIT 1")
        
        if len(sqlResults) == 0:
            return None
        
        sqlResults = sqlResults[0]
        
        if sqlResults["season"] == None or sqlResults["episode"] == None or sqlResults["airdate"] == None:
            return None
    
        logger.log("Newest DB episode for "+show.name+" was "+str(sqlResults['season'])+"x"+str(sqlResults['episode']), logger.DEBUG)
        
        return (int(sqlResults["season"]), int(sqlResults["episode"]), int(sqlResults["airdate"]))

    def refreshShow(self, show):

        logger.log("Performing refresh on "+show.name)

        show.refreshDir()
        
        show.writeEpisodeNFOs()


    def updateShowFromTVDB(self, show, force=False):
        
        if show == None:
            return None
        
        logger.log("Beginning update of "+show.name)
        
        # get episode list from DB
        logger.log("Loading all episodes from the database", logger.DEBUG)
        DBEpList = show.loadEpisodesFromDB()
        
        # get episode list from TVDB
        logger.log("Loading all episodes from theTVDB", logger.DEBUG)
        TVDBEpList = show.loadEpisodesFromTVDB(cache=not force)
        
        if TVDBEpList == None:
            logger.log("No data returned from TVDB, unable to update this show", logger.ERROR)
            return None
        
        # for each ep we found on TVDB delete it from the DB list
        for curSeason in TVDBEpList:
            for curEpisode in TVDBEpList[curSeason]:
                logger.log("Removing "+str(curSeason)+"x"+str(curEpisode)+" from the DB list", logger.DEBUG)
                if curSeason in DBEpList and curEpisode in DBEpList[curSeason]:
                    del DBEpList[curSeason][curEpisode]

        # for the remaining episodes in the DB list just delete them from the DB
        for curSeason in DBEpList:
            for curEpisode in DBEpList[curSeason]:
                logger.log("Permanently deleting episode "+str(curSeason)+"x"+str(curEpisode)+" from the database", logger.MESSAGE)
                curEp = show.getEpisode(curSeason, curEpisode)
                try:
                    curEp.deleteEpisode()
                except exceptions.EpisodeDeletedException:
                    pass
        
        # now that we've updated the DB from TVDB see if there's anything we can add from TVRage
        with show.lock:
            logger.log("Attempting to supplement show info with info from TVRage", logger.DEBUG)
            show.loadLatestFromTVRage()
            if show.tvrid == 0:
                show.setTVRID()

        self.refreshShow(show)
        
        logger.log("Flushing unneeded episodes from memory", logger.DEBUG)
        show.flushEpisodes()
        
        logger.log("Update complete")
        
        

    def updateShowsFromTVDB(self, force=False):
        
        logger.log("Beginning update of all shows")
        
        for show in sickbeard.showList:
            
            self.updateShowFromTVDB(show, force)

        logger.log("All shows' updates are complete.")

    def run(self):
        self.updateShowsFromTVDB()