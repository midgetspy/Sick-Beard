# Author: Dennis Lutter <lad1337@gmail.com>
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

import datetime
import cherrypy
import sickbeard
import webserve
from sickbeard import db, logger, exceptions, history
from sickbeard.exceptions import ex
from common import *

try:
    import json
except ImportError:
    from lib import simplejson as json


_dateFormat = "%Y-%m-%d %H:%M"
dateFormat = ""
dayofWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
 
class Api:
    """
        generic api will always return json
    """
    version = 0.1 
    intent = 4

    @cherrypy.expose
    def default(self, *args, **kwargs):

        self.apiKey = "1234"
        access,accessMsg,args,kwargs = self._grand_access(self.apiKey,args,kwargs)

        # set the output callback
        # default json
        outputCallback = self._out_as_json

        # do we have acces ?
        if access:
            logger.log(accessMsg,logger.DEBUG)
        else:
            logger.log(accessMsg,logger.WARNING)
            return outputCallback(_error(accessMsg))

        # global dateForm
        # TODO: refactor dont change the module var all the time
        global dateFormat
        dateFormat = _dateFormat
        if kwargs.has_key("dateForm"):
            dateFormat = str(kwargs["dateForm"])
            del kwargs["dateForm"]


        # set the original call_dispatcher as the local _call_dispatcher
        _call_dispatcher = call_dispatcher
        # if profile was set wrap "_call_dispatcher" in the profile function
        if kwargs.has_key("profile"):
            from lib.profilehooks import profile
            _call_dispatcher = profile(_call_dispatcher,immediate=True)
            del kwargs["profile"]

        # if debug was set call the "call_dispatcher"
        if kwargs.has_key("debug"):
            outDict = _call_dispatcher(args,kwargs) # this way we can debug the cherry.py traceback in the browser
            del kwargs["debug"]
        else:# if debug was not set we wrap the "call_dispatcher" in a try block to assure a json output
            try:
                outDict = _call_dispatcher(args,kwargs)
            except Exception, e:
                logger.log("API: "+ex(e),logger.ERROR)
                outDict = _error(ex(e))

        return outputCallback(outDict)


    def _out_as_json(self,dict):
        response = cherrypy.response
        response.headers['Content-Type'] = 'application/json;charset=UTF-8'
        try:
            out = json.dumps(dict, indent=self.intent, sort_keys=True)
        except Exception, e: # if we fail to generate the output fake a error
            out = '{"error": "while composing output: "'+ex(e)+'"}'
        return out


    def _grand_access(self,realKey,args,kwargs):
        remoteIp = cherrypy.request.remote.ip

        apiKey = kwargs.get("apikey",None)

        if not apiKey:
            # this also checks if the length of the first element
            # is the length of the realKey .. it is nice but will through the error "no key" even if you miss one char 
            # if args and len(args[0]) == len(realKey):
            if args: # if we have keyless vars we assume first one is the api key
                apiKey = args[0]
                args = args[1:] # remove the apikey from the args tuple
        else:
            del kwargs["apikey"]


        if apiKey == realKey:
            msg = u"Api key accepted. ACCESS GRANTED"
            return True, msg, args, kwargs
        elif not apiKey:
            msg = u"NO api key given by '"+remoteIp+"'. ACCESS DENIED"
            return False, msg, args, kwargs
        else:
            msg = u"Api key '"+apiKey+"' given by '"+remoteIp+"' NOT accepted. ACCESS DENIED"
            return False, msg, args, kwargs


def call_dispatcher(args, kwargs):
    logger.log("api: all args: '"+str(args)+"'",logger.DEBUG)
    logger.log("api: all kwargs: '"+str(kwargs)+"'",logger.DEBUG)
    logger.log("api: dateFormat: '"+str(dateFormat)+"'",logger.DEBUG)

    cmd = None
    if args:
        cmd = args[0]
        args = args[1:]

    if kwargs.get("cmd"):
        cmd = kwargs.get("cmd")

    if _functionMaper.get(cmd, False):
        outDict = _functionMaper.get(cmd)(args,kwargs)
    elif _is_int(cmd):
        outDict = id_url_wrapper(cmd,args,kwargs)        
    else:
        outDict = getIndex(args,kwargs)

    return outDict


