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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import time
import datetime
import sqlite3

import sickbeard

from sickbeard import db
from sickbeard import logger
from sickbeard.common import Quality

from sickbeard import helpers, exceptions, show_name_helpers, scene_exceptions
from sickbeard import name_cache
from sickbeard.exceptions import ex

#import xml.etree.cElementTree as etree
import xml.dom.minidom

from lib.tvdb_api import tvdb_api, tvdb_exceptions
from sickbeard.completparser import CompleteParser


class CacheDBConnection(db.DBConnection):

    def __init__(self, providerName):
        db.DBConnection.__init__(self, "cache.db")

        # Create the table if it's not already there
        try:
            sql = "CREATE TABLE "+providerName+" (name TEXT, season NUMERIC, episodes TEXT, tvrid NUMERIC, tvdbid NUMERIC, url TEXT, time NUMERIC, quality TEXT, release_group TEXT);"
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

    def __init__(self, provider):

        self.provider = provider
        self.providerID = self.provider.getID()
        self.minTime = 10

    def _getDB(self):

        return CacheDBConnection(self.providerID)

    def _clearCache(self):

        myDB = self._getDB()

        myDB.action("DELETE FROM "+self.providerID+" WHERE 1")

    def _getRSSData(self):

        data = None

        return data

    def _checkAuth(self, data):
        return True

    def _checkItemAuth(self, title, url):
        return True

    def updateCache(self):

        if not self.shouldUpdate():
            return

        data = self._getRSSData()

        # as long as the http request worked we count this as an update
        if data:
            self.setLastUpdate()
        else:
            return []

        # now that we've loaded the current RSS feed lets delete the old cache
        logger.log(u"Clearing "+self.provider.name+" cache and updating with new information")
        self._clearCache()

        if not self._checkAuth(data):
            raise exceptions.AuthException("Your authentication info for "+self.provider.name+" is incorrect, check your config")

        try:
            parsedXML = xml.dom.minidom.parseString(data)
            items = parsedXML.getElementsByTagName('item')
        except Exception, e:
            logger.log(u"Error trying to load "+self.provider.name+" RSS feed: "+ex(e), logger.ERROR)
            logger.log(u"Feed contents: "+repr(data), logger.DEBUG)
            return []

        if parsedXML.documentElement.tagName != 'rss':
            logger.log(u"Resulting XML from "+self.provider.name+" isn't RSS, not parsing it", logger.ERROR)
            return []

        for item in items:

            self._parseItem(item)

    def _translateLinkURL(self, url):
        return url.replace('&amp;','&')


    def _parseItem(self, item):
        """Return None
        parse a single rss feed item and add its info to the chache
        will check for needed infos
        """
        title = helpers.get_xml_text(item.getElementsByTagName('title')[0])
        url = helpers.get_xml_text(item.getElementsByTagName('link')[0])

        self._checkItemAuth(title, url)

        # we at least need a title and url, if one is missing stop
        if not title or not url:
            logger.log(u"The XML returned from the "+self.provider.name+" feed is incomplete, this result is unusable", logger.ERROR)
            return

        url = self._translateLinkURL(url)

        logger.log(u"Adding item from RSS to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

    def _getLastUpdate(self):
        myDB = self._getDB()
        sqlResults = myDB.select("SELECT time FROM lastUpdate WHERE provider = ?", [self.providerID])

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
                    {'provider': self.providerID})

    lastUpdate = property(_getLastUpdate)

    def shouldUpdate(self):
        # if we've updated recently then skip the update
        if datetime.datetime.today() - self.lastUpdate < datetime.timedelta(minutes=self.minTime):
            logger.log(u"Last update was too soon, using old cache: today()-"+str(self.lastUpdate)+"<"+str(datetime.timedelta(minutes=self.minTime)), logger.DEBUG)
            return False

        return True

    def _addCacheEntry(self, name, url, season=None, episodes=None, tvdb_id=0, tvrage_id=0, quality=None, extraNames=[]):
        """Return False|None
        Parse the name and try to get as much info out of it as we can
        Will use anime regex's if this is called from fanzub
        On a succesfull parse it will add the parsed infos into the cache.db
        This dosen't mean the parsed result is usefull
        """
        myDB = self._getDB()

        # if we don't have complete info then parse the filename to get it
        for curName in [name] + extraNames:
            cp = CompleteParser()
            cpr = cp.parse(curName)
            if cpr:
                break
        else:
            return False

        episodeText = "|"+"|".join(map(str, cpr.episodes))+"|"
        # get the current timestamp
        curTimestamp = int(time.mktime(datetime.datetime.today().timetuple()))
        myDB.action("INSERT INTO "+self.providerID+" (name, season, episodes, tvrid, tvdbid, url, time, quality, release_group) VALUES (?,?,?,?,?,?,?,?,?)",
                    [name, cpr.season, episodeText, 0, cpr.tvdbid, url, curTimestamp, cpr.quality, cpr.release_group])


    def searchCache(self, episode, manualSearch=False):
        neededEps = self.findNeededEpisodes(episode, manualSearch)
        return neededEps[episode]

    def listPropers(self, date=None, delimiter="."):

        myDB = self._getDB()

        sql = "SELECT * FROM "+self.providerID+" WHERE name LIKE '%.PROPER.%' OR name LIKE '%.REPACK.%'"

        if date != None:
            sql += " AND time >= "+str(int(time.mktime(date.timetuple())))

        #return filter(lambda x: x['tvdbid'] != 0, myDB.select(sql))
        return myDB.select(sql)

    def findNeededEpisodes(self, episode = None, manualSearch=False):
        neededEps = {}

        if episode:
            neededEps[episode] = []

        myDB = self._getDB()

        if not episode:
            sqlResults = myDB.select("SELECT * FROM "+self.providerID)
        else:
            sqlResults = myDB.select("SELECT * FROM "+self.providerID+" WHERE tvdbid = ? AND season = ? AND episodes LIKE ?", [episode.show.tvdbid, episode.scene_season, "%|"+str(episode.scene_episode)+"|%"])

        # for each cache entry
        for curResult in sqlResults:

            # skip non-tv crap (but allow them for Newzbin cause we assume it's filtered well)
            if self.providerID != 'newzbin' and not show_name_helpers.filterBadReleases(curResult["name"]):
                continue

            # get the show object, or if it's not one of our shows then ignore it
            showObj = helpers.findCertainShow(sickbeard.showList, int(curResult["tvdbid"]))
            if not showObj:
                continue

            # get season and ep data (ignoring multi-eps for now)
            curSeason = int(curResult["season"])
            if curSeason == -1:
                continue
            curEp = curResult["episodes"].split("|")[1]
            if not curEp:
                continue
            curEp = int(curEp)
            curQuality = int(curResult["quality"])

            # if the show says we want that episode then add it to the list
            if not showObj.wantEpisode(curSeason, curEp, curQuality, manualSearch):
                logger.log(u"Skipping "+curResult["name"]+" because we don't want an episode that's "+Quality.qualityStrings[curQuality], logger.DEBUG)

            else:

                if episode:
                    epObj = episode
                else:
                    epObj = showObj.getEpisode(curSeason, curEp)

                # build a result object
                title = curResult["name"]
                url = curResult["url"]

                logger.log(u"Found result " + title + " at " + url)

                result = self.provider.getResult([epObj])
                result.url = url
                result.name = title
                result.quality = curQuality
                result.release_group = curResult["release_group"]

                # add it to the list
                if epObj not in neededEps:
                    neededEps[epObj] = [result]
                else:
                    neededEps[epObj].append(result)

        return neededEps
