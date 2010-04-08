from tvapi_classes import TVShowData, TVEpisodeData
from sickbeard.tvclasses import TVShow, TVEpisode

from sickbeard import tvapi

def findTVShow(name):
    return tvapi.store.find(TVShow, TVShow.tvdb_id == TVShowData.tvdb_id, TVShowData.name == name).one()

def getTVShow(tvdb_id):
    result = tvapi.store.find(TVShow, TVShow.tvdb_id == tvdb_id)
    return result.one()

def createTVShow(tvdb_id):
    curShowObj = getTVShow(tvdb_id)
    if curShowObj:
        return curShowObj
    
    # make the show
    showObj = TVShow(tvdb_id)
    
    # get the metadata
    showObj.update()
    
    # make a TVEpisode for any TVEpisodeData objects that don't already have one
    for epData in tvapi.store.find(TVEpisodeData, TVEpisodeData.show_id == tvdb_id):
        if not epData.ep_obj:
            epObj = TVEpisode(showObj)
            epObj.addEp(ep=epData)
            tvapi.store.add(epObj)
    
    tvapi.store.add(showObj)
    tvapi.store.commit()
    
    return showObj