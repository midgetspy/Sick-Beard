import datetime

from storm.locals import Int, Unicode, List, Float, Date, Bool, \
                        Reference, ReferenceSet, Storm
from storm.expr import And

from tvapi.tvapi_classes import TVShowData, TVEpisodeData

from sickbeard import tvapi

from tvapi import tvapi_tvdb, tvapi_tvrage

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
    location = Unicode()
    seasonFolders = Bool()
    paused = Bool()
    
    show_data = Reference(tvdb_id, "TVShowData.tvdb_id")
    
    def __init__(self, tvdb_id):
        self.tvdb_id = tvdb_id

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

        result = tvapi.store.find(TVEpisodeData, And(*conditions))
        return result

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
    
    _show = Int()
    
    show = Reference(_show, "TVShow.tvdb_id")
    episodes_data = ReferenceSet(eid, "TVEpisodeData._eid")
    
    def _getStatus(self):
        if self._status == None:
            if self.episodes_data.count() == 1:
                epData = self.episodes_data.one()
                if epData.aired >= datetime.date.today():
                    return 11 #TODO: UNAIRED
                else:
                    return 22 #TODO: SKIPPED
            else:
                return 33 #UNKNOWN
        else:
            return self._status
    
    def _setStatus(self, value):
        self._status = value
    
    status = property(_getStatus, _setStatus)
    
    def __init__(self, show):
        self.show = show

    def addEp(self, season, episode):
        """
        Add an episode to the episode data list (TVEpisode.episodes)
        """
        result = tvapi.store.find(TVEpisodeData, TVEpisodeData.show_id == self.show.tvdb_id, TVEpisodeData.season == season, TVEpisodeData.episode == episode)
        
        if result.count() == 1:
            self.episodes_data.add(result.one())
        else:
            raise Exception()

    def getEp(self, season, episode):
        result = self.episodes_data.find(TVEpisodeData.show_id == self.show.tvdb_id, TVEpisodeData.season == season, TVEpisodeData.episode == episode)
        
        if result.count() == 1:
            return result.one()
        else:
            raise Exception()
   
