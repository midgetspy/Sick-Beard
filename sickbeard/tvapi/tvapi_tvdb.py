import datetime

from storm.locals import Store

from lib.tvdb_api import tvdb_api, tvdb_exceptions

from tvapi_classes import TVShowData, TVEpisodeData

from sickbeard import tvapi
from sickbeard import exceptions

class Logger():
    DEBUG = 1
    MESSAGE = 2
    ERROR = 3
    def log(self, message, blah=MESSAGE):
        if blah > Logger.DEBUG:
            print message
logger = Logger()

def loadShow(tvdb_id, cache=True):

    store = Store(tvapi.database)

    try:
        tvdbObj = tvdb_api.Tvdb(actors=True, language='en', cache=cache)
        tvdbShow = tvdbObj[tvdb_id]
    except tvdb_exceptions.tvdb_error, e:
        raise
    
    showData = store.find(TVShowData, TVShowData.tvdb_id == tvdb_id).one()
    if showData == None:
        logger.log("Show doesn't exist in DB, making new entry", logger.DEBUG)
        showData = TVShowData(tvdb_id)
        store.add(showData)
        #store.commit()

    logger.log("Updating all info for show "+str(tvdb_id)+"from TVDB", logger.DEBUG)

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

    store.commit()

    resultingData = {}

    for season in tvdbShow:
        for episode in tvdbShow[season]:
            result = loadEpisode(tvdb_id, season, episode, tvdbObj)
            if result:
                if season not in resultingData:
                    resultingData[season] = []
                resultingData[season].append(result)
    
    return resultingData
    

def loadEpisode(tvdb_id, season, episode, tvdbObj=None, cache=True):
    
    store = Store(tvapi.database)
    
    try:
        if tvdbObj == None:
            tvdbObj = tvdb_api.Tvdb(language='en', cache=cache)
        epObj = tvdbObj[tvdb_id][season][episode]
    except tvdb_exceptions.tvdb_error, e:
        raise

    epData = store.find(TVEpisodeData,
                              TVEpisodeData.show_id == tvdb_id,
                              TVEpisodeData.season == season,
                              TVEpisodeData.episode == episode).one()
    if epData == None:
        epData = TVEpisodeData(tvdb_id, season, episode)
        store.add(epData)
        store.commit()

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
    
    # weird data on tvdb is messing this up, but we don't need it anyway (for now at least)
    #epData.imdb_id = unicode(epObj['imdb_id'])

    store.commit()

    return epData