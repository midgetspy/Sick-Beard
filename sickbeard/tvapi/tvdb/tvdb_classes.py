from storm.locals import Unicode, Pickle, Int, Date, Float, Storm, Reference, ReferenceSet

from sickbeard.tvapi import proxy

class TVShowData_TVDB(Storm):
    __storm_table__ = "tvshowdata_tvdb"

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

    def __init__(self, tvdb_id):
        self.tvdb_id = tvdb_id

    def proxy(self):
        return proxy.GenericProxy(self)

class TVEpisodeData_TVDB(Storm):
    __storm_table__ = "tvepisodedata_tvdb"
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
    
    tvdb_id = Int()

    def __init__(self, show_id, season, episode):
        self.show_id = show_id
        self.season = season
        self.episode = episode

    def proxy(self):
        return proxy.GenericProxy(self)
