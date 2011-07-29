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
    
    @cherrypy.expose
    def builder(self, *args, **kwargs):
        t = webserve.PageTemplate(file="apiBuilder.tmpl")
        #t.showList = sickbeard.showList

        def titler(x):
            if not x:
                return x
            if x.lower().startswith('a '):
                    x = x[2:]
            elif x.lower().startswith('the '):
                    x = x[4:]
            return x

        t.sortedShowList = sorted(sickbeard.showList, lambda x, y: cmp(titler(x.name), titler(y.name)))
        return webserve._munge(t)

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
    """calls the appropriate CMD class
        looks for a cmd in args and kwargs
        or calls the ShorthandWrapper when the first args element is a number
        it falls back to the index cmd
    """
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
        outDict = _functionMaper.get(cmd)(args,kwargs).run() 
    elif _is_int(cmd):
        outDict = ShorthandWrapper(args,kwargs,cmd).run() 
    else:
        outDict = CMDIndex(args,kwargs).run()

    return outDict

class ApiCall(object):
    _help = {"desc":"No help message available. Pleas tell the devs that a help msg is missing for this cmd"}
    
    def __init__(self, args, kwargs):
        # missing
        try:
            if self._missing:
                self.run = self.return_missing
        except AttributeError:
            pass
        # help
        if kwargs.has_key("help"):
            self.run = self.return_help

    def run(self):
        # override with real output function in subclass
        return {}

    def return_help(self):
        return self._help
    
    def return_missing(self):
        if len(self._missing) == 1:
            msg = "The required parameter: '" + self._missing[0] +"' was not set"
        else:
            msg = "The required parameters: '" + "','".join(self._missing) +"' where not set"
        return _error(msg)
    
    def check_params(self,args,kwargs,key,default,required=False):
        # TODO: explain this
        """
            this does the url shorthand magic
            and saves missing keys in self._missing
        """
        missing = True
        if args:
            default = args[0]
            missing = False
            args = args[1:]
        if kwargs.get(key):
            default = kwargs.get(key)
            missing = False
        if required:
            try:
                self._missing
            except AttributeError:
                self._missing = []
            if missing and key not in self._missing:
                self._missing.append(key)
        return default,args

class CMDIndex(ApiCall):
    _help = {"desc":"Display this Message"}
    def __init__(self,args,kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
        
    def run(self):
        return {'sb_version': sickbeard.version.SICKBEARD_VERSION, 'api_version':Api.version, "cmdOverview":"TODO"}


class CMDShows(ApiCall):
    _help = {"desc":"Display all Shows"}
    def __init__(self,args,kwargs):
        # required
        # optional
        self.sort,args = self.check_params(args, kwargs, "sort", "id")
        self.paused,args = self.check_params(args, kwargs, "paused", None)
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
           
    def run(self):
        shows = {}
        for show in sickbeard.showList:
            if self.paused and not self.paused == str(show.paused):
                continue
            showDict = {"paused":show.paused,
                        "quality":_get_quality_string(show.quality),
                        "language":show.lang,
                        "tvrage_id":show.tvrid,
                        "tvrage_name":show.tvrname}
            if self.sort == "show":
                showDict["tvdbid"] = show.tvdbid
                shows[show.name] = showDict
            else:
                showDict["show_name"] = show.name
                shows[show.tvdbid] = showDict
        return shows

class CMDShow(ApiCall):
    _help = {"requiredParameters":["tvdbid"],
             "desc":"Display Show information including episode statistics"}

    def __init__(self,args,kwargs):
        # required
        self.tvdbid,args = self.check_params(args, kwargs, "tvdbid", None, True)
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs) 
    
    def run(self):
        show = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not show:
            raise ApiError("Show not Found")
    
        showDict = {}
        showDict["season_list"] = CMDSeasonList((), {"tvdbid":self.tvdbid}).run()

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
        showDict["language"] = show.lang
        showDict["show_name"] = show.name
        showDict["paused"] = show.paused
        showDict["air_by_date"] = show.air_by_date
        showDict["season_folders"] = show.seasonfolders
        showDict["airs"] = show.airs
        showDict["tvrage_id"] = show.tvrid
        showDict["tvrage_name"] = show.tvrname

        return showDict

