from fanart.items import Immutable, LeafItem, ResourceItem, CollectableItem
import fanart


class BackgroundItem(LeafItem):
    KEY = fanart.TYPE.MUSIC.BACKGROUND


class CoverItem(LeafItem):
    KEY = fanart.TYPE.MUSIC.COVER


class LogoItem(LeafItem):
    KEY = fanart.TYPE.MUSIC.LOGO


class DiscItem(LeafItem):
    KEY = fanart.TYPE.MUSIC.DISC

    @Immutable.mutablemethod
    def __init__(self, id, url, likes, disc, size):
        super(DiscItem, self).__init__(id, url, likes)
        self.disc = int(disc)
        self.size = int(size)


class Artist(ResourceItem):
    WS = fanart.WS.MUSIC

    @Immutable.mutablemethod
    def __init__(self, name, mbid, albums, backgrounds, logos):
        self.name = name
        self.mbid = mbid
        self.albums = albums
        self.backgrounds = backgrounds
        self.logos = logos

    @classmethod
    def from_dict(cls, resource):
        assert len(resource) == 1, 'Bad Format Map'
        name, resource = resource.items()[0]
        return cls(
            name=name,
            mbid=resource['mbid_id'],
            albums=Album.collection_from_dict(resource.get('albums', {})),
            backgrounds=BackgroundItem.extract(resource),
            logos=LogoItem.extract(resource),
        )


class Album(CollectableItem):

    @Immutable.mutablemethod
    def __init__(self, mbid, covers, arts):
        self.mbid = mbid
        self.covers = covers
        self.arts = arts

    @classmethod
    def from_dict(cls, key, resource):
        return cls(
            mbid=key,
            covers=CoverItem.extract(resource),
            arts=DiscItem.extract(resource),
        )
