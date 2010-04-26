import datetime
import os.path
import operator
import re
import glob
import urllib
import threading

from storm.locals import Int, Unicode, Bool, Reference, ReferenceSet, Storm, Select, Min, AutoReload
from storm.expr import And

import sickbeard

from sickbeard import common, exceptions, helpers
from sickbeard import config
from sickbeard import processTV
from sickbeard import encodingKludge as ek
from sickbeard import metadata

from sickbeard.tvapi.tvapi_classes import TVEpisodeData, TVShowData

from sickbeard.tvapi import proxy, safestore
from sickbeard.tvapi.tvdb import tvdb_update
from sickbeard.tvapi.tvrage import tvrage_update

from sickbeard import logger

import xml.etree.cElementTree as etree

from lib.tvnamer.utils import FileParser
from lib.tvnamer import tvnamer_exceptions


class TVShow(Storm):
    """
    Represents a show that's been added in Sick Beard. Stores all data specific to
    TV shows in Sick Beard (as opposed to the data that is specific to the TV show
    in any context, aka the show's metadata).
    
    TVShow(tvdb_id):
        tvdb_id: The thetvdb.com ID for the show that this object represents.
    """
    
    __storm_table__ = "tvshow"

    tvdb_id = Int(primary=True)

    # show folder
    _location = Unicode()
    seasonfolders = Bool()
    paused = Bool()
    quality = Int()
    
    show_data = Reference(tvdb_id, "TVShowData.tvdb_id")
    episodes = ReferenceSet(tvdb_id, "TVEpisode._show_id")
    
    def __init__(self, tvdb_id):
        self.tvdb_id = tvdb_id
        self.lock = threading.Lock()

    def proxy(self):
        return proxy.TVShowProxy(self)

    def _getLocation(self):
        if self._location and ek.ek(os.path.isdir, self._location):
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

    def updateMetadata(self, cache=False):
        """
        Updates the show's metadata from TVDB and TVRage.
        
        cache: default=False
            If this is true then the TVDB API will use the cached copies of metadata to update. With the local
            database being used to store the data I can't think of a single reason you'd ever need this.
        """
        
        # loads TVDB data into the database
        tvdb_update.loadShow(self.tvdb_id, cache)
        sickbeard.storeManager.commit()
        
        try:
            tvrage_update.loadShow(self.tvdb_id)
            #pass
        except exceptions.TVRageException, e:
            logger.log("Error while trying to set TVRage info: "+str(e), logger.WARNING)

        # update any existing data objects with the new metadata
        if self.show_data:
            self.show_data.update()
        for epObj in self.show_data.episodes_data:
            epObj.update()

        sickbeard.storeManager.commit()
    
    def nextEpisodes(self, fromDate=None, untilDate=None):
        """
        Returns a list containing the next episode(s) with aired date between fromDate
        and untilDate (inclusive). If no untilDate is given then episodes in the next
        week are given. If no episodes between fromDate an untilDate exist then the next
        available episode is given.
        
        fromDate: default=None
            datetime.date object representing the lower bound of air dates to return.
            If not specified, datetime.date.today() is used
        untilDate: default=None
            datetime.date object representing the upper bound of air dates to return.
            If not specified, only the next-airing episode is returned.
        """
        if not fromDate:
            fromDate = datetime.date.today()
        
        conditions = [TVEpisodeData.aired >= fromDate, TVEpisodeData.tvdb_show_id == self.tvdb_id]
        
        # find all eps until untilDate or else the next 7 days
        if not untilDate:
            untilDate = fromDate + datetime.timedelta(days=7)
        conditions.append(TVEpisodeData.aired <= untilDate)
        
        result = sickbeard.storeManager._store.find(TVEpisodeData, And(*conditions))
        
        # if there are no results in the specified interval then just get the next eps
        if result.count() == 0:
            subselect = Select(Min(TVEpisodeData.aired),
                               And(TVEpisodeData.aired >= fromDate,
                               TVEpisodeData.tvdb_show_id == self.tvdb_id),
                               [TVEpisodeData])
            result = sickbeard.storeManager._store.find(TVEpisodeData,
                                                        TVEpisodeData.aired == subselect,
                                                        TVEpisodeData.tvdb_show_id == self.tvdb_id)
        
        return result
    
    def getEp(self, season, episode): # I'd like to replace this with [season][episode] eventually
        """
        Returns a specific TVEpisodeData belonging to this show. If it doesn't exist, returns None.
        """
        
        epData = sickbeard.storeManager._store.find(TVEpisodeData,
                                  TVEpisodeData.tvdb_show_id == self.tvdb_id,
                                  TVEpisodeData.season == season,
                                  TVEpisodeData.episode == episode)
        
        if epData.one():
            return epData.one().ep_obj
        else:
            return None

    def writeEpisodeMetafiles(self):
        
        if not ek.ek(os.path.isdir, self._location):
            logger.log("Show dir doesn't exist, skipping NFO generation")
            return
        
        logger.log("Writing metadata for all episodes")
        
        for epObj in self.episodes:
            epObj.createMetaFiles()
    
    def getImages(self):
        pass
    
    def delete(self):
        for epObj in self.episodes:
            try:
                epObj.delete()
            except exceptions.EpisodeDeletedException:
                pass
        sickbeard.storeManager._store.remove(self.show_data)
        sickbeard.storeManager._store.remove(self)
        sickbeard.storeManager.commit()
    
    def refreshDir(self):
        
        # make sure the show dir is where we think it is
        if not ek.ek(os.path.isdir, self._location):
            return False
        
        nfoFilename = ek.ek(os.path.join, self._location, "tvshow.nfo")
        
        # if metadata creation is turned on then make ourselves a tvshow.nfo, unless we already have one
        if sickbeard.CREATE_METADATA and not ek.ek(os.path.isfile, nfoFilename):
            logger.log("No tvshow.nfo found, generating one")
            rootNode = metadata.makeShowNFO(self)
            nfoTree = etree.ElementTree( rootNode )
            nfo_fh = ek.ek(open, nfoFilename, 'w')
            nfoTree.write( nfo_fh, encoding="utf-8" ) 
            nfo_fh.close()

        # run through all locations from DB, check that they exist
        logger.log(str(self.tvdb_id) + ": Loading all episodes with a location from the database")
        
        for epObj in self.episodes:
            if not epObj.location:
                continue
            
            curLoc = os.path.normpath(epObj.location)
        
            # if the path doesn't exist
            # or if it's not in our show dir
            if not ek.ek(os.path.isfile, curLoc) or \
            os.path.normpath(os.path.commonprefix([os.path.normpath(x) for x in (curLoc, self.location)])) != os.path.normpath(self.location):
            
                logger.log("Location "+curLoc+" doesn't exist, removing it and changing our status to SKIPPED", logger.DEBUG)
                #with curEp.lock:
                epObj.location = None
                if epObj.status == common.DOWNLOADED:
                    epObj.status = common.SKIPPED
                epObj.hasnfo = False
                epObj.hastbn = False

        # for each media file in the folder
        for curFile in helpers.listMediaFiles(self._location):
            logger.log("Checking file "+curFile+" for a TVEpisode", logger.DEBUG)
            
            # get the episode object if it exists
            epObj = sickbeard.storeManager._store.find(TVEpisode, TVEpisode.location == curFile).one()
            
            # if not, make it
            if not epObj:
                epObj = TVEpisode.createEpFromName(ek.ek(os.path.basename, curFile), self.tvdb_id)

            if not epObj:
                logger.log("Unable to find episode metadata for "+curFile+", giving up", logger.ERROR)
                continue
                
            epObj.location = curFile
            epObj.status = common.DOWNLOADED
            sickbeard.storeManager.commit()

    
    def renameEpisodes(self):
        """
        Goes through every episode with an associated file and renames it according to the
        rename options.
        """

        # for each episode in the show
        for epObj in self.episodes:

            if not epObj.location:
                continue

            # get the correct name
            goodName = epObj.prettyName()
            
            # fix up the location, just in case
            curLocation = ek.ek(os.path.normpath, epObj.location)

            # get the filename of the episode and the folder it lives in 
            actualName = ek.ek(os.path.splitext, ek.ek(os.path.basename, curLocation))[0]
            curEpDir = os.path.dirname(curLocation)

            if goodName == actualName:
                logger.log("File " + epObj.location + " is already named correctly, skipping", logger.DEBUG)
                continue

            # rename the file and update the object with the new location
            result = processTV.renameFile(epObj.location, goodName)
            if result != False:
                epObj.location = result
            
            # get a list of all associated files
            associatedFiles = ek.ek(glob.glob, ek.ek(os.path.join, curEpDir, actualName + "*").replace("[","*").replace("]","*"))

            # rename all associated files
            for associatedFile in associatedFiles:
                result = processTV.renameFile(associatedFile, goodName)
                if result == False:
                    logger.log("Unable to rename file "+associatedFile, logger.ERROR)
            
            epObj.checkForMetaFiles()

    @staticmethod
    def findTVShow(name):
        result = sickbeard.storeManager.safe_store("find", TVShow, TVShow.tvdb_id == TVShowData.tvdb_id, TVShowData.name == name)
        return proxy._getProxy(sickbeard.storeManager.safe_store(result.one))
    
    @staticmethod
    def getTVShow(tvdb_id):
        result = sickbeard.storeManager.safe_store("find", TVShow, TVShow.tvdb_id == tvdb_id)
        return proxy._getProxy(sickbeard.storeManager.safe_store(result.one))

    @staticmethod
    def createTVShow(tvdb_id):
        curShowObj = TVShow.getTVShow(tvdb_id)
        if curShowObj:
            return curShowObj

        from storm.tracer import debug
        import sys
        
        debug(True, stream=sys.stdout)
        
        # make the show
        showObj = proxy._getProxy(sickbeard.storeManager.safe_store(TVShow, tvdb_id))
        sickbeard.storeManager.safe_store("add", showObj.obj)
        sickbeard.storeManager.safe_store("commit")
        
        # get the metadata
        showObj.updateMetadata()
        
        # make a TVEpisode for any tvapi_classes.TVEpisodeData objects that don't already have one
        for epData in safestore.safe_list(sickbeard.storeManager.safe_store("find",
                                                                            TVEpisodeData,
                                                                            TVEpisodeData.tvdb_show_id == tvdb_id)):
    
            if not epData.ep_obj:
                logger.log("Creating TVEpisode object for episode "+str(epData.season)+"x"+str(epData.episode), logger.DEBUG)
                print "Creating TVEpisode object for episode "+str(epData.season)+"x"+str(epData.episode) 
                epObj = proxy._getProxy(sickbeard.storeManager.safe_store(TVEpisode, showObj))
                sickbeard.storeManager.safe_store(epObj.addEp, ep=epData)
                sickbeard.storeManager.safe_store("add", epObj.obj)
                logger.log("Added a TVEpisode to the TVEpisodeData: "+str(epData._eid)+" == "+str(epObj.eid)+" and "+str(epData.ep_obj)+" == "+str(epObj), logger.DEBUG)
                print "Added a TVEpisode to the TVEpisodeData: "+str(epData._eid)+" == "+str(epObj.eid)+" and "+str(epData.ep_obj)+" == "+str(epObj)
                #store.commit()
        
        #store.add(showObj)
        sickbeard.storeManager.safe_store("commit")
        
        debug(False)
        
        return showObj


