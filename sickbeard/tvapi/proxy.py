import sickbeard
import sqlite3

from sickbeard import logger

class GenericProxy():
    def __init__(self, obj):
        self.__dict__['obj'] = obj

    def _safe(self, func, *args, **kwargs):
        return sickbeard.storeManager.safe_store(func, *args, **kwargs)

    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        return self.obj.__repr__()+"+proxy"

    def __getattr__(self, name):
        if name in ("__call__"):
            return getattr(self.obj, name)

        try:
            return getattr(self.obj, name)
        except sqlite3.ProgrammingError, e:
            if str(e).startswith("SQLite objects created in a thread can only be used in that same thread."):
                return sickbeard.storeManager.safe_store(getattr, self.obj, name)
            else:
                raise

    def __setattr__(self, name, value):
        sickbeard.storeManager.safe_store(setattr, self.obj, name, value)
    

class TVShowProxy(GenericProxy):

    def __init__(self, show):
        GenericProxy.__init__(self, show)
        self.__dict__['show_data'] = _getProxy(sickbeard.storeManager.safe_store(getattr, show, 'show_data'))

    def delete(self):
        return self._safe(self.obj.delete)
    
    def nextEpisodes(self):
        return self._safe(self.obj.nextEpisodes)
    
    def refreshDir(self):
        return self._safe(self.obj.refreshDir)
    
    def getImages(self):
        return self._safe(self.obj.getImages)
    
    def writeEpisodeMetafiles(self):
        return self._safe(self.obj.writeEpisodeMetafiles)
    
    def renameEpisodes(self):
        return self._safe(self.obj.renameEpisodes)
    


class TVEpisodeProxy(GenericProxy):
    def prettyName(self, *args, **kwargs):
        return self._safe(self.obj.prettyName, *args, **kwargs)

class TVEpisodeDataProxy(GenericProxy):
    def __init__(self, epData):
        GenericProxy.__init__(self, epData)
        self.__dict__['ep_obj'] = _getProxy(sickbeard.storeManager.safe_store(getattr, epData, 'ep_obj'))
        self.__dict__['show_data'] = _getProxy(sickbeard.storeManager.safe_store(getattr, epData, 'show_data'))

    def delete(self):
        return self._safe(self.obj.delete)

class TVShowDataProxy(GenericProxy):
    def season(self, season):
        self._safe(self.obj.season, season)


def _getProxy(obj):
    """
    Returns the appropriate thread-safe proxy object if it exists, or else returns
    the object that was passed in.
    """
    if type(obj) == sickbeard.tvclasses.TVShow:
        return TVShowProxy(obj)
    elif type(obj) == sickbeard.tvclasses.TVEpisode:
        return TVEpisodeProxy(obj)
    elif type(obj) == sickbeard.tvapi.tvapi_classes.TVShowData:
        return TVShowDataProxy(obj)
    elif type(obj) == sickbeard.tvapi.tvapi_classes.TVEpisodeData:
        return TVEpisodeDataProxy(obj)
    else:
        return obj


