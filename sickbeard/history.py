import db
import sqlite3
import datetime

from sickbeard import logger
from sickbeard.common import *

dateFormat = "%Y%m%d%H%M%S"

def _logHistoryItem(action, showid, season, episode, quality, resource, provider):

    logDate = datetime.datetime.today().strftime(dateFormat)
    
    myDB = db.DBConnection()
    myDB.action("INSERT INTO history (action, date, showid, season, episode, quality, resource, provider) VALUES (?,?,?,?,?,?,?,?)", [action, logDate, showid, season, episode, quality, resource, provider])
    

def logSnatch(searchResult):
    
    showid = int(searchResult.episode.show.tvdbid)
    season = int(searchResult.episode.season)
    episode = int(searchResult.episode.episode)
    quality = searchResult.quality
    
    provider = searchResult.provider
    
    if searchResult.predownloaded:
        action = ACTION_PRESNATCHED
    else:
        action = ACTION_SNATCHED

    resource = searchResult.extraInfo[0]
    
    _logHistoryItem(action, showid, season, episode, quality, resource, provider)

def logDownload(episode, filename):
    
    showid = int(episode.show.tvdbid)
    season = int(episode.season)
    episode = int(episode.episode)
    
    quality = -1
    provider = -1
    
    action = ACTION_DOWNLOADED
    
    _logHistoryItem(action, showid, season, episode, quality, filename, provider)

    