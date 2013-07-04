import fanart
from fanart.items import LeafItem, Immutable, ResourceItem


class MovieItem(LeafItem):

    @Immutable.mutablemethod
    def __init__(self, id, url, likes, lang):
        super(MovieItem, self).__init__(id, url, likes)
        self.language = lang


class DiscItem(MovieItem):
    KEY = fanart.TYPE.MOVIE.DISC

    @Immutable.mutablemethod
    def __init__(self, id, url, likes, lang, disc, disc_type):
        super(MovieItem, self).__init__(id, url, likes)
        self.disc = int(disc)
        self.disc_type = disc_type


class ArtItem(MovieItem):
    KEY = fanart.TYPE.MOVIE.ART


class LogoItem(MovieItem):
    KEY = fanart.TYPE.MOVIE.LOGO


class Movie(ResourceItem):
    WS = fanart.WS.MOVIE

    @Immutable.mutablemethod
    def __init__(self, name, imdbid, tmdbid, arts, logos, discs):
        self.name = name
        self.imdbid = imdbid
        self.tmdbid = tmdbid
        self.arts = arts
        self.logos = logos
        self.discs = discs

    @classmethod
    def from_dict(cls, resource):
        assert len(resource) == 1, 'Bad Format Map'
        name, resource = resource.items()[0]
        return cls(
            name=name,
            imdbid=resource['imdb_id'],
            tmdbid=resource['tmdb_id'],
            arts=ArtItem.extract(resource),
            logos=LogoItem.extract(resource),
            discs=DiscItem.extract(resource),
        )
