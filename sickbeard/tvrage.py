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



import urllib, urllib2
import datetime
import traceback

import sickbeard

from sickbeard import logger
from sickbeard.common import *

from sickbeard import db
from sickbeard import exceptions, helpers

from lib.tvdb_api import tvdb_api, tvdb_exceptions

class TVRage:
    
    def __init__(self, show):
        
        self.show = show
        
        self.lastEpInfo = None
        self.nextEpInfo = None
        
        self._tvrid = 0
        self._tvrname = None
        
        if self.show.tvrid == 0:
            
            # if it's the right show then use the tvrage ID that the last lookup found (cached in self._trvid)
            if self.confirmShow() or self.checkSync():
                
                if self._tvrid == 0 or self._tvrname == None:
                    raise exceptions.TVRageException("We confirmed sync but got invalid data (no ID/name)")
                
                logger.log("Setting TVRage ID for "+show.name+" to "+str(self._tvrid))
                self.show.tvrid = self._tvrid
                self.show.saveToDB()

        if self.show.tvrname == "" or self.show.tvrname == None:

            if self._tvrname == None:
                self._getTVRageInfo()

            logger.log("Setting TVRage Show Name for "+show.name+" to "+self._tvrname)
            self.show.tvrname = self._tvrname
            self.show.saveToDB()


    def confirmShow(self, force=False):
        
        if self.show.tvrid != 0 and not force:
            logger.log("We already have a TVRage ID, skipping confirmation", logger.DEBUG)
            return True
        
        logger.log("Checking the first episode of each season to see if the air dates match between TVDB and TVRage")
        
        try:

            try:
                t = tvdb_api.Tvdb(**sickbeard.TVDB_API_PARMS)
            except tvdb_exceptions.tvdb_exception, e:
                logger.log("Currently this doesn't work with TVDB down but with some DB magic it can be added", logger.DEBUG)
                return None
            
            # check the first episode of every season
            for curSeason in t[self.show.tvdbid]:

                logger.log("Checking TVDB and TVRage sync for season "+str(curSeason), logger.DEBUG)

                airdate = None

                try:
                    
                    # don't do specials and don't do seasons with no episode 1
                    if curSeason == 0 or 1 not in t[self.show.tvdbid]:
                        continue
                    
                    # get the episode info from TVDB
                    ep = t[self.show.tvdbid][curSeason][1]
                
                    # make sure we have a date to compare with 
                    if ep["firstaired"] == "" or ep["firstaired"] == None:
                        continue

                    # get a datetime object
                    rawAirdate = [int(x) for x in ep["firstaired"].split("-")]
                    airdate = datetime.date(rawAirdate[0], rawAirdate[1], rawAirdate[2])
            
                    # get the episode info from TVRage
                    info = self._getTVRageInfo(curSeason, 1)
                    
                    # make sure we have enough info
                    if info == None or not info.has_key('Episode Info'):
                        logger.log("TVRage doesn't have the episode info, skipping it", logger.DEBUG)
                        continue
                        
                    # parse the episode info
                    curEpInfo = self._getEpInfo(info['Episode Info'])
                    
                    # make sure we got some info back
                    if curEpInfo == None:
                        continue
                        
                # if we couldn't compare with TVDB try comparing it with the local database
                except tvdb_exceptions.tvdb_exception, e:
                    logger.log("Unable to check TVRage info against TVDB: "+str(e))
    
                    logger.log("Trying against DB instead", logger.DEBUG)
    
                    myDB = db.DBConnection()
                    sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND season = ? and episode = ?", [self.show.tvdbid, self.lastEpInfo['season'], self.lastEpInfo['episode']])
                    
                    if len(sqlResults) == 0:
                        raise exceptions.EpisodeNotFoundException("Unable to find episode in DB")
                    else:
                        airdate = datetime.date.fromordinal(int(sqlResults[0]["airdate"]))
                
                
                # check if TVRage and TVDB have the same airdate for this episode
                if curEpInfo['airdate'] == airdate:
                    logger.log("Successful match for TVRage and TVDB data for episode "+str(curSeason)+"x1)", logger.DEBUG)
                    return True

                logger.log("Date from TVDB for episode " + str(curSeason) + "x1: " + str(airdate), logger.DEBUG)
                logger.log("Date from TVRage for episode " + str(curSeason) + "x1: " + str(curEpInfo['airdate']), logger.DEBUG)
        
        except Exception, e:
            logger.log("Error encountered while checking TVRage<->TVDB sync: " + str(e), logger.WARNING)
            logger.log(traceback.format_exc(), logger.DEBUG)
        
        return False
    
    def checkSync(self, info=None):
        
        logger.log("Checking the last aired episode to see if the dates match between TVDB and TVRage")
        
        if self.lastEpInfo == None or self.nextEpInfo == None:
            self._saveLatestInfo(info)
        
        if self.nextEpInfo['season'] == 0 or self.nextEpInfo['episode'] == 0:
            return None
        
        try:
        
            airdate = None
        
            # make sure the last TVDB episode matches our last episode
            try:
                t = tvdb_api.Tvdb(**sickbeard.TVDB_API_PARMS)
                ep = t[self.show.tvdbid][self.lastEpInfo['season']][self.lastEpInfo['episode']]

                if ep["firstaired"] == "" or ep["firstaired"] == None:
                    return None

                rawAirdate = [int(x) for x in ep["firstaired"].split("-")]
                airdate = datetime.date(rawAirdate[0], rawAirdate[1], rawAirdate[2])
            
            except tvdb_exceptions.tvdb_exception, e:
                logger.log("Unable to check TVRage info against TVDB: "+str(e))

                logger.log("Trying against DB instead", logger.DEBUG)

                myDB = db.DBConnection()
                sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND season = ? and episode = ?", [self.show.tvdbid, self.lastEpInfo['season'], self.lastEpInfo['episode']])
                
                if len(sqlResults) == 0:
                    raise exceptions.EpisodeNotFoundException("Unable to find episode in DB")
                else:
                    airdate = datetime.date.fromordinal(int(sqlResults[0]["airdate"]))
            
            logger.log("Date from TVDB for episode " + str(self.lastEpInfo['season']) + "x" + str(self.lastEpInfo['episode']) + ": " + str(airdate), logger.DEBUG)
            logger.log("Date from TVRage for episode " + str(self.lastEpInfo['season']) + "x" + str(self.lastEpInfo['episode']) + ": " + str(self.lastEpInfo['airdate']), logger.DEBUG)
        
            if self.lastEpInfo['airdate'] == airdate:
                return True
            
        except Exception, e:
            logger.log("Error encountered while checking TVRage<->TVDB sync: " + str(e), logger.WARNING)
            logger.log(traceback.format_exc(), logger.DEBUG)
        
        return False
    
    def _getTVRageInfo(self, season=None, episode=None, full=False):
        
        url = "http://services.tvrage.com/tools/quickinfo.php?"
        
        # if we need full info OR if we don't have a tvrage id, use show name
        if full == True or self.show.tvrid == 0:
            if self.show.tvrname != "" and self.show.tvrname != None:
                showName = self.show.tvrname
            else:
                showName = self.show.name

            urlData = {'show': showName.encode('utf-8')}

        # if we don't need full info and we have a tvrage id, use it
        else:
            urlData = {'sid': self.show.tvrid}
        
        if season != None and episode != None:
            urlData['ep'] = str(season)+'x'+str(episode)

        # build the URL
        url += urllib.urlencode(urlData)

        logger.log("Loading TVRage info from URL: " + url, logger.DEBUG)

        try:
            result = helpers.getURL(url)
        except (urllib2.HTTPError, IOError), e:
            logger.log("Unable to load TVRage info: " + str(e))
            raise exceptions.TVRageException("urlopen call to " + url + " failed")
        
        urlData = [x.decode('utf-8') for x in result.splitlines()]
        
        info = {}
        
        for x in urlData:
            key, value = x.split("@")
            key = key.replace('<pre>','')
            info[key] = value.strip()

        # save it for later in case somebody is curious
        if info.has_key('Show ID'):
            self._tvrid = info['Show ID']

        if info.has_key('Show Name'):
            self._tvrname = info['Show Name']

        return info
    
    def _saveLatestInfo(self, info=None):

        if info == None:
            info = self._getTVRageInfo()
        
        if not info.has_key('Next Episode') or not info.has_key('Latest Episode'):
            raise exceptions.TVRageException("TVRage doesn't have all the required info for this show")
            
        self.lastEpInfo = self._getEpInfo(info['Latest Episode'])
        self.nextEpInfo = self._getEpInfo(info['Next Episode'])
        
        if self.lastEpInfo == None or self.nextEpInfo == None:
            raise exceptions.TVRageException("TVRage has malformed data, unable to update the show")

        
    def _getEpInfo(self, epString):

        logger.log("Parsing info from TVRage: " + epString, logger.DEBUG)
        
        epInfo = epString.split('^')
        
        numInfo = [int(x) for x in epInfo[0].split('x')]
        
        try:
            date = datetime.datetime.strptime(epInfo[2], "%b/%d/%Y").date()
        except ValueError, e:
            try:
                date = datetime.datetime.strptime(epInfo[2], "%d/%b/%Y").date()
            except ValueError, e:
                logger.log("Unable to figure out the time from the TVRage data "+epInfo[2])
                return None
        
        toReturn = {'season': int(numInfo[0]), 'episode': numInfo[1], 'name': epInfo[1], 'airdate': date}
        
        logger.log("Result of parse: " + str(toReturn), logger.DEBUG)
        
        return toReturn

    def findLatestEp(self):

        # will use tvrage name if it got set in the constructor, or tvdb name if not
        info = self._getTVRageInfo(full=True)
        
        if not self.checkSync(info):
            raise exceptions.TVRageException("TVRage info isn't in sync with TVDB, not using data")
        
        myDB = db.DBConnection()
        
        # double check that it's not already in there
        sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?", [self.show.tvdbid, self.nextEpInfo['season'], self.nextEpInfo['episode']])
        
        if len(sqlResults) > 0:
            raise exceptions.TVRageException("Show is already in database, not adding the TVRage info")

        # insert it
        myDB.action("INSERT INTO tv_episodes (showid, tvdbid, name, season, episode, description, airdate, hasnfo, hastbn, status, location) VALUES (?,?,?,?,?,?,?,?,?,?,?)", \
                    [self.show.tvdbid, -1, self.nextEpInfo['name'], self.nextEpInfo['season'], self.nextEpInfo['episode'], '', self.nextEpInfo['airdate'].toordinal(), 0, 0, UNAIRED, ''])

        # once it's in the DB make an object and return it
        ep = None
       
        try:
            ep = self.show.getEpisode(self.nextEpInfo['season'], self.nextEpInfo['episode'])
        except exceptions.SickBeardException, e:
            logger.log("Unable to create episode from tvrage (could be for a variety of reasons): " + str(e))
   
        return ep