class CMDStats(ApiCall):
    _help = {"requiredParameters":["tvdbid"],
             "desc":"Display episodes statistcs for a given show"}

    def __init__(self, args, kwargs):
        # required
        self.tvdbid,args = self.check_params(args, kwargs, "tvdbid", None, False)
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
        
    def run(self):
        """this is sparta
            no realy this is crazy ... i don't even understand all of this
            and some is done by trial and error
            if anyone can or has the will to check this please do

            TODO: remove the seasonlist from this cmd
        """

        # show stats
        episode_status_counts_total = {}
        episode_status_counts_total["total"] = 0
        for status in statusStrings.statusStrings.keys():
            if status in [UNKNOWN,DOWNLOADED,SNATCHED,SNATCHED_PROPER]:
                continue
            episode_status_counts_total[status] = 0
        
        # add all the downloaded qualities
        episode_qualities_counts_download = {}
        episode_qualities_counts_download["total"] = 0
        for statusCode in Quality.DOWNLOADED:
            status, quality = Quality.splitCompositeStatus(statusCode)
            if quality in [Quality.NONE]:
                continue
            episode_qualities_counts_download[statusCode] = 0

        # add all snatched qualities
        episode_qualities_counts_snatch = {}
        episode_qualities_counts_snatch["total"] = 0
        for statusCode in Quality.SNATCHED + Quality.SNATCHED_PROPER:
            status, quality = Quality.splitCompositeStatus(statusCode)
            if quality in [Quality.NONE]:
                continue
            episode_qualities_counts_snatch[statusCode] = 0
    
        myDB = db.DBConnection(row_type="dict")
        sqlResults = myDB.select( "SELECT status,season FROM tv_episodes WHERE showid = ?", [self.tvdbid])
        # the main loop that goes through all episodes
        for row in sqlResults:
            status, quality = Quality.splitCompositeStatus(int(row["status"]))
            
            episode_status_counts_total["total"] += 1
            
            if status in Quality.DOWNLOADED:
                episode_qualities_counts_download["total"] += 1
                episode_qualities_counts_download[int(row["status"])] += 1
            
            elif status in Quality.SNATCHED+Quality.SNATCHED_PROPER:
                episode_qualities_counts_snatch["total"] += 1
                episode_qualities_counts_snatch[int(row["status"])] += 1
            else:
                episode_status_counts_total[status] += 1 
        
        # the outgoing container
        episodes_stats = {}
        episodes_stats["downloaded"] = {}
        # truning codes into strings
        for statusCode in episode_qualities_counts_download:
            if statusCode is "total":
                episodes_stats["downloaded"]["total"] = episode_qualities_counts_download[statusCode]
                continue
            status, quality = Quality.splitCompositeStatus(statusCode)
            statusString = Quality.qualityStrings[quality].lower().replace(" ","_").replace("(","").replace(")","")
            episodes_stats["downloaded"][statusString] = episode_qualities_counts_download[statusCode]
        
         
        episodes_stats["snatched"] = {}
        # truning codes into strings
        # and combining proper and normal
        for statusCode in episode_qualities_counts_snatch:
            if statusCode is "total":
                episodes_stats["snatched"]["total"] = episode_qualities_counts_snatch[statusCode]
                continue
            status, quality = Quality.splitCompositeStatus(statusCode)
            statusString = Quality.qualityStrings[quality].lower().replace(" ","_").replace("(","").replace(")","")
            if episodes_stats["snatched"].has_key(Quality.qualityStrings[quality]):
                episodes_stats["snatched"][statusString] += episode_qualities_counts_snatch[statusCode]
            else:
                episodes_stats["snatched"][statusString] = episode_qualities_counts_snatch[statusCode]

        #episodes_stats["total"] = {}
        for statusCode in episode_status_counts_total:
            if statusCode is "total":
                episodes_stats["total"] = episode_status_counts_total[statusCode]
                continue
            status, quality = Quality.splitCompositeStatus(statusCode)
            statusString = statusStrings.statusStrings[statusCode].lower().replace(" ","_").replace("(","").replace(")","")
            episodes_stats[statusString] = episode_status_counts_total[statusCode]
        
        return episodes_stats

