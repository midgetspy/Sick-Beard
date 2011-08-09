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

import os.path
import time
import datetime
import threading

import cherrypy
import sickbeard
import webserve
from sickbeard import db, logger, exceptions, history
from sickbeard.exceptions import ex
from sickbeard import encodingKludge as ek
from sickbeard import search_queue
from common import *

try:
    import json
except ImportError:
    from lib import simplejson as json


_dateFormat = "%Y-%m-%d %H:%M"
dateFormat = ""
dayofWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
 
class Api:
    """ api class that returns json results """
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

        def titler(x):
            if not x:
                return x
            if x.lower().startswith('a '):
                    x = x[2:]
            elif x.lower().startswith('the '):
                    x = x[4:]
            return x

        t.sortedShowList = sorted(sickbeard.showList, lambda x, y: cmp(titler(x.name), titler(y.name)))

        myDB = db.DBConnection(row_type="dict")
        seasonSQLResults = {}
        episodeSQLResults = {}

        for curShow in t.sortedShowList:
            seasonSQLResults[curShow.tvdbid] = myDB.select("SELECT DISTINCT season FROM tv_episodes WHERE showid = ? ORDER BY season DESC", [curShow.tvdbid])

        for curShow in t.sortedShowList:
            episodeSQLResults[curShow.tvdbid] = myDB.select("SELECT DISTINCT season,episode FROM tv_episodes WHERE showid = ? ORDER BY season DESC, episode DESC", [curShow.tvdbid])

        t.seasonSQLResults = seasonSQLResults
        t.episodeSQLResults = episodeSQLResults
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
        """ validate api key and log result """
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
    """ calls the appropriate CMD class
        looks for a cmd in args and kwargs
        or calls the TVDBShorthandWrapper when the first args element is a number
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
        outDict = TVDBShorthandWrapper(args,kwargs,cmd).run() 
    else:
        outDict = CMD_SickBeard(args,kwargs).run()

    return outDict

class ApiCall(object):
    _help = {"desc":"No help message available. Please tell the devs that a help msg is missing for this cmd"}
    
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
        try:
            if self._requiredParams:
                pass
        except AttributeError:
            self._requiredParams = []
        try:
            if self._optionalParams:
                pass
        except AttributeError:
            self._optionalParams = []

        for list,type in [(self._requiredParams,"requiredParameters"),
                          (self._optionalParams,"optionalPramameters")]:
            if self._help.has_key(type):
                for key in list:
                    if self._help[type].has_key(key):
                        continue
                    self._help[type][key] = "no description"
            elif list:
                for key in list:
                    self._help[type] = {}
                    self._help[type][key] = "no description"
            else:
                self._help[type] = {}

        return self._help
    
    def return_missing(self):
        if len(self._missing) == 1:
            msg = "The required parameter: '" + self._missing[0] +"' was not set"
        else:
            msg = "The required parameters: '" + "','".join(self._missing) +"' where not set"
        return _error(msg)
    
    def check_params(self,args,kwargs,key,default,required=False):
        # TODO: explain this
        """ function to check passed params for the shorthand wrapper
            and to detect missing/required param
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
                self._requiredParams.append(key)
            except AttributeError:
                self._missing = []
                self._requiredParams = []
                self._requiredParams.append(key)
            if missing and key not in self._missing:
                self._missing.append(key)
        else:
            try:
                self._optionalParams.append(key)
            except AttributeError:
                self._optionalParams = []
                self._optionalParams.append(key)

        return default,args


