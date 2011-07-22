

import cherrypy
import sqlite3
import tv
import sickbeard
from sickbeard import db
from common import *
import datetime
import webserve
from sickbeard import logger

try:
    import json
except ImportError:
    from lib import simplejson as json
    
class Api:
    
    """
        generic api will always return json
    """
    intent = 4
    
    @cherrypy.expose
    def default(self, *args, **kwargs):
        self.apiKey = "1234"
        apiKey = None
        if args: # if we have keyless vars we assume first one is the api key
            apiKey = args[0]
            args = args[1:] # remove the apikey from the args tuple
        
        if kwargs.get("key"):
            apiKey = kwargs.get("key")
            del kwargs["key"]
        
        # defauld is json ^^
        outputCallback = self._out_as_jason
        if kwargs.get("out") == "xml": # output xml can only be set with post/get
            outputCallback = self._out_as_xml
        
        if apiKey == self.apiKey:
            logger.log("api key '"+str(apiKey)+"' accepted",logger.DEBUG)
        else:
            logger.log("api key '"+str(apiKey)+"' NOT accepted",logger.DEBUG)
            return outputCallback(_error('Wrong API KEY'))
        
        outDict = call_dispatcher(args,kwargs) 
        return outputCallback(outDict)
    
    def _out_as_jason(self,dict):
        response = cherrypy.response
        response.headers['Content-Type'] = 'application/json'
        return json.dumps(dict, indent=self.intent)
    
    def _out_as_xml(self,dict):
        #TODO: implement
        return "implement me!"
    
dayofWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
intent = 4


def call_dispatcher(args, kwargs):
    
    logger.log("all args: '"+str(args)+"'",logger.DEBUG)
    logger.log("all kwargs '"+str(kwargs)+"'",logger.DEBUG)
    
    func = None
    if args:
        func = args[0]
        args = args[1:]
        
    if kwargs.get("func"):
        func = kwargs.get("func")
    
    if _functionMaper.get(func, False):
        outDict = _functionMaper.get(func)(args,kwargs)
    elif _is_int(func):
        outDict = id_url_wrapper(func,args,kwargs)        
    else:
        outDict = index(args,kwargs)
    
    return outDict


def index(args,kwargs):
    
    return {'sb_version': sickbeard.version.SICKBEARD_VERSION, 'api_version':0.1}


def shows(args,kwargs):
    # this garanties that order is either by the first args element
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


def getShow(id=None, ep=None, season=None, status=[], pure=False):
    if id == None:
        return _error("No show id given")
    if season and not _is_int(season):
            return _error("Season not parsable")

    show = sickbeard.helpers.findCertainShow(sickbeard.showList, int(id))
    if not show:
        return _error("Show not Found")

    showDict = {}
    episodes = {}
    if ep or season:
        episodes,sList,eCount = _get_episodes(id, season=season, status=status, pure=pure)
        showDict["episodes"] = episodes
    eUnused,sList,eCount = _get_episodes(id)
    
    showDict["season_list"] = sList
    showDict["episode_count"] = eCount
    
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
    
    return showDict


def getSeason(args, kwargs):
    sid,args = _check_params(args, kwargs, "sid", None)
    s,args = _check_params(args, kwargs, "s", None)
    
    if s and not _is_int(s):
        return _error("Season not parsable")

    episodes,sList,eCount = _get_episodes(sid,season=s)
    return episodes


def getEpisodes(args, kwargs):
    sid,args = _check_params(args, kwargs, "id", None)
    s,args = _check_params(args, kwargs, "s", None)
    status,args = _check_params(args, kwargs, "status", [])
    
    if s == "all":
        s = None
     
    if status:
        status = status.split(";")
    episodes,sList,eCount = _get_episodes(sid, season=s, status=status)
    
    return episodes
    

 
def getEpisode(args, kwargs):
    sid,args = _check_params(args, kwargs, "sid", None)
    s,args = _check_params(args, kwargs, "s", None)
    e,args = _check_params(args, kwargs, "e", None)
    x,args = _check_params(args, kwargs, "x", None)
    
    
    if x:
        try:
            tmpList = x.split("x")
            s = tmpList[0]
            e = tmpList[1]
        except:
            pass
    if s == "all":
        s = None

    myDB = db.DBConnection(row_type="dict")
    sqlResults = myDB.select( "SELECT * FROM tv_episodes WHERE showid = ? AND episode = ? AND season = ?", [sid,e,s])
    episode = {}
    if len(sqlResults) == 1:
        episode = _make_episode_nice(sqlResults[0])
    try:
        del episode["hastbn"]
        del episode["hasnfo"]
        del episode["episode_id"]
    except:
        pass
    return episode

def commingEpisodes(args,kwargs):
    sort,args = _check_params(args, kwargs, "sort", "date")
    
    if not sort in ["date","show","network"]:
        return '{"error":"Sort by '+sort+' not possible"}'
    
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

        airdate = datetime.date.fromordinal(int(ep["airdate"]))
        ep["airdate"] = str(airdate)
        ep["quality"] = _get_quality_string(ep["quality"])
        ep["weekday"] = dayofWeek[airdate.weekday()]
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
        return getShow(sid)

def _is_int(foo):
    try:
        int(foo)
    except:
        return False
    else:
        return True

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
    elif season:
        season = str(season)
        pure = True
        
    
    show = sickbeard.helpers.findCertainShow(sickbeard.showList, int(showId))
          
    myDB = db.DBConnection(row_type="dict")
    sqlResults = myDB.select( "SELECT * FROM tv_episodes WHERE showid = ? ORDER BY season*1000+episode DESC", [showId])
    episodes = {}
    episode_count = 0
    season_list = []
    for epResult in sqlResults:
        curSeason = str(epResult["season"])      
        if season and season != curSeason:
            continue

        epResult = _make_episode_nice(epResult)
        
        if status and not epResult["status"] in status:
            continue

        if pure:
            episodes[epResult["episode"]] = epResult
        else:   
            if not episodes.has_key(epResult["season"]):
                episodes[epResult["season"]] = {}
                season_list.append(curSeason)
            episodes[epResult["season"]][epResult["episode"]] = epResult
        
        if curSeason != 0:
            episode_count += 1
        
        # delete not needed fields
        epResult = _remove_clutter(epResult)
        #FIXME: this dosen't work
        try:
            epResult["location"] = epResult["location"].lstrip(show.location)
        except:
            pass
        
    return episodes, season_list, episode_count
    
def _make_episode_nice(epResult):
    epResult["status"] = statusStrings[epResult["status"]]
    epResult["airdate"] = str(datetime.date.fromordinal(int(epResult["airdate"])))
      
    return epResult

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
        if we have any values in args default becomes the first value
        this args element is then removed if remove = True
        if a value is in kwargs with key = key defauld becomes the value of that element with given key
        yes this might override the value allready set by the first args element
        kwargs overrides args ... period
        if none of the above is True default is send back
        and we send the new args back 
    """
    if args:
        default = args[0]
        if remove:
            logger.log("deleting first tuple element",logger.DEBUG)
            args = args[1:]
    if kwargs.get(key):
        default = kwargs.get(key)
    
    return default,args



_functionMaper = {"index":index,
                  "shows":shows,
                  "episodes":getEpisodes,
                  "episode":getEpisode,
                  "season":getSeason,
                  "future":commingEpisodes,
                  }
