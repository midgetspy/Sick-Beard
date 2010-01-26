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
import threading
import time
import urllib2
import sqlite3
import traceback

import sickbeard

from sickbeard import db

from sickbeard import exceptions
from sickbeard.logging import *

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
                Logger().log("Starting new update task for show " + self.updateQueue[0].show.name)
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
        Logger().log("Updating single show "+self.show.name)
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
        except IOError as e:
            Logger().log("Unable to retrieve updated shows, assuming everything needs updating: " + str(e), ERROR)
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
    
        Logger().log("Retrieving the last TVDB update time from the DB", DEBUG)
        
        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM info")
        
        if len(sqlResults) == 0:
            lastTVDB = 0
        elif sqlResults[0]["last_tvdb"] == None or sqlResults[0]["last_tvdb"] == "":
            lastTVDB = 0
        else:
            lastTVDB = int(sqlResults[0]["last_tvdb"])
    
        Logger().log("Last TVDB update changed from " + str(self._lastTVDB) + " to " + str(lastTVDB), DEBUG)
        
        self._lastTVDB = lastTVDB
        
        return self._lastTVDB
    
    
    def _set_lastTVDB(self, when):
    
        Logger().log("Setting the last TVDB update in the DB to " + str(int(when)), DEBUG)
        
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
    
        Logger().log("Newest DB episode for "+show.name+" was "+str(sqlResults['season'])+"x"+str(sqlResults['episode']), DEBUG)
        
        return (int(sqlResults["season"]), int(sqlResults["episode"]), int(sqlResults["airdate"]))

    def refreshShow(self, show):

        Logger().log("Performing refresh on "+show.name)

        show.refreshDir()
        
        show.writeEpisodeNFOs()


    def updateShowFromTVDB(self, show, force=False):
        
        if show == None:
            return None
        
        Logger().log("Beginning update of "+show.name)
        
        # get episode list from DB
        Logger().log("Loading all episodes from the database", DEBUG)
        DBEpList = show.loadEpisodesFromDB()
        
        # get episode list from TVDB
        Logger().log("Loading all episodes from theTVDB", DEBUG)
        TVDBEpList = show.loadEpisodesFromTVDB(cache=not force)
        
        if TVDBEpList == None:
            Logger().log("No data returned from TVDB, unable to update this show", ERROR)
            return None
        
        # for each ep we found on TVDB delete it from the DB list
        for curSeason in TVDBEpList:
            for curEpisode in TVDBEpList[curSeason]:
                Logger().log("Removing "+str(curSeason)+"x"+str(curEpisode)+" from the DB list", DEBUG)
                if curSeason in DBEpList and curEpisode in DBEpList[curSeason]:
                    del DBEpList[curSeason][curEpisode]

        # for the remaining episodes in the DB list just delete them from the DB
        for curSeason in DBEpList:
            for curEpisode in DBEpList[curSeason]:
                Logger().log("Permanently deleting episode "+str(curSeason)+"x"+str(curEpisode)+" from the database", MESSAGE)
                curEp = show.getEpisode(curSeason, curEpisode)
                try:
                    curEp.deleteEpisode()
                except exceptions.EpisodeDeletedException:
                    pass
        
        # now that we've updated the DB from TVDB see if there's anything we can add from TVRage
        with show.lock:
            Logger().log("Attempting to supplement show info with info from TVRage", DEBUG)
            show.loadLatestFromTVRage()
            if show.tvrid == 0:
                show.setTVRID()

        self.refreshShow(show)
        
        Logger().log("Flushing unneeded episodes from memory", DEBUG)
        show.flushEpisodes()
        
        Logger().log("Update complete")
        
        

    def updateShowsFromTVDB(self, force=False):
        
        Logger().log("Beginning update of all shows")
        
        for show in sickbeard.showList:
            
            self.updateShowFromTVDB(show, force)

        Logger().log("All shows' updates are complete.")

    def run(self):
        self.updateShowsFromTVDB()