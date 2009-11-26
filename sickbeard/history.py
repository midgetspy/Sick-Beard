import db
import sqlite3
import datetime

from sickbeard.logging import *
from sickbeard.common import *

dateFormat = "%Y%m%d%H%M%S"

def _logHistoryItem(action, showid, season, episode, quality, resource, provider):

    myDB = db.DBConnection()
    myDB.checkDB()

    logDate = datetime.datetime.today().strftime(dateFormat)
    
    try:
        sql = "INSERT INTO history (action, date, showid, season, episode, quality, resource, provider) VALUES (?,?,?,?,?,?,?,?)"
        sqlValues = [action, logDate, showid, season, episode, quality, resource, provider]
        Logger().log("SQL: " + sql + " with "+str(sqlValues), DEBUG)
        myDB.connection.execute(sql, sqlValues)
        myDB.connection.commit()
    except sqlite3.DatabaseError as e:
        Logger().log("Fatal error executing query '" + sql + "' with "+str(sqlValues)+": " + str(e), ERROR)
        raise


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

    