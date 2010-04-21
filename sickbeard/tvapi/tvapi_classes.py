from storm.locals import Int, Unicode, Float, Reference, ReferenceSet, Date, Pickle, Storm

import sickbeard

from sickbeard import logger

import proxy, safestore
from tvdb import tvdb_classes

class TVShowData(Storm):
    __storm_table__ = "tvshowdata"

    tvdb_id = Int(primary=True)
    tvrage_id = Int()
    imdb_id = Unicode()

    show_obj = Reference(tvdb_id, "TVShow.tvdb_id")
    episodes_data = ReferenceSet(tvdb_id, "TVEpisodeData.tvdb_show_id")

    name = Unicode()
    plot = Unicode()
    genres = Pickle()
    network = Unicode()
    duration = Int()
    actors = Pickle()
    firstaired = Date()
    status = Unicode()
    classification = Unicode()
    country = Unicode()
    rating = Float()
    contentrating = Unicode()

    _cached_seasons = None
    _cached_episodes = {}
    
    def __init__(self, tvdb_id):
        self.tvdb_id = tvdb_id

    def proxy(self):
        return proxy.TVShowDataProxy(self)

    def update(self):
        """
        Gets all metadata associated with this show (TVDB/TVRage/etc) and combines it to form
        a global metadata object to be used inside Sick Beard.
        """
        
        tvdb_data_list = safestore.safe_list(sickbeard.storeManager.safe_store("find", tvdb_classes.TVShowData_TVDB, tvdb_classes.TVShowData_TVDB.tvdb_id == self.tvdb_id))
        if len(tvdb_data_list) == 0:
            tvdb_data = None
        else:
            tvdb_data = tvdb_data_list[0]
        
        if not tvdb_data:
            return
        
        # just use all TVDB data for now
        self.name = tvdb_data.name
        self.plot = tvdb_data.plot
        self.genres = tvdb_data.genres
        self.network = tvdb_data.network
        self.duration = tvdb_data.duration
        self.actors = tvdb_data.actors
        self.firstaired = tvdb_data.firstaired
        self.status = tvdb_data.status
        self.classification = tvdb_data.classification
        self.country = tvdb_data.country
        self.rating = tvdb_data.rating
        self.contentrating = tvdb_data.contentrating
        

    # give a list of seasons
    def _seasons(self):
        """
        Getter for the seasons property. Returns a list of seasons available for this show.
        Caches the result to limit unnecessary SQL queries.
        """

        if self._cached_seasons != None:
            return self._cached_seasons
        
        toReturn = []
        for x in sickbeard.storeManager._store.execute("SELECT distinct season from tvepisodedata where show_id = ?", (self.tvdb_id,)):
            toReturn.append(x[0])
        
        if self._cached_seasons == None:
            self._cached_seasons = toReturn
        
        return toReturn
    
    seasons = property(_seasons)

    # provide a list of episode numbers for obj[season] accesses
    def season(self, season):
        """
        Allows access to episode lists via TVEpisodeData[season]. Returns a list of episodes
        in the given season. Caches the result to limit unnecessary SQL queries.
        """

        # if it's been looked up before just return the cache
        if season in self._cached_episodes:
            return self._cached_episodes[season]
        
        toReturn = []
        for x in sickbeard.storeManager._store.execute("SELECT episode FROM tvepisodedata WHERE show_id = ? AND season = ?", (self.tvdb_id, season)):
            toReturn.append(x[0])

        # put the new lookup in the cache
        self._cached_episodes[season] = toReturn
        
        return toReturn

    def resetCache(self, season=None):
        """
        Clear the season/episode cache. If a season is given then only that season's episodes
        are refreshed. 
        """
        
        # reset the season list
        self._cached_seasons = None
        
        # if there's a specific season given then delete it, else just empty the whole thing
        if season:
            if season in self._cached_episodes:
                del self._cached_episodes[season]
        else:
            self._cached_episodes = {}
    
class TVEpisodeData(Storm):
    __storm_table__ = "tvepisodedata"
    __storm_primary__ = "tvdb_show_id", "season", "episode"

    tvdb_show_id = Int()
    tvrage_show_id = Int()
    
    season = Int()
    episode = Int()

    _eid = Int()

    name = Unicode()
    description = Unicode()
    aired = Date()
    director = Unicode()
    writer = Unicode()
    rating = Float()
    gueststars = Pickle()
    thumb = Unicode()

    show_data = Reference(tvdb_show_id, "TVShowData.tvdb_id")
    ep_obj = Reference(_eid, "TVEpisode.eid")

    def __init__(self, tvdb_show_id, season, episode):
        self.tvdb_show_id = tvdb_show_id
        self.season = season
        self.episode = episode
        
        #self.update()

    def proxy(self):
        return proxy.TVEpisodeDataProxy(self)

    def update(self):
        """
        Gets all metadata associated with this episode (TVDB/TVRage/etc) and combines it to form
        a global metadata object to be used inside Sick Beard.
        """
        
        logger.log("Updating the data for TVEpisodeData for "+str(self.season)+"x"+str(self.episode), logger.DEBUG)
        
        tvdb_data_rs = sickbeard.storeManager.safe_store("find", tvdb_classes.TVEpisodeData_TVDB,
                                                                   tvdb_classes.TVEpisodeData_TVDB.show_id == self.tvdb_show_id,
                                                                   tvdb_classes.TVEpisodeData_TVDB.season == self.season,
                                                                   tvdb_classes.TVEpisodeData_TVDB.episode == self.episode)
        tvdb_data_list = safestore.safe_list(tvdb_data_rs)
        if len(tvdb_data_list) == 0:
            logger.log("No TVDB data found for this episode", logger.DEBUG)
            tvdb_data = None
        else:
            tvdb_data = tvdb_data_list[0]

        if not tvdb_data:
            return
        
        # just use all TVDB data for now
        self.name = tvdb_data.name
        self.description = tvdb_data.description
        self.aired = tvdb_data.aired
        self.director = tvdb_data.director
        self.writer = tvdb_data.writer
        self.rating = tvdb_data.rating
        self.gueststars = tvdb_data.gueststars
        self.thumb = tvdb_data.thumb
        

    def delete(self):
        """
        Deletes the episode data from the database, and if the associated episode object
        has no other metadata associated with it then it's deleted as well.
        """
        if self.ep_obj and self.ep_obj.episodes_data.count() == 1:
            self.ep_obj.delete()
        else:
            sickbeard.storeManager._store.remove(self)

    def __storm_invalidated__(self):
        self.show_data.resetCache(self.season)

    def __storm_loaded__(self):
        self.show_data.resetCache(self.season)
