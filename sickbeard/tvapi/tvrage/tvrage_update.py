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



import urllib
import datetime
import traceback

from sickbeard import exceptions, common, logger
from sickbeard.tvapi import proxy, safestore

from sickbeard.tvapi.tvdb.tvdb_classes import TVShowData_TVDB

from sickbeard.tvapi.tvapi_classes import TVShowData, TVEpisodeData

import sickbeard

#from sickbeard.tvapi.tvapi_classes import TVShowData, TVEpisodeData
from sickbeard.tvapi.tvrage.tvrage_classes import TVShowData_TVRage, TVEpisodeData_TVRage

def _makeTVR(tvdb_id):
    
    # this whole module is a kludge so what's one more. grab the TVDB name to use for searching the ID
    showList = safestore.safe_list(sickbeard.storeManager.safe_store("find", TVShowData, TVShowData.tvdb_id == tvdb_id))
    if len(showList) > 0:
        showData = showList[0]
    else:
        raise exceptions.TVRageException("Unable to find a TVShowData object for this show")
        
    showList = safestore.safe_list(sickbeard.storeManager.safe_store("find", TVShowData_TVRage, TVShowData_TVRage.tvdb_id == tvdb_id))
    if len(showList) == 0:
        logger.log("Show doesn't exist in DB, making new entry", logger.DEBUG)
        showDataTVR = proxy._getProxy(sickbeard.storeManager.safe_store(TVShowData_TVRage, tvdb_id))
        sickbeard.storeManager.safe_store("add", showDataTVR.obj)
    else:
        showDataTVR = showList[0]

    tvr = TVRage(showDataTVR, showData)
        
    sickbeard.storeManager.commit()

    return tvr

def loadShow(tvdb_id):

    tvr = _makeTVR(tvdb_id)

    try:
        ep = tvr.findLatestEp()
    except exceptions.TVRageException, e:
        logger.log("Unable to find next episode on TVRage: "+str(e), logger.DEBUG)

    sickbeard.storeManager.commit()


def getID(tvdb_id):

    tvr = _makeTVR(tvdb_id)

    return tvr._tvrage_id