class TVEpisode(Storm):
    """
    Represents an episode of a show that's added in Sick Beard. Stores all data
    specific to a TV episode in Sick Beard (as opposed to the data that is specific
    to the TV episode in any context, aka the episode's metadata).
    
    TVEpisode(show):
        A TVShow instance of the show that this episode belongs to.
    
    episodes:
        A list of all TVEpisodeData objects associated to this TVEpisode. 
    
    addEp(season, episode):
        season: The season number of the episode to add
        episode: The episode number of the episode to add
        Adds the specified TVEpisodeData object to the internal .episodes list. Throws
        a TODO exception if the episode doesn't exist. 
    """
    
    __storm_table__ = "tvepisode"
    
    eid = Int(primary=True)

    # file location
    location = Unicode()

    # sick beard status (skipped, missed, snatched, etc)
    _status = Int()
    
    # whether nfo/tbn exists
    hasnfo = Bool()
    hastbn = Bool()
    
    _show_id = Int()
    
    show = Reference(_show_id, "TVShow.tvdb_id")
    episodes_data = ReferenceSet(eid, "TVEpisodeData._eid")
    
    def __init__(self, show, season=None, episode=None):
        # dereference the proxy if applicable
        if isinstance(show, proxy.GenericProxy):
            show = show.obj

        self.show = show
        if season != None and episode != None:
            self.addEp(season, episode)

        self.lock = threading.Lock()

    def proxy(self):
        return proxy.TVEpisodeProxy(self)

    def _getStatus(self):
        if self._status == None:
            if self.episodes_data.count() == 1:
                epData = self.episodes_data.one()
                if not epData.aired:
                    return common.UNKNOWN
                elif epData.aired >= datetime.date.today():
                    return common.UNAIRED
                else:
                    return common.SKIPPED
            else:
                return common.UNKNOWN
        else:
            return self._status
    
    def _setStatus(self, value):
        self._status = value
    
    status = property(_getStatus, _setStatus)
    
    def update(self):
        for epData in self.episodes_data:
            logger.log("Calling update on TVEpisodeData for "+str(epData.season)+"x"+str(epData.episode), logger.DEBUG)
            epData.update()
    
    def epDataList(self):
        return [x for x in self.episodes_data]

    def addEp(self, season=None, episode=None, ep=None):
        """
        Add an episode to the episode data list (TVEpisode.episodes)
        """

        if not ep:
            logger.log("Creating and adding TVEpisodeData object for "+str(season)+"x"+str(episode)+" to the TVEpisode object", logger.DEBUG)

            result = sickbeard.storeManager._store.find(TVEpisodeData,
                                                        TVEpisodeData.tvdb_show_id == self.show.tvdb_id,
                                                        TVEpisodeData.season == season,
                                                        TVEpisodeData.episode == episode)
            
            if result.count() == 1:
                ep = result.one()
            # if the episode doesn't have an epData object then we need to make one for it
            else:
                ep = TVEpisodeData(self.show.tvdb_id, season, episode)
                ep.update()
                #raise Exception("The season/episode given didn't return a single episode: "+str(season)+"x"+str(episode))

        else:
            logger.log("Adding the existing TVEpisodeData object for "+str(ep.season)+"x"+str(ep.episode)+" to the TVEpisode object", logger.DEBUG)
            print "Adding the existing TVEpisodeData object for "+str(ep.season)+"x"+str(ep.episode)+" to the TVEpisode object"

        if ep not in self.episodes_data:
            logger.log("Performing the add and committing it", logger.DEBUG)
            print "Performing the add and committing it"
            self.episodes_data.add(ep)
            sickbeard.storeManager.commit()
            logger.log("After I did the add, hopefully "+str(ep._eid)+" == "+str(self.eid), logger.DEBUG)
            print "After I did the add, hopefully "+str(ep._eid)+" == "+str(self.eid)

        # keep the status up to date
        self._status = self._getStatus() 

        logger.log("Set my status to "+str(self._status), logger.DEBUG)
        print "Set my status to "+str(self._status)


    def checkForMetaFiles(self):

        # check for nfo and tbn
        if ek.ek(os.path.isfile, self.location):
            self.hasnfo = ek.ek(os.path.isfile, helpers.replaceExtension(self.location, 'nfo'))
            self.hastbn = ek.ek(os.path.isfile, helpers.replaceExtension(self.location, 'tbn'))

    def createMetaFiles(self, force=False):
        if not ek.ek(os.path.isdir, self.show._location):
            logger.log("The show dir is missing, not bothering to try to create metadata", logger.WARNING)
            return
        elif not self.location or not ek.ek(os.path.isfile, self.location):
            logger.log("This episode has no file, not bothering to create metadata", logger.DEBUG)
            return

        self.checkForMetaFiles()

        if sickbeard.CREATE_METADATA or force:
            self.createNFO(force)
        
        if sickbeard.CREATE_IMAGES or force:
            self.createTBN(force)
        
        self.checkForMetaFiles()

    def createTBN(self, force=False):
        """
        Retrieves a thumbnail file from URLs in the episodes' associated metadata. If the TVEpisode
        has no location no file is created. Doesn't overwrite existing thumbnails by default.
        
        force: default=False
            If true then this function will download a tbn even if there as an existing tbn (it will
            overwrite it).
        """
        
        if self.hastbn and not force:
            return
        
        if self.location and ek.ek(os.path.isfile, self.location):
            tbnFilename = helpers.replaceExtension(self.location, "tbn")
        else:
            logger.log("No file exists for this episode, skipping thumbnail download", logger.DEBUG)

        tbnURLList = [] 

        # find all possible URLs for this file
        for epData in self.episodes_data:
            if epData.thumb:
                tbnURLList.append(epData.thumb)
        
        if len(tbnURLList) == 0:
            logger.log("Unable to find any thumbnail URLs for this episode, can't download a TBN", logger.WARNING)
            return
        
        logger.log('Writing thumb to ' + tbnFilename)
        for curURL in tbnURLList:
            try:
                ek.ek(urllib.urlretrieve, curURL, tbnFilename)
            except IOError:
                logger.log("Unable to download thumbnail from "+curURL, logger.ERROR)
                return None
            
            if not ek.ek(os.path.isfile, tbnFilename):
                logger.log("Tried to download "+curURL+" to "+tbnFilename+" but something went wrong.", logger.WARNING)
                continue
            else:
                break


    def createNFO(self, force=False):
        """
        Generates an XBMC-compatible NFO file for this episode. Multi-episode files are supported
        in an <xbmcmultiepisode> block.
        
        force: default=False
            If true then this function will download even if there as an existing nfo (it will
            overwrite it).
        """
        
        if self.hasnfo and not force:
            return
        
        if self.episodes_data.count() == 0:
            return False
        elif self.episodes_data.count() > 1:
            rootNode = etree.Element( "xbmcmultiepisode" )
            for epData in self.episodes_data:
                rootNode.append(metadata.makeEpNFO(epData))
        else:
            rootNode = metadata.makeEpNFO(self.episodes_data.one())

        # Set our namespace correctly
        for ns in sickbeard.XML_NSMAP.keys():
            rootNode.set(ns, sickbeard.XML_NSMAP[ns])

        # self.location should always be absolute paths, no need to append self.show.location
        nfoFilename = helpers.replaceExtension(self.location, "nfo")

        nfoTree = etree.ElementTree( rootNode )
        nfo_fh = ek.ek(open, nfoFilename, 'w')
        nfoTree.write( nfo_fh, encoding="utf-8" ) 
        nfo_fh.close()


    def delete(self):
        for epData in self.episodes_data:
            sickbeard.storeManager._store.remove(epData)
            del epData
        sickbeard.storeManager._store.remove(self)
        raise exceptions.EpisodeDeletedException()

    def fullPath(self):
        if not os.path.isabs(self.location):
            return os.path.join(self.show.location, self.location)
    
    def prettyName (self, naming_show_name=None, naming_ep_type=None, naming_multi_ep_type=None,
                    naming_ep_name=None, naming_sep_type=None, naming_use_periods=None):
        """
        Builds a name string for the episode based on the config naming settings or
        alternately on the settings provided as arguments. For multi-episode files
        it combines names like "Ep Name (1)" and "Ep Name (2)" into simply "Ep Name",
        or for non-linked names it includes all names separated by a &. For files with
        more than 3 episodes no name is given at all (it gets far too long).
        """
        
        regex = "(.*) \(\d\)"

        if self.episodes_data.count() == 1:
            goodName = self.episodes_data.one().name

        elif self.episodes_data.count() > 3:
            goodName = ''

        else:
            singleName = True
            curGoodName = None

            for curName in [x.name for x in self.episodes_data]:
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
                goodName = " & ".join([x.name for x in self.episodes_data])
        
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
        
        goodEpString = ''
        
        # cycle through the episode data, sorted by episode number ascending
        for (s, e) in sorted([(x.season, x.episode) for x in self.episodes_data], key=operator.itemgetter(1)):

            # if it's the first one then make the initial string out of it
            if not goodEpString:
                goodEpString = config.naming_ep_type[naming_ep_type] % {'seasonnumber': s, 'episodenumber': e}
            else:
                goodEpString += config.naming_multi_ep_type[naming_multi_ep_type][naming_ep_type] % {'seasonnumber': s, 'episodenumber': e}
        
        if goodName != '':
            goodName = config.naming_sep_type[naming_sep_type] + goodName

        finalName = ""
        
        if naming_show_name:
            finalName += self.show.show_data.name + config.naming_sep_type[naming_sep_type]

        finalName += goodEpString

        if naming_ep_name:
            finalName += goodName
        
        if naming_use_periods:
            finalName = re.sub("\s+", ".", finalName)

        return finalName

    @staticmethod
    def createEpFromName(name, tvdb_id=None):
        
        try:
            myParser = FileParser(name)
            epInfo = myParser.parse()
        except tvnamer_exceptions.InvalidFilename:
            #logger.log("Unable to parse the filename "+name+" into a valid episode", logger.ERROR)
            return None
    
        if not tvdb_id:
            # try looking the name up in the DB
            
            # if that fails try a TVDB lookup
            pass
        
        showObj = TVShow.getTVShow(tvdb_id)
        epObj = showObj.getEp(epInfo.seasonnumber, epInfo.episodenumbers[0])
        
        if epObj:
            for anotherEpNum in epInfo.episodenumbers[1:]:
                epObj.addEp(epInfo.seasonnumber, anotherEpNum)
        
            if os.path.isfile(name):
                epObj.location = name
        
        return epObj


