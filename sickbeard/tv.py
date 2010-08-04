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
import urllib
import re
import glob

import sickbeard

import xml.etree.cElementTree as etree

from lib.tvdb_api import tvdb_api, tvnamer, tvdb_exceptions
from lib.tvnamer.utils import FileParser
from lib.tvnamer import tvnamer_exceptions

from sickbeard import db
from sickbeard import helpers, exceptions, logger
from sickbeard import processTV
from sickbeard import tvrage
from sickbeard import config
from sickbeard import metadata

from sickbeard import encodingKludge as ek

from common import *

class TVShow(object):

    def __init__ (self, tvdbid):
    
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

        self.lock = threading.Lock()
        self._isDirGood = False
        
        self.episodes = {}

        otherShow = helpers.findCertainShow(sickbeard.showList, self.tvdbid)
        if otherShow != None:
            raise exceptions.MultipleShowObjectsException("Can't create a show if it already exists")
        
        self.loadFromDB()
        
        self.saveToDB()
    
    
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
        logger.log("Setter sets location to " + newLocation, logger.DEBUG)
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
                if myEp not in sickbeard.comingList and \
                myEp not in sickbeard.airingList:
                    self.episodes[curSeason][curEp] = None
                    del myEp
            
    
    def getEpisode(self, season, episode, file=None, noCreate=False):

        #return TVEpisode(self, season, episode)
    
        if not season in self.episodes:
            self.episodes[season] = {}
        
        ep = None
        
        if not episode in self.episodes[season] or self.episodes[season][episode] == None:
            if noCreate:
                return None
            
            logger.log(str(self.tvdbid) + ": An object for episode " + str(season) + "x" + str(episode) + " didn't exist in the cache, trying to create it", logger.DEBUG)

            if file != None:
                ep = TVEpisode(self, season, episode, file)
            else:
                ep = TVEpisode(self, season, episode)
            
            if ep != None:
                self.episodes[season][episode] = ep
        
        return self.episodes[season][episode]

    def writeShowNFO(self):

        if not ek.ek(os.path.isdir, self._location):
            logger.log(str(self.tvdbid) + ": Show dir doesn't exist, skipping NFO generation")
            return

        xmlData = metadata.makeShowNFO(self.tvdbid)
            
        # Make it purdy
        helpers.indentXML( xmlData )
    
        nfo_fh = ek.ek(open, ek.ek(os.path.join, self._location, "tvshow.nfo"), 'w')
        nfo = etree.ElementTree( xmlData )
        nfo.write( nfo_fh, encoding="utf-8" )
        nfo_fh.close()

    def writeMetadata(self):
        
        if not ek.ek(os.path.isdir, self._location):
            logger.log(str(self.tvdbid) + ": Show dir doesn't exist, skipping NFO generation")
            return

        if sickbeard.CREATE_IMAGES:
            self.getImages()
        
        if sickbeard.CREATE_METADATA:
            self.writeShowNFO()
            self.writeEpisodeNFOs()


    def writeEpisodeNFOs (self):
        
        if not ek.ek(os.path.isdir, self._location):
            logger.log(str(self.tvdbid) + ": Show dir doesn't exist, skipping NFO generation")
            return
        
        logger.log(str(self.tvdbid) + ": Writing NFOs for all episodes")
        
        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = " + str(self.tvdbid) + " AND location != ''")
        
        for epResult in sqlResults:
            logger.log(str(self.tvdbid) + ": Retrieving/creating episode " + str(epResult["season"]) + "x" + str(epResult["episode"]), logger.DEBUG)
            curEp = self.getEpisode(epResult["season"], epResult["episode"])
            curEp.createMetaFiles()


    # find all media files in the show folder and create episodes for as many as possible
    def loadEpisodesFromDir (self):

        if not os.path.isdir(self._location):
            logger.log(str(self.tvdbid) + ": Show dir doesn't exist, not loading episodes from disk")
            return
        
        logger.log(str(self.tvdbid) + ": Loading all episodes from the show directory " + self._location)

        # get file list
        mediaFiles = helpers.listMediaFiles(self._location)

        # create TVEpisodes from each media file (if possible)
        for mediaFile in mediaFiles:
            
            curEpisode = None
            
            logger.log(str(self.tvdbid) + ": Creating episode from " + mediaFile, logger.DEBUG)
            try:
                curEpisode = self.makeEpFromFile(os.path.join(self._location, mediaFile))
            except (exceptions.ShowNotFoundException, exceptions.EpisodeNotFoundException), e:
                logger.log("Episode "+mediaFile+" returned an exception: "+str(e), logger.ERROR)
            except exceptions.EpisodeDeletedException:
                logger.log("The episode deleted itself when I tried making an object for it", logger.DEBUG)
                    

            # store the reference in the show
            if curEpisode != None:
                curEpisode.saveToDB()
    
    
    def loadEpisodesFromDB(self):
    
        logger.log("Loading all episodes from the DB")
    
        myDB = db.DBConnection()
        sql = "SELECT * FROM tv_episodes WHERE showid="+str(self.tvdbid)
        sqlResults = myDB.select(sql)
        
        scannedEps = {}
        
        for curResult in sqlResults:
            
            curSeason = int(curResult["season"])
            curEpisode = int(curResult["episode"])
            
            if not curSeason in scannedEps:
                scannedEps[curSeason] = {}
            
            logger.log("Loading episode "+str(curSeason)+"x"+str(curEpisode)+" from the DB", logger.DEBUG)
            
            try:
                curEp = self.getEpisode(curSeason, curEpisode)
                curEp.loadFromDB(curSeason, curEpisode)
                curEp.loadFromTVDB()
                scannedEps[curSeason][curEpisode] = True
            except exceptions.EpisodeDeletedException:
                logger.log("Tried loading an episode from the DB that should have been deleted, skipping it", logger.DEBUG)
                continue

        return scannedEps
    

    def loadEpisodesFromTVDB(self, cache=True):
    
        # There's gotta be a better way of doing this but we don't wanna
        # change the cache value elsewhere
        ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

        if not cache:
            ltvdb_api_parms['cache'] = 'recache'

        try:
            t = tvdb_api.Tvdb(**ltvdb_api_parms)
            showObj = t[self.tvdbid]
        except tvdb_exceptions.tvdb_error:
            logger.log("TVDB timed out, unable to update episodes from TVDB", logger.ERROR)
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
                        ep.loadFromTVDB()
                    except exceptions.EpisodeDeletedException:
                        logger.log("The episode was deleted, skipping the rest of the load")
                        continue
                
                with ep.lock:
                    logger.log(str(self.tvdbid) + ": Loading info from theTVDB for episode " + str(season) + "x" + str(episode), logger.DEBUG)
                    ep.loadFromTVDB(season, episode)
                    ep.saveToDB()
                
                scannedEps[season][episode] = True

        return scannedEps

    def setTVRID(self, force=False):
        
        if self.tvrid != 0 and not force:
            logger.log("No need to get the TVRage ID, it's already populated", logger.DEBUG)
            return

        logger.log("Attempting to retrieve the TVRage ID", logger.DEBUG)

        try:
            # load the tvrage object, it will set the ID in its constructor if possible
            tvr = tvrage.TVRage(self)
            self.saveToDB()
        except exceptions.TVRageException, e:
            logger.log("Couldn't get TVRage ID because we're unable to sync TVDB and TVRage: "+str(e), logger.DEBUG)
            return        
        
    def getImages(self, fanart=None, poster=None):
        
        if not sickbeard.CREATE_IMAGES:
            logger.log("Skipping image retrieval since metadata creation is turned off", logger.DEBUG)
            return

        try:
            t = tvdb_api.Tvdb(banners=True, **sickbeard.TVDB_API_PARMS)
            myShow = t[self.tvdbid]
        except (tvdb_exceptions.tvdb_error, IOError), e:
            logger.log("Unable to look up show on TVDB, not downloading images: "+str(e), logger.ERROR)
            return None

        fanartURL = myShow['fanart']
        posterURL = myShow['poster']

        # get the image data
        if not ek.ek(os.path.isfile, ek.ek(os.path.join, self.location, "fanart.jpg")):
            fanartData = None
            if fanart != None:
                fanartData = helpers.getShowImage(fanartURL, fanart)
            
            # if we had a custom image number that failed OR we had no custom number then get the default one
            if fanartData == None:
                fanartData = helpers.getShowImage(fanartURL)
    
            if fanartData == None:
                logger.log("Unable to retrieve fanart, skipping", logger.WARNING)
            else:
                try:
                    outFile = ek.ek(open, ek.ek(os.path.join, self.location, "fanart.jpg"), 'wb')
                    outFile.write(fanartData)
                    outFile.close()
                except IOError, e:
                    logger.log("Unable to write fanart to "+ek.ek(os.path.join, self.location, "fanart.jpg")+" - are you sure the show folder is writable? "+str(e), logger.ERROR)
        
        # get the image data
        if not ek.ek(os.path.isfile, ek.ek(os.path.join, self.location, "folder.jpg")):
            posterData = None
            if poster != None:
                posterData = helpers.getShowImage(posterURL, poster)
            
            # if we had a custom image number that failed OR we had no custom number then get the default one
            if posterData == None:
                posterData = helpers.getShowImage(posterURL)
    
            if posterData == None:
                logger.log("Unable to retrieve poster, skipping", logger.WARNING)
            else:
                try:
                    outFile = ek.ek(open, ek.ek(os.path.join, self.location, "folder.jpg"), 'wb')
                    outFile.write(posterData)
                    outFile.close()
                except IOError, e:
                    logger.log("Unable to write poster to "+ek.ek(os.path.join, self.location, "folder.jpg")+" - are you sure the show folder is writable? "+str(e), logger.ERROR)

        seasonData = None 
        #  How many seasons? 
        numOfSeasons = len(myShow) 
        
        # if we have no season banners then just finish
        if 'season' not in myShow['_banners'] or 'season' not in myShow['_banners']['season']:
            return
        
        # Give us just the normal poster-style season graphics 
        seasonsArtObj = myShow['_banners']['season']['season']
        
        # This holds our resulting dictionary of season art 
        seasonsDict = {} 
        
        # Returns a nested dictionary of season art with the season 
        # number as primary key. It's really overkill but gives the option 
        # to present to user via ui to pick down the road. 
        for seasonNum in range(numOfSeasons): 
            # dumb, but we do have issues with types here so make it 
            # strings for now 
            seasonNum = str(seasonNum) 
            seasonsDict[seasonNum] = {} 
            for seasonArtID in seasonsArtObj.keys(): 
                seasonArtID = str(seasonArtID) 
                if seasonsArtObj[seasonArtID]['season'] == seasonNum and seasonsArtObj[seasonArtID]['language'] == 'en': 
                    seasonsDict[seasonNum][seasonArtID] = seasonsArtObj[seasonArtID]['_bannerpath'] 
            if len(seasonsDict[seasonNum]) > 0: 
                # Just grab whatever's there for now 
                season, seasonURL = seasonsDict[seasonNum].popitem() 
            
                # Our specials thumbnail is, well, special
                if seasonNum == '0':
                    seasonFileName = 'season-specials'
                else:
                    seasonFileName = 'season' + seasonNum.zfill(2) 
            
                # Let's do the check before we pull the file 
                if not ek.ek(os.path.isfile, ek.ek(os.path.join, self.location, seasonFileName+'.tbn')):

                    seasonData = helpers.getShowImage(seasonURL) 
            
                    if seasonData == None: 
                        logger.log("Unable to retrieve season poster, skipping", logger.ERROR) 
                    else:
                        try:
                            outFile = ek.ek(open, ek.ek(os.path.join, self.location, seasonFileName+'.tbn'), 'wb') 
                            outFile.write(seasonData) 
                            outFile.close()
                        except IOError, e:
                            logger.log("Unable to write fanart - are you sure the show folder is writable? "+str(e), logger.ERROR)


    def loadLatestFromTVRage(self):
        
        try:
            # load the tvrage object
            tvr = tvrage.TVRage(self)

            newEp = tvr.findLatestEp()
            
            if newEp != None:
                logger.log("TVRage gave us an episode object - saving it for now", logger.DEBUG)
                newEp.saveToDB()
            
            # make an episode out of it
        except exceptions.TVRageException, e:
            logger.log("Unable to add TVRage info: " + str(e), logger.WARNING)
            


    # make a TVEpisode object from a media file
    def makeEpFromFile(self, file):

        if not ek.ek(os.path.isfile, file):
            logger.log(str(self.tvdbid) + ": That isn't even a real file dude... " + file)
            return None

        logger.log(str(self.tvdbid) + ": Creating episode object from " + file, logger.DEBUG)

        try:
            myParser = FileParser(file)
            epInfo = myParser.parse()
        except tvnamer_exceptions.InvalidFilename:
            logger.log("Unable to parse the filename "+file+" into a valid episode", logger.ERROR)
            return None

        if len(epInfo.episodenumbers) == 0:
            logger.log("No episode number found in "+file+", ignoring it", logger.ERROR)
            return None

        # for now lets assume that any episode in the show dir belongs to that show
        season = epInfo.seasonnumber
        episodes = epInfo.episodenumbers
        rootEp = None

        # if we have an air-by-date show then get the real season/episode numbers
        if season == -1:
            try:
                t = tvdb_api.Tvdb(**sickbeard.TVDB_API_PARMS)
                epObj = t[self.tvdbid].airedOn(episodes[0])[0]
                season = int(epObj["seasonnumber"])
                episodes = [int(epObj["episodenumber"])]
            except tvdb_exceptions.tvdb_episodenotfound, e:
                logger.log("Unable to find episode with date "+str(episodes[0])+" for show "+self.name+", skipping", logger.WARNING)
                return None

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
                if ek.ek(os.path.normpath, curEp.location) != ek.ek(os.path.normpath, file):
                    logger.log("The old episode had a different file associated with it, I will re-check the quality based on the new filename "+file, logger.DEBUG)
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
                newQuality = Quality.nameQuality(file)
                logger.log("Since this file has been renamed, I checked "+file+" and found quality "+Quality.qualityStrings[newQuality], logger.DEBUG)
                if newQuality != Quality.UNKNOWN:
                    curEp.status = Quality.compositeStatus(DOWNLOADED, newQuality)


            elif sickbeard.helpers.isMediaFile(file) and curEp.status not in Quality.DOWNLOADED + [ARCHIVED]:
                
                oldStatus, oldQuality = Quality.splitCompositeStatus(curEp.status)
                newQuality = Quality.nameQuality(file)
                if newQuality == Quality.UNKNOWN:
                    newQuality = Quality.assumeQuality(file)
                newStatus = None
                
                # if it was snatched and now exists then set the status correctly
                if oldStatus == SNATCHED and oldQuality <= newQuality:
                    logger.log("STATUS: this ep used to be snatched with quality "+Quality.qualityStrings[oldQuality]+" but a file exists with quality "+Quality.qualityStrings[newQuality]+" so I'm setting the status to DOWNLOADED", logger.DEBUG)
                    newStatus = DOWNLOADED
                
                # if it was snatched proper and we found a higher quality one then allow the status change
                elif oldStatus == SNATCHED_PROPER and oldQuality < newQuality:
                    logger.log("STATUS: this ep used to be snatched proper with quality "+Quality.qualityStrings[oldQuality]+" but a file exists with quality "+Quality.qualityStrings[newQuality]+" so I'm setting the status to DOWNLOADED", logger.DEBUG)
                    newStatus = DOWNLOADED

                elif oldStatus not in (SNATCHED, SNATCHED_PROPER):
                    newStatus = DOWNLOADED
                
                if newStatus != None:
                    with curEp.lock:
                        logger.log("STATUS: we have an associated file, so setting the status from "+str(curEp.status)+" to DOWNLOADED/" + str(Quality.statusFromName(file)), logger.DEBUG)
                        curEp.status = Quality.compositeStatus(newStatus, newQuality)
                        
            with curEp.lock:
                curEp.saveToDB()
                
        # creating metafiles on the root should be good enough
        if rootEp != None:
            with rootEp.lock:
                rootEp.createMetaFiles()

        return None

    
    def loadFromDB(self, skipNFO=False):

        logger.log(str(self.tvdbid) + ": Loading show info from database")

        myDB = db.DBConnection()
        
        sqlResults = myDB.select("SELECT * FROM tv_shows WHERE tvdb_id = " + str(self.tvdbid))

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

            self.quality = int(sqlResults[0]["quality"])
            self.seasonfolders = int(sqlResults[0]["seasonfolders"])
            self.paused = int(sqlResults[0]["paused"])

            self._location = sqlResults[0]["location"]

            if self.tvrid == 0:
                self.tvrid = int(sqlResults[0]["tvr_id"])
    
    def loadFromTVDB(self, cache=True):

        logger.log(str(self.tvdbid) + ": Loading show info from theTVDB") 

        # There's gotta be a better way of doing this but we don't wanna
        # change the cache value elsewhere
        ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

        if not cache:
            ltvdb_api_parms['cache'] = 'recache'

        t = tvdb_api.Tvdb(**ltvdb_api_parms)
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
            logger.log("There was an error parsing your existing tvshow.nfo file: " + str(e), logger.ERROR)
            logger.log("Attempting to rename it to tvshow.nfo.old", logger.DEBUG)

            try:
                xmlFileObj.close()
                ek.ek(os.rename, xmlFile, xmlFile + ".old")
            except Exception, e:
                logger.log("Failed to rename your tvshow.nfo file - you need to delete it or fix it: " + str(e), logger.ERROR)
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
        innerQuery = "SELECT airdate FROM tv_episodes WHERE showid = " + str(self.tvdbid) + " AND airdate >= " + str(datetime.date.today().toordinal()) + " AND status = " + str(UNAIRED) + " ORDER BY airdate ASC LIMIT 1"
        query = "SELECT * FROM tv_episodes WHERE showid = " + str(self.tvdbid) + " AND airdate >= " + str(datetime.date.today().toordinal()) + " AND airdate <= ("+innerQuery+") and status = " + str(UNAIRED)
        sqlResults = myDB.select(query)
    
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
        myDB.action("DELETE FROM tv_episodes WHERE showid = " + str(self.tvdbid))
        myDB.action("DELETE FROM tv_shows WHERE tvdb_id = " + str(self.tvdbid))
        
        # remove self from show list
        sickbeard.showList = [x for x in sickbeard.showList if x.tvdbid != self.tvdbid]
        
    def refreshDir(self):

        # make sure the show dir is where we think it is
        if not os.path.isdir(self._location):
            return False
        
        # load from dir
        self.loadEpisodesFromDir()
            
        # run through all locations from DB, check that they exist
        logger.log(str(self.tvdbid) + ": Loading all episodes with a location from the database")
        
        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = " + str(self.tvdbid) + " AND location != ''")
        
        for ep in sqlResults:
            curLoc = os.path.normpath(ep["location"])
            season = int(ep["season"])
            episode = int(ep["episode"])
            
            try:
                curEp = self.getEpisode(season, episode)
            except exceptions.EpisodeDeletedException:
                logger.log("The episode was deleted while we were refreshing it, moving on to the next one", logger.DEBUG)
                continue
            
            # if the path doesn't exist or if it's not in our show dir
            if not ek.ek(os.path.isfile, curLoc) or not os.path.normpath(curLoc).startswith(os.path.normpath(self.location)):
            
                logger.log(str(self.tvdbid) + ": Location for " + str(season) + "x" + str(episode) + " doesn't exist, removing it and changing our status to SKIPPED", logger.DEBUG)
                with curEp.lock:
                    curEp.location = ''
                    if curEp.status in Quality.DOWNLOADED:
                        curEp.status = SKIPPED
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
        sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = " + str(self.tvdbid) + " AND location != ''")
        
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
        
        logger.log("File results: " + str(fileLocations), logger.DEBUG)

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
            curEpDir = os.path.dirname(curLocation)

            if goodName == actualName[0]:
                logger.log(str(self.tvdbid) + ": File " + rootEp.location + " is already named correctly, skipping", logger.DEBUG)
                continue
            
            with rootEp.lock:
                result = processTV.renameFile(rootEp.location, rootEp.prettyName())
                if result != False:
                    rootEp.location = result
                    for relEp in rootEp.relatedEps:
                        relEp.location = result
            
            fileList = ek.ek(glob.glob, ek.ek(os.path.join, curEpDir, actualName[0] + "*").replace("[","*").replace("]","*"))

            for file in fileList:
                result = processTV.renameFile(file, rootEp.prettyName())
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
                        "startyear": self.startyear,
                        "tvr_name": self.tvrname
                        }

        myDB.upsert("tv_shows", newValueDict, controlValueDict)
        
        
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
        return toReturn

        
    def wantEpisode(self, season, episode, quality, manualSearch=False):
        
        logger.log("Checking if we want episode "+str(season)+"x"+str(episode)+" at quality "+Quality.qualityStrings[quality], logger.DEBUG)

        # if the quality isn't one we want under any circumstances then just say no
        anyQualities, bestQualities = Quality.splitQuality(self.quality)
        logger.log("A,B = "+str(anyQualities)+" "+str(bestQualities)+" and we are "+str(quality), logger.DEBUG)
        
        if quality not in anyQualities + bestQualities:
            return False

        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT status FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?", [self.tvdbid, season, episode])
        
        if not sqlResults or not len(sqlResults):
            logger.log("Unable to find the episode", logger.DEBUG)
            return False
        
        epStatus = int(sqlResults[0]["status"])

        # if we know we don't want it then just say no
        if epStatus in (SKIPPED, IGNORED, ARCHIVED) and not manualSearch:
            logger.log("Ep is skipped, not bothering", logger.DEBUG)
            return False

        # if it's one of these then we want it as long as it's in our allowed initial qualities
        if quality in anyQualities + bestQualities:
            if epStatus in (WANTED, UNAIRED, SKIPPED):
                logger.log("Ep is wanted/unaired/skipped, definitely get it", logger.DEBUG)
                return True
            elif epStatus in (IGNORED, ARCHIVED) and manualSearch:
                logger.log("Ep is ignored/archived and you manually searched so overriding the default and allowing the quality", logger.DEBUG)
                return True
        
        curStatus, curQuality = Quality.splitCompositeStatus(epStatus)
        
        # if we are re-downloading then we only want it if it's in our bestQualities list and better than what we have
        if curStatus in Quality.SNATCHED + Quality.DOWNLOADED and quality in bestQualities and quality > curQuality:
            logger.log("We already have this ep but the new one is better quality, saying yes", logger.DEBUG)
            return True

        logger.log("None of the conditions were met so I'm just saying no", logger.DEBUG)
        return False
        
        
    def getOverview(self, epStatus):

        anyQualities, bestQualities = Quality.splitQuality(self.quality)
        if bestQualities:
            maxBestQuality = max(bestQualities)
        else:
            maxBestQuality = None 
    
        if epStatus == WANTED:
            return Overview.WANTED
        elif epStatus in (UNAIRED, UNKNOWN):
            return Overview.UNAIRED
        elif epStatus in (SKIPPED, IGNORED):
            return Overview.SKIPPED
        elif epStatus == ARCHIVED:
            return Overview.GOOD
        elif epStatus in Quality.DOWNLOADED + Quality.SNATCHED + Quality.SNATCHED_PROPER:
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

        
class TVEpisode:

    def __init__(self, show, season, episode, file=""):
    
        self.name = ""
        self.season = season
        self.episode = episode
        self.description = ""
        self.airdate = datetime.date.fromordinal(1)
        self.hasnfo = False
        self.hastbn = False
        self.status = UNKNOWN

        self.tvdbid = 0

        self.show = show
        self.location = file
        
        self.lock = threading.Lock()
        
        self.specifyEpisode(self.season, self.episode)

        self.relatedEps = []

        self.checkForMetaFiles()

    def checkForMetaFiles(self): 
        
        oldhasnfo = self.hasnfo
        oldhastbn = self.hastbn
        
        # check for nfo and tbn
        if ek.ek(os.path.isfile, self.location):
            if ek.ek(os.path.isfile, ek.ek(os.path.join, self.show.location, helpers.replaceExtension(self.location, 'nfo'))):
                self.hasnfo = True
            else:
                self.hasnfo = False
                
            if ek.ek(os.path.isfile, ek.ek(os.path.join, self.show.location, helpers.replaceExtension(self.location, 'tbn'))):
                self.hastbn = True
            else:
                self.hastbn = False

        # if either setting has changed return true, if not return false
        return oldhasnfo != self.hasnfo or oldhastbn != self.hastbn 
        
    def specifyEpisode(self, season, episode):
        
        sqlResult = self.loadFromDB(season, episode)
        
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
        
        self.saveToDB()
        
    
    def loadFromDB(self, season, episode):

        logger.log(str(self.show.tvdbid) + ": Loading episode details from DB for episode " + str(season) + "x" + str(episode), logger.DEBUG)

        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = " + str(self.show.tvdbid) + " AND season = " + str(season) + " AND episode = " + str(episode))

        if len(sqlResults) > 1:
            raise exceptions.MultipleDBEpisodesException("Your DB has two records for the same show somehow.")
        elif len(sqlResults) == 0:
            logger.log(str(self.show.tvdbid) + ": Episode " + str(self.season) + "x" + str(self.episode) + " not found in the database", logger.DEBUG) 
            return False
        else:
            #NAMEIT logger.log("AAAAA from" + str(self.season)+"x"+str(self.episode) + " -" + self.name + " to " + str(sqlResults[0]["name"]))
            if sqlResults[0]["name"] != None:
                self.name = sqlResults[0]["name"] 
            self.season = season
            self.episode = episode
            self.description = sqlResults[0]["description"]
            if self.description == None:
                self.description = ""
            self.airdate = datetime.date.fromordinal(int(sqlResults[0]["airdate"]))
            #logger.log("1 Status changes from " + str(self.status) + " to " + str(sqlResults[0]["status"]), logger.DEBUG)
            self.status = int(sqlResults[0]["status"])
            
            # don't overwrite my location
            if sqlResults[0]["location"] != "" and sqlResults[0]["location"] != None:
                self.location = os.path.normpath(sqlResults[0]["location"])
            
            self.tvdbid = int(sqlResults[0]["tvdbid"])
            
            return True
    
    
    def loadFromTVDB(self, season=None, episode=None, cache=True):

        if season == None:
            season = self.season
        if episode == None:
            episode = self.episode

        logger.log(str(self.show.tvdbid) + ": Loading episode details from theTVDB for episode " + str(season) + "x" + str(episode), logger.DEBUG)

        # There's gotta be a better way of doing this but we don't wanna
        # change the cache value elsewhere
        ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

        if not cache:
            ltvdb_api_parms['cache'] = 'recache'

        try:
            t = tvdb_api.Tvdb(**ltvdb_api_parms)
            myEp = t[self.show.tvdbid][season][episode]
        except (tvdb_exceptions.tvdb_error, IOError), e:
            logger.log("TVDB threw up an error: "+str(e), logger.DEBUG)
            # if the episode is already valid just log it, if not throw it up
            if self.name:
                logger.log("TVDB timed out but we have enough info from other sources, allowing the error", logger.DEBUG)
                return
            else:
                logger.log("TVDB timed out, unable to create the episode", logger.ERROR)
                return False
        except (tvdb_exceptions.tvdb_episodenotfound, tvdb_exceptions.tvdb_seasonnotfound):
            logger.log("Unable to find the episode on tvdb... has it been removed? Should I delete from db?", logger.DEBUG)
            # if I'm no longer on TVDB but I once was then delete myself from the DB
            if self.tvdbid != -1:
                self.deleteEpisode()
            return

            
        if not myEp["firstaired"]:
            myEp["firstaired"] = str(datetime.date.fromordinal(1))
            
        if myEp["episodename"] == None or myEp["episodename"] == "":
            logger.log("This episode ("+self.show.name+" - "+str(season)+"x"+str(episode)+") has no name on TVDB")
            # if I'm incomplete on TVDB but I once was complete then just delete myself from the DB for now
            if self.tvdbid != -1:
                self.deleteEpisode()
            return False

        #NAMEIT logger.log("BBBBBBBB from " + str(self.season)+"x"+str(self.episode) + " -" +self.name+" to "+myEp["episodename"])
        self.name = myEp["episodename"]
        self.season = season
        self.episode = episode
        self.description = myEp["overview"]
        if self.description == None:
            self.description = ""
        rawAirdate = [int(x) for x in myEp["firstaired"].split("-")]
        try:
            self.airdate = datetime.date(rawAirdate[0], rawAirdate[1], rawAirdate[2])
        except ValueError:
            logger.log("Malformed air date retrieved from TVDB ("+self.show.name+" - "+str(season)+"x"+str(episode)+")", logger.ERROR)
            # if I'm incomplete on TVDB but I once was complete then just delete myself from the DB for now
            if self.tvdbid != -1:
                self.deleteEpisode()
            return False
            
        self.tvdbid = myEp["id"]

        if not os.path.isdir(self.show._location):
            logger.log("The show dir is missing, not bothering to change the episode statuses since it'd probably be invalid")
            return

        logger.log(str(self.show.tvdbid) + ": Setting status for " + str(season) + "x" + str(episode) + " based on status " + str(self.status) + " and existence of " + self.location, logger.DEBUG)
        
        if not ek.ek(os.path.isfile, self.location):

            # if we don't have the file
            if self.airdate >= datetime.date.today() and self.status not in Quality.SNATCHED + Quality.SNATCHED_PROPER:
                # and it hasn't aired yet set the status to UNAIRED
                logger.log("Episode airs in the future, changing status from " + str(self.status) + " to " + str(UNAIRED), logger.DEBUG)
                self.status = UNAIRED
            elif self.airdate == datetime.date.fromordinal(1):
                logger.log("Episode has no air date, automatically marking it skipped", logger.DEBUG)
                self.status = SKIPPED
            else:
                if self.status == UNAIRED:
                    self.status = WANTED
    
                # if we somehow are still UNKNOWN then just skip it
                elif self.status == UNKNOWN:
                        self.status = SKIPPED

        # if we have a media file then it's downloaded
        elif sickbeard.helpers.isMediaFile(self.location):
            # leave propers alone, you have to either post-process them or manually change them back
            if self.status not in Quality.SNATCHED_PROPER + Quality.DOWNLOADED + Quality.SNATCHED + [ARCHIVED]:
                logger.log("5 Status changes from " + str(self.status) + " to " + str(Quality.statusFromName(self.location)), logger.DEBUG)
                self.status = Quality.statusFromName(self.location)

        # shouldn't get here probably
        else:
            logger.log("6 Status changes from " + str(self.status) + " to " + str(UNKNOWN), logger.DEBUG)
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
                    logger.log("7 Status changes from " + str(self.status) + " to " + str(Quality.statusFromName(self.location)), logger.DEBUG)
                    self.status = Quality.statusFromName(self.location)
        
            nfoFile = sickbeard.helpers.replaceExtension(self.location, "nfo")
            logger.log(str(self.show.tvdbid) + ": Using NFO name " + nfoFile, logger.DEBUG)
            
            if ek.ek(os.path.isfile, nfoFile):
                try:
                    showXML = etree.ElementTree(file = nfoFile)
                except (SyntaxError, ValueError), e:
                    logger.log("Error loading the NFO, backing up the NFO and skipping for now: " + str(e), logger.ERROR) #TODO: figure out what's wrong and fix it
                    try:
                        ek.ek(os.rename, nfoFile, nfoFile + ".old")
                    except Exception, e:
                        logger.log("Failed to rename your episode's NFO file - you need to delete it or fix it: " + str(e), logger.ERROR)
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
        toReturn += self.show.name + " - " + str(self.season) + "x" + str(self.episode) + " - " + self.name + "\n"
        toReturn += "location: " + self.location + "\n"
        toReturn += "description: " + self.description + "\n"
        toReturn += "airdate: " + str(self.airdate.toordinal()) + " (" + str(self.airdate) + ")\n"
        toReturn += "hasnfo: " + str(self.hasnfo) + "\n"
        toReturn += "hastbn: " + str(self.hastbn) + "\n"
        toReturn += "status: " + str(self.status) + "\n"
        return toReturn

        
    def createMetaFiles(self, force=False):
        
        if not os.path.isdir(self.show._location):
            logger.log(str(self.show.tvdbid) + ": The show dir is missing, not bothering to try to create metadata")
            return

        epsToWrite = [self] + self.relatedEps

        shouldSave = self.checkForMetaFiles()

        if sickbeard.CREATE_METADATA or force:
            result = self.createNFOs(epsToWrite, force)
            if result == None:
                return False
            elif result == True:
                shouldSave = True
        
        if sickbeard.CREATE_IMAGES or force:
            result = self.createArt(epsToWrite, force)
            if result == None:
                return False
            elif result == True:
                shouldSave = True

        # save our new NFO statuses to the DB
        if shouldSave:
            self.saveToDB()

        
    def createNFOs(self, epsToWrite, force=False):
        
        shouldSave = False

        try:
            t = tvdb_api.Tvdb(actors=True, **sickbeard.TVDB_API_PARMS)
            myShow = t[self.show.tvdbid]
        except tvdb_exceptions.tvdb_shownotfound, e:
            raise exceptions.ShowNotFoundException(str(e))
        except tvdb_exceptions.tvdb_error, e:
            logger.log("Unable to connect to TVDB while creating meta files - skipping - "+str(e), logger.ERROR)
            return

        if len(epsToWrite) > 1:
            rootNode = etree.Element( "xbmcmultiepisode" )
        else:
            rootNode = etree.Element( "episodedetails" )

        # Set our namespace correctly
        for ns in XML_NSMAP.keys():
            rootNode.set(ns, XML_NSMAP[ns])
        
        needsNFO = not self.hasnfo
        if force:
            needsNFO = True

        # if we're not forcing then we want to make an NFO unless every related ep already has one
        else:
            for curEp in epsToWrite:
                if not curEp.hasnfo:
                    break
                needsNFO = False

        # write an NFO containing info for all matching episodes
        for curEpToWrite in epsToWrite:
        
            try:
                myEp = myShow[curEpToWrite.season][curEpToWrite.episode]
            except (tvdb_exceptions.tvdb_episodenotfound, tvdb_exceptions.tvdb_seasonnotfound):
                logger.log("Unable to find episode " + str(curEpToWrite.season) + "x" + str(curEpToWrite.episode) + " on tvdb... has it been removed? Should I delete from db?")
                return None
            
            if myEp["firstaired"] == None and self.season == 0:
                myEp["firstaired"] = str(datetime.date.fromordinal(1))
            
            if myEp["episodename"] == None or myEp["firstaired"] == None:
                return None
                
            if not needsNFO:
                logger.log("Skipping metadata generation for myself ("+str(self.season)+"x"+str(self.episode)+")", logger.DEBUG)
                continue
            else:
                logger.log("Creating metadata for myself ("+str(self.season)+"x"+str(self.episode)+")", logger.DEBUG)
            
            if len(epsToWrite) > 1:
                episode = etree.SubElement( rootNode, "episodedetails" )
            else:
                episode = rootNode

            title = etree.SubElement( episode, "title" )
            if curEpToWrite.name != None:
                title.text = curEpToWrite.name

            season = etree.SubElement( episode, "season" )
            season.text = str(curEpToWrite.season)
    
            episodenum = etree.SubElement( episode, "episode" )
            episodenum.text = str(curEpToWrite.episode)
            
            aired = etree.SubElement( episode, "aired" )
            if curEpToWrite.airdate != datetime.date.fromordinal(1):
                aired.text = str(curEpToWrite.airdate)
            else:
                aired.text = ''
    
            plot = etree.SubElement( episode, "plot" )
            if curEpToWrite.description != None:
                plot.text = curEpToWrite.description
    
            displayseason = etree.SubElement( episode, "displayseason" )
            if myEp.has_key('airsbefore_season'):
                displayseason_text = myEp['airsbefore_season']
                if displayseason_text != None:
                    displayseason.text = displayseason_text
    
            displayepisode = etree.SubElement( episode, "displayepisode" )
            if myEp.has_key('airsbefore_episode'):
                displayepisode_text = myEp['airsbefore_episode']
                if displayepisode_text != None:
                    displayepisode.text = displayepisode_text
    
            thumb = etree.SubElement( episode, "thumb" )
            thumb_text = myEp['filename']
            if thumb_text != None:
                thumb.text = thumb_text
    
            watched = etree.SubElement( episode, "watched" )
            watched.text = 'false'
    
            credits = etree.SubElement( episode, "credits" )
            credits_text = myEp['writer']
            if credits_text != None:
                credits.text = credits_text
    
            director = etree.SubElement( episode, "director" )
            director_text = myEp['director']
            if director_text != None:
                director.text = director_text

            rating = etree.SubElement( episode, "rating" )
            rating_text = myEp['rating']
            if rating_text != None:
                rating.text = rating_text
    
            gueststar_text = myEp['gueststars']
            if gueststar_text != None:
                for actor in gueststar_text.split('|'):
                    cur_actor = etree.SubElement( episode, "actor" )
                    cur_actor_name = etree.SubElement(
                        cur_actor, "name"
                        )
                    cur_actor_name.text = actor
    
            for actor in myShow['_actors']:
                cur_actor = etree.SubElement( episode, "actor" )

                cur_actor_name = etree.SubElement( cur_actor, "name" )
                cur_actor_name.text = actor['name']

                cur_actor_role = etree.SubElement( cur_actor, "role" )
                cur_actor_role_text = actor['role']
                if cur_actor_role_text != None:
                    cur_actor_role.text = cur_actor_role_text

                cur_actor_thumb = etree.SubElement( cur_actor, "thumb" )
                cur_actor_thumb_text = actor['image']
                if cur_actor_thumb_text != None:
                    cur_actor_thumb.text = cur_actor_thumb_text
                    
            if ek.ek(os.path.isfile, self.location):
                nfoFilename = helpers.replaceExtension(self.location, 'nfo')
            else:
                nfoFilename = helpers.sanitizeFileName(self.prettyName() + '.nfo')
    
            logger.log('Writing nfo to ' + nfoFilename)
            #
            # Make it purdy
            helpers.indentXML( rootNode )

            nfo = etree.ElementTree( rootNode )
            nfo_fh = ek.ek(open, nfoFilename, 'w')
            nfo.write( nfo_fh, encoding="utf-8" ) 
            nfo_fh.close()
            
            for epToWrite in epsToWrite:
                epToWrite.hasnfo = True
                shouldSave = True
        # end if needsNFO

        return shouldSave


    def createArt(self, epsToWrite, force=False):

        shouldSave = False

        try:
            t = tvdb_api.Tvdb(actors=True, **sickbeard.TVDB_API_PARMS)
            myShow = t[self.show.tvdbid]
        except tvdb_exceptions.tvdb_shownotfound, e:
            raise exceptions.ShowNotFoundException(str(e))
        except tvdb_exceptions.tvdb_error, e:
            logger.log("Unable to connect to TVDB while creating meta files - skipping - "+str(e), logger.ERROR)
            return

        thumbFilename = None

        # write an NFO containing info for all matching episodes
        for curEpToWrite in epsToWrite:
        
            try:
                myEp = myShow[curEpToWrite.season][curEpToWrite.episode]
            except (tvdb_exceptions.tvdb_episodenotfound, tvdb_exceptions.tvdb_seasonnotfound):
                logger.log("Unable to find episode " + str(curEpToWrite.season) + "x" + str(curEpToWrite.episode) + " on tvdb... has it been removed? Should I delete from db?")
                return None
            
            if curEpToWrite == self:
                thumbFilename = myEp["filename"]

        if not self.hastbn or force:
            if thumbFilename != None:
                if ek.ek(os.path.isfile, self.location):
                    tbnFilename = helpers.replaceExtension(self.location, 'tbn')
                else:
                    tbnFilename = helpers.sanitizeFileName(self.prettyName() + '.tbn')
                logger.log('Writing thumb to ' + tbnFilename)
                try:
                    ek.ek(urllib.urlretrieve, thumbFilename, tbnFilename)
                except IOError:
                    logger.log("Unable to download thumbnail from "+thumbFilename, logger.ERROR)
                    return None
                #TODO: check that it worked
                self.hastbn = True
                shouldSave = True

        return shouldSave

    def deleteEpisode(self):

        logger.log("Deleting "+self.show.name+" "+str(self.season)+"x"+str(self.episode)+" from the DB", logger.DEBUG)
        
        # remove myself from the show dictionary
        if self.show.getEpisode(self.season, self.episode, noCreate=True) == self:
            logger.log("Removing myself from my show's list", logger.DEBUG)
            del self.show.episodes[self.season][self.episode]
        
        # make sure it's not in any ep lists
        if self in sickbeard.airingList:
            logger.log("Removing myself from the airing list", logger.DEBUG)
            sickbeard.airingList.remove(self)
        if self in sickbeard.comingList:
            logger.log("Removing myself from the coming list", logger.DEBUG)
            sickbeard.comingList.remove(self)
        
        # delete myself from the DB
        logger.log("Deleting myself from the database", logger.DEBUG)
        myDB = db.DBConnection()
        sql = "DELETE FROM tv_episodes WHERE showid="+str(self.show.tvdbid)+" AND season="+str(self.season)+" AND episode="+str(self.episode)
        myDB.action(sql)
        
        raise exceptions.EpisodeDeletedException()
        
    def saveToDB(self):
    
        logger.log(str(self.show.tvdbid) + ": Saving episode details to database", logger.DEBUG)

        logger.log("STATUS IS " + str(self.status), logger.DEBUG)
    
        myDB = db.DBConnection()
        newValueDict = {"tvdbid": self.tvdbid,
                        "name": self.name,
                        "description": self.description,
                        "airdate": self.airdate.toordinal(),
                        "hasnfo": self.hasnfo,
                        "hastbn": self.hastbn,
                        "status": self.status,
                        "location": self.location}
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
        
    def prettyName (self, naming_show_name=None, naming_ep_type=None, naming_multi_ep_type=None,
                    naming_ep_name=None, naming_sep_type=None, naming_use_periods=None, naming_quality=None):
        
        regex = "(.*) \(\d\)"


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
        
        if naming_multi_ep_type == None:
            naming_multi_ep_type = sickbeard.NAMING_MULTI_EP_TYPE
        
        if naming_sep_type == None:
            naming_sep_type = sickbeard.NAMING_SEP_TYPE
        
        if naming_use_periods == None:
            naming_use_periods = sickbeard.NAMING_USE_PERIODS
        
        if naming_quality == None:
            naming_quality = sickbeard.NAMING_QUALITY
        
        if self.show.genre and "Talk Show" in self.show.genre and sickbeard.NAMING_DATES:
            goodEpString = str(self.airdate)
        else:
            goodEpString = config.naming_ep_type[naming_ep_type] % {'seasonnumber': self.season, 'episodenumber': self.episode}
        
        for relEp in self.relatedEps:
            goodEpString += config.naming_multi_ep_type[naming_multi_ep_type][naming_ep_type] % {'seasonnumber': relEp.season, 'episodenumber': relEp.episode}
        
        if goodName != '':
            goodName = config.naming_sep_type[naming_sep_type] + goodName

        finalName = ""
        
        if naming_show_name:
            finalName += self.show.name + config.naming_sep_type[naming_sep_type]

        finalName += goodEpString

        if naming_ep_name:
            finalName += goodName

        if naming_quality:
            epStatus, epQual = Quality.splitCompositeStatus(self.status)
            if epQual != Quality.NONE:
                finalName += config.naming_sep_type[naming_sep_type] + Quality.qualityStrings[epQual]
        
        if naming_use_periods:
            finalName = re.sub("\s+", ".", finalName)

        return finalName
        
        
