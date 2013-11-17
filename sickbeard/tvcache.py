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

from sickbeard import helpers, show_name_helpers
from sickbeard import name_cache
from sickbeard.exceptions import ex, AuthException

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import elementtree.ElementTree as etree

from lib.tvdb_api import tvdb_api, tvdb_exceptions

from name_parser.parser import NameParser, InvalidNameException


class CacheDBConnection(db.DBConnection):

    def __init__(self, providerName):
        db.DBConnection.__init__(self, "cache.db")

        # Create the table if it's not already there
        try:
            sql = "CREATE TABLE " + providerName + " (name TEXT, season NUMERIC, episodes TEXT, tvrid NUMERIC, tvdbid NUMERIC, url TEXT, time NUMERIC, quality TEXT);"
            self.connection.execute(sql)
            self.connection.commit()
        except sqlite3.OperationalError, e:
            if str(e) != "table " + providerName + " already exists":
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

        myDB.action("DELETE FROM " + self.providerID + " WHERE 1")

    def _getRSSData(self):

        data = None

        return data

    def _checkAuth(self, parsedXML):
        return True

    def _checkItemAuth(self, title, url):
        return True

    def updateCache(self):

        if not self.shouldUpdate():
            return

        if self._checkAuth(None):

            data = self._getRSSData()

            # as long as the http request worked we count this as an update
            if data:
                self.setLastUpdate()
            else:
                return []

            # now that we've loaded the current RSS feed lets delete the old cache
            logger.log(u"Clearing " + self.provider.name + " cache and updating with new information")
            self._clearCache()

            parsedXML = helpers.parse_xml(data)

            if parsedXML is None:
                logger.log(u"Error trying to load " + self.provider.name + " RSS feed", logger.ERROR)
                return []

            if self._checkAuth(parsedXML):

                if parsedXML.tag == 'rss':
                    items = parsedXML.findall('.//item')

                else:
                    logger.log(u"Resulting XML from " + self.provider.name + " isn't RSS, not parsing it", logger.ERROR)
                    return []

                for item in items:
                    self._parseItem(item)

            else:
                raise AuthException(u"Your authentication credentials for " + self.provider.name + " are incorrect, check your config")

        return []

    def _translateTitle(self, title):
        return title.replace(' ', '.')

    def _translateLinkURL(self, url):
        return url.replace('&amp;', '&')

    def _parseItem(self, item):

        title = helpers.get_xml_text(item.find('title'))
        url = helpers.get_xml_text(item.find('link'))

        self._checkItemAuth(title, url)

        if title and url:
            title = self._translateTitle(title)
            url = self._translateLinkURL(url)

            logger.log(u"Adding item from RSS to cache: " + title, logger.DEBUG)
            self._addCacheEntry(title, url)

        else:
            logger.log(u"The XML returned from the " + self.provider.name + " feed is incomplete, this result is unusable", logger.DEBUG)
            return

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
            logger.log(u"Last update was too soon, using old cache: today()-" + str(self.lastUpdate) + "<" + str(datetime.timedelta(minutes=self.minTime)), logger.DEBUG)
            return False

        return True

    def _addCacheEntry(self, name, url, season=None, episodes=None, tvdb_id=0, tvrage_id=0, quality=None, extraNames=[]):

        myDB = self._getDB()

        parse_result = None

        # if we don't have complete info then parse the filename to get it
        for curName in [name] + extraNames:
            try:
                myParser = NameParser()
                parse_result = myParser.parse(curName)
            except InvalidNameException:
                logger.log(u"Unable to parse the filename " + curName + " into a valid episode", logger.DEBUG)
                continue

        if not parse_result:
            logger.log(u"Giving up because I'm unable to parse this name: " + name, logger.DEBUG)
            return False

        if not parse_result.series_name:
            logger.log(u"No series name retrieved from " + name + ", unable to cache it", logger.DEBUG)
            return False

        tvdb_lang = None

        # if we need tvdb_id or tvrage_id then search the DB for them
        if not tvdb_id or not tvrage_id:

            # if we have only the tvdb_id, use the database
            if tvdb_id:
                showObj = helpers.findCertainShow(sickbeard.showList, tvdb_id)
                if showObj:
                    tvrage_id = showObj.tvrid
                    tvdb_lang = showObj.lang
                else:
                    logger.log(u"We were given a TVDB id " + str(tvdb_id) + " but it doesn't match a show we have in our list, so leaving tvrage_id empty", logger.DEBUG)
                    tvrage_id = 0

            # if we have only a tvrage_id then use the database
            elif tvrage_id:
                showObj = helpers.findCertainTVRageShow(sickbeard.showList, tvrage_id)
                if showObj:
                    tvdb_id = showObj.tvdbid
                    tvdb_lang = showObj.lang
                else:
                    logger.log(u"We were given a TVRage id " + str(tvrage_id) + " but it doesn't match a show we have in our list, so leaving tvdb_id empty", logger.DEBUG)
                    tvdb_id = 0

            # if they're both empty then fill out as much info as possible by searching the show name
            else:

                # check the name cache and see if we already know what show this is
                logger.log(u"Checking the cache to see if we already know the tvdb id of " + parse_result.series_name, logger.DEBUG)
                tvdb_id = name_cache.retrieveNameFromCache(parse_result.series_name)

                # remember if the cache lookup worked or not so we know whether we should bother updating it later
                if tvdb_id == None:
                    logger.log(u"No cache results returned, continuing on with the search", logger.DEBUG)
                    from_cache = False
                else:
                    logger.log(u"Cache lookup found " + repr(tvdb_id) + ", using that", logger.DEBUG)
                    from_cache = True

                # if the cache failed, try looking up the show name in the database
                if tvdb_id == None:
                    logger.log(u"Trying to look the show up in the show database", logger.DEBUG)
                    showResult = helpers.searchDBForShow(parse_result.series_name)
                    if showResult:
                        logger.log(parse_result.series_name + " was found to be show " + showResult[1] + " ("+str(showResult[0]) + ") in our DB.", logger.DEBUG)
                        tvdb_id = showResult[0]

                # if the DB lookup fails then do a comprehensive regex search
                if tvdb_id == None:
                    logger.log(u"Couldn't figure out a show name straight from the DB, trying a regex search instead", logger.DEBUG)
                    for curShow in sickbeard.showList:
                        if show_name_helpers.isGoodResult(name, curShow, False):
                            logger.log(u"Successfully matched " + name + " to " + curShow.name + " with regex", logger.DEBUG)
                            tvdb_id = curShow.tvdbid
                            tvdb_lang = curShow.lang
                            break

                # if tvdb_id was anything but None (0 or a number) then
                if not from_cache:
                    name_cache.addNameToCache(parse_result.series_name, tvdb_id)

                # if we came out with tvdb_id = None it means we couldn't figure it out at all, just use 0 for that
                if tvdb_id == None:
                    tvdb_id = 0

                # if we found the show then retrieve the show object
                if tvdb_id:
                    showObj = helpers.findCertainShow(sickbeard.showList, tvdb_id)
                    if showObj:
                        tvrage_id = showObj.tvrid
                        tvdb_lang = showObj.lang

        # if we weren't provided with season/episode information then get it from the name that we parsed
        if not season:
            season = parse_result.season_number if parse_result.season_number != None else 1
        if not episodes:
            episodes = parse_result.episode_numbers

        # if we have an air-by-date show then get the real season/episode numbers
        if parse_result.air_by_date and tvdb_id:
            try:
                # There's gotta be a better way of doing this but we don't wanna
                # change the language value elsewhere
                ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

                if not (tvdb_lang == "" or tvdb_lang == "en" or tvdb_lang == None):
                    ltvdb_api_parms['language'] = tvdb_lang

                t = tvdb_api.Tvdb(**ltvdb_api_parms)
                epObj = t[tvdb_id].airedOn(parse_result.air_date)[0]
                season = int(epObj["seasonnumber"])
                episodes = [int(epObj["episodenumber"])]
            except tvdb_exceptions.tvdb_episodenotfound:
                logger.log(u"Unable to find episode with date " + str(parse_result.air_date) + " for show " + parse_result.series_name + ", skipping", logger.WARNING)
                return False
            except tvdb_exceptions.tvdb_error, e:
                logger.log(u"Unable to contact TVDB: " + ex(e), logger.WARNING)
                return False

        episodeText = "|" + "|".join(map(str, episodes)) + "|"

        # get the current timestamp
        curTimestamp = int(time.mktime(datetime.datetime.today().timetuple()))

        if not quality:
            quality = Quality.nameQuality(name)

        myDB.action("INSERT INTO " + self.providerID + " (name, season, episodes, tvrid, tvdbid, url, time, quality) VALUES (?,?,?,?,?,?,?,?)",
                    [name, season, episodeText, tvrage_id, tvdb_id, url, curTimestamp, quality])

    def searchCache(self, episode, manualSearch=False):
        neededEps = self.findNeededEpisodes(episode, manualSearch)
        return neededEps[episode]

    def listPropers(self, date=None, delimiter="."):

        myDB = self._getDB()

        sql = "SELECT * FROM " + self.providerID + " WHERE name LIKE '%.PROPER.%' OR name LIKE '%.REPACK.%'"

        if date != None:
            sql += " AND time >= " + str(int(time.mktime(date.timetuple())))

        #return filter(lambda x: x['tvdbid'] != 0, myDB.select(sql))
        return myDB.select(sql)

    def findNeededEpisodes(self, episode=None, manualSearch=False):
        neededEps = {}

        if episode:
            neededEps[episode] = []

        myDB = self._getDB()

        if not episode:
            sqlResults = myDB.select("SELECT * FROM " + self.providerID)
        else:
            sqlResults = myDB.select("SELECT * FROM " + self.providerID + " WHERE tvdbid = ? AND season = ? AND episodes LIKE ?", [episode.show.tvdbid, episode.season, "%|" + str(episode.episode) + "|%"])

        # for each cache entry
        for curResult in sqlResults:

            # skip non-tv crap
            if not show_name_helpers.filterBadReleases(curResult["name"]):
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
                logger.log(u"Skipping " + curResult["name"] + " because we don't want an episode that's " + Quality.qualityStrings[curQuality], logger.DEBUG)

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

                # add it to the list
                if epObj not in neededEps:
                    neededEps[epObj] = [result]
                else:
                    neededEps[epObj].append(result)

        return neededEps
