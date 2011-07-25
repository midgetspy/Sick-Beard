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
from sickbeard import db, logger, exceptions
from sickbeard.exceptions import ex
from common import *

try:
    import json
except ImportError:
    from lib import simplejson as json


dateFormat = ""
dayofWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
 
class Api:
    
    """
        generic api will always return json
    """
    intent = 4

    @cherrypy.expose
    def default(self, *args, **kwargs):
        
        
        self.apiKey = "1234"
        access,accessMsg,args,kwargs = self._grand_access(self.apiKey,args,kwargs)

        # set the output callback
        # default json
        outputCallback = self._out_as_jason

        # do we have acces ?
        if access:
            logger.log(accessMsg,logger.DEBUG)
        else:
            logger.log(accessMsg,logger.WARNING)
            return outputCallback(_error(accessMsg))
        
        # global dateForm
        # TODO: refactor dont change the module var all the time
        global dateFormat
        dateFormat = "%Y-%m-%d"
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
    
    def _out_as_jason(self,dict):
        response = cherrypy.response
        response.headers['Content-Type'] = 'application/json;charset=UTF-8'
        try:
            out = json.dumps(dict, indent=self.intent)
        except Exception, e: # if we fail to generate the output fake a error
            out = '{"error": "while composing output: "'+ex(e)+'"}'
        return out
    
  
    def _grand_access(self,realKey,args,kwargs):
        remoteIp = cherrypy.request.remote.ip
        
        
        apiKey = kwargs.get("apikey",None)
       
        if not apiKey:
            if args: # if we have keyless vars we assume first one is the api key
                apiKey = args[0]
                args = args[1:] # remove the apikey from the args tuple
        else:
            del kwargs["apikey"]

     
        if apiKey == realKey:
            msg = "Api key accepted. ACCESS GRANTED"
            return True, msg, args, kwargs
        elif not apiKey:
            msg = "NO api key given by '"+remoteIp+"'. ACCESS DENIED"
            return False, msg, args, kwargs
        else:
            msg = "Api key '"+str(apiKey)+"' given by '"+remoteIp+"' NOT accepted. ACCESS DENIED"
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
        outDict = index(args,kwargs)
    
    return outDict


def index(args,kwargs):
    
    return {'sb_version': sickbeard.version.SICKBEARD_VERSION, 'api_version':0.1}


def shows(args,kwargs):
    # this qgranties that order is either by the first args element
    # or by the the kwargs value with the key "order"
    # it will default to "id"
    # if we found a args element the first element is removed !!
    order,args = _check_params(args, kwargs, "order", "id")
    # one args element is gone so the next one should be onlyActive
    onlyActive,args = _check_params(args, kwargs, "onlyActive", None)
    # you will see this pattern in all function that can called directly
    
    shows = {}
    for show in sickbeard.showList:
        if onlyActive and show.paused:
            continue
        
        showDict = {"paused":show.paused,"quality":_get_quality_string(show.quality),"language":show.lang}
        if order == "name":
            showDict["tvdbid"] = show.tvdbid
            shows[show.name] = showDict
        else:
            showDict["name"] = show.name
            shows[show.tvdbid] = showDict
    
    showsSorted = {}
    for key in sorted(shows.iterkeys()):
        showsSorted[key] = shows[key]
        
    return showsSorted


def getShow(args, kwargs):
    id,args = _check_params(args, kwargs, "id", None)
    season,args = _check_params(args, kwargs, "season", None)
    status,args = _check_params(args, kwargs, "status", [])
    
    
    if id == None:
        raise ApiError("No show id given")

    show = sickbeard.helpers.findCertainShow(sickbeard.showList, int(id))
    if not show:
        raise ApiError("Show not Found")

    showDict = {}
    _episodes = {}
    if season:
        _episodes,episodeCounts,sList = _get_episodes(id, season=season, status=status) #@UnsusedVariable
        showDict["episodes"] = _episodes
    else:
        _episodes,episodeCounts,sList = _get_episodes(id)
    
    showDict["season_list"] = sList
    showDict["episode_stats"] = episodeCounts
    
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
    sid,args = _check_params(args, kwargs, "sid", None)
    s,args = _check_params(args, kwargs, "s", None)
    
    episodes,episodeCounts,sList = _get_episodes(sid,season=s)
    
    return episodes


def getEpisodes(args, kwargs):
    sid,args = _check_params(args, kwargs, "id", None)
    s,args = _check_params(args, kwargs, "s", None)
    status,args = _check_params(args, kwargs, "status", [])
    
    if status:
        status = status.split(";")
    episodes,sList,eCount = _get_episodes(sid, season=s, status=status)
    
    return episodes
    

 
