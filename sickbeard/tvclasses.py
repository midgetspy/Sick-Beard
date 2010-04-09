import datetime
import os.path

from storm.locals import Int, Unicode, Bool, Reference, ReferenceSet, Storm, Store
from storm.expr import And

from tvapi.tvapi_classes import TVEpisodeData
from tvapi import tvapi_tvdb, tvapi_tvrage

import sickbeard

from sickbeard import common, exceptions, helpers
from sickbeard import tvapi
from sickbeard import encodingKludge as ek

import sickbeard.nfo

from sickbeard import logger

import xml.etree.cElementTree as etree

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
        logger.log("Setter sets location to " + newLocation)
        if ek.ek(os.path.isdir, newLocation) and ek.ek(os.path.isfile, ek.ek(os.path.join, newLocation, "tvshow.nfo")):
            self._location = newLocation
            self._isDirGood = True
        else:
            raise exceptions.NoNFOException("Invalid folder for the show!")

    location = property(_getLocation, _setLocation)

    def update(self, cache=True):
        tvapi_tvdb.loadShow(self.tvdb_id, cache)
        #tvapi_tvrage.loadShow(self.tvdb_id)
    
    def nextEpisodes(self, fromDate=None, untilDate=None):
        """
        Returns a list containing the next episode(s) with aired date between fromDate
        and untilDate (inclusive).
        
        fromDate: default=None
            datetime.date object representing the lower bound of air dates to return.
            If not specified, datetime.date.today() is used
        untilDate: default=None
            datetime.date object representing the upper bound of air dates to return.
            If not specified, only the next-airing episode is returned.
        """
        if not fromDate:
            fromDate = datetime.date.today()
        
        conditions = [TVEpisodeData.aired >= fromDate]
        
        if untilDate:
            conditions.append(TVEpisodeData.aired <= untilDate)

        store = Store(tvapi.database)
        result = store.find(TVEpisodeData, And(*conditions))
        return result
    
    def getEp(self, season, episode): # I'd like to replace this with [season][episode] eventually
        """
        Returns a specific TVEpisodeData belonging to this show. If it doesn't exist, returns None.
        """
        
        store = Store(tvapi.database)
        epData = store.find(TVEpisodeData,
                                  TVEpisodeData.show_id == self.tvdb_id,
                                  TVEpisodeData.season == season,
                                  TVEpisodeData.episode == episode)
        
        if epData.one():
            return epData.one().ep_obj
        else:
            return None

    def writeEpisodeMetafiles (self):
        
        if not os.path.isdir(self._location):
            #logger.log(str(self.tvdb_id) + ": Show dir doesn't exist, skipping NFO generation")
            return
        
        #logger.log(str(self.tvdb_id) + ": Writing NFOs for all episodes")
        
        for epObj in self.episodes:
            epObj.createMetaFiles()
    
    def getImages(self):
        pass
    
    def deleteShow(self):
        pass
    
    def refreshDir(self):
        
        # make sure the show dir is where we think it is
        if not ek.ek(os.path.isdir, self._location):
            return False
        
        # run through all locations from DB, check that they exist
        logger.log(str(self.tvdb_id) + ": Loading all episodes with a location from the database")
        
        for epObj in self.episodes:
            if not epObj.location:
                continue
            
            curLoc = os.path.normpath(epObj.location)
        
            # if the path doesn't exist
            # or if there's no season folders and it's not inside our show dir 
            # or if there are season folders and it's in the main dir:
            # or if it's not in our show dir at all
            if not ek.ek(os.path.isfile, curLoc) or \
            (not self.seasonfolders and os.path.normpath(os.path.dirname(curLoc)) != os.path.normpath(self.location)) or \
            (self.seasonfolders and os.path.normpath(os.path.dirname(curLoc)) == os.path.normpath(self.location)) or \
            os.path.normpath(os.path.commonprefix([os.path.normpath(x) for x in (curLoc, self.location)])) != os.path.normpath(self.location):
            
                logger.log("Location "+curLoc+" doesn't exist, removing it and changing our status to SKIPPED", logger.DEBUG)
                #with curEp.lock:
                epObj.location = ''
                if epObj.status == common.DOWNLOADED:
                    epObj.status = common.SKIPPED
                epObj.hasnfo = False
                epObj.hastbn = False

    
    def fixEpisodeNames(self):
        pass

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
    
    def _getStatus(self):
        if self._status == None:
            if self.episodes_data.count() == 1:
                epData = self.episodes_data.one()
                if not epData.aired:
                    return common.SKIPPED
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
    
    def __init__(self, show, season=None, episode=None):
        self.show = show
        if season != None and episode != None:
            self.addEp(season, episode)

    def epDataList(self):
        return [x for x in self.episodes_data]

    def addEp(self, season=None, episode=None, ep=None):
        """
        Add an episode to the episode data list (TVEpisode.episodes)
        """
        store = Store(tvapi.database)
        if not ep:
            result = store.find(TVEpisodeData, TVEpisodeData.show_id == self.show.tvdb_id, TVEpisodeData.season == season, TVEpisodeData.episode == episode)
            
            if result.count() == 1:
                ep = result.one()
            else:
                raise Exception()

        self.episodes_data.add(ep)
        store.commit()

        # keep the status up to date
        self._status = self._getStatus() 


    def checkForMetaFiles(self):
        pass
    
    def createMetaFiles(self):
        pass
    
    def createArt(self):
        pass

    def createNFO(self):
        
        if self.episodes_data.count() == 0:
            return False
        elif self.episodes_data.count() > 1:
            rootNode = etree.Element( "xbmcmultiepisode" )
            for epData in self.episodes_data:
                rootNode.append(sickbeard.nfo.makeEpNFO(epData))
        else:
            rootNode = sickbeard.nfo.makeEpNFO(self.episodes_data.one())

        # Set our namespace correctly
        for ns in sickbeard.XML_NSMAP.keys():
            rootNode.set(ns, sickbeard.XML_NSMAP[ns])

        nfo = etree.ElementTree( rootNode )
        #nfo_fh = ek.ek(open, ek.ek(os.path.join, self.show.location, nfoFilename), 'w')
        nfo_fh = open(os.path.join(self.show.location, "test.nfo"), 'w')
        nfo.write( nfo_fh, encoding="utf-8" ) 
        nfo_fh.close()
        
    def deleteEpisode(self):
        pass

    def fullPath(self):
        return os.path.join(self.show.location, self.location)
    
    def prettyName(self):
        return self.show.name + " - " + " & ".join([str(x.season) + "x" + str(x.episode) + " - " + x.name for x in self.episodes_data])