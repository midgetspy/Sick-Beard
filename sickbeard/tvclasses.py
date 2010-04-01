from storm.locals import Int, Unicode, List, Float, Date, Bool, \
                        Reference, ReferenceSet

from tvapi.tvapi_classes import TVShowData, TVEpisodeData

from sickbeard import tvapi

from tvapi import tvapi_tvdb

class TVShow(object):
    __storm_table__ = "tvshow"

    tvdb_id = Int(primary=True)
    location = Unicode()
    seasonFolders = Bool()
    paused = Bool()
    
    data = Reference(tvdb_id, TVShowData.tvdb_id)
    
    def __init__(self, tvdb_id):
        self.tvdb_id = tvdb_id

    def update(self, cache=True):
        tvapi_tvdb.loadShow(self.tvdb_id, cache)
    

class TVEpisode(object):
    __storm_table__ = "tvepisode"
    
    eid = Int(primary=True)
    location = Unicode()
    status = Int()
    hasnfo = Bool()
    hastbn = Bool()
    
    _show = Int()
    
    show = Reference(_show, TVShow.tvdb_id)
    
    def __init__(self, show):
        self.show = show

    def addEp(self, season, episode):
        result = tvapi.store.find(TVEpisodeData, TVEpisodeData.show_id == self.show.tvdb_id, TVEpisodeData.season == season, TVEpisodeData.episode == episode)
        
        if result.count() == 1:
            self.episodes.add(result.one())
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


