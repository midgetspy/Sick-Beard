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

import os.path
import datetime
import threading
import re
import glob
from sickbeard.completparser import CompleteParser
from sickbeard.common import statusStrings
try:
    import json
except ImportError:
    from lib import simplejson as json
import urllib2, httplib

import sickbeard

import xml.etree.cElementTree as etree

from name_parser.parser import InvalidNameException

from lib.tvdb_api import tvdb_api, tvdb_exceptions

from sickbeard import db
from sickbeard import helpers, exceptions, logger
from sickbeard.exceptions import ex
from sickbeard import tvrage
from sickbeard import config
from sickbeard import image_cache
from sickbeard import postProcessor

from sickbeard import encodingKludge as ek

from common import Quality, Overview
from common import DOWNLOADED, SNATCHED, SNATCHED_PROPER, ARCHIVED, IGNORED, UNAIRED, WANTED, SKIPPED, UNKNOWN

class TVShow(object):

    def __init__ (self, tvdbid, lang=""):

        self.tvdbid = tvdbid

        self._location = ""
        self.name = ""
        self.tvrid = 0
        self.tvrname = ""
        self.network = ""
        self.genre = ""
        self.runtime = 0
        self.quality = int(sickbeard.QUALITY_DEFAULT)
        self.seasonfolders = int(sickbeard.SEASON_FOLDERS_DEFAULT)

        self.status = ""
        self.airs = ""
        self.startyear = 0
        self.paused = 0
        self.air_by_date = 0
        self.lang = lang
        self.anime = 0

        self.lock = threading.Lock()
        self._isDirGood = False

        self.episodes = {}
        
        otherShow = helpers.findCertainShow(sickbeard.showList, self.tvdbid)
        if otherShow != None:
            raise exceptions.MultipleShowObjectsException("Can't create a show if it already exists")

        self.loadFromDB()
        
        self.saveToDB()
        
        self.seasonNumberCache = []
    
    def _is_anime(self):
        if(self.anime > 0):
            return True
        else:
            return False
    is_anime = property(_is_anime)
    
    def _getLocation(self):
        if ek.ek(os.path.isdir, self._location):
            return self._location
        else:
            raise exceptions.ShowDirNotFoundException("Show folder doesn't exist, you shouldn't be using it")

        if self._isDirGood:
            return self._location
        else:
            raise exceptions.NoNFOException("Show folder doesn't exist, you shouldn't be using it")

    def _setLocation(self, newLocation):
        logger.log(u"Setter sets location to " + newLocation, logger.DEBUG)
        if ek.ek(os.path.isdir, newLocation):
            self._location = newLocation
            self._isDirGood = True
        else:
            raise exceptions.NoNFOException("Invalid folder for the show!")

    location = property(_getLocation, _setLocation)

    # delete references to anything that's not in the internal lists
    def flushEpisodes(self):

        for curSeason in self.episodes:
            for curEp in self.episodes[curSeason]:
                myEp = self.episodes[curSeason][curEp]
                self.episodes[curSeason][curEp] = None
                del myEp


    def getEpisode(self, season, episode, file=None, noCreate=False, absolute_number=None, scene=False):
        """Return TVEpisode(self, season, episode) | None
        """
        # if we get an anime get the real season and episode
        if self.anime and absolute_number != None and season == None and episode == None:
            myDB = db.DBConnection()
            sql = "SELECT * FROM tv_episodes WHERE showid = ? and absolute_number = ? and season != 0"
            sqlResults = myDB.select(sql, [self.tvdbid, absolute_number])
                
            if len(sqlResults) == 1:
                episode = int(sqlResults[0]["episode"])
                season = int(sqlResults[0]["season"])
                logger.log("Found episode by absolute_number:"+str(absolute_number)+" which is "+str(season)+"x"+str(episode), logger.DEBUG)
            elif len(sqlResults) > 1:
                logger.log("Multiple entries for absolute number: "+str(absolute_number)+" in show: "+self.name+" found ", logger.ERROR)
                return None
            else:
                logger.log("No entries for absolute number: "+str(absolute_number)+" in show: "+self.name+" found.", logger.DEBUG)
                return None
            
            """
            i am taking this out because it is not the right way to go and is prducing errors
            else:
                logger.log("No entries for absolute number: "+str(absolute_number)+" in show: "+self.name+" found. will try with absolute number as episode number from first season", logger.DEBUG)
                # this fix the first season for shows that dont have absolute numbering from the tvdb
                season = 1
                episode = absolute_number
            """
        def createCurSeasonDict():
            if not season in self.episodes:
                self.episodes[season] = {}

        createCurSeasonDict()
        ep = None
        
        if (not episode in self.episodes[season] or self.episodes[season][episode] == None) or scene:
            if noCreate:
                return None

            logger.log(str(self.tvdbid) + ": An object for episode " + str(season) + "x" + str(episode) + " didn't exist in the cache, trying to create it", logger.DEBUG)

            if file != None:
                ep = TVEpisode(self, season, episode, file, scene)
            else:
                ep = TVEpisode(self, season, episode, scene=scene)

            if ep != None:
                if scene: # if scene mode was active we need to use the new ep season episode numbers
                    season = ep.season
                    episode = ep.episode
                    createCurSeasonDict() # recheck current "real" season dict
                self.episodes[season][episode] = ep
        
        return self.episodes[season][episode]

    def writeShowNFO(self):

        result = False

        if not ek.ek(os.path.isdir, self._location):
            logger.log(str(self.tvdbid) + u": Show dir doesn't exist, skipping NFO generation")
            return False

        for cur_provider in sickbeard.metadata_provider_dict.values():
            result = cur_provider.create_show_metadata(self) or result

        return result

    def writeMetadata(self):

        if not ek.ek(os.path.isdir, self._location):
            logger.log(str(self.tvdbid) + u": Show dir doesn't exist, skipping NFO generation")
            return

        self.getImages()

        self.writeShowNFO()
        self.writeEpisodeNFOs()


    def writeEpisodeNFOs (self):

        if not ek.ek(os.path.isdir, self._location):
            logger.log(str(self.tvdbid) + ": Show dir doesn't exist, skipping NFO generation")
            return

        logger.log(str(self.tvdbid) + ": Writing NFOs for all episodes")

        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND location != ''", [self.tvdbid])

        for epResult in sqlResults:
            logger.log(str(self.tvdbid) + ": Retrieving/creating episode " + str(epResult["season"]) + "x" + str(epResult["episode"]), logger.DEBUG)
            curEp = self.getEpisode(epResult["season"], epResult["episode"])
            curEp.createMetaFiles()


    # find all media files in the show folder and create episodes for as many as possible
    def loadEpisodesFromDir (self):

        if not ek.ek(os.path.isdir, self._location):
            logger.log(str(self.tvdbid) + ": Show dir doesn't exist, not loading episodes from disk")
            return
        logger.log(str(self.tvdbid) + ": ############################################ ")
        logger.log(str(self.tvdbid) + ": Loading all episodes from the show directory " + self._location)
        logger.log(str(self.tvdbid) + ": ############################################ ")
        # get file list
        mediaFiles = helpers.listMediaFiles(self._location)

        # create TVEpisodes from each media file (if possible)
        for mediaFile in mediaFiles:

            curEpisode = None

            logger.log(str(self.tvdbid) + ": Creating episode from " + mediaFile, logger.DEBUG)
            try:
                curEpisode = self.makeEpFromFile(os.path.join(self._location, mediaFile))
            except (exceptions.ShowNotFoundException, exceptions.EpisodeNotFoundException), e:
                logger.log(u"Episode "+mediaFile+" returned an exception: "+ex(e), logger.ERROR)
            except exceptions.EpisodeDeletedException:
                logger.log(u"The episode deleted itself when I tried making an object for it", logger.DEBUG)

            # store the reference in the show
            if curEpisode != None:
                curEpisode.saveToDB()


    def loadEpisodesFromDB(self):

        logger.log(u"Loading all episodes from the DB")

        myDB = db.DBConnection()
        sql = "SELECT * FROM tv_episodes WHERE showid = ?"
        sqlResults = myDB.select(sql, [self.tvdbid])

        scannedEps = {}

        ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

        if self.lang:
            ltvdb_api_parms['language'] = self.lang

        t = tvdb_api.Tvdb(**ltvdb_api_parms)

        cachedShow = t[self.tvdbid]
        cachedSeasons = {}

        for curResult in sqlResults:

            deleteEp = False
                    
            curSeason = int(curResult["season"])
            curEpisode = int(curResult["episode"])
            if curSeason not in cachedSeasons:
                try:
                    cachedSeasons[curSeason] = cachedShow[curSeason]
                except tvdb_exceptions.tvdb_seasonnotfound, e:
                    logger.log(u"Error when trying to load the episode from TVDB: "+e.message, logger.WARNING)
                    deleteEp = True

            if not curSeason in scannedEps:
                scannedEps[curSeason] = {}

            logger.log(u"Loading episode "+str(curSeason)+"x"+str(curEpisode)+" from the DB", logger.DEBUG)

            try:
                curEp = self.getEpisode(curSeason, curEpisode)
                
                # if we found out that the ep is no longer on TVDB then delete it from our database too
                if deleteEp:
                    curEp.deleteEpisode()
                
                curEp.loadFromDB(curSeason, curEpisode)
                curEp.loadFromTVDB(tvapi=t, cachedSeason=cachedSeasons[curSeason])
                scannedEps[curSeason][curEpisode] = True
            except exceptions.EpisodeDeletedException:
                logger.log(u"Tried loading an episode from the DB that should have been deleted, skipping it", logger.DEBUG)
                continue

        return scannedEps


    def loadEpisodesFromTVDB(self, cache=True):
        
        self._clearSeasonNumbersCache()
        
        # There's gotta be a better way of doing this but we don't wanna
        # change the cache value elsewhere
        ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

        if not cache:
            ltvdb_api_parms['cache'] = 'recache'

        if self.lang:
            ltvdb_api_parms['language'] = self.lang

        try:
            t = tvdb_api.Tvdb(**ltvdb_api_parms)
            showObj = t[self.tvdbid]
        except tvdb_exceptions.tvdb_error:
            logger.log(u"TVDB timed out, unable to update episodes from TVDB", logger.ERROR)
            return None

        logger.log(str(self.tvdbid) + ": Loading all episodes from theTVDB...")

        scannedEps = {}

        for season in showObj:
            scannedEps[season] = {}
            for episode in showObj[season]:
                # need some examples of wtf episode 0 means to decide if we want it or not
                if episode == 0:
                    continue
                try:
                    #ep = TVEpisode(self, season, episode)
                    ep = self.getEpisode(season, episode)
                except exceptions.EpisodeNotFoundException:
                    logger.log(str(self.tvdbid) + ": TVDB object for " + str(season) + "x" + str(episode) + " is incomplete, skipping this episode")
                    continue
                else:
                    try:
                        ep.loadFromTVDB(tvapi=t)
                    except exceptions.EpisodeDeletedException:
                        logger.log(u"The episode was deleted, skipping the rest of the load")
                        continue

                with ep.lock:
                    logger.log(str(self.tvdbid) + ": Loading info from theTVDB for episode " + str(season) + "x" + str(episode), logger.DEBUG)
                    ep.loadFromTVDB(season, episode, tvapi=t)
                    if ep.dirty:
                        ep.saveToDB()

                scannedEps[season][episode] = True

        return scannedEps

    def loadEpisodeSceneNumbers(self):
        url = "http://thexem.de/map/all?id=%s&origin=tvdb&destination=scene" % self.tvdbid
        logger.log("xem url: " + url, logger.DEBUG)
        opener = urllib2.build_opener()
        try:
            f = opener.open(url)
        except (EOFError, IOError), e:
            logger.log(u"Unable to connect to XEM. Is thexem.de down ?" + ex(e), logger.ERROR)
            return False
        except httplib.InvalidURL, e:
            logger.log(u"Invalid XEM host. Is thexem.de down ?: " + ex(e), logger.ERROR)
            return False
        if not f:
            logger.log(u"Empty response from " + url + ": " + ex(e), logger.ERROR)
            return False
        try:
            xemJson = json.loads(f.read())
        except ValueError, e:
            return False

        epList = self.loadEpisodesFromDB()
        for curSeason in epList:
            for curEp in epList[curSeason]:
                epObj = self.getEpisode(curSeason, curEp)
                epObj.scene_season = None
                epObj.scene_episode = None
                epObj.scene_absolute_number = None
                epObj.saveToDB()

        if xemJson['result'] == 'failure':
            logger.log(u"XEM said failure. message: " + xemJson['message'], logger.DEBUG)
            return False

        for epNumbers in xemJson['data']:
            tvdb = epNumbers['tvdb']
            scene = epNumbers['scene']
            if not tvdb['season'] in epList or not tvdb['episode'] in epList[tvdb['season']]:
                logger.log(str(self.tvdbid) + ": NOT adding scene number. tvdb: " + str(tvdb) + "| scene: " + str(scene) + " we dont have a ep with this (tvdb) sxxexx", logger.WARNING)

            logger.log(str(self.tvdbid) + ": adding scene number. tvdb: " + str(tvdb) + "| scene: " + str(scene), logger.DEBUG)
            curEp = self.getEpisode(tvdb['season'], tvdb['episode'])
            curEp.scene_season = scene['season']
            curEp.scene_episode = scene['episode']
            curEp.scene_absolute_number = scene['absolute']
            curEp.saveToDB()
        return True

    def setTVRID(self, force=False):

        if self.tvrid != 0 and not force:
            logger.log(u"No need to get the TVRage ID, it's already populated", logger.DEBUG)
            return

        logger.log(u"Attempting to retrieve the TVRage ID", logger.DEBUG)

        try:
            # load the tvrage object, it will set the ID in its constructor if possible
            tvrage.TVRage(self)
            self.saveToDB()
        except exceptions.TVRageException, e:
            logger.log(u"Couldn't get TVRage ID because we're unable to sync TVDB and TVRage: "+ex(e), logger.DEBUG)
            return

    def getImages(self, fanart=None, poster=None):

        poster_result = fanart_result = season_thumb_result = False

        for cur_provider in sickbeard.metadata_provider_dict.values():
            logger.log("Running season folders for "+cur_provider.name, logger.DEBUG)
            poster_result = cur_provider.create_poster(self) or poster_result
            fanart_result = cur_provider.create_fanart(self) or fanart_result
            season_thumb_result = cur_provider.create_season_thumbs(self) or season_thumb_result

        return poster_result or fanart_result or season_thumb_result

    def loadLatestFromTVRage(self):

        try:
            # load the tvrage object
            tvr = tvrage.TVRage(self)

            newEp = tvr.findLatestEp()

            if newEp != None:
                logger.log(u"TVRage gave us an episode object - saving it for now", logger.DEBUG)
                newEp.saveToDB()

            # make an episode out of it
        except exceptions.TVRageException, e:
            logger.log(u"Unable to add TVRage info: " + ex(e), logger.WARNING)



    # make a TVEpisode object from a media file
    def makeEpFromFile(self, file):

        if not ek.ek(os.path.isfile, file):
            logger.log(str(self.tvdbid) + ": That isn't even a real file dude... " + file)
            return None

        logger.log(str(self.tvdbid) + ": -------------------------------------------- ", logger.DEBUG)
        logger.log(str(self.tvdbid) + ": Creating episode object from " + file, logger.DEBUG)
        logger.log(str(self.tvdbid) + ": -------------------------------------------- ", logger.DEBUG)

        cp = CompleteParser(show=self, tvdbActiveLookUp=True)
        cpr = cp.parse(file)
        if not cpr.sxxexx:
            logger.log(u"No conclusive information found in " + file + ", ignoring it", logger.ERROR)
            return None

        # for now lets assume that any episode in the show dir belongs to that show
        season = cpr.season
        episodes = cpr.episodes
        rootEp = None

        for curEpNum in episodes:

            episode = int(curEpNum)

            logger.log(str(self.tvdbid) + ": " + file + " parsed to " + self.name + " " + str(season) + "x" + str(episode), logger.DEBUG)

            checkQualityAgain = False
            curEp = self.getEpisode(season, episode)

            if curEp == None:
                try:
                    curEp = self.getEpisode(season, episode, file)
                except exceptions.EpisodeNotFoundException:
                    logger.log(str(self.tvdbid) + ": Unable to figure out what this file is, skipping", logger.ERROR)
                    continue

            else:
                # if there is a new file associated with this ep then re-check the quality
                if curEp.location and ek.ek(os.path.normpath, curEp.location) != ek.ek(os.path.normpath, file):
                    logger.log(u"The old episode had a different file associated with it, I will re-check the quality based on the new filename "+file, logger.DEBUG)
                    checkQualityAgain = True

                with curEp.lock:
                    curEp.location = file
                    curEp.checkForMetaFiles()

            if rootEp == None:
                rootEp = curEp
            else:
                rootEp.relatedEps.append(curEp)

            # if they replace a file on me I'll make some attempt at re-checking the quality
            if checkQualityAgain:
                newQuality = Quality.nameQuality(file, self.is_anime)
                logger.log(u"Since this file has been renamed, I checked "+file+" and found quality "+Quality.qualityStrings[newQuality], logger.DEBUG)
                if newQuality != Quality.UNKNOWN:
                    curEp.status = Quality.compositeStatus(DOWNLOADED, newQuality)


            elif sickbeard.helpers.isMediaFile(file) and curEp.status not in Quality.DOWNLOADED + [ARCHIVED, IGNORED]:

                oldStatus, oldQuality = Quality.splitCompositeStatus(curEp.status)
                newQuality = Quality.nameQuality(file, self.is_anime)
                if newQuality == Quality.UNKNOWN:
                    newQuality = Quality.assumeQuality(file)

                newStatus = None

                # if it was snatched and now exists then set the status correctly
                if oldStatus == SNATCHED and oldQuality <= newQuality:
                    logger.log(u"STATUS: this ep used to be snatched with quality "+Quality.qualityStrings[oldQuality]+" but a file exists with quality "+Quality.qualityStrings[newQuality]+" so I'm setting the status to DOWNLOADED", logger.DEBUG)
                    newStatus = DOWNLOADED

                # if it was snatched proper and we found a higher quality one then allow the status change
                elif oldStatus == SNATCHED_PROPER and oldQuality < newQuality:
                    logger.log(u"STATUS: this ep used to be snatched proper with quality "+Quality.qualityStrings[oldQuality]+" but a file exists with quality "+Quality.qualityStrings[newQuality]+" so I'm setting the status to DOWNLOADED", logger.DEBUG)
                    newStatus = DOWNLOADED

                elif oldStatus not in (SNATCHED, SNATCHED_PROPER):
                    newStatus = DOWNLOADED

                if newStatus != None:
                    with curEp.lock:
                        logger.log(u"STATUS: we have an associated file, so setting the status from "+str(curEp.status)+" to DOWNLOADED/" + str(Quality.statusFromName(file)), logger.DEBUG)
                        curEp.status = Quality.compositeStatus(newStatus, newQuality)

            with curEp.lock:
                curEp.saveToDB()

        # creating metafiles on the root should be good enough
        if rootEp != None:
            with rootEp.lock:
                rootEp.createMetaFiles()

        return rootEp


    def loadFromDB(self, skipNFO=False):

        logger.log(str(self.tvdbid) + ": Loading show info from database",logger.DEBUG)

        myDB = db.DBConnection()

        sqlResults = myDB.select("SELECT * FROM tv_shows WHERE tvdb_id = ?", [self.tvdbid])

        if len(sqlResults) > 1:
            raise exceptions.MultipleDBShowsException()
        elif len(sqlResults) == 0:
            logger.log(str(self.tvdbid) + ": Unable to find the show in the database")
            return
        else:
            if self.name == "":
                self.name = sqlResults[0]["show_name"]
            self.tvrname = sqlResults[0]["tvr_name"]
            if self.network == "":
                self.network = sqlResults[0]["network"]
            if self.genre == "":
                self.genre = sqlResults[0]["genre"]

            self.runtime = sqlResults[0]["runtime"]

            self.status = sqlResults[0]["status"]
            if self.status == None:
                self.status = ""
            self.airs = sqlResults[0]["airs"]
            if self.airs == None:
                self.airs = ""
            self.startyear = sqlResults[0]["startyear"]
            if self.startyear == None:
                self.startyear = 0

            self.air_by_date = sqlResults[0]["air_by_date"]
            if self.air_by_date == None:
                self.air_by_date = 0

            self.quality = int(sqlResults[0]["quality"])
            self.seasonfolders = int(sqlResults[0]["seasonfolders"])
            self.paused = int(sqlResults[0]["paused"])

            self._location = sqlResults[0]["location"]

            if self.tvrid == 0:
                self.tvrid = int(sqlResults[0]["tvr_id"])

            if self.lang == "":
                self.lang = sqlResults[0]["lang"]
            
            self.anime = sqlResults[0]["anime"]
            if self.anime == None:
                self.anime = 0


    def loadFromTVDB(self, cache=True, tvapi=None, cachedSeason=None):

        logger.log(str(self.tvdbid) + ": Loading show info from theTVDB")

        # There's gotta be a better way of doing this but we don't wanna
        # change the cache value elsewhere
        if tvapi is None:
            ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

            if not cache:
                ltvdb_api_parms['cache'] = 'recache'
            
            if self.lang:
                ltvdb_api_parms['language'] = self.lang

            t = tvdb_api.Tvdb(**ltvdb_api_parms)

        else:
            t = tvapi

        myEp = t[self.tvdbid]

        self.name = myEp["seriesname"]

        self.genre = myEp['genre']
        self.network = myEp['network']

        if myEp["airs_dayofweek"] != None and myEp["airs_time"] != None:
            self.airs = myEp["airs_dayofweek"] + " " + myEp["airs_time"]

        if myEp["firstaired"] != None and myEp["firstaired"]:
            self.startyear = int(myEp["firstaired"].split('-')[0])

        if self.airs == None:
            self.airs = ""

        if myEp["status"] != None:
            self.status = myEp["status"]

        if self.status == None:
            self.status = ""

        self.saveToDB()


    def loadNFO (self):

        if not os.path.isdir(self._location):
            logger.log(str(self.tvdbid) + ": Show dir doesn't exist, can't load NFO")
            raise exceptions.NoNFOException("The show dir doesn't exist, no NFO could be loaded")

        logger.log(str(self.tvdbid) + ": Loading show info from NFO")

        xmlFile = os.path.join(self._location, "tvshow.nfo")

        try:
            xmlFileObj = open(xmlFile, 'r')
            showXML = etree.ElementTree(file = xmlFileObj)

            if showXML.findtext('title') == None or (showXML.findtext('tvdbid') == None and showXML.findtext('id') == None):
                raise exceptions.NoNFOException("Invalid info in tvshow.nfo (missing name or id):" \
                    + str(showXML.findtext('title')) + " " \
                    + str(showXML.findtext('tvdbid')) + " " \
                    + str(showXML.findtext('id')))

            self.name = showXML.findtext('title')
            if showXML.findtext('tvdbid') != None:
                self.tvdbid = int(showXML.findtext('tvdbid'))
            elif showXML.findtext('id'):
                self.tvdbid = int(showXML.findtext('id'))
            else:
                raise exceptions.NoNFOException("Empty <id> or <tvdbid> field in NFO")

        except (exceptions.NoNFOException, SyntaxError, ValueError), e:
            logger.log(u"There was an error parsing your existing tvshow.nfo file: " + ex(e), logger.ERROR)
            logger.log(u"Attempting to rename it to tvshow.nfo.old", logger.DEBUG)

            try:
                xmlFileObj.close()
                ek.ek(os.rename, xmlFile, xmlFile + ".old")
            except Exception, e:
                logger.log(u"Failed to rename your tvshow.nfo file - you need to delete it or fix it: " + ex(e), logger.ERROR)
            raise exceptions.NoNFOException("Invalid info in tvshow.nfo")

        if showXML.findtext('studio') != None:
            self.network = showXML.findtext('studio')
        if self.network == None and showXML.findtext('network') != None:
            self.network = ""
        if showXML.findtext('genre') != None:
            self.genre = showXML.findtext('genre')
        else:
            self.genre = ""

        # TODO: need to validate the input, I'm assuming it's good until then


    def nextEpisode(self):

        logger.log(str(self.tvdbid) + ": Finding the episode which airs next", logger.DEBUG)

        myDB = db.DBConnection()
        innerQuery = "SELECT airdate FROM tv_episodes WHERE showid = ? AND airdate >= ? AND status = ? ORDER BY airdate ASC LIMIT 1"
        innerParams = [self.tvdbid, datetime.date.today().toordinal(), UNAIRED]
        query = "SELECT * FROM tv_episodes WHERE showid = ? AND airdate >= ? AND airdate <= (" + innerQuery + ") and status = ?"
        params = [self.tvdbid, datetime.date.today().toordinal()] + innerParams + [UNAIRED]
        sqlResults = myDB.select(query, params)

        if sqlResults == None or len(sqlResults) == 0:
            logger.log(str(self.tvdbid) + ": No episode found... need to implement tvrage and also show status", logger.DEBUG)
            return []
        else:
            logger.log(str(self.tvdbid) + ": Found episode " + str(sqlResults[0]["season"]) + "x" + str(sqlResults[0]["episode"]), logger.DEBUG)
            foundEps = []
            for sqlEp in sqlResults:
                curEp = self.getEpisode(int(sqlEp["season"]), int(sqlEp["episode"]))
                foundEps.append(curEp)
            return foundEps

        # if we didn't get an episode then try getting one from tvrage

        # load tvrage info

        # extract NextEpisode info

        # verify that we don't have it in the DB somehow (ep mismatch)


    def deleteShow(self):

        myDB = db.DBConnection()
        myDB.action("DELETE FROM tv_episodes WHERE showid = ?", [self.tvdbid])
        myDB.action("DELETE FROM tv_shows WHERE tvdb_id = ?", [self.tvdbid])

        # remove self from show list
        sickbeard.showList = [x for x in sickbeard.showList if x.tvdbid != self.tvdbid]
        
        # clear the cache
        image_cache_dir = ek.ek(os.path.join, sickbeard.CACHE_DIR, 'images')
        for cache_file in ek.ek(glob.glob, ek.ek(os.path.join, image_cache_dir, str(self.tvdbid)+'.*')):
            logger.log(u"Deleting cache file "+cache_file)
            os.remove(cache_file)

    def populateCache(self):
        cache_inst = image_cache.ImageCache()
        
        logger.log(u"Checking & filling cache for show "+self.name)
        cache_inst.fill_cache(self)

    def refreshDir(self):

        # make sure the show dir is where we think it is
        if not ek.ek(os.path.isdir, self._location):
            return False

        # load from dir
        self.loadEpisodesFromDir()

        # run through all locations from DB, check that they exist
        logger.log(str(self.tvdbid) + ": Loading all episodes with a location from the database")

        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND location != ''", [self.tvdbid])

        for ep in sqlResults:
            curLoc = os.path.normpath(ep["location"])
            season = int(ep["season"])
            episode = int(ep["episode"])

            try:
                curEp = self.getEpisode(season, episode)
            except exceptions.EpisodeDeletedException:
                logger.log(u"The episode was deleted while we were refreshing it, moving on to the next one", logger.DEBUG)
                continue

            # if the path doesn't exist or if it's not in our show dir
            if not ek.ek(os.path.isfile, curLoc) or not os.path.normpath(curLoc).startswith(os.path.normpath(self.location)):

                with curEp.lock:
                    # if it used to have a file associated with it and it doesn't anymore then set it to IGNORED
                    if curEp.location and curEp.status in Quality.DOWNLOADED:
                        logger.log(str(self.tvdbid) + ": Location for " + str(season) + "x" + str(episode) + " doesn't exist, removing it and changing our status to IGNORED", logger.DEBUG)
                        curEp.status = IGNORED
                    curEp.location = ''
                    curEp.hasnfo = False
                    curEp.hastbn = False
                    curEp.saveToDB()



    def fixEpisodeNames(self):

        if not os.path.isdir(self._location):
            logger.log(str(self.tvdbid) + ": Show dir doesn't exist, can't rename episodes")
            return

        # load episodes from my folder
        self.loadEpisodesFromDir()

        logger.log(str(self.tvdbid) + ": Loading all episodes with a location from the database")

        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND location != ''", [self.tvdbid])

        # build list of locations
        fileLocations = {}
        for epResult in sqlResults:
            goodLoc = os.path.normpath(epResult["location"])
            goodSeason = int(epResult["season"])
            goodEpisode = int(epResult["episode"])
            if fileLocations.has_key(goodLoc):
                fileLocations[goodLoc].append((goodSeason, goodEpisode))
            else:
                fileLocations[goodLoc] = [(goodSeason, goodEpisode)]

        logger.log(u"File results: " + str(fileLocations), logger.DEBUG)

        for curLocation in fileLocations:

            epList = fileLocations[curLocation]

            # get the root episode and add all related episodes to it
            rootEp = None
            for myEp in epList:
                curEp = self.getEpisode(myEp[0], myEp[1])
                if rootEp == None:
                    rootEp = curEp
                    rootEp.relatedEps = []
                else:
                    rootEp.relatedEps.append(curEp)

            goodName = rootEp.prettyName()
            actualName = os.path.splitext(os.path.basename(curLocation))

            if goodName == actualName[0]:
                logger.log(str(self.tvdbid) + ": File " + rootEp.location + " is already named correctly, skipping", logger.DEBUG)
                continue

            with rootEp.lock:
                result = helpers.rename_file(rootEp.location, rootEp.prettyName())
                if result != False:
                    rootEp.location = result
                    for relEp in rootEp.relatedEps:
                        relEp.location = result

            fileList = postProcessor.PostProcessor(curLocation)._list_associated_files(curLocation)
            logger.log(u"Files associated to "+curLocation+": "+str(fileList), logger.DEBUG)

            for file in fileList:
                result = helpers.rename_file(file, rootEp.prettyName())
                if result == False:
                    logger.log(str(self.tvdbid) + ": Unable to rename file "+file, logger.ERROR)

            for curEp in [rootEp]+rootEp.relatedEps:
                curEp.checkForMetaFiles()

            with rootEp.lock:
                rootEp.saveToDB()
                for relEp in rootEp.relatedEps:
                    relEp.saveToDB()


    def saveToDB(self):

        logger.log(str(self.tvdbid) + ": Saving show info to database", logger.DEBUG)

        myDB = db.DBConnection()

        controlValueDict = {"tvdb_id": self.tvdbid}
        newValueDict = {"show_name": self.name,
                        "tvr_id": self.tvrid,
                        "location": self._location,
                        "network": self.network,
                        "genre": self.genre,
                        "runtime": self.runtime,
                        "quality": self.quality,
                        "airs": self.airs,
                        "status": self.status,
                        "seasonfolders": self.seasonfolders,
                        "paused": self.paused,
                        "air_by_date": self.air_by_date,
                        "startyear": self.startyear,
                        "tvr_name": self.tvrname,
                        "lang": self.lang,
                        "anime": self.anime
                        }

        myDB.upsert("tv_shows", newValueDict, controlValueDict)
        helpers.update_anime_support()


    def __str__(self):
        toReturn = ""
        toReturn += "name: " + self.name + "\n"
        toReturn += "location: " + self._location + "\n"
        toReturn += "tvdbid: " + str(self.tvdbid) + "\n"
        if self.network != None:
            toReturn += "network: " + self.network + "\n"
        if self.airs != None:
            toReturn += "airs: " + self.airs + "\n"
        if self.status != None:
            toReturn += "status: " + self.status + "\n"
        toReturn += "startyear: " + str(self.startyear) + "\n"
        toReturn += "genre: " + self.genre + "\n"
        toReturn += "runtime: " + str(self.runtime) + "\n"
        toReturn += "quality: " + str(self.quality) + "\n"
        toReturn += "anime: " + str(self.is_anime) + "\n"
        return toReturn


    def wantEpisode(self, season, episode, quality, manualSearch=False):

        logger.log(u"Checking if we want episode "+str(season)+"x"+str(episode)+" at quality "+Quality.qualityStrings[quality], logger.DEBUG)

        # if the quality isn't one we want under any circumstances then just say no
        anyQualities, bestQualities = Quality.splitQuality(self.quality)
        logger.log(u"any,best = "+str(anyQualities)+" "+str(bestQualities)+" and we are "+str(quality), logger.DEBUG)

        if quality not in anyQualities + bestQualities:
            logger.log(u"I know for sure I don't want this episode, saying no", logger.DEBUG)
            return False

        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT status FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?", [self.tvdbid, season, episode])

        if not sqlResults or not len(sqlResults):
            logger.log(u"Unable to find the episode", logger.DEBUG)
            return False

        epStatus = int(sqlResults[0]["status"])

        logger.log(u"current episode status: " + statusStrings[epStatus], logger.DEBUG)

        # if we know we don't want it then just say no
        if epStatus in (SKIPPED, IGNORED, ARCHIVED) and not manualSearch:
            logger.log(u"Ep is skipped, not bothering", logger.DEBUG)
            return False

        # if it's one of these then we want it as long as it's in our allowed initial qualities
        if quality in anyQualities + bestQualities:
            if epStatus in (WANTED, UNAIRED, SKIPPED):
                logger.log(u"Ep is wanted/unaired/skipped, definitely get it", logger.DEBUG)
                return True
            elif manualSearch:
                logger.log(u"Usually I would ignore this ep but because you forced the search I'm overriding the default and allowing the quality", logger.DEBUG)
                return True
            else:
                logger.log(u"This quality looks like something we might want but I don't know for sure yet", logger.DEBUG)

        curStatus, curQuality = Quality.splitCompositeStatus(epStatus)

        # if we are re-downloading then we only want it if it's in our bestQualities list and better than what we have
        if curStatus in Quality.SNATCHED + Quality.DOWNLOADED and quality in bestQualities and quality > curQuality:
            logger.log(u"We already have this ep but the new one is better quality, saying yes", logger.DEBUG)
            return True

        logger.log(u"None of the conditions were met so I'm just saying no", logger.DEBUG)
        return False


    def getOverview(self, epStatus):

        if epStatus == WANTED:
            return Overview.WANTED
        elif epStatus in (UNAIRED, UNKNOWN):
            return Overview.UNAIRED
        elif epStatus in (SKIPPED, IGNORED):
            return Overview.SKIPPED
        elif epStatus == ARCHIVED:
            return Overview.GOOD
        elif epStatus in Quality.DOWNLOADED + Quality.SNATCHED + Quality.SNATCHED_PROPER:

            anyQualities, bestQualities = Quality.splitQuality(self.quality) #@UnusedVariable
            if bestQualities:
                maxBestQuality = max(bestQualities)
            else:
                maxBestQuality = None

            epStatus, curQuality = Quality.splitCompositeStatus(epStatus)

            # if they don't want re-downloads then we call it good if they have anything
            if maxBestQuality == None:
                return Overview.GOOD
            # if they have one but it's not the best they want then mark it as qual
            elif curQuality < maxBestQuality:
                return Overview.QUAL
            # if it's >= maxBestQuality then it's good
            else:
                return Overview.GOOD

    def getAllSeasonNumbers(self):
        if not self._seasonNumberCache:
            myDB = db.DBConnection()
            sqlResults = myDB.select("SELECT DISTINCT(season) as season FROM tv_episodes WHERE showid = ? AND season > 0", [self.tvdbid])
            self._seasonNumberCache = [int(x["season"]) for x in sqlResults]

        return self._seasonNumberCache

    def _clearSeasonNumbersCache(self):
        self._seasonNumberCache = []

    def getPreviuosAiredCount(self, season, episode):
        myDB = db.DBConnection()
        epCount = myDB.select("SELECT COUNT(tvdbid) count FROM tv_episodes WHERE showid = ? AND season != 0 AND airdate > 1 AND (( season = ? AND episode < ? ) OR ( season < ? ))", [self.tvdbid, season, episode, season])
        if len(epCount):
            return int(epCount[0]['count'])
        return 0

