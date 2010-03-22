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

class TVCache():
    
    def __init__(self, providerName):
    
        self.providerName = providerName

    def _getDB(self):
        
        return db.DBConnection("cache.db")

    def _clearCache(self):
        
        myDB = self._getDB()
        
        myDB.action("DELETE FROM "+self.providerName+" WHERE 1")
    
    def updateCache(self):
        
        print "This should be overridden by implementing classes" 
        
        pass

    def searchCache(self, show, season, episode, quality=ANY):
        
        myDB = self._getDB()
        
        sql = "SELECT * FROM "+self.providerName+" WHERE tvdbid = "+str(show.tvdbid)+ \
              " AND season = "+str(season)+" AND episode = "+str(episode)

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