class TVDBShorthandWrapper(ApiCall):
    _help = {"desc":"this is an internal function wrapper. call the help command directly for more information"}
    def __init__(self, args, kwargs, sid):
        self.origArgs = args
        self.kwargs = kwargs
        self.sid = sid
        
        self.s,args = self.check_params(args, kwargs, "s", None)
        self.e,args = self.check_params(args, kwargs, "e", None)
        self.args = args
        
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ internal function wrapper """
        # how to add a var to a tuple
        # http://stackoverflow.com/questions/1380860/add-variables-to-tuple
        argstmp = (0,self.sid) # make a new tuple
        args = argstmp + self.origArgs # add both
        args = args[1:] # remove first fake element
        if self.e:
            return CMD_Episode(args, self.kwargs).run()
        elif self.s:
            return CMD_Seasons(args, self.kwargs).run()
        else:
            return CMD_Show(args, self.kwargs).run()


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
    return {"error":msg}

def _result(msg,error=None):
    if error == None:
        return {"result":msg}
    else:
        return {"result":msg,"error":error}
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

class ApiError(Exception):
    "Generic API error"

class IntParseError(Exception):
    "A value could not be parsed into a int. But should be parsable to a int "

#-------------------------------------------------------------------------------------#

class CMD_Help(ApiCall):
    _help = {"desc":"display help information for a given subject/command",
             "optionalPramameters":{"subject":"command - the top level command",
                                  }
             }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.subject,args = self.check_params(args, kwargs, "subject", "help")
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ display help information for a given subject/command """
        if _functionMaper.has_key(self.subject):
            msg = _functionMaper.get(self.subject)((),{"help":1}).run()
        else:
            msg = _error("no such cmd")
        return msg


class CMD_ComingEpisodes(ApiCall):
    _help = {"desc":"display the coming episodes",
             "optionalPramameters":{"sort":"date/network/show - change the sort order"}
             }

    def __init__(self, args, kwargs): 
        # required
        # optional
        self.sort,args = self.check_params(args, kwargs, "sort", "date")
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ display the coming episodes """
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
            if not ep["network"]:
                ep["network"] = ""
            ep["airdate"] = _ordinal_to_dateForm(ordinalAirdate)
            ep["quality"] = _get_quality_string(ep["quality"])
            # TODO: choose eng weekday string OR number of weekday as int
            ep["weekday"] = dayofWeek[datetime.date.fromordinal(ordinalAirdate).weekday()]
            finalEpResults.append(ep)
        return finalEpResults


class CMD_Episode(ApiCall):
    _help = {"desc":"display detailed info about an episode",
             "requiredParameters":{"tvdbid":"tvdbid - thetvdb.com unique id of a show",
                                   "season":"## - the season number",
                                   "episode":"## - the episode number"
                                  },
             "optionalPramameters":{"full_path":"show the full absolute path (if valid) instead of a relative path for the episode location"}
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid,args = self.check_params(args, kwargs, "tvdbid", None, True)
        self.s,args = self.check_params(args, kwargs, "season", None, True)
        self.e,args = self.check_params(args, kwargs, "episode", None, True)
        # optional
        self.fullPath,args = self.check_params(args, kwargs, "full_path", "0")
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ display detailed info about an episode """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            raise ApiError("Show not Found")

        myDB = db.DBConnection(row_type="dict")
        sqlResults = myDB.select( "SELECT name, description, airdate, status, location FROM tv_episodes WHERE showid = ? AND episode = ? AND season = ?", [self.tvdbid,self.e,self.s])
        if not len(sqlResults) == 1:
            raise ApiError("Episode not Found")
        episode = sqlResults[0]
        # handle path options
        # absolute vs relative vs broken
        showPath = None
        try:
            showPath = showObj.location
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