def dirty_setter(attr_name):
    def wrapper(self, val):
        if getattr(self, attr_name) != val:
            setattr(self, attr_name, val)
            self.dirty = True
    return wrapper

class TVEpisode(object):

    def __init__(self, show, season, episode, file="", scene=False):

        self._name = ""
        self._season = season
        self._episode = episode
        self._absolute_number = 0
        self._description = ""
        self._airdate = datetime.date.fromordinal(1)
        self._hasnfo = False
        self._hastbn = False
        self._status = UNKNOWN
        self._tvdbid = 0

        self.scene = scene
        self._scene_season = None
        self._scene_episode = None
        self._scene_absolute_number = None
        if self.scene:
            self._scene_season = self._season
            self._scene_episode = self._episode

        # setting any of the above sets the dirty flag
        self.dirty = True

        self.show = show
        self._location = file

        self.lock = threading.Lock()

        self.relatedEps = []

        self.specifyEpisode(self.season, self.episode)

        self.checkForMetaFiles()

    name = property(lambda self: self._name, dirty_setter("_name"))
    season = property(lambda self: self._season, dirty_setter("_season"))
    episode = property(lambda self: self._episode, dirty_setter("_episode"))
    absolute_number = property(lambda self: self._absolute_number, dirty_setter("_absolute_number"))
    description = property(lambda self: self._description, dirty_setter("_description"))
    airdate = property(lambda self: self._airdate, dirty_setter("_airdate"))
    hasnfo = property(lambda self: self._hasnfo, dirty_setter("_hasnfo"))
    hastbn = property(lambda self: self._hastbn, dirty_setter("_hastbn"))
    status = property(lambda self: self._status, dirty_setter("_status"))
    tvdbid = property(lambda self: self._tvdbid, dirty_setter("_tvdbid"))
    location = property(lambda self: self._location, dirty_setter("_location"))
    
    scene_season = property(lambda self: self._getSceneOrTVDBSeason(), dirty_setter("_scene_season"))
    scene_episode = property(lambda self: self._getSceneOrTVDBEpisode(), dirty_setter("_scene_episode"))
    scene_absolute_number = property(lambda self: self._getSceneOrTVDBAbsolute(), dirty_setter("_scene_absolute_number"))

    def _getSceneOrTVDBSeason(self):
        if self._scene_season == None:
            return self.season
        else:
            return self._scene_season

    def _getSceneOrTVDBEpisode(self):
        if self._scene_episode == None:
            return self.episode
        else:
            return self._scene_episode

    def _getSceneOrTVDBAbsolute(self):
        if self._scene_absolute_number == None:
            return self.absolute_number
        else:
            return self._scene_absolute_number

    def checkForMetaFiles(self):

        oldhasnfo = self.hasnfo
        oldhastbn = self.hastbn

        cur_nfo = False
        cur_tbn = False

        # check for nfo and tbn
        if ek.ek(os.path.isfile, self.location):
            for cur_provider in sickbeard.metadata_provider_dict.values():
                if cur_provider.episode_metadata:
                    new_result = cur_provider._has_episode_metadata(self)
                else:
                    new_result = False
                cur_nfo = new_result or cur_nfo
                
                if cur_provider.episode_thumbnails:
                    new_result = cur_provider._has_episode_thumb(self)
                else:
                    new_result = False
                cur_tbn = new_result or cur_tbn

        self.hasnfo = cur_nfo
        self.hastbn = cur_tbn

        # if either setting has changed return true, if not return false
        return oldhasnfo != self.hasnfo or oldhastbn != self.hastbn

    def specifyEpisode(self, season, episode):

        sqlResult = self.loadFromDB(season, episode)
        # we need this because if the db loading is done with scene we change the acctuay ep ans season number
        # and these numbers are not valid any more and have been replaced with tvdb numbers
        if sqlResult:
            season = self.season
            episode = self.episode
        
        # only load from NFO if we didn't load from DB
        if ek.ek(os.path.isfile, self.location) and self.name == "":
            try:
                self.loadFromNFO(self.location)
            except exceptions.NoNFOException:
                logger.log(str(self.show.tvdbid) + ": There was an error loading the NFO for episode " + str(season) + "x" + str(episode), logger.ERROR)
                pass

        # if we tried loading it from NFO and didn't find the NFO, use TVDB
        if self.hasnfo == False:
            try:
                result = self.loadFromTVDB(season, episode)
            except exceptions.EpisodeDeletedException:
                result = False

            # if we failed TVDB, NFO *and* SQL then fail
            if result == False and not sqlResult:
                raise exceptions.EpisodeNotFoundException("Couldn't find episode " + str(season) + "x" + str(episode))
        
        # don't update if not needed
        if self.dirty:
            self.saveToDB()


    def loadFromDB(self, season, episode):
        
        msg = ''
        if self.scene:
            msg = "(mode: scene numbers)"
        logger.log(str(self.show.tvdbid) + ": Loading episode details from DB for episode " + msg + " " + str(season) + "x" + str(episode), logger.DEBUG)
        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?", [self.show.tvdbid, season, episode])

        myDB = db.DBConnection()
        if not self.scene:
            sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?", [self.show.tvdbid, season, episode])
        else:
            sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND scene_season = ? AND scene_episode = ?", [self.show.tvdbid, season, episode])
            

        if len(sqlResults) > 1 and not self.scene:
            raise exceptions.MultipleDBEpisodesException("Your DB has two records for the same episode somehow."+msg)
        elif len(sqlResults) > 1 and self.scene:
            first = True
            for relatedEP in sqlResults:
                if first: # first shal be root ep
                    first = False
                    continue
                logger.log(str(self.show.tvdbid) + ": Adding a related episode because of a scene mapping with tvdb numbers " + str(relatedEP["season"]) + "x" + str(relatedEP["episode"]), logger.DEBUG)

                rel_ep_obj = TVEpisode(self.show, int(relatedEP["season"]), int(relatedEP["episode"]))
                self.relatedEps.append(rel_ep_obj)

        elif len(sqlResults) == 0:
            logger.log(str(self.show.tvdbid) + ": Episode " + msg + str(self.season) + "x" + str(self.episode) + " not found in the database", logger.DEBUG)
            return False
        else:
            #NAMEIT logger.log(u"AAAAA from" + str(self.season)+"x"+str(self.episode) + " -" + self.name + " to " + str(sqlResults[0]["name"]))
            if sqlResults[0]["name"] != None:
                self.name = sqlResults[0]["name"]

            if not self.scene:
                self.season = season
                self.episode = episode
            else:
                self.season = int(sqlResults[0]["season"])
                self.episode = int(sqlResults[0]["episode"])
            self.absolute_number = sqlResults[0]["absolute_number"]

            self.description = sqlResults[0]["description"]
            if self.description == None:
                self.description = ""
            self.airdate = datetime.date.fromordinal(int(sqlResults[0]["airdate"]))
            #logger.log(u"1 Status changes from " + str(self.status) + " to " + str(sqlResults[0]["status"]), logger.DEBUG)
            self.status = int(sqlResults[0]["status"])

            # don't overwrite my location
            if sqlResults[0]["location"] != "" and sqlResults[0]["location"] != None:
                self.location = os.path.normpath(sqlResults[0]["location"])

            self.tvdbid = int(sqlResults[0]["tvdbid"])
            
            # does one now a better way to test for NULL in the db field ?
            if isinstance(sqlResults[0]["scene_season"], int):
                self.scene_season = int(sqlResults[0]["scene_season"])

            if isinstance(sqlResults[0]["scene_episode"], int):
                self.scene_episode = int(sqlResults[0]["scene_episode"])
                
            if isinstance(sqlResults[0]["scene_absolute_number"], int):
                self.scene_absolute_number = int(sqlResults[0]["scene_absolute_number"])

            logger.log("Episode loading done " + msg + str(self.season) + "x" + str(self.episode) + "a" + str(self.absolute_number), logger.DEBUG)
            logger.log("Episode loading done " + msg + str(self.scene_season) + "x" + str(self.scene_episode) + "a" + str(self.scene_absolute_number), logger.DEBUG)
            
            self.scene = False
            self.dirty = False
            return True


    def loadFromTVDB(self, season=None, episode=None, cache=True, tvapi=None, cachedSeason=None):

        if season == None:
            season = self.season
        if episode == None:
            episode = self.episode

        logger.log(str(self.show.tvdbid) + ": Loading episode details from theTVDB for episode " + str(season) + "x" + str(episode), logger.DEBUG)

        tvdb_lang = self.show.lang

        try:
            if cachedSeason is None:
                logger.log(u"No chache for this episode", logger.DEBUG)
                if tvapi is None:
                    # There's gotta be a better way of doing this but we don't wanna
                    # change the cache value elsewhere
                    ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

                    if not cache:
                        ltvdb_api_parms['cache'] = 'recache'

                    if tvdb_lang:
                            ltvdb_api_parms['language'] = tvdb_lang

                    t = tvdb_api.Tvdb(**ltvdb_api_parms)
                else:
                    t = tvapi
                myEp = t[self.show.tvdbid][season][episode]
            else:
                logger.log(u"Chached for this episode", logger.DEBUG)
                myEp = cachedSeason[episode]

        except (tvdb_exceptions.tvdb_error, IOError), e:
            logger.log(u"TVDB threw up an error: "+ex(e), logger.DEBUG)
            # if the episode is already valid just log it, if not throw it up
            if self.name:
                logger.log(u"TVDB timed out but we have enough info from other sources, allowing the error", logger.DEBUG)
                return
            else:
                logger.log(u"TVDB timed out, unable to create the episode", logger.ERROR)
                return False
        except (tvdb_exceptions.tvdb_episodenotfound, tvdb_exceptions.tvdb_seasonnotfound):
            logger.log(u"Unable to find the episode on tvdb... has it been removed? Should I delete from db?", logger.DEBUG)
            # if I'm no longer on TVDB but I once was then delete myself from the DB
            if self.tvdbid != -1:
                self.deleteEpisode()
            return

        if not myEp["firstaired"]:
            myEp["firstaired"] = str(datetime.date.fromordinal(1))

        if myEp["episodename"] == None or myEp["episodename"] == "":
            logger.log(u"This episode ("+self.show.name+" - "+str(season)+"x"+str(episode)+") has no name on TVDB")
            # if I'm incomplete on TVDB but I once was complete then just delete myself from the DB for now
            if self.tvdbid != -1:
                self.deleteEpisode()
            return False
        
        if myEp["absolute_number"] == None or myEp["absolute_number"] == "":
            logger.log(u"This episode ("+self.show.name+" - "+str(season)+"x"+str(episode)+") has no absolute number on TVDB", logger.DEBUG)
        else: 
            logger.log(str(self.show.tvdbid) + ": The absolute_number for " + str(season) + "x" + str(episode)+" is : "+myEp["absolute_number"], logger.DEBUG)
            self.absolute_number = int(myEp["absolute_number"])

        #NAMEIT logger.log(u"BBBBBBBB from " + str(self.season)+"x"+str(self.episode) + " -" +self.name+" to "+myEp["episodename"])
        self.name = myEp["episodename"]
        self.season = season
        self.episode = episode
        
        tmp_description = myEp["overview"]
        if tmp_description == None:
            self.description = ""
        else:
            self.description = tmp_description
        rawAirdate = [int(x) for x in myEp["firstaired"].split("-")]
        try:
            self.airdate = datetime.date(rawAirdate[0], rawAirdate[1], rawAirdate[2])
        except ValueError:
            logger.log(u"Malformed air date retrieved from TVDB ("+self.show.name+" - "+str(season)+"x"+str(episode)+")", logger.ERROR)
            # if I'm incomplete on TVDB but I once was complete then just delete myself from the DB for now
            if self.tvdbid != -1:
                self.deleteEpisode()
            return False
        
        #early conversion to int so that episode doesn't get marked dirty
        self.tvdbid = int(myEp["id"])
        
        if not ek.ek(os.path.isdir, self.show._location):
            logger.log(u"The show dir is missing, not bothering to change the episode statuses since it'd probably be invalid")
            return

        logger.log(str(self.show.tvdbid) + ": Setting status for " + str(season) + "x" + str(episode) + " based on status " + str(self.status) + " and existence of " + self.location, logger.DEBUG)

        if not ek.ek(os.path.isfile, self.location):

            # if we don't have the file
            if self.airdate >= datetime.date.today() and self.status not in Quality.SNATCHED + Quality.SNATCHED_PROPER:
                # and it hasn't aired yet set the status to UNAIRED
                logger.log(u"Episode airs in the future, changing status from " + str(self.status) + " to " + str(UNAIRED), logger.DEBUG)
                self.status = UNAIRED
            # if there's no airdate then set it to skipped (and respect ignored)
            elif self.airdate == datetime.date.fromordinal(1):
                if self.status == IGNORED:
                    logger.log(u"Episode has no air date, but it's already marked as ignored", logger.DEBUG)
                elif self.season > 0 and self.show.getPreviuosAiredCount(self.season, self.episode):
                    logger.log(u"Episode has no air date, it's not a special and we have previously aired episodes, automatically marking it unaired", logger.DEBUG)
                    self.status = UNAIRED
                else:
                    logger.log(u"Episode has no air date and it's a special (or we dont have previously aired episodes), automatically marking it skipped", logger.DEBUG)
                    self.status = SKIPPED
            # if we don't have the file and the airdate is in the past
            else:
                if self.status == UNAIRED:
                    self.status = WANTED

                # if we somehow are still UNKNOWN then just skip it
                elif self.status == UNKNOWN:
                    self.status = SKIPPED

                else:
                    logger.log(u"Not touching status because we have no ep file, the airdate is in the past, and the status is "+str(self.status), logger.DEBUG)

        # if we have a media file then it's downloaded
        elif sickbeard.helpers.isMediaFile(self.location):
            # leave propers alone, you have to either post-process them or manually change them back
            if self.status not in Quality.SNATCHED_PROPER + Quality.DOWNLOADED + Quality.SNATCHED + [ARCHIVED]:
                logger.log(u"5 Status changes from " + str(self.status) + " to " + str(Quality.statusFromName(self.location)), logger.DEBUG)
                self.status = Quality.statusFromName(self.location)

        # shouldn't get here probably
        else:
            logger.log(u"6 Status changes from " + str(self.status) + " to " + str(UNKNOWN), logger.DEBUG)
            self.status = UNKNOWN


        # hasnfo, hastbn, status?


    def loadFromNFO(self, location):

        if not os.path.isdir(self.show._location):
            logger.log(str(self.show.tvdbid) + ": The show dir is missing, not bothering to try loading the episode NFO")
            return

        logger.log(str(self.show.tvdbid) + ": Loading episode details from the NFO file associated with " + location, logger.DEBUG)

        self.location = location

        if self.location != "":

            if self.status == UNKNOWN:
                if sickbeard.helpers.isMediaFile(self.location):
                    logger.log(u"7 Status changes from " + str(self.status) + " to " + str(Quality.statusFromName(self.location)), logger.DEBUG)
                    self.status = Quality.statusFromName(self.location)

            nfoFile = sickbeard.helpers.replaceExtension(self.location, "nfo")
            logger.log(str(self.show.tvdbid) + ": Using NFO name " + nfoFile, logger.DEBUG)

            if ek.ek(os.path.isfile, nfoFile):
                try:
                    showXML = etree.ElementTree(file = nfoFile)
                except (SyntaxError, ValueError), e:
                    logger.log(u"Error loading the NFO, backing up the NFO and skipping for now: " + ex(e), logger.ERROR) #TODO: figure out what's wrong and fix it
                    try:
                        ek.ek(os.rename, nfoFile, nfoFile + ".old")
                    except Exception, e:
                        logger.log(u"Failed to rename your episode's NFO file - you need to delete it or fix it: " + ex(e), logger.ERROR)
                    raise exceptions.NoNFOException("Error in NFO format")

                for epDetails in showXML.getiterator('episodedetails'):
                    if epDetails.findtext('season') == None or int(epDetails.findtext('season')) != self.season or \
                       epDetails.findtext('episode') == None or int(epDetails.findtext('episode')) != self.episode:
                        logger.log(str(self.show.tvdbid) + ": NFO has an <episodedetails> block for a different episode - wanted " + str(self.season) + "x" + str(self.episode) + " but got " + str(epDetails.findtext('season')) + "x" + str(epDetails.findtext('episode')), logger.DEBUG)
                        continue

                    if epDetails.findtext('title') == None or epDetails.findtext('aired') == None:
                        raise exceptions.NoNFOException("Error in NFO format (missing episode title or airdate)")

                    self.name = epDetails.findtext('title')
                    self.episode = int(epDetails.findtext('episode'))
                    self.season = int(epDetails.findtext('season'))

                    self.description = epDetails.findtext('plot')
                    if self.description == None:
                        self.description = ""

                    if epDetails.findtext('aired'):
                        rawAirdate = [int(x) for x in epDetails.findtext('aired').split("-")]
                        self.airdate = datetime.date(rawAirdate[0], rawAirdate[1], rawAirdate[2])
                    else:
                        self.airdate = datetime.date.fromordinal(1)

                    self.hasnfo = True
            else:
                self.hasnfo = False

            if ek.ek(os.path.isfile, sickbeard.helpers.replaceExtension(nfoFile, "tbn")):
                self.hastbn = True
            else:
                self.hastbn = False


    def __str__ (self):

        toReturn = ""
        toReturn += str(self.show.name) + " - " + str(self.season) + "x" + str(self.episode) + " - " + str(self.name) + "\n"
        toReturn += "location: " + str(self.location) + "\n"
        toReturn += "description: " + str(self.description) + "\n"
        toReturn += "airdate: " + str(self.airdate.toordinal()) + " (" + str(self.airdate) + ")\n"
        toReturn += "hasnfo: " + str(self.hasnfo) + "\n"
        toReturn += "hastbn: " + str(self.hastbn) + "\n"
        toReturn += "status: " + str(self.status) + "\n"
        return toReturn


    def createMetaFiles(self, force=False):

        if not ek.ek(os.path.isdir, self.show._location):
            logger.log(str(self.show.tvdbid) + ": The show dir is missing, not bothering to try to create metadata")
            return

        self.createNFO(force)
        self.createThumbnail(force)

        if self.checkForMetaFiles():
            self.saveToDB()


    def createNFO(self, force=False):

        result = False

        for cur_provider in sickbeard.metadata_provider_dict.values():
            result = cur_provider.create_episode_metadata(self) or result

        return result


    def createThumbnail(self, force=False):

        result = False

        for cur_provider in sickbeard.metadata_provider_dict.values():
            result = cur_provider.create_episode_thumb(self) or result

        return result

    def deleteEpisode(self):

        logger.log(u"Deleting "+self.show.name+" "+str(self.season)+"x"+str(self.episode)+" from the DB", logger.DEBUG)

        # remove myself from the show dictionary
        if self.show.getEpisode(self.season, self.episode, noCreate=True) == self:
            logger.log(u"Removing myself from my show's list", logger.DEBUG)
            del self.show.episodes[self.season][self.episode]

        # delete myself from the DB
        logger.log(u"Deleting myself from the database", logger.DEBUG)
        myDB = db.DBConnection()
        sql = "DELETE FROM tv_episodes WHERE showid="+str(self.show.tvdbid)+" AND season="+str(self.season)+" AND episode="+str(self.episode)
        myDB.action(sql)

        raise exceptions.EpisodeDeletedException()

    def saveToDB(self, forceSave=False):
        if not self.dirty and not forceSave:
            logger.log(str(self.show.tvdbid) + ": Not saving episode to db - record is not dirty", logger.DEBUG)
            return

        logger.log(str(self.show.tvdbid) + ": Saving episode details to database", logger.DEBUG)

        logger.log(u"STATUS IS " + str(statusStrings[self.status]), logger.DEBUG)

        myDB = db.DBConnection()
        newValueDict = {"tvdbid": self.tvdbid,
                        "name": self.name,
                        "description": self.description,
                        "airdate": self.airdate.toordinal(),
                        "hasnfo": self.hasnfo,
                        "hastbn": self.hastbn,
                        "status": self.status,
                        "location": self.location,
                        "absolute_number": self.absolute_number,
                        "scene_season": self._scene_season,
                        "scene_episode": self._scene_episode,
                        "scene_absolute_number": self._scene_absolute_number}
        controlValueDict = {"showid": self.show.tvdbid,
                            "season": self.season,
                            "episode": self.episode}

        # use a custom update/insert method to get the data into the DB
        myDB.upsert("tv_episodes", newValueDict, controlValueDict)


    def fullPath (self):
        if self.location == None or self.location == "":
            return None
        else:
            return os.path.join(self.show.location, self.location)

    def getOverview(self):
        return self.show.getOverview(self.status)

    def prettyName (self, naming_show_name=None,
                        naming_ep_type=None,
                        naming_multi_ep_type=None,
                        naming_ep_name=None,
                        naming_anime=None,
                        naming_sep_type=None,
                        naming_use_periods=None,
                        naming_quality=None):

        regex = "(.*) \(\d\)"

        goodEpString = ''

        self.relatedEps = sorted(self.relatedEps, key=lambda x: x.episode)

        if len(self.relatedEps) == 0:
            goodName = self.name

        elif len(self.relatedEps) > 1:
            goodName = ''

        else:
            singleName = True
            curGoodName = None

            for curName in [self.name]+[x.name for x in self.relatedEps]:
                match = re.match(regex, curName)
                if not match:
                    singleName = False
                    break

                if curGoodName == None:
                    curGoodName = match.group(1)
                elif curGoodName != match.group(1):
                    singleName = False
                    break


            if singleName:
                goodName = curGoodName
            else:
                goodName = self.name
                for relEp in self.relatedEps:
                    goodName += " & " + relEp.name

        if naming_show_name == None:
            naming_show_name = sickbeard.NAMING_SHOW_NAME

        if naming_ep_name == None:
            naming_ep_name = sickbeard.NAMING_EP_NAME

        if naming_ep_type == None:
            naming_ep_type = sickbeard.NAMING_EP_TYPE
            
        if naming_anime == None:
            naming_anime = sickbeard.NAMING_ANIME

        if naming_multi_ep_type == None:
            naming_multi_ep_type = sickbeard.NAMING_MULTI_EP_TYPE

        if naming_sep_type == None:
            naming_sep_type = sickbeard.NAMING_SEP_TYPE

        if naming_use_periods == None:
            naming_use_periods = sickbeard.NAMING_USE_PERIODS

        if naming_quality == None:
            naming_quality = sickbeard.NAMING_QUALITY
        #episode string begin
        if self.show.air_by_date and sickbeard.NAMING_DATES:
            try:
                goodEpString = self.airdate.strftime("%Y.%m.%d")
            except ValueError:
                pass
             
        # if we didn't set it to the air-by-date value use the season/ep
        if not goodEpString:
            goodEpString = config.naming_ep_type[naming_ep_type] % {'seasonnumber': self.season, 'episodenumber': self.episode}
            
            
        for relEp in self.relatedEps:
            goodEpString += config.naming_multi_ep_type[naming_multi_ep_type][naming_ep_type] % {'seasonnumber': relEp.season, 'episodenumber': relEp.episode}

        # anime ?
        if self.show.anime and naming_anime != 3:
            #FIXME: this should be set on show creation !!
            if self.absolute_number == 0:
                curAbsolute_number = self.episode
            else:
                curAbsolute_number = self.absolute_number
            
            if self.season != 0: # dont set absolute numbers if we are on specials !
                if naming_anime == 1: # this crazy person wants both ! (note: +=)
                    goodEpString += config.naming_sep_type[naming_sep_type]+"%(#)03d" % {"#":curAbsolute_number}
                elif naming_anime == 2: # total anime freak only need the absolute number ! (note: =)
                    goodEpString = "%(#)03d" % {"#":curAbsolute_number}
            
                for relEp in self.relatedEps:
                    if relEp.absolute_number != 0:
                        goodEpString += "-"+"%(#)03d" % {"#":relEp.absolute_number}
                    else:
                        goodEpString += "-"+"%(#)03d" % {"#":relEp.episode}
            
        #episode string end
        
        if goodName != '':
            goodName = config.naming_sep_type[naming_sep_type] + goodName

        finalName = ""

        if naming_show_name:
            finalName += self.show.name + config.naming_sep_type[naming_sep_type]

        finalName += goodEpString

        if naming_ep_name:
            finalName += goodName

        if naming_quality:
            epStatus, epQual = Quality.splitCompositeStatus(self.status) #@UnusedVariable
            if epQual != Quality.NONE:
                finalName += config.naming_sep_type[naming_sep_type] + Quality.qualityStrings[epQual]

        if naming_use_periods:
            finalName = re.sub("\s+", ".", finalName)

        return finalName

