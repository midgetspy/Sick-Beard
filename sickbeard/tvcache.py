import time
import datetime
import sqlite3
import urllib

import gzip
import urllib2
import StringIO

import sickbeard

from sickbeard import db
from sickbeard import logger
from sickbeard.common import *

from sickbeard import helpers

from lib.tvnamer.utils import FileParser
from lib.tvnamer import tvnamer_exceptions

class CacheDBConnection(db.DBConnection):

    def __init__(self, providerName):
        db.DBConnection.__init__(self, "cache.db")

        # Create the table if it's not already there
        try:
            sql = "CREATE TABLE "+providerName+" (name TEXT, season NUMERIC, episodes TEXT, tvrid NUMERIC, tvdbid NUMERIC, url TEXT, time NUMERIC, quality TEXT);"
            self.connection.execute(sql)
            self.connection.commit()
        except sqlite3.OperationalError, e:
            if str(e) != "table "+providerName+" already exists":
                raise

        # Create the table if it's not already there
        try:
            sql = "CREATE TABLE lastUpdate (provider TEXT, time NUMERIC);"
            self.connection.execute(sql)
            self.connection.commit()
        except sqlite3.OperationalError, e:
            if str(e) != "table lastUpdate already exists":
                raise

class TVCache():
    
    def __init__(self, providerName):
    
        self.providerName = providerName
        self.minTime = 10

    def _getDB(self):
        
        return CacheDBConnection(self.providerName)

    def _clearCache(self):
        
        myDB = self._getDB()
        
        myDB.action("DELETE FROM "+self.providerName+" WHERE 1")
    
    def updateCache(self):
        
        print "This should be overridden by implementing classes" 
        
        pass

    def _getLastUpdate(self):
        myDB = self._getDB()
        sqlResults = myDB.select("SELECT time FROM lastUpdate WHERE provider = ?", [self.providerName])
        
        if sqlResults:
            lastTime = int(sqlResults[0]["time"])
        else:
            lastTime = 0
        
        return datetime.datetime.fromtimestamp(lastTime)
    
    def setLastUpdate(self, toDate=None):
        
        if not toDate:
            toDate = datetime.datetime.today()
        
        myDB = self._getDB()
        myDB.upsert("lastUpdate",
                    {'time': int(time.mktime(toDate.timetuple()))},
                    {'provider': self.providerName})
    
    lastUpdate = property(_getLastUpdate)
    
    def shouldUpdate(self):
        # if we've updated recently then skip the update
        if datetime.datetime.today() - self.lastUpdate < datetime.timedelta(minutes=self.minTime):
            logger.log("Last update was too soon, using old cache", logger.DEBUG)
            return False
    
        return True

    def _addCacheEntry(self, name, url, season=None, episodes=None, tvdb_id=0, tvrage_id=0, quality=None, extraNames=[]):
        
        myDB = self._getDB()
        
        epInfo = None
        
        # if we don't have complete info then parse the filename to get it
        for curName in [name] + extraNames:
            try:
                myParser = FileParser(curName)
                epInfo = myParser.parse()
            except tvnamer_exceptions.InvalidFilename:
                logger.log("Unable to parse the filename "+curName+" into a valid episode", logger.DEBUG)
                continue
        
        if not epInfo:
            logger.log("Giving up because I'm unable to figure out what show/etc this is: "+name, logger.DEBUG)
            return False
        
        if not epInfo.seriesname:
            logger.log("No series name retrieved from "+name+", unable to cache it", logger.DEBUG)
            return False

        # if we need tvdb_id or tvrage_id then search the DB for them
        if not tvdb_id or not tvrage_id:
            
            # if we have only the tvdb_id, use the database
            if tvdb_id:
                showObj = helpers.findCertainShow(sickbeard.showList, tvdb_id)
                if showObj:
                    tvrage_id = showObj.tvrid
                else:
                    logger.log("We were given a TVDB id "+str(tvdb_id)+" but it doesn't match a show we have in our list, so leaving tvrage_id empty", logger.DEBUG)
                    tvrage_id = 0 
            
            # if we have only a tvrage_id then use the database
            elif tvrage_id:
                showObj = helpers.findCertainTVRageShow(sickbeard.showList, tvrage_id)
                if showObj:
                    tvdb_id = showObj.tvdbid
                else:
                    logger.log("We were given a TVRage id "+str(tvrage_id)+" but it doesn't match a show we have in our list, so leaving tvdb_id empty", logger.DEBUG)
                    tvdb_id = 0 
            
            # if they're both empty then fill out as much info as possible by searching the show name
            else:    

                showResult = helpers.searchDBForShow(epInfo.seriesname)
                if showResult:
                    logger.log(epInfo.seriesname+" was found to be show "+showResult[1]+" ("+str(showResult[0])+") in our DB.", logger.DEBUG)
                    tvdb_id = showResult[0]
                    showObj = helpers.findCertainShow(sickbeard.showList, tvdb_id)
                    if not showObj:
                        logger.log("This should never have happened, post a bug about this!", logger.ERROR)
                        raise Exception("BAD STUFF HAPPENED")
                    tvrage_id = showObj.tvrid
            
            
        if not season:
            season = epInfo.seasonnumber
        if not episodes:
            episodes = epInfo.episodenumbers

        episodeText = "|"+"|".join(map(str, episodes))+"|"
        
        
        # get the current timestamp
        curTimestamp = int(time.mktime(datetime.datetime.today().timetuple()))
        
        if not quality:
            if any(x in name.lower() for x in ("720p", "1080p", "x264")):
                quality = HD
            elif any(x in name.lower() for x in ("xvid", "divx")):
                quality = SD
            else:
                logger.log("Unable to figure out the quality of "+name+", assuming SD", logger.DEBUG)
                quality = SD
        
        myDB.action("INSERT INTO "+self.providerName+" (name, season, episodes, tvrid, tvdbid, url, time, quality) VALUES (?,?,?,?,?,?,?,?)",
                    [name, season, episodeText, tvrage_id, tvdb_id, url, curTimestamp, quality])
        
        

    def searchCache(self, show, season, episode, quality=ANY):
        
        myDB = self._getDB()
        
        sql = "SELECT * FROM "+self.providerName+" WHERE tvdbid = "+str(show.tvdbid)+ \
              " AND season = "+str(season)+" AND episodes LIKE '%|"+str(episode)+"|%'"

        if quality != ANY:
            sql += " AND quality = "+str(quality)
        
        return myDB.select(sql)
    
    def listPropers(self, date=None):
        
        myDB = self._getDB()
        
        sql = "SELECT * FROM "+self.providerName+" WHERE name LIKE '%.PROPER.%' OR name LIKE '%.REPACK.%'"
        
        if date != None:
            sql += " AND time >= "+str(int(time.mktime(date.timetuple())))
        
        #return filter(lambda x: x['tvdbid'] != 0, myDB.select(sql))
        return myDB.select(sql)

