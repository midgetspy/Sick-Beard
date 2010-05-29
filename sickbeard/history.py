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
    
    showid = int(searchResult.episode.show.tvdbid)
    season = int(searchResult.episode.season)
    episode = int(searchResult.episode.episode)
    quality = searchResult.quality
    
    providerModule = providers.getProviderModule(searchResult.provider)
    if providerModule != None:
        provider = providerModule.providerName
    else:
        provider = "unknown"
    
    action = Quality.compositeStatus(SNATCHED, searchResult.quality)

    resource = searchResult.extraInfo[0]
    
    _logHistoryItem(action, showid, season, episode, quality, resource, provider)

def logDownload(episode, filename):
    
    showid = int(episode.show.tvdbid)
    season = int(episode.season)
    epNum = int(episode.episode)
    
    quality = -1
    provider = -1
    
    oldQuality, oldStatus = Quality.splitCompositeQuality(episode.status)
    if oldStatus == SNATCHED:
        action = Quality.compositeStatus(DOWNLOADED, oldQuality)
    else:
        action = Quality.compositeStatus(DOWNLOADED, Quality.UNKNOWN)
    
    _logHistoryItem(action, showid, season, epNum, quality, filename, provider)

    