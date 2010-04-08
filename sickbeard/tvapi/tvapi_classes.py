from storm.locals import Int, Unicode, Float, Reference, Date, Pickle, Storm

from sickbeard.tvapi import store 

class TVShowData(Storm):
    __storm_table__ = "tvshowdata"

    tvdb_id = Int(primary=True)
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

    tvrage_id = Int()
    tvrage_name = Unicode()
    
    imdb_id = Unicode()
    
    show_obj = Reference(tvdb_id, "TVShow.tvdb_id")
    
    _cached_seasons = None
    _cached_episodes = {}
    
    def __init__(self, tvdb_id):
        self.tvdb_id = tvdb_id

    # give a list of seasons
    def _seasons(self):
        """
        Getter for the seasons property. Returns a list of seasons available for this show.
        Caches the result to limit unnecessary SQL queries.
        """

        if self._cached_seasons != None:
            return self._cached_seasons
        
        toReturn = []
        for x in store.execute("SELECT distinct season from tvepisodedata where show_id = ?", (self.tvdb_id,)):
            toReturn.append(x[0])
        
        if self._cached_seasons == None:
            self._cached_seasons = toReturn
        
        return toReturn
    
    seasons = property(_seasons)

    # provide a list of episode numbers for obj[season] accesses
    def __getitem__(self, key):
        """
        Allows access to episode lists via TVEpisodeData[season]. Returns a list of episodes
        in the given season. Caches the result to limit unnecessary SQL queries.
        """

        # if it's been looked up before just return the cache
        if key in self._cached_episodes:
            return self._cached_episodes[key]
        
        toReturn = []
        for x in store.execute("SELECT episode FROM tvepisodedata WHERE show_id = ? AND season = ?", (self.tvdb_id, key)):
            toReturn.append(x[0])

        # put the new lookup in the cache
        self._cached_episodes[key] = toReturn
        
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
    __storm_primary__ = "show_id", "season", "episode"

    show_id = Int()
    season = Int()
    episode = Int()
    name = Unicode()
    description = Unicode()
    aired = Date()
    director = Unicode()
    writer = Unicode()
    rating = Float()
    gueststars = Pickle()

    thumb = Unicode()

    displayseason = Int()
    displayepisode = Int()
    #other season/episode info needed for absolute/dvd/etc ordering
    
    _eid = Int()
    
    tvdb_id = Int()
    imdb_id = Unicode()

    show_data = Reference(show_id, "TVShowData.tvdb_id")
    ep_obj = Reference(_eid, "TVEpisode.eid")

    def __init__(self, show_id, season, episode):
        self.show_id = show_id
        self.season = season
        self.episode = episode

    def __storm_invalidated__(self):
        self.show_data.resetCache(self.season)

    def __storm_loaded__(self):
        self.show_data.resetCache(self.season)