def getIndex(args,kwargs):
    return {'sb_version': sickbeard.version.SICKBEARD_VERSION, 'api_version':Api.version}


def getShows(args,kwargs):
    # this qgranties that order is either by the first args element
    # or by the the kwargs value with the key "order"
    # it will default to "id"
    # if we found a args element the first element is removed !!
    order,args,missing = _check_params(args, kwargs, "order", "id")
    # one args element is gone so the next one should be paused
    paused,args,missing = _check_params(args, kwargs, "paused", None, missing)
    # you will see this pattern in all function that can called directly


    shows = {}
    for show in sickbeard.showList:
        if paused and not paused == str(show.paused):
            continue

        showDict = {"paused":show.paused,"quality":_get_quality_string(show.quality),"language":show.lang}
        if order == "name":
            showDict["tvdbid"] = show.tvdbid
            shows[show.name] = showDict
        else:
            showDict["name"] = show.name
            shows[show.tvdbid] = showDict

    return shows


def getShow(args, kwargs):
    tvdbid,args,missing = _check_params(args, kwargs, "tvdbid", None, [])
    if missing:
        return _missing_param(missing)
    season,args,missing = _check_params(args, kwargs, "season", None)
    status,args,missing = _check_params(args, kwargs, "status", [])


    show = sickbeard.helpers.findCertainShow(sickbeard.showList, int(tvdbid))
    if not show:
        raise ApiError("Show not Found")

    showDict = {}
    _episodes = {}
    if season:
        _episodes,episodeCounts,sList = _get_episodes(tvdbid, season=season, status=status) #@UnsusedVariable
        showDict["episodes"] = _episodes
    else:
        _episodes,episodeCounts,sList = _get_episodes(tvdbid)

    showDict["season_list"] = sList
    showDict["stats"] = episodeCounts

    genreList = []
    if show.genre:
        genreListTmp = show.genre.split("|")
        for genre in genreListTmp:
            if genre:
                genreList.append(genre)
    showDict["genre"] = genreList
    showDict["quality"] = _get_quality_string(show.quality)

    try:
        showDict["location"] = show.location
    except:
        showDict["location"] = ""

    # easy stuff
    showDict["name"] = show.name
    showDict["tvrage_name"] = show.tvrname
    showDict["paused"] = show.paused
    showDict["air_by_date"] = show.air_by_date
    showDict["seasonfolders"] = show.seasonfolders
    showDict["airs"] = show.airs

    return showDict


def getSeason(args, kwargs):
    tvdbid,args,missing = _check_params(args, kwargs, "tvdbid", None, [])
    s,args,missing = _check_params(args, kwargs, "s", None, missing)
    if missing:
        return _missing_param(missing)
    episodes,episodes_stats, season_list = _get_episodes(tvdbid,season=s)
    
    return episodes


def getEpisodes(args, kwargs):
    tvdbid,args,missing = _check_params(args, kwargs, "tvdbid", None, [])
    s,args,missing = _check_params(args, kwargs, "s", None, missing)
    if missing:
        return _missing_param(missing)
    status,args,missing = _check_params(args, kwargs, "status", [])

    if status:
        status = status.split(",")
    episodes,episodes_stats, season_list = _get_episodes(tvdbid, season=s, status=status)

    return episodes


