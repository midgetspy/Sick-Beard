# Author: Tyler Fenby <tylerfenby@gmail.com>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import re
import urllib
import datetime


from sickbeard import db
from sickbeard import logger
from sickbeard import common
from sickbeard import exceptions
from sickbeard.history import dateFormat


def _log_helper(message, level=logger.MESSAGE):
    logger.log(message, level)
    return message + u"\n"


def prepareFailedName(release):
    """Standardizes release name for failed DB"""

    fixed = urllib.unquote(release)
    if(fixed.endswith(".nzb")):
        fixed = fixed.rpartition(".")[0]

    fixed = re.sub("[\.\-\+\ ]", "_", fixed)
    return fixed


def logFailed(release):
    log_str = u""
    size = -1
    provider = ""

    release = prepareFailedName(release)

    myDB = db.DBConnection("failed.db")
    sql_results = myDB.select("SELECT * FROM history WHERE release=?", [release])

    if len(sql_results) == 0:
        log_str += _log_helper(u"Release not found in snatch history. Recording it as bad with no size and no proivder.", logger.WARNING)
        log_str += _log_helper(u"Future releases of the same name from providers that don't return size will be skipped.", logger.WARNING)
    elif len(sql_results) > 1:
        log_str += _log_helper(u"Multiple logged snatches found for release", logger.WARNING)
        sizes = len(set(x["size"] for x in sql_results))
        providers = len(set(x["provider"] for x in sql_results))
        if sizes == 1:
            log_str += _log_helper(u"However, they're all the same size. Continuing with found size.", logger.WARNING)
            size = sql_results[0]["size"]
        else:
            log_str += _log_helper(u"They also vary in size. Deleting the logged snatches and recording this release with no size/provider", logger.WARNING)
            for result in sql_results:
                deleteLoggedSnatch(result["release"], result["size"], result["provider"])

        if providers == 1:
            log_str += _log_helper(u"They're also from the same provider. Using it as well.")
            provider = sql_results[0]["provider"]
    else:
        size = sql_results[0]["size"]
        provider = sql_results[0]["provider"]

    if not hasFailed(release, size, provider):
        myDB.action("INSERT INTO failed (release, size, provider) VALUES (?, ?, ?)", [release, size, provider])

    deleteLoggedSnatch(release, size, provider)

    return log_str


def logSuccess(release):
    # Placeholder for now. We want to maintain history in case a download
    # succeeds but is bad.
    pass


def hasFailed(release, size, provider="%"):
    """
    Returns True if a release has previously failed.

    If provider is given, return True only if the release is found
    with that specific provider. Otherwise, return True if the release
    is found with any provider.
    """

    myDB = db.DBConnection("failed.db")
    sql_results = myDB.select(
        "SELECT * FROM failed WHERE release=? AND size=? AND provider LIKE ?",
        [prepareFailedName(release), size, provider])

    return (len(sql_results) > 0)


def revertEpisodes(show_obj, season, episodes):
    """Restore the episodes of a failed download to their original state"""
    myDB = db.DBConnection("failed.db")
    log_str = u""

    sql_results = myDB.select("SELECT * FROM history WHERE showtvdbid=? AND season=?", [show_obj.tvdbid, season])
    # {episode: result, ...}
    history_eps = dict([(res["episode"], res) for res in sql_results])

    if len(episodes) > 0:
        for cur_episode in episodes:
            try:
                ep_obj = show_obj.getEpisode(season, cur_episode)
            except exceptions.EpisodeNotFoundException, e:
                log_str += _log_helper(u"Unable to create episode, please set its status manually: " + exceptions.ex(e), logger.WARNING)
                continue

            log_str += _log_helper(u"Reverting episode (%s, %s): %s" % (season, cur_episode, ep_obj.name))
            with ep_obj.lock:
                if cur_episode in history_eps:
                    log_str += _log_helper(u"Found in history")
                    ep_obj.status = history_eps[cur_episode]['old_status']
                else:
                    log_str += _log_helper(u"WARNING: Episode not found in history. Setting it back to WANTED", logger.WARNING)
                    ep_obj.status = common.WANTED

                ep_obj.saveToDB()
    else:
        # Whole season
        log_str += _log_helper(u"Setting season to wanted: " + str(season))
        for ep_obj in show_obj.getAllEpisodes(season):
            log_str += _log_helper(u"Reverting episode (%d, %d): %s" % (season, ep_obj.episode, ep_obj.name))
            with ep_obj.lock:
                if ep_obj in history_eps:
                    log_str += _log_helper(u"Found in history")
                    ep_obj.status = history_eps[ep_obj]['old_status']
                else:
                    log_str += _log_helper(u"WARNING: Episode not found in history. Setting it back to WANTED", logger.WARNING)
                    ep_obj.status = common.WANTED

                ep_obj.saveToDB()

    return log_str

