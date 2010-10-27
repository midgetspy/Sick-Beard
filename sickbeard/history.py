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

    for curEpObj in searchResult.episodes:

        showid = int(curEpObj.show.tvdbid)
        season = int(curEpObj.season)
        episode = int(curEpObj.episode)
        quality = searchResult.quality

        providerClass = searchResult.provider
        if providerClass != None:
            provider = providerClass.name
        else:
            provider = "unknown"

        action = Quality.compositeStatus(SNATCHED, searchResult.quality)

        resource = searchResult.name

        _logHistoryItem(action, showid, season, episode, quality, resource, provider)

def logDownload(episode, filename):

    showid = int(episode.show.tvdbid)
    season = int(episode.season)
    epNum = int(episode.episode)

    quality = -1
    provider = -1

    action = episode.status

    _logHistoryItem(action, showid, season, epNum, quality, filename, provider)