class CMDSeasonList(ApiCall):
    def __init__(self, args, kwargs):
        # required
        self.tvdbid,args = self.check_params(args, kwargs, "tvdbid", None, True)
        # optional
        self.sort,args = self.check_params(args, kwargs, "sort", "desc") # "asc" and "desc" default and fallback is "desc"
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        myDB = db.DBConnection(row_type="dict")
        if self.sort == "asc":
            sqlResults = myDB.select( "SELECT DISTINCT season FROM tv_episodes WHERE showid = ? ORDER BY season ASC", [self.tvdbid])
        else:
            sqlResults = myDB.select( "SELECT DISTINCT season FROM tv_episodes WHERE showid = ? ORDER BY season DESC", [self.tvdbid])
        seasonList = [] # a list with all season numbers
        for row in sqlResults:
            seasonList.append(int(row["season"]))

        return seasonList

class CMDSeasons(ApiCall):
    def __init__(self, args, kwargs):
        # required
        self.tvdbid,args = self.check_params(args, kwargs, "tvdbid", None, True)
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
    
    def run(self):
        myDB = db.DBConnection(row_type="dict")
        sqlResults = myDB.select( "SELECT name,episode,airdate,status,season FROM tv_episodes WHERE showid = ?", [self.tvdbid])
        seasons = {}
        for row in sqlResults:
            row["status"] = statusStrings[row["status"]]
            row["airdate"] = _ordinal_to_dateForm(row["airdate"])
            curSeason = int(row["season"])
            curEpisode = int(row["episode"])
            del row["season"]
            del row["episode"]
            if not seasons.has_key(curSeason):
                seasons[curSeason] = {}
            seasons[curSeason][curEpisode] = row
        
        return seasons

class CMDSeason(ApiCall):
    
    def __init__(self, args, kwargs):
        # required
        self.tvdbid,args = self.check_params(args, kwargs, "tvdbid", None, True)
        self.season,args = self.check_params(args, kwargs, "season", None, True)
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        myDB = db.DBConnection(row_type="dict")
        sqlResults = myDB.select( "SELECT name, episode, airdate, status FROM tv_episodes WHERE showid = ? AND season = ?", [self.tvdbid,self.season])
        if len(sqlResults) is 0:
            raise ApiError("No season found")
        episodes = {}
        for row in sqlResults:
            curEpisode = int(row["episode"])
            del row["episode"]
            row["status"] = statusStrings[row["status"]]
            row["airdate"] = _ordinal_to_dateForm(row["airdate"])
            if not episodes.has_key(curEpisode):
                episodes[curEpisode] = {}
            episodes[curEpisode] = row
        return episodes

class CMDEpisode(ApiCall):
    _help = {"desc":"Get detailed info on a episode",
             "requiredParameters":{"tvdbid":"the tvdb id of the show",
                                   "season":"the season number",
                                   "episode":"the episode number"},
             }
    def __init__(self, args, kwargs):   
        # required
        self.tvdbid,args = self.check_params(args, kwargs, "tvdbid", None, True)
        self.s,args = self.check_params(args, kwargs, "season", None, True)
        self.e,args = self.check_params(args, kwargs, "episode", None, True)
        # optional
        self.fullPath,args = self.check_params(args, kwargs, "fullPath", "0")
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        myDB = db.DBConnection(row_type="dict")
        sqlResults = myDB.select( "SELECT name, description, airdate, status, location FROM tv_episodes WHERE showid = ? AND episode = ? AND season = ?", [self.tvdbid,self.e,self.s])
        if not len(sqlResults) == 1:
            raise ApiError("No episode found")
        episode = sqlResults[0]
        # handle path options
        # absolute vs relative vs broken
        showPath = None
        show = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        try:
            showPath = show.location
        except:
            pass
    
        if self.fullPath == "1" and showPath: # we get the full path by default so no need to change
            pass 
        elif self.fullPath and showPath:
            #i am using the length because lstrip removes to much
            showPathLength = len(showPath)+1 # the / or \ yeah not that nice i know
            episode["location"] = episode["location"][showPathLength:]
        elif not showPath: # show dir is broken ... episode path will be empty
            episode["location"] = ""
        # convert stuff to human form
        episode["airdate"] = _ordinal_to_dateForm(episode["airdate"])
        episode["status"] = _get_status_Strings(episode["status"])
        return episode

