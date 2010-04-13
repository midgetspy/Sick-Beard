import sickbeard
import sqlite3

class GenericProxy():
    def __init__(self, obj):
        self.__dict__['obj'] = obj

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
        self.__dict__['show_data'] = GenericProxy(sickbeard.storeManager.safe_store(getattr, show, 'show_data'))
    

class TVEpisodeProxy(GenericProxy):
    pass

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
        return GenericProxy(obj)
    elif type(obj) == sickbeard.tvapi.tvapi_classes.TVEpisodeData:
        return GenericProxy(obj)
    else:
        return obj


