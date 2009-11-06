from sickbeard import common, db, exceptions, helpers, nzb
from sickbeard.logging import *
from sickbeard.common import * 

import datetime
import sqlite3
import threading
import time
import traceback

class CurrentSearchScheduler():

    def __init__(self):
        
        self.isActive = False
        self.lastRun = datetime.datetime.fromordinal(1)
        self.searcher = CurrentSearcher()
        self.cycleTime = datetime.timedelta(minutes=10)
        
        self.thread = None
        self.initThread()
        
        self.abort = False
    
    def initThread(self):
        if self.thread == None or not self.thread.isAlive():
            self.thread = threading.Thread(None, self.runSearch, "SEARCH")
    
    def runSearch(self):
        
        while True:
            
            currentTime = datetime.datetime.now()
            
            if currentTime - self.lastRun > self.cycleTime:
                self.lastRun = currentTime
                try:
                    self.searcher.searchForTodaysEpisodes()
                except Exception as e:
                    Logger().log("Search generated an exception: " + str(e), ERROR)
                    Logger().log(traceback.format_exc(), DEBUG)
            
            if self.abort:
                self.abort = False
                self.thread = None
                return
            
            time.sleep(1) 
            

class CurrentSearcher():
    
    def __init__(self):
        self.lock = threading.Lock()
        self.cycleTime = datetime.timedelta(minutes=5)
    
    def searchForTodaysEpisodes(self):

        self._changeMissingEpisodes()

        sickbeard.updateMissingList()
        sickbeard.updateAiringList()
        sickbeard.updateComingList()

        with self.lock:
    
            Logger().log("Beginning search for todays episodes", DEBUG)
    
            #epList = self._getEpisodesToSearchFor()
            epList = sickbeard.missingList + sickbeard.airingList
            
            if epList == None or len(epList) == 0:
                Logger().log("No episodes were found to download")
                return
            
            for curEp in epList:
                
                foundNZBs = nzb.findNZB(curEp)
                
                if len(foundNZBs) == 0:
                    Logger().log("Unable to find NZB for " + curEp.prettyName())
                
                else:
                    
                    # just use the first result for now
                    nzb.snatchNZB(foundNZBs[0])



    def _changeMissingEpisodes(self):
        
        myDB = db.DBConnection()
        myDB.checkDB()

        curDate = datetime.date.today().toordinal()

        Logger().log("Changing all old missing episodes to status MISSED")
        
        try:
            sql = "SELECT * FROM tv_episodes WHERE status=" + str(UNAIRED) + " AND airdate < " + str(curDate)
            sqlResults = myDB.connection.execute(sql).fetchall()
        except sqlite3.DatabaseError as e:
            Logger().log("Fatal error executing query '" + sql + "': " + str(e), ERROR)
            raise
    
        for sqlEp in sqlResults:
            
            try:
                show = helpers.findCertainShow (sickbeard.showList, int(sqlEp["showid"]))
            except exceptions.MultipleShowObjectsException:
                Logger().log("ERROR: expected to find a single show matching " + sqlEp["showid"]) 
                return None
            ep = show.getEpisode(sqlEp["season"], sqlEp["episode"], True)
            with ep.lock:
                ep.status = MISSED
                ep.saveToDB()


    def _getEpisodesToSearchFor(self):
    
        myDB = db.DBConnection()
        myDB.checkDB()
        
        curDate = datetime.date.today().toordinal()
        sqlResults = []
        
        foundEps = []
        
        self._changeMissingEpisodes()
        
        Logger().log("Searching the database for a list of new episodes to download")
        
        try:
            sql = "SELECT * FROM tv_episodes WHERE status IN (" + str(UNKNOWN) + ", " + str(UNAIRED) + ", " + str(PREDOWNLOADED) + ", " + str(MISSED) + ") AND airdate <= " + str(curDate)
            Logger().log("SQL: " + sql, DEBUG)
            sqlResults = myDB.connection.execute(sql).fetchall()
        except sqlite3.DatabaseError as e:
            Logger().log("Fatal error executing query '" + sql + "': " + str(e), ERROR)
            raise
    
        for sqlEp in sqlResults:
            print "FFS the status is " + str(sqlEp["status"])
            
            try:
                show = helpers.findCertainShow (sickbeard.showList, int(sqlEp["showid"]))
            except exceptions.MultipleShowObjectsException:
                Logger().log("ERROR: expected to find a single show matching " + sqlEp["showid"]) 
                return None
            ep = show.getEpisode(sqlEp["season"], sqlEp["episode"], True)
            foundEps.append(ep)
            Logger().log("Added " + ep.prettyName() + " to the list of episodes to download (status=" + str(ep.status))
        
        return foundEps