class CMDComingEpisodes(ApiCall):
    _help = {"desc":"Display comming episodes",
             "optionalPramameters":["sort"]}
    def __init__(self, args, kwargs): 
        # required
        # optional
        self.sort,args = self.check_params(args, kwargs, "sort", "date")
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
    def run(self):

        today = datetime.date.today().toordinal()
        next_week = (datetime.date.today() + datetime.timedelta(days=7)).toordinal()
        recently = (datetime.date.today() - datetime.timedelta(days=3)).toordinal()

        done_show_list = []
        qualList = Quality.DOWNLOADED + Quality.SNATCHED + [ARCHIVED, IGNORED]
        
        myDB = db.DBConnection(row_type="dict")
        sql_results = myDB.select("SELECT airdate,airs,episode,name AS 'ep_name',network,season,showid AS 'tvdbid',show_name, tv_shows.quality AS quality, tv_shows.status as show_status FROM tv_episodes, tv_shows WHERE season != 0 AND airdate >= ? AND airdate < ? AND tv_shows.tvdb_id = tv_episodes.showid AND tv_episodes.status NOT IN ("+','.join(['?']*len(qualList))+")", [today, next_week] + qualList)
        for cur_result in sql_results:
            done_show_list.append(int(cur_result["tvdbid"]))

        more_sql_results = myDB.select("SELECT airdate,airs,episode,name AS 'ep_name',network,season,showid AS 'tvdbid',show_name, tv_shows.quality AS quality, tv_shows.status as show_status FROM tv_episodes outer_eps, tv_shows WHERE season != 0 AND showid NOT IN ("+','.join(['?']*len(done_show_list))+") AND tv_shows.tvdb_id = outer_eps.showid AND airdate = (SELECT airdate FROM tv_episodes inner_eps WHERE inner_eps.showid = outer_eps.showid AND inner_eps.airdate >= ? ORDER BY inner_eps.airdate ASC LIMIT 1) AND outer_eps.status NOT IN ("+','.join(['?']*len(Quality.DOWNLOADED+Quality.SNATCHED))+")", done_show_list + [next_week] + Quality.DOWNLOADED + Quality.SNATCHED)
        sql_results += more_sql_results

        more_sql_results = myDB.select("SELECT airdate,airs,episode,name AS 'ep_name',network,season,showid AS 'tvdbid',show_name, tv_shows.quality AS quality, tv_shows.status as show_status FROM tv_episodes, tv_shows WHERE season != 0 AND tv_shows.tvdb_id = tv_episodes.showid AND airdate < ? AND airdate >= ? AND tv_episodes.status = ? AND tv_episodes.status NOT IN ("+','.join(['?']*len(qualList))+")", [today, recently, WANTED] + qualList)
        sql_results += more_sql_results


        # sort by air date
        sorts = {
            'date': (lambda x, y: cmp(int(x["airdate"]), int(y["airdate"]))),
            'show': (lambda a, b: cmp(a["show_name"], b["show_name"])),
            'network': (lambda a, b: cmp(a["network"], b["network"])),
        }

        #epList.sort(sorts[sort])
        sql_results.sort(sorts[self.sort])
        finalEpResults = []
        for ep in sql_results:
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
            finalEpResults.append(ep)
        return finalEpResults

