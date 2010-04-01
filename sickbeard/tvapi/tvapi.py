from tvapi_classes import TVShowData, TVEpisodeData
from sickbeard.tvclasses import TVShow, TVEpisode

from sickbeard import tvapi

def findTVShow(name):
    return tvapi.store.find(TVShow, TVShow.tvdb_id == TVShowData.tvdb_id, TVShowData.name == name).one()

def getTVShow(tvdb_id):
    result = tvapi.store.find(TVShow, TVShow.tvdb_id == tvdb_id)
    
    if result.count() == 0:
        result = TVShow(tvdb_id)
        tvapi.store.add(result)
        return result 
    else:
        return result.one()