def getEpisode(args, kwargs):
    sid,args = _check_params(args, kwargs, "sid", None)
    s,args = _check_params(args, kwargs, "s", None)
    e,args = _check_params(args, kwargs, "e", None)
    x,args = _check_params(args, kwargs, "x", None) # do we need this ?
    fullPath,args = _check_params(args, kwargs, "fullPath", False)

    if x:
        try:
            tmpList = x.split("x")
            s = tmpList[0]
            e = tmpList[1]
        except:
            pass
    if s == "all":
        s = None
    
    _is_int_multi(sid,e,s)
    
    show = sickbeard.helpers.findCertainShow(sickbeard.showList, int(sid))
    
    myDB = db.DBConnection(row_type="dict")
    sqlResults = myDB.select( "SELECT * FROM tv_episodes WHERE showid = ? AND episode = ? AND season = ?", [sid,e,s])
    episode = {}
    if len(sqlResults) == 1:
        episode = _make_episode_nice(sqlResults[0])
    else:
        raise ApiError("No episode found")
    
    # delete unneeded info
    try:
        del episode["hastbn"]
        del episode["hasnfo"]
        del episode["episode_id"]
    except:
        pass
    
    # handle path options
    # absolute vs relative vs broken
    showPath = None
    try:
        showPath = show.location
    except exceptions.NoNFOException:
        pass
    if not fullPath and showPath:
        #i am using the length because lstrip does remove to much
        showPathLength = len(showPath)+1 # the / or \ yeah not that nice i know
        episode["location"] = episode["location"][showPathLength:]
    elif not showPath: # show dir is broken ... episode path will be empty
        episode["location"] = ""
    elif fullPath and showPath: # we get the full path by default so no need to change
        pass
    
    # rename
    episode = _rename_element(episode,"sid","show_tvdbid")
    episode = _rename_element(episode,"tvdbid","ep_tvdbid")
    
    

    return episode

def commingEpisodes(args,kwargs):
    sort,args = _check_params(args, kwargs, "sort", "date")
    
    if not sort in ["date","show","network"]:
        return _error("Sort by '"+sort+"' not possible")
    
    epResults,today,next_week = webserve.WebInterface.commingEpisodesRaw(sort=sort ,row_type="dict")
    finalEpResults = {}
    count = 0
    for ep in epResults:

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
        del ep["genre"]
        del ep["episode_id"]
        del ep["lang"]
        del ep["tvdbid"]
        del ep["tvr_id"]
        del ep["startyear"]
        del ep["seasonfolders"]
        del ep["show_id"]
        
        finalEpResults[count] = _remove_clutter(ep)
        count += 1
       
    return finalEpResults


def id_url_wrapper(sid,args,kwargs):
    origArgs = args
    logger.log("args "+str(args),logger.DEBUG)
    s,args = _check_params(args, kwargs, "s", None)
    e,args = _check_params(args, kwargs, "e", None)
    x,args = _check_params(args, kwargs, "x", None)
    # how to add a var to a tuple
    # http://stackoverflow.com/questions/1380860/add-variables-to-tuple
    argstmp = (0,sid) # make a new tuple
    args = argstmp + origArgs # add both
    args = args[1:] # remove first fake element
    logger.log("args "+str(args),logger.DEBUG)
    if e or x:
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
    except ValueError:
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
    return qualityString

def _get_episodes(showId,season=None,status=[]):
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
              
    myDB = db.DBConnection(row_type="dict")
    sqlResults = myDB.select( "SELECT * FROM tv_episodes WHERE showid = ? ORDER BY season*1000+episode DESC", [showId])
    episodes = {} # will contain all episodes that selected
    
    # show stats
    all_count = 0 # all episodes
    loaded_count = 0
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
        

        epResult = _make_episode_nice(epResult)
        
        # add the specific status like "Downloaded (HDTV)"
        if not episode_status_counts.has_key(epResult["status"]):
            episode_status_counts[epResult["status"]] = 0
        episode_status_counts[epResult["status"]] += 1
            
        if season and season != curSeason:
            continue

        # skip episodes that dont match the status filter
        if status and not epResult["status"] in status:
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
        epResult = _add_prefix(epResult,"ep_","tvdbid")
        epResult = _add_prefix(epResult,"ep_","airdate")

    episodes_stats = {}
    for episode_status_count in episode_status_counts:
        episodes_stats[episode_status_count] = episode_status_counts[episode_status_count]

    episodes_stats["All"] = all_count
    episodes_stats["Downloaded"] = loaded_count

    return episodes, episodes_stats, season_list
    
def _make_episode_nice(epResult):
    epResult["status"] = statusStrings[epResult["status"]]
    epResult["airdate"] = _ordinal_to_dateForm(int(epResult["airdate"]))
    
    return epResult

def _add_prefixs(epResult,prefix):
    for key in epResult:
        epResult = _add_prefix(epResult, prefix, key)
    
    return epResult

def _add_prefix(epResult,prefix,key):
    try:
        if key.find(prefix) < 0:
            epResult[prefix+key] = epResult[key]
            del epResult[key]
    except KeyError:
        pass  
    return epResult

def _ordinal_to_dateForm(ordinal):
    airdate = datetime.date.fromordinal(ordinal)
    if not dateFormat or dateFormat == "ordinal":
        return ordinal
    return airdate.strftime(dateFormat)
    
    
def _remove_clutter(epResult):
    del epResult["showid"]
    del epResult["description"]
    del epResult["location"]
    del epResult["hastbn"]
    del epResult["hasnfo"]
    
    del epResult["episode"]
    del epResult["season"]
    
    return epResult


def _check_params(args,kwargs,key,default,remove=True):
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
    if args:
        default = args[0]
        if remove:
            args = args[1:]
    if kwargs.get(key):
        default = kwargs.get(key)
    
    return default,args



_functionMaper = {"index":index,
                  "show":getShow,
                  "shows":shows,
                  "episodes":getEpisodes,
                  "episode":getEpisode,
                  "season":getSeason,
                  "future":commingEpisodes,
                  }

class ApiError(Exception):
    "Generic API error"

class IntParseError(Exception):
    "A value could not be parsed into a int. But should be parsable to a int "