def getEpisode(args, kwargs):
    tvdbid,args,missing = _check_params(args, kwargs, "tvdbid", None, [])
    s,args,missing = _check_params(args, kwargs, "s", None, missing)
    e,args,missing = _check_params(args, kwargs, "e", None, missing)
    if missing:
        return _missing_param(missing)
    fullPath,args,missing = _check_params(args, kwargs, "fullPath", "0")

    if s == "all":
        s = None

    _is_int_multi(tvdbid,e,s)

    show = sickbeard.helpers.findCertainShow(sickbeard.showList, int(tvdbid))

    myDB = db.DBConnection(row_type="dict")
    #sqlResults = myDB.select( "SELECT showid AS 'tvdbid', tvdbid AS 'ep_tvdbid', name, season, episode, description, airdate AS 'ep_airdate', status, location FROM tv_episodes WHERE showid = ? AND episode = ? AND season = ?", [tvdbid,e,s])
    sqlResults = myDB.select( "SELECT * FROM tv_episodes WHERE showid = ? AND episode = ? AND season = ?", [tvdbid,e,s])
    episode = {}
    if len(sqlResults) == 1:
        episode = _make_episode_nice(sqlResults[0])
    else:
        raise ApiError("No episode found")

    # delete unneeded info
    del episode["hastbn"]
    del episode["hasnfo"]
    del episode["episode_id"]
    del episode["tvdbid"]

    # handle path options
    # absolute vs relative vs broken
    showPath = None
    try:
        showPath = show.location
    except:
        pass

    if fullPath == "1" and showPath: # we get the full path by default so no need to change
        pass 
    elif fullPath and showPath:
        #i am using the length because lstrip removes to much
        showPathLength = len(showPath)+1 # the / or \ yeah not that nice i know
        episode["location"] = episode["location"][showPathLength:]
    elif not showPath: # show dir is broken ... episode path will be empty
        episode["location"] = ""
    
    # rename
    episode = _rename_element(episode,"showid","tvdbid")


    return episode

def getComingEpisodes(args,kwargs):
    sort,args,missing = _check_params(args, kwargs, "sort", "date")

    if not sort in ["date","show","network"]:
        return _error("Sort by '"+sort+"' not possible")

    epResults,today,next_week = webserve.WebInterface.commingEpisodesRaw(sort=sort ,row_type="dict")
    finalEpResults = []
    for ep in epResults:
        """
            Missed:   yesterday... (less than 1week)
            Today:    today
            Soon:     tomorrow till next week
            Later:    later than next week
        """
        if ep["airdate"] < today:
            ep["status"] = "Missed"
        elif ep["airdate"] >= next_week:
            ep["status"] = "Later"
        elif ep["airdate"] >= today and ep["airdate"] < next_week:
            if ep["airdate"] == today:
                ep["status"] = "Today"
            else:
                ep["status"] = "Soon"
        ordinalAirdate = int(ep["airdate"])
        ep["airdate"] = _ordinal_to_dateForm(ordinalAirdate)
        ep["quality"] = _get_quality_string(ep["quality"])
        ep["weekday"] = dayofWeek[datetime.date.fromordinal(ordinalAirdate).weekday()]
        
        _rename_element(ep, "show_id", "tvdbid")
        del ep["genre"]
        del ep["episode_id"]
        del ep["lang"]
        del ep["tvdbid"]
        del ep["tvr_id"]
        del ep["startyear"]
        del ep["seasonfolders"]
        
        finalEpResults.append(_remove_clutter(ep))


    return finalEpResults


def getHistory(args,kwargs):
    limit,args,missing = _check_params(args, kwargs, "limit", 100)
    type,args,missing = _check_params(args, kwargs, "type", None)

    #_is_int_multi(limit)

    if type == "downloaded":
        type = "Downloaded"
    elif type == "snatched":
        type = "Snatched"

    myDB = db.DBConnection(row_type="dict")

    ulimit = min(int(limit), 100)
    if ulimit == 0:
        sqlResults = myDB.select("SELECT h.*, show_name FROM history h, tv_shows s WHERE h.showid=s.tvdb_id ORDER BY date DESC" )
    else:
        sqlResults = myDB.select("SELECT h.*, show_name FROM history h, tv_shows s WHERE h.showid=s.tvdb_id ORDER BY date DESC LIMIT ?",[ ulimit ] )

    results = []
    for row in sqlResults:
        status, quality = Quality.splitCompositeStatus(int(row["action"]))
        status = _get_status_Strings(status)
        if type and not status == type:
            continue
        row["action"] = status
        row["quality"] = _get_quality_string(quality)
        row["date"] = _historyDate_to_dateForm(str(row["date"]))
        _rename_element(row, "showid", "tvdbid")
        results.append(row)
    return results


