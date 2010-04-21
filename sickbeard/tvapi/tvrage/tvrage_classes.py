from storm.locals import Unicode, Pickle, Int, Date, Float, Storm, Reference

class TVShowData_TVRage(Storm):
    __storm_table__ = "tvshowdata_tvrage"

    tvrage_id = Int(primary=True)
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

    show_data = Reference(tvrage_id, "TVShowData.tvrage_id")

    def __init__(self, tvrage_id):
        self.tvrage_id = tvrage_id

class TVEpisodeData_TVRage(Storm):
    __storm_table__ = "tvepisodedata_tvrage"
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
    
    tvrage_id = Int()

    ep_data = Reference((show_id, season, episode),
                        ("TVEpisodeData.tvrage_show_id", "TVEpisodeData.season", "TVEpisodeData.episode"))
    ep_obj = Reference(_eid, "TVEpisode.eid")

    def __init__(self, show_id, season, episode):
        self.show_id = show_id
        self.season = season
        self.episode = episode
