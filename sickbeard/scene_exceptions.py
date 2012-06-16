# Author: Nic Wolfe <nic@wolfeden.ca>
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
import urllib, urllib2, httplib

from sickbeard.helpers import sanitizeSceneName
from sickbeard import name_cache, helpers
from sickbeard import logger
from sickbeard import db
import sickbeard
from lib import adba
try:
    import json
except ImportError:
    from lib import simplejson as json
import urllib2
from sickbeard.exceptions import ex

excpetionCache = {}
seasonExcpetionCache = {}

exception_tvdb = {}

def get_scene_exceptions(tvdb_id, season=-1):
    """
    Given a tvdb_id, return a list of all the scene exceptions.
    If no season is given it will only return scene_exceptions that are valid for all seasons
    """
    global excpetionCache
    if tvdb_id not in excpetionCache or season not in excpetionCache[tvdb_id]:
        myDB = db.DBConnection("cache.db")
        exceptions = myDB.select("SELECT show_name FROM scene_exceptions WHERE tvdb_id = ? and season = ?", [tvdb_id, season])
        exceptionsList = [cur_exception["show_name"] for cur_exception in exceptions]
        if not tvdb_id in excpetionCache:
            excpetionCache[tvdb_id] = {}
        excpetionCache[tvdb_id][season] = exceptionsList
    else:
        exceptionsList = excpetionCache[tvdb_id][season]

    if season == 1: # if we where looking for season 1 we can add generic names
        exceptionsList += get_scene_exceptions(tvdb_id, season=-1)
    
    #print "scene excpetions for: ", tvdb_id, "season: ", season, str(exceptionsList)
    
    return exceptionsList

def get_all_scene_exceptions(tvdb_id):
    myDB = db.DBConnection("cache.db")
    exceptions = myDB.select("SELECT show_name,season FROM scene_exceptions WHERE tvdb_id = ?", [tvdb_id])
    exceptionsList = {}
    [cur_exception["show_name"] for cur_exception in exceptions]
    for cur_exception in exceptions:
        if not cur_exception["season"] in exceptionsList:
            exceptionsList[cur_exception["season"]] = []
        exceptionsList[cur_exception["season"]].append(cur_exception["show_name"])
        
    return exceptionsList

def get_scene_seasons(tvdb_id):
    """
    return a list of season numbers that have scene exceptions
    """
    global seasonExcpetionCache
    if tvdb_id not in seasonExcpetionCache:
        myDB = db.DBConnection("cache.db")
        sqlResults = myDB.select("SELECT DISTINCT(season) as season FROM scene_exceptions WHERE tvdb_id = ?", [tvdb_id])
        seasonExcpetionCache[tvdb_id] = [int(x["season"]) for x in sqlResults]
    
    return seasonExcpetionCache[tvdb_id]


def get_scene_exception_by_name(show_name):
    return get_scene_exception_by_name_multiple(show_name)[0]

def get_scene_exception_by_name_multiple(show_name):
    """
    Given a show name, return the tvdbid of the exception, None if no exception
    is present.
    """

    myDB = db.DBConnection("cache.db")

    # try the obvious case first
    exception_result = myDB.select("SELECT tvdb_id, season FROM scene_exceptions WHERE LOWER(show_name) = ? ORDER BY season ASC", [show_name.lower()])
    if exception_result:
        return [(int(x["tvdb_id"]), int(x["season"])) for x in exception_result]

    out = []
    all_exception_results = myDB.select("SELECT show_name, tvdb_id, season FROM scene_exceptions")
    for cur_exception in all_exception_results:

        cur_exception_name = cur_exception["show_name"]
        cur_tvdb_id = int(cur_exception["tvdb_id"])
        cur_season = int(cur_exception["season"])

        if show_name.lower() in (cur_exception_name.lower(), sanitizeSceneName(cur_exception_name).lower().replace('.', ' ')):
            logger.log(u"Scene exception lookup got tvdb id " + str(cur_tvdb_id) + u", using that", logger.DEBUG)
            out.append((cur_tvdb_id, cur_season))
    if out:
        return out
    else:
        return [(None, None)]

