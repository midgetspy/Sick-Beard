from storm.locals import Int, Unicode, List, Float, Date, Bool, \
                        Reference, ReferenceSet

from tvapi.tvapi_classes import TVShowData, TVEpisodeData

from sickbeard import tvapi

from tvapi import tvapi_tvdb, tvapi_tvrage

class TVShow(object):
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
    
    data = Reference(tvdb_id, TVShowData.tvdb_id)
    
    def __init__(self, tvdb_id):
        self.tvdb_id = tvdb_id

    def update(self, cache=True):
        tvapi_tvdb.loadShow(self.tvdb_id, cache)
        tvapi_tvrage.loadShow(self.tvdb_id)
    
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

class TVEpisode(object):
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
    status = Int()
    
    # whether nfo/tbn exists
    hasnfo = Bool()
    hastbn = Bool()
    
    _show = Int()
    
    show = Reference(_show, TVShow.tvdb_id)
    
    def __init__(self, show):
        self.show = show

    def addEp(self, season, episode):
        """
        Add an episode to the episode data list (TVEpisode.episodes)
        """
        result = tvapi.store.find(TVEpisodeData, TVEpisodeData.show_id == self.show.tvdb_id, TVEpisodeData.season == season, TVEpisodeData.episode == episode)
        
        if result.count() == 1:
            self.episodes.add(result.one())
        else:
            raise Exception()

    def getEp(self, season, episode):
        result = self.episodes.find(TVEpisodeData.show_id == self.show.tvdb_id, TVEpisodeData.season == season, TVEpisodeData.episode == episode)
        
        if result.count() == 1:
            return result.one()
        else:
            raise Exception()
   
class EpisodeDataRel(object):
    __storm_table__ = "episodedatarel"
    __storm_primary__ = "eid", "show_id", "season", "episode"

    eid = Int()
    show_id = Int()
    season = Int()
    episode = Int()

TVEpisode.episodes = ReferenceSet(TVEpisode.eid, EpisodeDataRel.eid, 
                                  (EpisodeDataRel.show_id, EpisodeDataRel.season, EpisodeDataRel.episode),
                                  (TVEpisodeData.show_id, TVEpisodeData.season, TVEpisodeData.episode))