class CMDHistory(ApiCall):
    def __init__(self, args, kwargs):
        # required
        # optional
        self.limit,args = self.check_params(args, kwargs, "limit", 100)
        self.type,args = self.check_params(args, kwargs, "type", None)
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        self.typeCodes = []
        if self.type == "downloaded":
            self.type = "Downloaded"
            self.typeCodes = Quality.DOWNLOADED
        elif self.type == "snatched":
            self.type = "Snatched"
            self.typeCodes = Quality.SNATCHED
        else:
            self.typeCodes = Quality.SNATCHED + Quality.DOWNLOADED
        
        
        myDB = db.DBConnection(row_type="dict")
    
        ulimit = min(int(self.limit), 100)
        if ulimit == 0:
            sqlResults = myDB.select("SELECT h.*, show_name FROM history h, tv_shows s WHERE h.showid=s.tvdb_id AND action in ("+','.join(['?']*len(self.typeCodes))+") ORDER BY date DESC",self.typeCodes )
        else:
            sqlResults = myDB.select("SELECT h.*, show_name FROM history h, tv_shows s WHERE h.showid=s.tvdb_id AND action in ("+','.join(['?']*len(self.typeCodes))+") ORDER BY date DESC LIMIT ?",self.typeCodes+[ ulimit ] )
        
        results = []
        for row in sqlResults:
            status, quality = Quality.splitCompositeStatus(int(row["action"]))
            status = _get_status_Strings(status)
            if self.type and not status == self.type:
                continue
            row["action"] = status
            row["quality"] = _get_quality_string(quality)
            row["date"] = _historyDate_to_dateForm(str(row["date"]))
            _rename_element(row, "showid", "tvdbid")
            results.append(row)
        return results

class CMDHelp(ApiCall):
    _help = {"desc":"Get help for a subject/cmd",
             "optionalPramameters":["subject"]}
    def __init__(self, args, kwargs):
        # required
        # optional
        self.subject,args = self.check_params(args, kwargs, "subject", "help")
        ApiCall.__init__(self, args, kwargs)
    def run(self):
        if _functionMaper.has_key(self.subject):
            msg = _functionMaper.get(self.subject)((),{"help":1}).run()
        else:
            msg = _error("no such cmd")
        return msg
        
################################
#     shorthand wrapper        #
################################
class ShorthandWrapper(ApiCall):
    _help = {"desc":"This is a internal function wrapper. To get help for a command call the command direclty"}
    def __init__(self, args, kwargs, sid):
        self.origArgs = args
        self.kwargs = kwargs
        self.sid = sid
        
        self.s,args = self.check_params(args, kwargs, "s", None)
        self.e,args = self.check_params(args, kwargs, "e", None)
        self.args = args
        
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        # how to add a var to a tuple
        # http://stackoverflow.com/questions/1380860/add-variables-to-tuple
        argstmp = (0,self.sid) # make a new tuple
        args = argstmp + self.origArgs # add both
        args = args[1:] # remove first fake element
        if self.e:
            return CMDEpisode(args, self.kwargs).run()
        elif self.s:
            if self.s == "all":
                return CMDSeasons(args, self.kwargs).run()
            else:    
                return CMDSeason(args, self.kwargs).run()
        else:
            return CMDShow(args, self.kwargs).run()


################################
#     helper functions         #
################################
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

def _ordinal_to_dateForm(ordinal):
    # workaround for episodes with no airdate
    if int(ordinal) != 1:
        date = datetime.date.fromordinal(ordinal)
    else:
        return ""
    return _convert_date_dateform(date,ordinal)

def _historyDate_to_dateForm(timeString):
    date = datetime.datetime.strptime(timeString,history.dateFormat)
    return _convert_date_dateform(date,timeString)

def _convert_date_dateform(date,raw):
    if not dateFormat or dateFormat == "raw":
        return raw
    return date.strftime(dateFormat)

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

_functionMaper = {"index":CMDIndex,
                  "shows":CMDShows,
                  "show":CMDShow,
                  "stats":CMDStats,
                  "seasonList":CMDSeasonList,
                  "season":CMDSeason,
                  "seasons":CMDSeasons,
                  "episode":CMDEpisode,
                  "future":CMDComingEpisodes,
                  "history":CMDHistory,
                  "help":CMDHelp
                  }

class ApiError(Exception):
    "Generic API error"

class IntParseError(Exception):
    "A value could not be parsed into a int. But should be parsable to a int "