class TVRage:
    
    def __init__(self, showDataTVR, showData):
        
        self.showDataTVR = showDataTVR
        self.showData = showData
        
        self.lastEpInfo = None
        self.nextEpInfo = None
        
        self._tvrage_id = 0
        self._tvrage_name = None
        
        if not self.showDataTVR.tvrage_id:
            
            # if it's the right show then use the tvrage ID that the last lookup found (cached in self._trvid)
            if self.confirmShow() or self.checkSync():
                
                if self._tvrage_id == 0 or self._tvrage_name == None:
                    raise exceptions.TVRageException("We confirmed sync but got invalid data (no ID/name)")
                
                logger.log("Setting TVRage ID for "+str(self.showData.name)+" to "+str(self._tvrage_id))
                self.showDataTVR.tvrage_id = int(self._tvrage_id)
                #self.show.saveToDB()

        if not self.showDataTVR.name:

            if self._tvrage_name == None:
                self._getTVRageInfo()

            logger.log("Setting TVRage Show Name for "+self.showData.name+" to "+self._tvrage_name)
            self.showDataTVR.name = self._tvrage_name
            #self.show.saveToDB()


    def confirmShow(self, force=False):
        
        if self.showDataTVR.tvrage_id and not force:
            logger.log("We already have a TVRage ID, skipping confirmation", logger.DEBUG)
            return True
        
        logger.log("Checking the first episode of each season to see if the air dates match between TVDB and TVRage")
        
        try:

            # check the first episode of every season
            for curSeason in self.showData.seasons:
                
                logger.log("Checking TVDB and TVRage sync for season "+str(curSeason), logger.DEBUG)

                airdate = None

                # don't do specials and don't do seasons with no episode 1
                if curSeason == 0 or 1 not in self.showData.season(curSeason):
                    continue
                
                # get the episode info from the DB
                epDataTVRList = sickbeard.storeManager.safe_store("find",
                                                              TVEpisodeData_TVRage,
                                                              TVEpisodeData_TVRage.show_id == self.showDataTVR.tvdb_id,
                                                              TVEpisodeData_TVRage.season == curSeason,
                                                              TVEpisodeData_TVRage.episode == 1)
                epDataTVRList = safestore.safe_list(epDataTVRList)
                if len(epDataTVRList) == 0:
                    logger.log("Episode "+str(curSeason)+"x1 doesn't have TVRage data, creating some", logger.DEBUG)
                    epDataTVR = proxy._getProxy(sickbeard.storeManager.safe_store(TVEpisodeData_TVRage, self.showDataTVR.tvdb_id, curSeason, 1))
                    sickbeard.storeManager.safe_store("add", epDataTVR.obj)
                    sickbeard.storeManager.safe_store("flush")
                else:
                    epDataTVR = epDataTVRList[0]
                
                epDataList = safestore.safe_list(sickbeard.storeManager.safe_store("find", TVEpisodeData,
                                                                                   TVEpisodeData.tvdb_show_id == self.showDataTVR.tvdb_id,
                                                                                   TVEpisodeData.season == curSeason,
                                                                                   TVEpisodeData.episode == 1))
                if len(epDataList) == 0:
                    logger.log("This episode doesn't have a TVEpisodeData object, creating one", logger.DEBUG)
                    epData = sickbeard.storeManager.safe_store(TVEpisodeData, self.showDataTVR.tvdb_id, curSeason, 1)
                    sickbeard.storeManager.safe_store("add", epData)
                else:
                    epData = epDataList[0]

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
                
                epDataTVR.aired = curEpInfo['airdate']
                epDataTVR.name = curEpInfo['name']
                
                # if either is blank then this comparison isn't going to work 
                if not epDataTVR.aired or not epData.aired:
                    logger.log("Missing air date for one of the providers: "+str(epData.aired)+" vs "+str(epDataTVR.aired), logger.DEBUG)
                    continue

                # check if TVRage and TVDB have the same airdate for this episode
                if epDataTVR.aired == epData.aired:
                    logger.log("Successful match for TVRage and TVDB data for episode "+str(curSeason)+"x1)", logger.DEBUG)
                    return True

                logger.log("Date from TVDB for episode " + str(curSeason) + "x1: " + str(airdate), logger.DEBUG)
                logger.log("Date from TVRage for episode " + str(curSeason) + "x1: " + str(curEpInfo['airdate']), logger.DEBUG)
        
        except Exception, e:
            logger.log("Error encountered while checking TVRage<->TVDB sync: " + str(e), logger.ERROR)
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
        
            # get the episode info from the DB
            epDataTVRList = sickbeard.storeManager.safe_store("find",
                                                          TVEpisodeData_TVRage,
                                                          TVEpisodeData_TVRage.show_id == self.showDataTVR.tvdb_id,
                                                          TVEpisodeData_TVRage.season == self.lastEpInfo['season'],
                                                          TVEpisodeData_TVRage.episode == self.lastEpInfo['episode'])
            epDataTVRList = safestore.safe_list(epDataTVRList)
            if len(epDataTVRList) == 0:
                logger.log("Episode "+str(self.lastEpInfo['season'])+"x1 doesn't have TVRage data, creating some", logger.DEBUG)
                epDataTVR = proxy._getProxy(sickbeard.storeManager.safe_store(TVEpisodeData_TVRage, self.showDataTVR.tvdb_id, self.lastEpInfo['season'], self.lastEpInfo['episode']))
                sickbeard.storeManager.safe_store("add", epDataTVR.obj)
                sickbeard.storeManager.safe_store("flush")
            else:
                epDataTVR = epDataTVRList[0]

            # get the existing (aka TVDB) data to use for comparing
            epDataList = safestore.safe_list(sickbeard.storeManager.safe_store("find", TVEpisodeData,
                                                                               TVEpisodeData.tvdb_show_id == self.showDataTVR.tvdb_id,
                                                                               TVEpisodeData.season == self.lastEpInfo['season'],
                                                                               TVEpisodeData.episode == self.lastEpInfo['episode']))
            if len(epDataList) == 0:
                logger.log("This episode doesn't have a TVEpisodeData object, creating one", logger.DEBUG)
                epData = sickbeard.storeManager.safe_store(TVEpisodeData, self.showDataTVR.tvdb_id, self.lastEpInfo['season'], self.lastEpInfo['episode'])
                sickbeard.storeManager.safe_store("add", epData)
            else:
                epData = epDataList[0]

            # add the info we got off the web into the TVEpisodeData_TVRage object
            epDataTVR.aired = self.lastEpInfo['airdate']
            epDataTVR.name = self.lastEpInfo['name']

            # if the date for either of them isn't filled then we can't compare them
            if not epData.aired or not epDataTVR.aired:
                logger.log("Missing air date for one of the providers: "+str(epData.aired)+" vs "+str(epDataTVR.aired), logger.DEBUG)
                return None

            logger.log("Date from TVDB for episode " + str(self.lastEpInfo['season']) + "x" + str(self.lastEpInfo['episode']) + ": " + str(airdate), logger.DEBUG)
            logger.log("Date from TVRage for episode " + str(self.lastEpInfo['season']) + "x" + str(self.lastEpInfo['episode']) + ": " + str(self.lastEpInfo['airdate']), logger.DEBUG)
        
            if epData.aired == epDataTVR.aired:
                return True
            
        except Exception, e:
            logger.log("Error encountered while checking TVRage<->TVDB sync: " + str(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
        
        return False
    
    def _getTVRageInfo(self, season=None, episode=None, full=False):
        
        url = "http://services.tvrage.com/tools/quickinfo.php?"
        
        # if we need full info OR if we don't have a tvrage id, use show name
        if full == True or not self.showDataTVR.tvrage_id:
            showName = self.showDataTVR.name if self.showDataTVR.name else self.showData.name
            if not showName:
                raise exceptions.TVRageException("No TVDB show name to use for TVRage ID lookup")

            urlData = {'show': showName.encode('utf-8')}

        # if we don't need full info and we have a tvrage id, use it
        else:
            urlData = {'sid': self.showDataTVR.tvrage_id}
        
        if season != None and episode != None:
            urlData['ep'] = str(season)+'x'+str(episode)

        # build the URL
        url += urllib.urlencode(urlData)

        logger.log("Loading TVRage info from URL: " + url, logger.DEBUG)

        try:
            urlObj = urllib.urlopen(url)
        except (urllib.ContentTooShortError, IOError), e:
            logger.log("Unable to load TVRage info: " + str(e))
            raise exceptions.TVRageException("urlopen call to " + url + " failed")
        
        urlData = [x.decode('utf-8') for x in urlObj.readlines()]
        
        info = {}
        
        for x in urlData:
            key, value = x.split("@")
            key = key.replace('<pre>','')
            info[key] = value.strip()

        # save it for later in case somebody is curious
        if info.has_key('Show ID'):
            self._tvrage_id = info['Show ID']

        if info.has_key('Show Name'):
            self._tvrage_name = info['Show Name']

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
        
        # get the episode info from the DB
        epDataTVRList = sickbeard.storeManager.safe_store("find",
                                                      TVEpisodeData_TVRage,
                                                      TVEpisodeData_TVRage.show_id == self.showDataTVR.tvdb_id,
                                                      TVEpisodeData_TVRage.season == self.lastEpInfo['season'],
                                                      TVEpisodeData_TVRage.episode == self.lastEpInfo['episode'])
        epDataTVRList = safestore.safe_list(epDataTVRList)
        if len(epDataTVRList) == 0:
            epDataTVR = None
        else:
            epDataTVR = epDataTVRList[0]
    
        epDataList = safestore.safe_list(sickbeard.storeManager.safe_store("find", TVEpisodeData,
                                                                           TVEpisodeData.tvdb_show_id == self.showDataTVR.tvdb_id,
                                                                           TVEpisodeData.season == self.lastEpInfo['season'],
                                                                           TVEpisodeData.episode == self.lastEpInfo['episode']))
        if len(epDataList) == 0:
            logger.log("This episode doesn't have a TVEpisodeData object, creating one", logger.DEBUG)
            epData = sickbeard.storeManager.safe_store(TVEpisodeData, self.showDataTVR.tvdb_id, self.lastEpInfo['season'], self.lastEpInfo['episode'])
            sickbeard.storeManager.safe_store("add", epData)

        if epDataTVR:
            raise exceptions.TVRageException("Show is already in database, not adding the TVRage info")

        epData = sickbeard.storeManager.safe_store(TVEpisodeData_TVRage, self.showDataTVR.tvdb_id, self.nextEpInfo['season'], self.nextEpInfo['episode'])
        epData.name = self.nextEpInfo['name']
        epData.airdate = self.nextEpInfo['airdate']
        sickbeard.storeManager.safe_store("add", epData)

        return epData