def id_url_wrapper(sid,args,kwargs):
    origArgs = args
    logger.log("args "+str(args),logger.DEBUG)
    s,args,missing = _check_params(args, kwargs, "s", None)
    e,args,missing = _check_params(args, kwargs, "e", None)
    # how to add a var to a tuple
    # http://stackoverflow.com/questions/1380860/add-variables-to-tuple
    argstmp = (0,sid) # make a new tuple
    args = argstmp + origArgs # add both
    args = args[1:] # remove first fake element
    logger.log("args "+str(args),logger.DEBUG)
    if e:
        return getEpisode(args, kwargs)
    elif s:
        if s == "all":
            return getEpisodes(args, kwargs)
        else:    
            return getSeason(args, kwargs)
    else:
        return getShow(args, kwargs)


def _is_int(foo):
    try:
        int(foo)
    except:
        return False
    else:
        return True

def _is_int_multi(*vars):
    for var in vars:
        if var and not _is_int(var):
            raise IntParseError("'" +var + "' is not parsable into a int, but is supposed to be. Canceling")
    return True


def _rename_element(dict,oldKey,newKey):
    try:
        dict[newKey] = dict[oldKey]
        del dict[oldKey]
    except:
        pass
    return dict


def _error(msg):
    return {'error':msg}


def _get_quality_string(q):
    qualityString = "Custom"
    if q in qualityPresetStrings:
        qualityString = qualityPresetStrings[q]
    elif q in Quality.qualityStrings:
        qualityString = Quality.qualityStrings[q]
    return qualityString


def _get_status_Strings(s):
    return statusStrings[s]

def _missing_param(missingList):
    if len(missingList) == 1:
        msg = "The required parameter: " + missingList[0] +" was not set"
    else:
        msg = "The required parameters: " + ",".join(missingList) +" where not set"
    return _error(msg)


def _get_episodes(tvdbid,season=None,status=[]):
    """
        create a dictonary containing episode dicts
        if season only given season will be returned 
        if pure there is no season container around the episodes
        if status only gets episodes that have the a status in status
    """

    pure = False
    if season == "all":
        season = None

    _is_int_multi(season)

    if season:
        season = int(season)
        pure = True

    status = _replace_statusStrings_with_statusCodes(status)


    myDB = db.DBConnection(row_type="dict")
    #sqlResults = myDB.select( "SELECT episode_id, tvdbid AS 'ep_tvdbid', name, season, episode, airdate AS 'ep_airdate', status FROM tv_episodes WHERE showid = ? ORDER BY season*1000+episode DESC", [tvdbid])
    sqlResults = myDB.select( "SELECT * FROM tv_episodes WHERE showid = ? ORDER BY season*1000+episode DESC", [tvdbid])
    episodes = {} # will contain all episodes that selected

    # show stats
    all_count = 0 # all episodes
    loaded_count = 0
    snatched_count = 0
    season_list = [] # a list with all season numbers

    episode_status_counts = {}
    # add the default status
    for statusString in statusStrings.statusStrings:
        episode_status_counts[statusStrings[statusString]] = 0

    # loop through ALL episodes of show
    for epResult in sqlResults:
        
        curSeason = int(epResult["season"])  
        if curSeason != 0:
            all_count += 1
            if epResult["status"] in Quality.DOWNLOADED:
                loaded_count += 1
            elif epResult["status"] in Quality.SNATCHED:
                snatched_count += 1

        # skip episodes that dont match the status filter
        if status and not epResult["status"] in status:
            continue

        epResult = _make_episode_nice(epResult)

        # add the specific status like "Downloaded (HDTV)"
        if not episode_status_counts.has_key(epResult["status"]):
            episode_status_counts[epResult["status"]] = 0
        episode_status_counts[epResult["status"]] += 1

        if season and season != curSeason:
            continue

        # pure is true if we only requested one season
        if pure:
            episodes[epResult["episode"]] = epResult
        else:
            # do we have the season container already
            if not episodes.has_key(epResult["season"]):
                episodes[epResult["season"]] = {}
                season_list.append(curSeason)
            # add the episode to the season container
            episodes[epResult["season"]][epResult["episode"]] = epResult

        # delete not needed fields
        epResult = _remove_clutter(epResult)
        # give ambiguous fields a prefix
        del epResult["tvdbid"]

    episodes_stats = {}
    for episode_status_count in episode_status_counts:
        episodes_stats[episode_status_count] = episode_status_counts[episode_status_count]

    episodes_stats["Total"] = all_count
    episodes_stats["Downloaded"] = loaded_count
    episodes_stats["Snatched"] = loaded_count

    return episodes, episodes_stats, season_list


