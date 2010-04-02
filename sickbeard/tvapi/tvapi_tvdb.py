import datetime

from lib.tvdb_api import tvdb_api, tvdb_exceptions

from tvapi_classes import TVShowData, TVEpisodeData

from sickbeard import tvapi

def loadShow(tvdb_id, cache=True):

    try:
        tvdbObj = tvdb_api.Tvdb(actors=True, language='en', cache=cache)
        tvdbShow = tvdbObj[tvdb_id]
    except tvdb_exceptions.tvdb_error, e:
        raise
    
    showData = tvapi.store.find(TVShowData, TVShowData.tvdb_id == tvdb_id).one()
    if showData == None:
        showData = TVShowData(tvdb_id)
        tvapi.store.add(showData)

    showData.name = tvdbShow['seriesname']

    showData.plot = tvdbShow['overview']
    showData.genres = tvdbShow['genre'].split('|') if tvdbShow['genre'] != None else []
    showData.genres = filter(lambda x: len(x) > 0, showData.genres)
    showData.network = tvdbShow['network']
    showData.duration = int(tvdbShow['runtime']) if tvdbShow['runtime'] != None else None
    showData.actors = tvdbShow['_actors']
    rawAirdate = [int(x) for x in tvdbShow['firstaired'].split("-")] if tvdbShow['firstaired'] != None else None
    if rawAirdate != None:
        showData.firstaired = datetime.date(rawAirdate[0], rawAirdate[1], rawAirdate[2])
    showData.status = tvdbShow['status']
    showData.rating = float(tvdbShow['rating']) if tvdbShow['rating'] != None else None
    showData.contentrating = tvdbShow['contentrating']

    showData.imdb_id = tvdbShow['imdb_id']

    for season in tvdbShow:
        for episode in tvdbShow[season]:
            loadEpisode(tvdb_id, season, episode, tvdbObj)
    
    tvapi.store.commit()
    

def loadEpisode(tvdb_id, season, episode, tvdbObj=None, cache=True):
    
    try:
        if tvdbObj == None:
            tvdbObj = tvdb_api.Tvdb(language='en', cache=cache)
        e = tvdbObj[tvdb_id][season][episode]
    except tvdb_exceptions.tvdb_error, e:
        raise

    epData = tvapi.store.find(TVEpisodeData,
                              TVEpisodeData.show_id == tvdb_id,
                              TVEpisodeData.season == season,
                              TVEpisodeData.episode == episode).one()
    if epData == None:
        epData = TVEpisodeData(tvdb_id, season, episode)
        tvapi.store.add(epData)
    epData.name = e['episodename']
    