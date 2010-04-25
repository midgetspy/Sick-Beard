import db
import sqlite3
import datetime

from sickbeard import logger
from sickbeard.common import *
from sickbeard import providers

dateFormat = "%Y%m%d%H%M%S"

def _logHistoryItem(action, showid, season, episode, quality, resource, provider):

    logDate = datetime.datetime.today().strftime(dateFormat)
    
    myDB = db.DBConnection()
    myDB.action("INSERT INTO history (action, date, showid, season, episode, quality, resource, provider) VALUES (?,?,?,?,?,?,?,?)",
                [action, logDate, showid, season, episode, quality, resource, provider])
    

def logSnatch(searchResult):
    
    showid = searchResult.episode.tvdb_show_id
    season = searchResult.episode.season
    episode = searchResult.episode.episode
    quality = searchResult.quality
    
    providerModule = providers.getProviderModule(searchResult.provider)
    if providerModule != None:
        provider = providerModule.providerName
    else:
        provider = "unknown"
    
    if searchResult.predownloaded:
        action = ACTION_PRESNATCHED
    else:
        action = ACTION_SNATCHED

    resource = searchResult.extraInfo[0]
    
    _logHistoryItem(action, showid, season, episode, quality, resource, provider)

def logDownload(episode, filename):
    
    showid = episode.tvdb_show_id
    season = episode.season
    episode = episode.episode
    
    quality = -1
    provider = -1
    
    action = ACTION_DOWNLOADED
    
    _logHistoryItem(action, showid, season, episode, quality, filename, provider)

    