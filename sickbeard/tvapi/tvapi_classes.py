from storm.locals import Int, Unicode, Float, List, Reference, Date

class TVShowData(object):
    __storm_table__ = "tvshowdata"

    tvdb_id = Int(primary=True)
    name = Unicode()
    genres = List()
    network = Unicode()
    duration = Unicode()
    actors = List()
    firstAired = Unicode()
    status = Unicode()
    classification = Unicode()
    country = Unicode()
    rating = Float()
    tvrage_id = Int()
    imdb_id = Unicode()
    
    def __init__(self, tvdb_id):
        self.tvdb_id = tvdb_id
    
class TVEpisodeData(object):
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
    #other season/episode info needed for absolute/dvd/etc ordering
    tvdb_id = Int()
    imdb_id = Unicode()

    show = Reference(show_id, TVShowData.tvdb_id)

    def __init__(self, show_id, season, episode):
        self.show_id = show_id
        self.season = season
        self.episode = episode