class CMD_EpisodeSearch(ApiCall):
    _help = {"desc":"search for an episode. the response might take some time",
             "requiredParameters":{"tvdbid":"tvdbid - thetvdb.com unique id of a show",
                                   "season":"## - the season number",
                                   "episode":"## - the episode number"
                                  }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid,args = self.check_params(args, kwargs, "tvdbid", None, True)
        self.s,args = self.check_params(args, kwargs, "season", None, True)
        self.e,args = self.check_params(args, kwargs, "episode", None, True)
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ search for an episode """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            raise ApiError("Show not Found")

        # retrieve the episode object and fail if we can't get one 
        epObj = webserve._getEpisode(self.tvdbid,self.s, self.e)
        if isinstance(epObj, str):
            raise ApiError("Episode not Found")

        # make a queue item for it and put it on the queue
        ep_queue_item = search_queue.ManualSearchQueueItem(epObj)
        sickbeard.searchQueueScheduler.action.add_item(ep_queue_item) #@UndefinedVariable

        # wait until the queue item tells us whether it worked or not
        while ep_queue_item.success == None: #@UndefinedVariable
            time.sleep(1)

        # return the correct json value
        if ep_queue_item.success:
            return _result(statusStrings[epObj.status])

        return _result('failure','Unable to find episode')


class CMD_EpisodeSetStatus(ApiCall):
    _help = {"desc":"set status of an episode",
             "requiredParameters":{"tvdbid":"tvdbid - thetvdb.com unique id of a show",
                                   "season":"## - the season number",
                                   "episode":"## - the episode number",
                                   "status":"# - the status value: "+",".join(statusStrings.statusStrings.values()) # adding a list of all possible values
                                  }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid,args = self.check_params(args, kwargs, "tvdbid", None, True)
        self.s,args = self.check_params(args, kwargs, "season", None, True)
        self.e,args = self.check_params(args, kwargs, "episode", None, True)
        self.status,args = self.check_params(args, kwargs, "status", None, True)
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ set status of an episode """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            raise ApiError("Show not Found")

        # convert the string status to a int
        for status in statusStrings.statusStrings:
            if statusStrings[status].lower() == self.status.lower():
                self.status = status
                break
        # this should be obsolete bcause of the above
        if not statusStrings.has_key(int(self.status)):
            raise ApiError("Invalid Status")

        epObj = showObj.getEpisode(int(self.s), int(self.e))
        if epObj == None:
            raise ApiError("Episode not Found")

        if int(self.status) not in (3,5,6,7):
            raise ApiError("Status Prohibited")

        segment_list = []
        if int(self.status) == WANTED:
            # figure out what segment the episode is in and remember it so we can backlog it
            if epObj.show.air_by_date:
                ep_segment = str(epObj.airdate)[:7]
            else:
                ep_segment = epObj.season

            if ep_segment not in segment_list:
                segment_list.append(ep_segment)

        with epObj.lock:
            # don't let them mess up UNAIRED episodes
            if epObj.status == UNAIRED:
                raise ApiError("Refusing to change status because it is UNAIRED")
    
            if int(self.status) in Quality.DOWNLOADED and epObj.status not in Quality.SNATCHED + Quality.SNATCHED_PROPER + Quality.DOWNLOADED + [IGNORED] and not ek.ek(os.path.isfile, epObj.location):
                raise ApiError("Refusing to change status to DOWNLOADED because it's not SNATCHED/DOWNLOADED")
    
            epObj.status = int(self.status)
            epObj.saveToDB()

            for cur_segment in segment_list:
                cur_backlog_queue_item = search_queue.BacklogQueueItem(showObj, cur_segment)
                sickbeard.searchQueueScheduler.action.add_item(cur_backlog_queue_item) #@UndefinedVariable
                logger.log(u"Starting backlog for "+showObj.name+" season "+str(cur_segment)+" because some eps were set to wanted")
                return {"result": "Episode status changed to Wanted, and backlog started" }

        return {"result": "Episode status successfully changed to "+statusStrings[epObj.status]}


class CMD_Exceptions(ApiCall):
    _help = {"desc":"display scene exceptions for all or a given show",
             "optionalPramameters":{"tvdbid":"tvdbid - thetvdb.com unique id of a show",
                                  }
             }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.tvdbid,args = self.check_params(args, kwargs, "tvdbid", None, False)
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ display scene exceptions for all or a given show """
        myDB = db.DBConnection("cache.db",row_type="dict")

        if self.tvdbid == None:
            sqlResults = myDB.select("SELECT show_name,tvdb_id AS 'tvdbid' FROM scene_exceptions")
            exceptions = {}
            for row in sqlResults:
                tvdbid = row["tvdbid"]
                if not exceptions.has_key(tvdbid):
                    exceptions[tvdbid] = []
                exceptions[tvdbid].append(row["show_name"])

        else:
            showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
            if not showObj:
                raise ApiError("Show not Found")

            sqlResults = myDB.select("SELECT show_name,tvdb_id AS 'tvdbid' FROM scene_exceptions WHERE tvdb_id = ?", [self.tvdbid])
            exceptions = []
            for row in sqlResults:
                exceptions.append(row["show_name"])

        return exceptions


class CMD_History(ApiCall):
    _help = {"desc":"display sickbeard downloaded/snatched history",
             "optionalPramameters":{"limit":"## - limit returned results",
                                    "type":"downloaded/snatched - only show a specific type of results",
                                   }
             }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.limit,args = self.check_params(args, kwargs, "limit", 100)
        self.type,args = self.check_params(args, kwargs, "type", None)
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ display sickbeard downloaded/snatched history """
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
            row["resource_path"] = os.path.dirname(row["resource"])
            row["resource"] = os.path.basename(row["resource"])
            results.append(row)
        return results


class CMD_HistoryClear(ApiCall):
    _help = {"desc":"clear sickbeard's history",
             }

    def __init__(self,args,kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
        
    def run(self):
        """ clear sickbeard's history """
        myDB = db.DBConnection()
        myDB.action("DELETE FROM history WHERE 1=1")
        return _result("History Cleared")


class CMD_HistoryTrim(ApiCall):
    _help = {"desc":"trim sickbeard's history by removing entries greater than 30 days old"
             }

    def __init__(self,args,kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
        
    def run(self):
        """ trim sickbeard's history """
        myDB = db.DBConnection()
        myDB.action("DELETE FROM history WHERE date < "+str((datetime.datetime.today()-datetime.timedelta(days=30)).strftime(history.dateFormat)))
        return _result("Removed history entries greater than 30 days old")


class CMD_Logs(ApiCall):
    _help = {"desc":"insert description here"
             }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.minLevel,args = self.check_params(args, kwargs, "minlevel", "error")
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ view log """
        # 10 = Debug / 20 = Info / 30 = Warning / 40 = Error
        minLevel = logger.reverseNames[self.minLevel.upper()]

        data = []
        if os.path.isfile(logger.sb_log_instance.log_file):
            f = ek.ek(open, logger.sb_log_instance.log_file)
            data = f.readlines()
            f.close()

        regex =  "^(\w{3})\-(\d\d)\s*(\d\d)\:(\d\d):(\d\d)\s*([A-Z]+)\s*(.+?)\s*\:\:\s*(.*)$"

        finalData = []

        numLines = 0
        lastLine = False
        numToShow = min(50, len(data))

        for x in reversed(data):

            x = x.decode('utf-8')
            match = re.match(regex, x)

            if match:
                level = match.group(6)
                if level not in logger.reverseNames:
                    lastLine = False
                    continue

                if logger.reverseNames[level] >= minLevel:
                    lastLine = True
                    finalData.append(x.rstrip("\n"))
                else:
                    lastLine = False
                    continue

            elif lastLine:
                finalData.append("AA"+x)

            numLines += 1

            if numLines >= numToShow:
                break

        return finalData


class CMD_SickBeard(ApiCall):
    _help = {"desc":"display misc sickbeard related information"
             }

    def __init__(self,args,kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
        
    def run(self):
        """ display misc sickbeard related information """
        myDB = db.DBConnection(row_type="dict")
        sqlResults = myDB.select( "SELECT last_backlog FROM info")
        for row in sqlResults:
            row["last_backlog"] = _ordinal_to_dateForm(row["last_backlog"])

        return {"sb_version": sickbeard.version.SICKBEARD_VERSION, "api_version":Api.version, "cmdOverview":sorted(_functionMaper.keys()), "last_backlog": row["last_backlog"]}


class CMD_SickBeardCheckScheduler(ApiCall):
    _help = {"desc":"query the scheduler"
             }

    def __init__(self,args,kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
        
    def run(self):
        """ query the scheduler """
        backlogPaused = sickbeard.searchQueueScheduler.action.is_backlog_paused() #@UndefinedVariable
        backlogRunning = sickbeard.searchQueueScheduler.action.is_backlog_in_progress() #@UndefinedVariable
        searchStatus = sickbeard.currentSearchScheduler.action.amActive #@UndefinedVariable

        return {"backlogPaused": bool(backlogPaused), "backlogRunning": bool(backlogRunning), "searchStatus": bool(searchStatus)}


class CMD_SickBeardForceSearch(ApiCall):
    _help = {"desc":"force the episode search early"
             }

    def __init__(self,args,kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
        
    def run(self):
        """ force the episode search early """
        # Changing all old missing episodes to status WANTED
        # Beginning search for new episodes on RSS
        # Searching all providers for any needed episodes
        result = sickbeard.currentSearchScheduler.forceRun()
        if result:
            return {"result": "Episode search forced"}
        return {"result": "Failure"}


class CMD_SickBeardPauseBacklog(ApiCall):
    _help = {"desc":"pause the backlog search"
             }

    def __init__(self,args,kwargs):
        # required
        # optional
        self.paused,args = self.check_params(args, kwargs, "pause", None)
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
        
    def run(self):
        """ pause the backlog search """
        if self.paused == "1":
            sickbeard.searchQueueScheduler.action.pause_backlog() #@UndefinedVariable
            return {"result": "Backlog Paused"}
        else:
            sickbeard.searchQueueScheduler.action.unpause_backlog() #@UndefinedVariable
            return {"result": "Backlog Unpaused"}



class CMD_SickBeardPing(ApiCall):
    _help = {"desc":"check to see if sickbeard is running"
             }

    def __init__(self,args,kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
        
    def run(self):
        """ check to see if sickbeard is running """
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        if sickbeard.started:
            return {"result": "Pong ("+str(sickbeard.PID)+")"}
        else:
            return {"result": "Pong"}


class CMD_SickBeardRestart(ApiCall):
    _help = {"desc":"restart sickbeard"
             }

    def __init__(self,args,kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
        
    def run(self):
        """ restart sickbeard """
        threading.Timer(2, sickbeard.invoke_restart, [False]).start()
        return {"result":"Sick Beard is restarting..."}


class CMD_SickBeardShutdown(ApiCall):
    _help = {"desc":"shutdown sickbeard"
             }

    def __init__(self,args,kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
        
    def run(self):
        """ shutdown sickbeard """
        threading.Timer(2, sickbeard.invoke_shutdown).start()
        return {"result":"Sick Beard is shutting down..."}


class CMD_SeasonList(ApiCall):
    _help = {"desc":"display the season list for a given show",
             "requiredParameters":{"tvdbid":"tvdbid - thetvdb.com unique id of a show",
                                  },
             "optionalPramameters":{"sort":"asc - change the sort order from descending to ascending"}
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid,args = self.check_params(args, kwargs, "tvdbid", None, True)
        # optional
        self.sort,args = self.check_params(args, kwargs, "sort", "desc") # "asc" and "desc" default and fallback is "desc"
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ display the season list for a given show """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            raise ApiError("Show not Found")

        myDB = db.DBConnection(row_type="dict")
        if self.sort == "asc":
            sqlResults = myDB.select( "SELECT DISTINCT season FROM tv_episodes WHERE showid = ? ORDER BY season ASC", [self.tvdbid])
        else:
            sqlResults = myDB.select( "SELECT DISTINCT season FROM tv_episodes WHERE showid = ? ORDER BY season DESC", [self.tvdbid])
        seasonList = [] # a list with all season numbers
        for row in sqlResults:
            seasonList.append(int(row["season"]))

        return seasonList


class CMD_Seasons(ApiCall):
    _help = {"desc":"display a listing of episodes for all or a given season",
             "requiredParameters":{"tvdbid":"tvdbid - thetvdb.com unique id of a show",
                                  },
             "optionalPramameters":{"season":"## - the season number",
                                  }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid,args = self.check_params(args, kwargs, "tvdbid", None, True)
        # optional
        self.season,args = self.check_params(args, kwargs, "season", None, False)
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ display a listing of episodes for all or a given show """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            raise ApiError("Show not Found")

        myDB = db.DBConnection(row_type="dict")

        if self.season == None:
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

        else:
            sqlResults = myDB.select( "SELECT name, episode, airdate, status FROM tv_episodes WHERE showid = ? AND season = ?", [self.tvdbid,self.season])
            if len(sqlResults) is 0:
                raise ApiError("Season not Found")
            seasons = {}
            for row in sqlResults:
                curEpisode = int(row["episode"])
                del row["episode"]
                row["status"] = statusStrings[row["status"]]
                row["airdate"] = _ordinal_to_dateForm(row["airdate"])
                if not seasons.has_key(curEpisode):
                    seasons[curEpisode] = {}
                seasons[curEpisode] = row

        return seasons


class CMD_Show(ApiCall):
    _help = {"desc":"display information for a given show",
             "requiredParameters":{"tvdbid":"tvdbid - thetvdb.com unique id of a show",
                                  }
             }

    def __init__(self,args,kwargs):
        # required
        self.tvdbid,args = self.check_params(args, kwargs, "tvdbid", None, True)
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs) 
    
    def run(self):
        """ display information for a given show """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            raise ApiError("Show not Found")

        showDict = {}
        showDict["season_list"] = CMD_SeasonList((), {"tvdbid":self.tvdbid}).run()
    
        genreList = []
        if showObj.genre:
            genreListTmp = showObj.genre.split("|")
            for genre in genreListTmp:
                if genre:
                    genreList.append(genre)
        showDict["genre"] = genreList
        showDict["quality"] = _get_quality_string(showObj.quality)
    
        try:
            showDict["location"] = showObj.location
        except:
            showDict["location"] = ""
    
        # easy stuff
        showDict["language"] = showObj.lang
        showDict["show_name"] = showObj.name
        showDict["paused"] = showObj.paused
        showDict["air_by_date"] = showObj.air_by_date
        showDict["season_folders"] = showObj.seasonfolders
        showDict["airs"] = showObj.airs
        showDict["tvrage_id"] = showObj.tvrid
        showDict["tvrage_name"] = showObj.tvrname

        return showDict


class CMD_ShowAdd(ApiCall):
    _help = {"desc":"add a show in sickbeard",
             }

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ add a show in sickbeard """
        return _result("Not yet implmented")


class CMD_ShowDelete(ApiCall):
    _help = {"desc":"delete a show in sickbeard",
             "requiredParameters":{"tvdbid":"tvdbid - thetvdb.com unique id of a show",
                                  }
             }

    def __init__(self,args,kwargs):
        # required
        self.tvdbid,args = self.check_params(args, kwargs, "tvdbid", None, True)
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
        
    def run(self):
        """ delete a show in sickbeard """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            raise ApiError("Show not Found")

        if sickbeard.showQueueScheduler.action.isBeingAdded(showObj) or sickbeard.showQueueScheduler.action.isBeingUpdated(showObj): #@UndefinedVariable
            raise ApiError("Show can not be deleted while being added or updated")

        showObj.deleteShow()
        return _result(str(showObj.name)+" has been deleted")


class CMD_ShowRefresh(ApiCall):
    _help = {"desc":"refresh a show in sickbeard",
             "requiredParameters":{"tvdbid":"tvdbid - thetvdb.com unique id of a show",
                                  }
             }

    def __init__(self,args,kwargs):
        # required
        self.tvdbid,args = self.check_params(args, kwargs, "tvdbid", None, True)
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
        
    def run(self):
        """ refresh a show in sickbeard """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            raise ApiError("Show not Found")

        try:
            sickbeard.showQueueScheduler.action.refreshShow(showObj) #@UndefinedVariable
            return _result(str(showObj.name)+" has queued to be refreshed")
        except exceptions.CantRefreshException, e:
            return _result("Unable to refresh " + str(showObj.name), ex(e))


class CMD_ShowUpdate(ApiCall):
    _help = {"desc":"update a show in sickbeard",
             "requiredParameters":{"tvdbid":"tvdbid - thetvdb.com unique id of a show",
                                  }
             }

    def __init__(self,args,kwargs):
        # required
        self.tvdbid,args = self.check_params(args, kwargs, "tvdbid", None, True)
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
        
    def run(self):
        """ update a show in sickbeard """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            raise ApiError("Show not Found")

        try:
            sickbeard.showQueueScheduler.action.updateShow(showObj, bool(force)) #@UndefinedVariable
            return _result(str(showObj.name)+" has queued to be updated")
        except exceptions.CantUpdateException, e:
            return _result("Unable to update " + str(showObj.name), ex(e))


class CMD_Shows(ApiCall):
    _help = {"desc":"display all shows in sickbeard",
             "optionalPramameters":{"sort":"show - sort the list of shows by show name instead of tvdbid",
                                    "paused":"0/1 - only show the shows that are set to paused",
                                  },
             }

    def __init__(self,args,kwargs):
        # required
        # optional
        self.sort,args = self.check_params(args, kwargs, "sort", "id")
        self.paused,args = self.check_params(args, kwargs, "paused", None)
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
           
    def run(self):
        """ display all shows in sickbeard """
        shows = {}
        for curShow in sickbeard.showList:
            if self.paused and not self.paused == str(curShow.paused):
                continue
            showDict = {"paused":curShow.paused,
                        "quality":_get_quality_string(curShow.quality),
                        "language":curShow.lang,
                        "tvrage_id":curShow.tvrid,
                        "tvrage_name":curShow.tvrname}
            if self.sort == "show":
                showDict["tvdbid"] = curShow.tvdbid
                shows[curShow.name] = showDict
            else:
                showDict["show_name"] = curShow.name
                shows[curShow.tvdbid] = showDict
        return shows


class CMD_Stats(ApiCall):
    _help = {"desc":"display episode statistics for a given show",
             "requiredParameters":{"tvdbid":"tvdbid - thetvdb.com unique id of a show",
                                  }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid,args = self.check_params(args, kwargs, "tvdbid", None, False)
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)
        
    def run(self):
        """ display episode statistics for a given show """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            raise ApiError("Show not Found")

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
            elif status == 0: # we dont count NONE = 0 = N/A
                pass
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


_functionMaper = {"help":CMD_Help,
                  "future":CMD_ComingEpisodes,
                  "episode":CMD_Episode,
                  "episode.search":CMD_EpisodeSearch,
                  "episode.setstatus":CMD_EpisodeSetStatus,
                  "exceptions":CMD_Exceptions,
                  "history":CMD_History,
                  "history.clear":CMD_HistoryClear,
                  "history.trim":CMD_HistoryTrim,
                  "logs":CMD_Logs,
                  "sb":CMD_SickBeard,
                  "sb.checkscheduler":CMD_SickBeardCheckScheduler,
                  "sb.forcesearch":CMD_SickBeardForceSearch,
                  "sb.pausebacklog":CMD_SickBeardPauseBacklog,
                  "sb.ping":CMD_SickBeardPing,
                  "sb.restart":CMD_SickBeardRestart,
                  "sb.shutdown":CMD_SickBeardShutdown,
                  "seasonlist":CMD_SeasonList,
                  "seasons":CMD_Seasons,
                  "show":CMD_Show,
                  "show.add":CMD_ShowAdd,
                  "show.delete":CMD_ShowDelete,
                  "show.refresh":CMD_ShowRefresh,
                  "show.update":CMD_ShowUpdate,
                  "shows":CMD_Shows,
                  "stats":CMD_Stats
                  }