def markFailed(show_obj, season, episodes):
    log_str = u""

    if len(episodes) > 0:
        for cur_episode in episodes:
            try:
                ep_obj = show_obj.getEpisode(season, cur_episode)
            except exceptions.EpisodeNotFoundException, e:
                log_str += _log_helper(u"Unable to get episode, please set its status manually: " + exceptions.ex(e), logger.WARNING)
                continue

            with ep_obj.lock:
                ep_obj.status = common.FAILED
                ep_obj.saveToDB()
    else:
        # Whole season
        for ep_obj in show_obj.getAllEpisodes(season):
            with ep_obj.lock:
                ep_obj.status = common.FAILED
                ep_obj.saveToDB()

    return log_str

def logSnatch(searchResult):
    myDB = db.DBConnection("failed.db")

    logDate = datetime.datetime.today().strftime(dateFormat)
    release = prepareFailedName(searchResult.name)

    providerClass = searchResult.provider
    if providerClass is not None:
        provider = providerClass.name
    else:
        provider = "unknown"

    show_obj = searchResult.episodes[0].show

    for episode in searchResult.episodes:
        old_status = show_obj.getEpisode(episode.season, episode.episode).status

        myDB.action(
            "INSERT INTO history (date, size, release, provider, showtvdbid, season, episode, old_status)"
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [logDate, searchResult.size, release, provider, show_obj.tvdbid, episode.season, episode.episode, old_status])


def deleteLoggedSnatch(release, size, provider):
    myDB = db.DBConnection("failed.db")

    release = prepareFailedName(release)

    myDB.action("DELETE FROM history WHERE release=? AND size=? AND provider=?",
                [release, size, provider])


def trimHistory():
    myDB = db.DBConnection("failed.db")
    myDB.action("DELETE FROM history WHERE date < " + str((datetime.datetime.today() - datetime.timedelta(days=30)).strftime(dateFormat)))


def findRelease(showtvdbid, season, episode):
    """
    Find release in history by show ID, season, and episode.
    Raise exception if multiple found.
    """

    myDB = db.DBConnection("failed.db")
    sql_results = myDB.select(
        "SELECT release FROM history WHERE showtvdbid=? AND season=? AND episode=?",
        [showtvdbid, season, episode])

    logger.log(u"findRelease results: " + str([x["release"] for x in sql_results]), logger.DEBUG)

    if len(sql_results) == 0:
        logger.log(u"Release not found (%s, %s, %s)" % (showtvdbid, season, episode),
                   logger.WARNING)
        raise exceptions.FailedHistoryNotFoundException()
    elif len(sql_results) > 1:
        # Multi-snatched (i.e., user meddling)
        # Clear it and start fresh
        logger.log(u"Multi-snatch detected. (%s, %s, %s)" % (showtvdbid, season, episode),
                   logger.WARNING)
        myDB.select("DELETE FROM history WHERE showtvdbid=? AND season=? AND episode=?",
                    [showtvdbid, season, episode])
        # Clear multi-ep by release as well so we don't have partial history
        # for a release
        for result in sql_results:
            myDB.select("DELETE FROM HISTORY where release=?", [result["release"]])

        raise exceptions.FailedHistoryMultiSnatchException()
    else:
        return sql_results[0]["release"]

    