def retrieve_exceptions(localOnly=False):
    """
    Looks up the exceptions on github, parses them into a dict, and inserts them into the
    scene_exceptions table in cache.db. Also clears the scene name cache.
    """

    # exceptions are stored on github pages
    url = 'http://midgetspy.github.com/sb_tvdb_scene_exceptions/exceptions.txt'
    url2 = 'http://lad1337.github.com/sb_tvdb_scene_exceptions/anime_exceptions.txt'
    exception_dict = {}
    if not localOnly:
        exception_dict = _retrieve_exceptions_fetcher(url)
        exception_dict.update(_retrieve_exceptions_fetcher(url2)) # server anime exceptions

    local_exceptions = _retrieve_anidb_mainnames()
    for local_ex in local_exceptions: # anidb xml anime exceptions
        if local_ex in exception_dict:
            exception_dict[local_ex] = exception_dict[local_ex] + local_exceptions[local_ex]
        else:
            exception_dict[local_ex] = local_exceptions[local_ex]

    xem_exceptions = _xem_excpetions_fetcher()
    for xem_ex in xem_exceptions: # anidb xml anime exceptions
        if xem_ex in exception_dict:
            exception_dict[xem_ex] = exception_dict[xem_ex] + xem_exceptions[xem_ex]
        else:
            exception_dict[xem_ex] = xem_exceptions[xem_ex]

    if not len(exception_dict):
        logger.log("retrived exception list is totally empty. Assuming remote server error not flushing local and stoping now")
        return False

    myDB = db.DBConnection("cache.db")
    myDB.action("DELETE FROM scene_exceptions") # flush current list

    # write all the exceptions we got off the net into the database
    for cur_tvdb_id in exception_dict:

        for cur_exception_dict in exception_dict[cur_tvdb_id]:
            cur_exception, curSeason = cur_exception_dict.items()[0]
            myDB.action("INSERT INTO scene_exceptions (tvdb_id, show_name, season) VALUES (?,?,?)", [cur_tvdb_id, cur_exception, curSeason])

    name_cache.clearCache()
    global excpetionCache
    global seasonExcpetionCache
    excpetionCache = {}
    seasonExcpetionCache = {}
    buil_name_set()

def _retrieve_exceptions_fetcher(url):

    exception_dict = {}
    open_url = urllib.urlopen(url)

    # each exception is on one line with the format tvdb_id: 'show name 1', 'show name 2', etc
    for cur_line in open_url.readlines():
        tvdb_id, sep, aliases = cur_line.partition(':') #@UnusedVariable

        if not aliases:
            continue

        tvdb_id = int(tvdb_id)

        # regex out the list of shows, taking \' into account
        # all simple sb scene exceptions are for all seasons -> season = -1
        alias_list = [{re.sub(r'\\(.)', r'\1', x):-1} for x in re.findall(r"'(.*?)(?<!\\)',?", aliases)]

        exception_dict[tvdb_id] = alias_list
    return exception_dict

def _retrieve_anidb_mainnames():

    anidb_mainNames = {}
    for show in sickbeard.showList:
        if show.is_anime:
            try:
                anime = adba.Anime(None, name=show.name, tvdbid=show.tvdbid, autoCorrectName=True)
            except:
                continue
            else:
                if anime.name and anime.name != show.name:
                    anidb_mainNames[show.tvdbid] = [{anime.name:-1}]

    logger.log("anidb anime names: " + str(anidb_mainNames), logger.DEBUG)
    return anidb_mainNames


def _xem_excpetions_fetcher():
    exception_dict = {}
    opener = urllib2.build_opener()

    url = "http://thexem.de/map/allNames?origin=tvdb&seasonNumbers=1"
    try:
        f = opener.open(url)
    except (EOFError, IOError), e:
        logger.log(u"Unable to connect to XEM. Is thexem.de down ?" + ex(e), logger.ERROR)
        return exception_dict
    except httplib.InvalidURL, e:
        logger.log(u"Invalid XEM host. Is thexem.de down ?: " + ex(e), logger.ERROR)
        return exception_dict
    if not f:
        logger.log(u"Empty response from " + url + ": " + ex(e), logger.ERROR)
        return exception_dict
    try:
        xemJson = json.loads(f.read())
    except ValueError, e:
        pass

    if xemJson['result'] == 'failure':
        return exception_dict

    for tvdbid, names in xemJson['data'].items():
        exception_dict[int(tvdbid)] = names

    logger.log(u"xem exception dict: " + str(exception_dict), logger.DEBUG)
    return exception_dict


def getSceneSeasons(tvdb_id):
    """get a list of season numbers that have scene excpetions
    """
    myDB = db.DBConnection("cache.db")
    seasons = myDB.select("SELECT DISTINCT season FROM scene_exceptions WHERE tvdb_id = ?", [tvdb_id])
    return [cur_exception["season"] for cur_exception in seasons]


def buil_name_set():
    logger.log(u"Updating internal scene name cache", logger.MESSAGE)
    _excpetionDots = []
    global exception_tvdb
    exception_tvdb = {}

    for show in sickbeard.showList:
        for curSeason in [-1] + sickbeard.scene_exceptions.get_scene_seasons(show.tvdbid):
            exception_tvdb[helpers.full_sanitizeSceneName(show.name)] = show.tvdbid
            _excpetionDots.append(".")
            for name in get_scene_exceptions(show.tvdbid, season=curSeason):
                exception_tvdb[name] = show.tvdbid
                exception_tvdb[helpers.full_sanitizeSceneName(name)] = show.tvdbid
                _excpetionDots.append(".")

    logger.log(u"Updated internal scene name cache " + "".join(_excpetionDots), logger.MESSAGE)
    logger.log(u"Internal scene name cache set to: " + str(exception_tvdb), logger.DEBUG)