def _make_episode_nice(epResult):
    epResult["status"] = statusStrings[epResult["status"]]
    epResult["airdate"] = _ordinal_to_dateForm(int(epResult["airdate"]))

    return epResult


def _ordinal_to_dateForm(ordinal):
    date = datetime.date.fromordinal(ordinal)
    return _convert_date_dateform(date,ordinal)


def _historyDate_to_dateForm(timeString):
    date = datetime.datetime.strptime(timeString,history.dateFormat)
    return _convert_date_dateform(date,timeString)


def _convert_date_dateform(date,raw):
    if not dateFormat or dateFormat == "raw":
        return raw
    return date.strftime(dateFormat)


def _remove_clutter(epResult):
    del epResult["showid"]
    del epResult["description"]
    del epResult["location"]
    del epResult["hastbn"]
    del epResult["hasnfo"]
    del epResult["episode_id"]

    del epResult["episode"]
    del epResult["season"]

    return epResult


def _replace_statusStrings_with_statusCodes(statusStrings):
    statusCodes = []
    if "snatched" in statusStrings:
        statusCodes += Quality.SNATCHED
    if "downloaded" in statusStrings:
        statusCodes += Quality.DOWNLOADED
    if "skipped" in statusStrings:
        statusCodes.append(SKIPPED)
    if "wanted" in statusStrings:
        statusCodes.append(WANTED)
    if "archived" in statusStrings:
        statusCodes.append(ARCHIVED)
    if "ignored" in statusStrings:
        statusCodes.append(IGNORED)
    if "unaired" in statusStrings:
        statusCodes.append(UNAIRED)
    return statusCodes


def _check_params(args,kwargs,key,default,missingList=[],remove=True):
    """
        this will return a tuple of mixed and mixed
        if we have any values in args default becomes the first value we find in args
        this args element is then removed if remove = True
        if a value is in kwargs with key = key defauld becomes the value of that element with given key
        yes this might override the value already set by the first args element
        kwargs overrides args ... period
        if none of the above is True default is send back
        and we send the new args back 
    """
    missing = True
    if args:
        default = args[0]
        missing = False
        if remove:
            args = args[1:]
    if kwargs.get(key):
        default = kwargs.get(key)
        missing = False
    if missing:
        missingList.append(key)
    return default,args,missingList


_functionMaper = {"index":getIndex,
                  "show":getShow,
                  "shows":getShows,
                  "episodes":getEpisodes,
                  "episode":getEpisode,
                  "season":getSeason,
                  "future":getComingEpisodes,
                  "history":getHistory,
                  }

class ApiError(Exception):
    "Generic API error"

class IntParseError(Exception):
    "A value could not be parsed into a int. But should be parsable to a int "
