import lib.fanart_api.fanart as fanart
from lib.fanart_api.fanart.items import LeafItem, Immutable, ResourceItem


class TvItem(LeafItem):
    @Immutable.mutablemethod
    def __init__(self, id, url, likes, lang):
        super(TvItem, self).__init__(id, url, likes)
        self.language = lang


class CharacterItem(TvItem):
    KEY = fanart.TYPE.TV.CHARACTER


class ArtItem(TvItem):
    KEY = fanart.TYPE.TV.ART


class LogoItem(TvItem):
    KEY = fanart.TYPE.TV.LOGO


class BackgroundItem(TvItem):
    KEY = fanart.TYPE.TV.BACKGROUND

    @Immutable.mutablemethod
    def __init__(self, id, url, likes, lang, season):
        super(BackgroundItem, self).__init__(id, url, likes, lang)
        self.season = 0 if season == 'all' else int(season)


class SeasonItem(TvItem):
    KEY = fanart.TYPE.TV.SEASONTHUMB

    @Immutable.mutablemethod
    def __init__(self, id, url, likes, lang, season):
        super(SeasonItem, self).__init__(id, url, likes, lang)
        self.season = int(season)


class ThumbItem(TvItem):
    KEY = fanart.TYPE.TV.THUMB


class HdLogoItem(TvItem):
    KEY = fanart.TYPE.TV.HDLOGO


class HdArtItem(TvItem):
    KEY = fanart.TYPE.TV.HDART


class TvShow(ResourceItem):
    WS = fanart.WS.TV

    @Immutable.mutablemethod
    def __init__(self, name, tvdbid, backgrounds, characters, arts, logos, seasons, thumbs, hdlogos, hdarts):
        self.name = name
        self.tvdbid = tvdbid
        self.backgrounds = backgrounds
        self.characters = characters
        self.arts = arts
        self.logos = logos
        self.seasons = seasons
        self.thumbs = thumbs
        self.hdlogos = hdlogos
        self.hdarts = hdarts

    @classmethod
    def from_dict(cls, resource):
        assert len(resource) == 1, 'Bad Format Map'
        name, resource = resource.items()[0]
        return cls(
            name=name,
            tvdbid=resource['thetvdb_id'],
            backgrounds=BackgroundItem.extract(resource),
            characters=CharacterItem.extract(resource),
            arts=ArtItem.extract(resource),
            logos=LogoItem.extract(resource),
            seasons=SeasonItem.extract(resource),
            thumbs=ThumbItem.extract(resource),
            hdlogos=HdLogoItem.extract(resource),
            hdarts=HdArtItem.extract(resource),
        )
