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

    def isInQueue(self, show):
        return show in self.updateQueue or show == self.currentlyUpdating

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

    def updateShowFromTVDB(self, show, force=False):
        
        if show == None:
            return None
        
        show.refreshDir()
        
        self._get_lastTVDB()
        
        newTime, updatedShows, updatedEpisodes = self._getUpdatedShows()
        Logger().log("Shows that have been updated since " + str(self._lastTVDB) + " are " + str(updatedShows), DEBUG)
        
        t = None
        
        try:
            t = tvdb_api.Tvdb(cache=False, lastTimeout=sickbeard.LAST_TVDB_TIMEOUT)
        except tvdb_exceptions.tvdb_error:
            Logger().log("Can't update from TVDB if we can't connect to it..", ERROR)
           
        doUpdate = updatedShows == None or int(show.tvdbid) in updatedShows or force
            
        if doUpdate:
            
            Logger().log("Updating " + str(show.name) + " (" + str(show.tvdbid) + ")")

            with show.lock:
                show.loadFromTVDB(cache=False)
                show.saveToDB()

            if force:
                Logger().log("Forcing update of all info from TVDB")
                show.loadEpisodesFromTVDB()
                
            else:
                # update each episode that has changed
                epList = sickbeard.getEpList(updatedEpisodes, show.tvdbid)
                Logger().log("Updated episodes for this show are " + str(epList), DEBUG)
                for curEp in epList:
                    Logger().log("Updating episode " + str(curEp.season) + "x" + str(curEp.episode))
                    curEp.loadFromTVDB(int(curEp.season), int(curEp.episode))
                    curEp.saveToDB()
                newestDBEp = self._getNewestDBEpisode(show)
                if t != None and newestDBEp != None:
                    s = t[int(show.tvdbid)]
                    
                    # make a list of all specials and all new eps
                    epList = []
                    epList += s.findNewerEps(newestDBEp[2])
                    if 0 in s:
                        epList += s[0].values()
                    for curEp in epList:
                        # add the episode
                        try:
                            newEp = show.getEpisode(int(curEp['seasonnumber']), int(curEp['episodenumber']))
                            Logger().log("Added episode "+show.name+" - "+str(newEp.season)+"x"+str(newEp.episode)+" to the DB.")
                        except exceptions.EpisodeNotFoundException as e:
                            Logger().log("Unable to create episode "+str(curEp["seasonnumber"])+"x"+str(curEp["episodenumber"])+", skipping", ERROR)
        
        # now that we've updated the DB from TVDB see if there's anything we can add from TVRage
        with show.lock:
            show.loadLatestFromTVRage()

        show.writeEpisodeNFOs()
        
        show.flushEpisodes()
        
        Logger().log("Update complete")


    def updateShowsFromTVDB(self):
    
        Logger().log("Beginning update of all shows", DEBUG)

        # check when we last updated
        self._get_lastTVDB()
        
        # get a list of shows that have changed since the last update
        newTime, updatedShows, updatedEpisodes = self._getUpdatedShows()
        Logger().log("Shows that have been updated since " + str(self._lastTVDB) + " are " + str(updatedShows) + " and now it's " + str(newTime), DEBUG)

        if newTime == 0:
            newTime = time.time()

        # if we didn't get a response from TVDB and it's been more than a day since our last update then force it
        forceUpdate = False
        if updatedShows == None:
            if datetime.datetime.now() - datetime.datetime.fromtimestamp(self._lastTVDB) >= datetime.timedelta(hours=24):
                forceUpdate = True
                Logger().log("No response received from TVDB and it's been more than 24 hrs since our last update so we're forcing all shows to update")
            else:
                Logger().log("No response received from TVDB, skipping update for now")
                return

        t = None
        try:
            t = tvdb_api.Tvdb(cache=False, lastTimeout=sickbeard.LAST_TVDB_TIMEOUT)
        except tvdb_exceptions.tvdb_error:
            Logger().log("Can't update from TVDB if we can't connect to it..", ERROR)

        allSuccessful = True

        # check each show to see if it's changed, if so then update it
        for show in sickbeard.showList:

            show.refreshDir()
            
            doUpdate = forceUpdate or int(show.tvdbid) in updatedShows

            Logger().log("Beginning update of show " + str(show.name) + " (" + str(show.tvdbid) + ")")

            try:
                if doUpdate:
                    with show.lock:
                        show.loadFromTVDB(cache=False)
                        show.saveToDB()
    
                    # update each episode that has changed
                    epList = sickbeard.getEpList(updatedEpisodes, show.tvdbid)
                    Logger().log("Updated episodes for this show are " + str(epList), DEBUG)
                    for curEp in epList:
                        Logger().log("Updating episode " + str(curEp.season) + "x" + str(curEp.episode))
                        curEp.loadFromTVDB(int(curEp.season), int(curEp.episode))
                        curEp.saveToDB()
                    
                    newestDBEp = self._getNewestDBEpisode(show)
                    if t != None and newestDBEp != None:
                        s = t[int(show.tvdbid)]
                    
                        # make a list of all specials and all new eps
                        epList = []
                        epList += s.findNewerEps(newestDBEp[2])
                        if 0 in s:
                            epList += s[0].values()
                        for curEp in epList:
                            # add the episode
                            try:
                                newEp = show.getEpisode(int(curEp['seasonnumber']), int(curEp['episodenumber']))
                                Logger().log("Added episode "+show.name+" - "+str(newEp.season)+"x"+str(newEp.episode)+" to the DB.")
                            except exceptions.EpisodeNotFoundException as e:
                                Logger().log("Unable to create episode "+show.name+" - "+str(newEp.season)+"x"+str(newEp.episode)+", skipping", ERROR)
            
            except tvdb_exceptions.tvdb_exception as e:
                allSuccessful = False
                Logger().log("There was an error with TVDB, show will only be updated from TVRage: "+str(e), ERROR)
                
                #show.loadEpisodesFromTVDB(False)

            show.flushEpisodes()
            
            with show.lock:
                Logger().log("Supplementing TVDB info with TVRage info if possible")
                show.loadLatestFromTVRage()
            
            if doUpdate:
                Logger().log("Update finished")
            else:
                Logger().log("Not updating show " + str(show.name) + " from TVDB, TVDB says it hasn't changed")

        # update our last update time if we didn't miss any shows on the way
        if allSuccessful:
            self._set_lastTVDB(newTime)

    def run(self):
        self.updateShowsFromTVDB()