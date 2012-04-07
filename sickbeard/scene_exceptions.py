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
import urllib, httplib
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

def get_scene_exceptions(tvdb_id):
    """
    Given a tvdb_id, return a list of all the scene exceptions.
    """
    global excpetionCache
    if tvdb_id not in excpetionCache:
        myDB = db.DBConnection("cache.db")
        exceptions = myDB.select("SELECT show_name FROM scene_exceptions WHERE tvdb_id = ?", [tvdb_id])
        exceptionsList = [cur_exception["show_name"] for cur_exception in exceptions]
        excpetionCache[tvdb_id] = exceptionsList
    else:
        exceptionsList = excpetionCache[tvdb_id]
    return exceptionsList

def get_scene_exception_by_name(show_name):
    """
    Given a show name, return the tvdbid of the exception, None if no exception
    is present.
    """

    myDB = db.DBConnection("cache.db")

    # try the obvious case first
    exception_result = myDB.select("SELECT tvdb_id FROM scene_exceptions WHERE LOWER(show_name) = ?", [show_name.lower()])
    if exception_result:
        return int(exception_result[0]["tvdb_id"])

    all_exception_results = myDB.select("SELECT show_name, tvdb_id FROM scene_exceptions")
    for cur_exception in all_exception_results:

        cur_exception_name = cur_exception["show_name"]
        cur_tvdb_id = int(cur_exception["tvdb_id"])

        if show_name.lower() in (cur_exception_name.lower(), sanitizeSceneName(cur_exception_name).lower().replace('.', ' ')):
            logger.log(u"Scene exception lookup got tvdb id " + str(cur_tvdb_id) + u", using that", logger.DEBUG)
            return cur_tvdb_id

    return None

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

    if not localOnly:
        xem_exceptions = _xem_excpetions_festcher(seasonOnly='all') # saesonOnly='all' means that only names that fit for all season are added and not season specific names
        for xem_ex_id in xem_exceptions: # xem json exceptions
            if xem_ex_id in exception_dict:
                exception_dict[xem_ex_id] = exception_dict[xem_ex_id] + xem_exceptions[xem_ex_id]
            else:
                exception_dict[xem_ex_id] = xem_exceptions[xem_ex_id]

    myDB = db.DBConnection("cache.db")

    changed_exceptions = False

    # write all the exceptions we got off the net into the database
    for cur_tvdb_id in exception_dict:

        # get a list of the existing exceptions for this ID
        existing_exceptions = [x["show_name"] for x in myDB.select("SELECT * FROM scene_exceptions WHERE tvdb_id = ?", [cur_tvdb_id])]

        for cur_exception in exception_dict[cur_tvdb_id]:
            # if this exception isn't already in the DB then add it
            if cur_exception not in existing_exceptions:
                myDB.action("INSERT INTO scene_exceptions (tvdb_id, show_name) VALUES (?,?)", [cur_tvdb_id, cur_exception])
                changed_exceptions = True

    # since this could invalidate the results of the cache we clear it out after updating
    if changed_exceptions:
        name_cache.clearCache()
        global excpetionCache
        excpetionCache = {}

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
        alias_list = [re.sub(r'\\(.)', r'\1', x) for x in re.findall(r"'(.*?)(?<!\\)',?", aliases)]

        exception_dict[tvdb_id] = alias_list
    return exception_dict

def _xem_excpetions_festcher(animeOnly=False, languageOnly=None, seasonOnly=None):
    exception_dict = {}
    opener = urllib2.build_opener()

    for show in sickbeard.showList:
        if show.is_anime or animeOnly == False:
            try:
                url = "http://thexem.de/map/names?origin=tvdb&id=%s" % str(show.tvdbid)
                f = opener.open(url)
            except (EOFError, IOError), e:
                logger.log(u"Unable to connect to SAB. Is thexem.de down ?" + ex(e), logger.ERROR)
                continue
            except httplib.InvalidURL, e:
                logger.log(u"Invalid XEM host. Is thexem.de down ?: " + ex(e), logger.ERROR)
                continue
            if not f:
                logger.log(u"Empty response from " + url + ": " + ex(e), logger.ERROR)
                continue
            try:
                xemJson = json.loads(f.read())
            except ValueError, e:
                pass

            if xemJson['result'] == 'failure':
                continue
            else:
                for season, languages in xemJson['data'].items():
                    if not (season == seasonOnly or seasonOnly == None):
                        continue

                    for language, names in languages.items():
                        if not (language == languageOnly or languageOnly == None):
                            continue

                        if show.tvdbid in exception_dict:
                            exception_dict[show.tvdbid] += names
                        else:
                            exception_dict[show.tvdbid] = names

    logger.log(u"xem exception dict: " + str(exception_dict), logger.DEBUG)
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
                    anidb_mainNames[show.tvdbid] = [anime.name]

    logger.log("anidb anime names: " + str(anidb_mainNames), logger.DEBUG)
    return anidb_mainNames


