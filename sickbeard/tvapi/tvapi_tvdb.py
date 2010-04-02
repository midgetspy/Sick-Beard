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
    showData.genres = tvdbShow['genre'].split('|') if tvdbShow['genre'] else []
    showData.genres = filter(lambda x: x != '', showData.genres)
    showData.network = tvdbShow['network']
    showData.duration = int(tvdbShow['runtime']) if tvdbShow['runtime'] else None
    showData.actors = tvdbShow['_actors']
    rawAirdate = [int(x) for x in tvdbShow['firstaired'].split("-")] if tvdbShow['firstaired'] else None
    if rawAirdate != None:
        showData.firstaired = datetime.date(rawAirdate[0], rawAirdate[1], rawAirdate[2])
    showData.status = tvdbShow['status']
    showData.rating = float(tvdbShow['rating']) if tvdbShow['rating'] else None
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
        epObj = tvdbObj[tvdb_id][season][episode]
    except tvdb_exceptions.tvdb_error, e:
        raise

    epData = tvapi.store.find(TVEpisodeData,
                              TVEpisodeData.show_id == tvdb_id,
                              TVEpisodeData.season == season,
                              TVEpisodeData.episode == episode).one()
    if epData == None:
        epData = TVEpisodeData(tvdb_id, season, episode)
        tvapi.store.add(epData)

    epData.name = epObj['episodename']
    
    epData.description = epObj['overview']

    rawAirdate = [int(x) for x in epObj['firstaired'].split("-")] if epObj['firstaired'] != None else None
    if rawAirdate != None:
        epData.aired = datetime.date(rawAirdate[0], rawAirdate[1], rawAirdate[2])
    epData.director = epObj['director']
    epData.writer = epObj['writer']
    epData.rating = float(epObj['rating']) if epObj['rating'] else None
    epData.gueststars = filter(lambda x: x != '', epObj['gueststars'].split('|')) if epObj['gueststars'] else []

    if 'airsbefore_season' in epObj and epObj['airsbefore_season']:
        epData.displayseason = int(epObj['airsbefore_season'])
    if 'airsbefore_episode' in epObj and epObj['airsbefore_episode']:
        epData.displayeposide = int(epObj['airsbefore_episode'])
    #other season/episode info needed for absolute/dvd/etc ordering
    
    epData.tvdb_id = int(epObj['id'])
    epData.imdb_id = epObj['imdb_id']
