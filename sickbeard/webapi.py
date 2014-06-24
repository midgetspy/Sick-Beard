# Author: Dennis Lutter <lad1337@gmail.com>
# Author: Jonathon Saine <thezoggy@gmail.com>
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

from __future__ import with_statement

import os
import time
import urllib
import datetime
import threading
import re
import traceback

import cherrypy
import sickbeard
import webserve
from sickbeard import db, logger, exceptions, history, ui, helpers
from sickbeard.exceptions import ex
from sickbeard import encodingKludge as ek
from sickbeard import search_queue
from sickbeard.common import SNATCHED, SNATCHED_PROPER, DOWNLOADED, SKIPPED, UNAIRED, IGNORED, ARCHIVED, WANTED, UNKNOWN
from common import Quality, qualityPresetStrings, statusStrings
from sickbeard import image_cache
from lib.tvdb_api import tvdb_api, tvdb_exceptions

try:
    import json
except ImportError:
    from lib import simplejson as json

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

dateFormat = "%Y-%m-%d"
dateTimeFormat = "%Y-%m-%d %H:%M"


RESULT_SUCCESS = 10  # only use inside the run methods
RESULT_FAILURE = 20  # only use inside the run methods
RESULT_TIMEOUT = 30  # not used yet :(
RESULT_ERROR = 40  # only use outside of the run methods !
RESULT_FATAL = 50  # only use in Api.default() ! this is the "we encountered an internal error" error
RESULT_DENIED = 60  # only use in Api.default() ! this is the acces denied error
result_type_map = {RESULT_SUCCESS: "success",
                  RESULT_FAILURE: "failure",
                  RESULT_TIMEOUT: "timeout",
                  RESULT_ERROR: "error",
                  RESULT_FATAL: "fatal",
                  RESULT_DENIED: "denied",
                  }
# basically everything except RESULT_SUCCESS / success is bad


class Api:
    """ api class that returns json results """
    version = 4  # use an int since float-point is unpredictable
    intent = 4

    @cherrypy.expose
    def default(self, *args, **kwargs):

        self.apiKey = sickbeard.API_KEY
        access, accessMsg, args, kwargs = self._grand_access(self.apiKey, args, kwargs)

        # set the output callback
        # default json
        outputCallbackDict = {'default': self._out_as_json,
                              'image': lambda x: x['image'],
                              }

        # do we have acces ?
        if access:
            logger.log(accessMsg, logger.DEBUG)
        else:
            logger.log(accessMsg, logger.WARNING)
            return outputCallbackDict['default'](_responds(RESULT_DENIED, msg=accessMsg))

        # set the original call_dispatcher as the local _call_dispatcher
        _call_dispatcher = call_dispatcher
        # if profile was set wrap "_call_dispatcher" in the profile function
        if 'profile' in kwargs:
            from lib.profilehooks import profile
            _call_dispatcher = profile(_call_dispatcher, immediate=True)
            del kwargs["profile"]

        # if debug was set call the "_call_dispatcher"
        if 'debug' in kwargs:
            # this way we can debug the cherry.py traceback in the browser
            outDict = _call_dispatcher(args, kwargs)
            del kwargs["debug"]
        # if debug was not set we wrap the "call_dispatcher" in a try block to assure a json output
        else:
            try:
                outDict = _call_dispatcher(args, kwargs)
            # seems like cherrypy uses exceptions for redirecting apparently this can happen when requesting images but it is ok so lets re raise it
            except cherrypy.HTTPRedirect:
                raise
            # real internal error oohhh nooo :(
            except Exception, e:
                logger.log(u"API :: " + ex(e), logger.ERROR)
                errorData = {"error_msg": ex(e),
                             "args": args,
                             "kwargs": kwargs}
                outDict = _responds(RESULT_FATAL, errorData, "SickBeard encountered an internal error! Please report to the Devs")

        if 'outputType' in outDict:
            outputCallback = outputCallbackDict[outDict['outputType']]
        else:
            outputCallback = outputCallbackDict['default']

        return outputCallback(outDict)

    @cherrypy.expose
    def builder(self):
        """ expose the api-builder template """
        t = webserve.PageTemplate(file="apiBuilder.tmpl")

        def titler(x):
            if not x:
                return x
            if x.lower().startswith('a '):
                x = x[2:]
            elif x.lower().startswith('the '):
                x = x[4:]
            return x

        # enforce a 100 show limit to ensure performance
        t.sortedShowList = sorted(sickbeard.showList, lambda x, y: cmp(titler(x.name), titler(y.name)))[0:100]

        myDB = db.DBConnection(row_type="dict")
        seasonSQLResults = {}
        episodeSQLResults = {}

        for curShow in t.sortedShowList:
            seasonSQLResults[curShow.tvdbid] = myDB.select("SELECT DISTINCT season FROM tv_episodes WHERE showid = ? ORDER BY season DESC", [curShow.tvdbid])

        for curShow in t.sortedShowList:
            episodeSQLResults[curShow.tvdbid] = myDB.select("SELECT DISTINCT season,episode FROM tv_episodes WHERE showid = ? ORDER BY season DESC, episode DESC", [curShow.tvdbid])

        t.seasonSQLResults = seasonSQLResults
        t.episodeSQLResults = episodeSQLResults

        myDB.connection.close()
        if len(sickbeard.API_KEY) == 32:
            t.apikey = sickbeard.API_KEY
        else:
            t.apikey = "api key not generated"

        return webserve._munge(t)

    def _out_as_json(self, dict):
        """ set cherrypy response to json """
        response = cherrypy.response
        request = cherrypy.request
        response.headers['Content-Type'] = 'application/json;charset=UTF-8'
        try:
            out = json.dumps(dict, indent=self.intent, sort_keys=True)
            callback = request.params.get('callback') or request.params.get('jsonp')
            if callback != None:
                # wrap with JSONP call if requested
                out = callback + '(' + out + ');'
        # if we fail to generate the output fake an error
        except Exception, e:
            logger.log(u"API :: " + traceback.format_exc(), logger.DEBUG)
            out = '{"result":"' + result_type_map[RESULT_ERROR] + '", "message": "error while composing output: "' + ex(e) + '"}'
        return out

    def _grand_access(self, realKey, args, kwargs):
        """ validate api key and log result """
        remoteIp = cherrypy.request.remote.ip
        apiKey = kwargs.get("apikey", None)
        if not apiKey:
            # if we have keyless vars we assume first one is the api key, always !
            if args:
                apiKey = args[0]
                # remove the apikey from the args tuple
                args = args[1:]
        else:
            del kwargs["apikey"]

        if sickbeard.USE_API != True:
            msg = u"API :: " + remoteIp + " - SB API Disabled. ACCESS DENIED"
            return False, msg, args, kwargs
        elif apiKey == realKey:
            msg = u"API :: " + remoteIp + " - gave correct API KEY. ACCESS GRANTED"
            return True, msg, args, kwargs
        elif not apiKey:
            msg = u"API :: " + remoteIp + " - gave NO API KEY. ACCESS DENIED"
            return False, msg, args, kwargs
        else:
            msg = u"API :: " + remoteIp + " - gave WRONG API KEY " + apiKey + ". ACCESS DENIED"
            return False, msg, args, kwargs


def call_dispatcher(args, kwargs):
    """ calls the appropriate CMD class
        looks for a cmd in args and kwargs
        or calls the TVDBShorthandWrapper when the first args element is a number
        or returns an error that there is no such cmd
    """
    logger.log(u"API :: all args: '" + str(args) + "'", logger.DEBUG)
    logger.log(u"API :: all kwargs: '" + str(kwargs) + "'", logger.DEBUG)

    cmds = None
    if args:
        cmds = args[0]
        args = args[1:]

    if "cmd" in kwargs:
        cmds = kwargs["cmd"]
        del kwargs["cmd"]

    outDict = {}
    if cmds != None:
        cmds = cmds.split("|")
        multiCmds = bool(len(cmds) > 1)
        for cmd in cmds:
            curArgs, curKwargs = filter_params(cmd, args, kwargs)
            cmdIndex = None
            # was a index used for this cmd ?
            if len(cmd.split("_")) > 1:
                # this gives us the clear cmd and the index
                cmd, cmdIndex = cmd.split("_")

            logger.log(u"API :: " + cmd + ": curKwargs " + str(curKwargs), logger.DEBUG)
            # skip these cmd while chaining
            if not (multiCmds and cmd in ('show.getposter', 'show.getbanner')):
                try:
                    if cmd in _functionMaper:
                        # get the cmd class, init it and run()
                        curOutDict = _functionMaper.get(cmd)(curArgs, curKwargs).run()
                    elif _is_int(cmd):
                        curOutDict = TVDBShorthandWrapper(curArgs, curKwargs, cmd).run()
                    else:
                        curOutDict = _responds(RESULT_ERROR, "No such cmd: '" + cmd + "'")
                # Api errors that we raised, they are harmless
                except ApiError, e:
                    curOutDict = _responds(RESULT_ERROR, msg=ex(e))
            # if someone chained one of the forbidden cmds they will get an error for this one cmd
            else:
                curOutDict = _responds(RESULT_ERROR, msg="The cmd '" + cmd + "' is not supported while chaining")

            if multiCmds:
                # note: if multiple same cmds are issued but one has not an index defined it will override all others
                # or the other way around, this depends on the order of the cmds this is not a bug

                # do we need a index dict for this cmd ?
                if cmdIndex is None:
                    outDict[cmd] = curOutDict
                else:
                    if not cmd in outDict:
                        outDict[cmd] = {}
                    outDict[cmd][cmdIndex] = curOutDict
            else:
                outDict = curOutDict

        # if we had multiple cmds we have to wrap it in a response dict
        if multiCmds:
            outDict = _responds(RESULT_SUCCESS, outDict)
    # index / no cmd given
    else:
        outDict = CMD_SickBeard(args, kwargs).run()

    return outDict


def filter_params(cmd, args, kwargs):
    """ return only params kwargs that are for cmd
        and rename them to a clean version (remove "<cmd>_")
        args are shared across all cmds

        all args and kwarks are lowerd

        cmd are separated by "|" e.g. &cmd=shows|future
        kwargs are namespaced with "." e.g. show.tvdbid=101501
        if a karg has no namespace asing it anyways (global)

        full e.g.
        /api?apikey=1234&cmd=show.seasonlist_asd|show.seasonlist_2&show.seasonlist_asd.tvdbid=101501&show.seasonlist_2.tvdbid=79488&sort=asc

        two calls of show.seasonlist
        one has the index "asd" the other one "2"
        the "tvdbid" kwargs / params have the indexed cmd as a namspace
        and the kwarg / param "sort" is a used as a global
    """
    curArgs = []
    for arg in args:
        curArgs.append(arg.lower())
    curArgs = tuple(curArgs)

    curKwargs = {}
    for kwarg in kwargs:
        if kwarg.find(cmd + ".") == 0:
            cleanKey = kwarg.rpartition(".")[2]
            curKwargs[cleanKey] = kwargs[kwarg].lower()
        # the kwarg was not namespaced therefore a "global"
        elif not "." in kwarg:
            curKwargs[kwarg] = kwargs[kwarg]
    return curArgs, curKwargs


class ApiCall(object):
    _help = {"desc": "No help message available. Please tell the devs that a help msg is missing for this cmd"}

    def __init__(self, args, kwargs):
        # missing
        try:
            if self._missing:
                self.run = self.return_missing
        except AttributeError:
            pass
        # help
        if 'help' in kwargs:
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

        for paramDict, type in [(self._requiredParams, "requiredParameters"),
                          (self._optionalParams, "optionalParameters")]:

            if type in self._help:
                for paramName in paramDict:
                    if not paramName in self._help[type]:
                        self._help[type][paramName] = {}
                    if paramDict[paramName]["allowedValues"]:
                        self._help[type][paramName]["allowedValues"] = paramDict[paramName]["allowedValues"]
                    else:
                        self._help[type][paramName]["allowedValues"] = "see desc"
                    self._help[type][paramName]["defaultValue"] = paramDict[paramName]["defaultValue"]

            elif paramDict:
                for paramName in paramDict:
                    self._help[type] = {}
                    self._help[type][paramName] = paramDict[paramName]
            else:
                self._help[type] = {}
        msg = "No description available"
        if "desc" in self._help:
            msg = self._help["desc"]
            del self._help["desc"]
        return _responds(RESULT_SUCCESS, self._help, msg)

    def return_missing(self):
        if len(self._missing) == 1:
            msg = "The required parameter: '" + self._missing[0] + "' was not set"
        else:
            msg = "The required parameters: '" + "','".join(self._missing) + "' where not set"
        return _responds(RESULT_ERROR, msg=msg)

    def check_params(self, args, kwargs, key, default, required, type, allowedValues):
        """ function to check passed params for the shorthand wrapper
            and to detect missing/required param
        """
        missing = True
        orgDefault = default

        if type == "bool":
            allowedValues = [0, 1]

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
                self._requiredParams = {}
                self._requiredParams[key] = {"allowedValues": allowedValues,
                                             "defaultValue": orgDefault}
            if missing and key not in self._missing:
                self._missing.append(key)
        else:
            try:
                self._optionalParams[key] = {"allowedValues": allowedValues,
                                             "defaultValue": orgDefault}
            except AttributeError:
                self._optionalParams = {}
                self._optionalParams[key] = {"allowedValues": allowedValues,
                                             "defaultValue": orgDefault}

        if default:
            default = self._check_param_type(default, key, type)
            if type == "bool":
                type = []
            self._check_param_value(default, key, allowedValues)

        return default, args

    def _check_param_type(self, value, name, type):
        """ checks if value can be converted / parsed to type
            will raise an error on failure
            or will convert it to type and return new converted value
            can check for:
            - int: will be converted into int
            - bool: will be converted to False / True
            - list: will always return a list
            - string: will do nothing for now
            - ignore: will ignore it, just like "string"
        """
        error = False
        if type == "int":
            if _is_int(value):
                value = int(value)
            else:
                error = True
        elif type == "bool":
            if value in ("0", "1"):
                value = bool(int(value))
            elif value in ("true", "True", "TRUE"):
                value = True
            elif value in ("false", "False", "FALSE"):
                value = False
            else:
                error = True
        elif type == "list":
            value = value.split("|")
        elif type == "string":
            pass
        elif type == "ignore":
            pass
        else:
            logger.log(u"API :: Invalid param type set " + str(type) + " can not check or convert ignoring it", logger.ERROR)

        if error:
            # this is a real ApiError !!
            raise ApiError(u"param: '" + str(name) + "' with given value: '" + str(value) + "' could not be parsed into '" + str(type) + "'")

        return value

    def _check_param_value(self, value, name, allowedValues):
        """ will check if value (or all values in it ) are in allowed values
            will raise an exception if value is "out of range"
            if bool(allowedValue) == False a check is not performed and all values are excepted
        """
        if allowedValues:
            error = False
            if isinstance(value, list):
                for item in value:
                    if not item in allowedValues:
                        error = True
            else:
                if not value in allowedValues:
                    error = True

            if error:
                # this is kinda a ApiError but raising an error is the only way of quitting here
                raise ApiError(u"param: '" + str(name) + "' with given value: '" + str(value) + "' is out of allowed range '" + str(allowedValues) + "'")


class TVDBShorthandWrapper(ApiCall):
    _help = {"desc": "this is an internal function wrapper. call the help command directly for more information"}

    def __init__(self, args, kwargs, sid):
        self.origArgs = args
        self.kwargs = kwargs
        self.sid = sid

        self.s, args = self.check_params(args, kwargs, "s", None, False, "ignore", [])
        self.e, args = self.check_params(args, kwargs, "e", None, False, "ignore", [])
        self.args = args

        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ internal function wrapper """
        args = (self.sid,) + self.origArgs
        if self.e:
            return CMD_Episode(args, self.kwargs).run()
        elif self.s:
            return CMD_ShowSeasons(args, self.kwargs).run()
        else:
            return CMD_Show(args, self.kwargs).run()


################################
#     helper functions         #
################################

def _sizeof_fmt(num):
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.00:
            return "%3.2f %s" % (num, x)
        num /= 1024.00


def _is_int(data):
    try:
        int(data)
    except (TypeError, ValueError, OverflowError):
        return False
    else:
        return True


def _rename_element(dict, oldKey, newKey):
    try:
        dict[newKey] = dict[oldKey]
        del dict[oldKey]
    except (ValueError, TypeError, NameError):
        pass
    return dict


def _responds(result_type, data=None, msg=""):
    """
    result is a string of given "type" (success/failure/timeout/error)
    message is a human readable string, can be empty
    data is either a dict or a array, can be a empty dict or empty array
    """
    if data is None:
        data = {}
    return {"result": result_type_map[result_type],
            "message": msg,
            "data": data}


def _get_quality_string(q):
    qualityString = "Custom"
    if q in qualityPresetStrings:
        qualityString = qualityPresetStrings[q]
    elif q in Quality.qualityStrings:
        qualityString = Quality.qualityStrings[q]
    return qualityString


def _get_status_Strings(s):
    return statusStrings[s]


def _ordinal_to_dateTimeForm(ordinal):
    # workaround for episodes with no airdate
    if int(ordinal) != 1:
        date = datetime.date.fromordinal(ordinal)
    else:
        return ""
    return date.strftime(dateTimeFormat)


def _ordinal_to_dateForm(ordinal):
    if int(ordinal) != 1:
        date = datetime.date.fromordinal(ordinal)
    else:
        return ""
    return date.strftime(dateFormat)


def _historyDate_to_dateTimeForm(timeString):
    date = datetime.datetime.strptime(timeString, history.dateFormat)
    return date.strftime(dateTimeFormat)


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


def _mapQuality(showObj):
    quality_map = _getQualityMap()

    anyQualities = []
    bestQualities = []

    iqualityID, aqualityID = Quality.splitQuality(int(showObj))
    if iqualityID:
        for quality in iqualityID:
            anyQualities.append(quality_map[quality])
    if aqualityID:
        for quality in aqualityID:
            bestQualities.append(quality_map[quality])
    return anyQualities, bestQualities


def _getQualityMap():
    return {Quality.SDTV: 'sdtv',
            Quality.SDDVD: 'sddvd',
            Quality.HDTV: 'hdtv',
            Quality.RAWHDTV: 'rawhdtv',
            Quality.FULLHDTV: 'fullhdtv',
            Quality.HDWEBDL: 'hdwebdl',
            Quality.FULLHDWEBDL: 'fullhdwebdl',
            Quality.HDBLURAY: 'hdbluray',
            Quality.FULLHDBLURAY: 'fullhdbluray',
            Quality.UNKNOWN: 'unknown'}


def _getRootDirs():
    if sickbeard.ROOT_DIRS == "":
        return {}

    rootDir = {}
    root_dirs = sickbeard.ROOT_DIRS.split('|')
    default_index = int(sickbeard.ROOT_DIRS.split('|')[0])

    rootDir["default_index"] = int(sickbeard.ROOT_DIRS.split('|')[0])
    # remove default_index value from list (this fixes the offset)
    root_dirs.pop(0)

    if len(root_dirs) < default_index:
        return {}

    # clean up the list - replace %xx escapes by their single-character equivalent
    root_dirs = [urllib.unquote_plus(x) for x in root_dirs]

    default_dir = root_dirs[default_index]

    dir_list = []
    for root_dir in root_dirs:
        valid = 1
        try:
            ek.ek(os.listdir, root_dir)
        except:
            valid = 0
        default = 0
        if root_dir is default_dir:
            default = 1

        curDir = {}
        curDir['valid'] = valid
        curDir['location'] = root_dir
        curDir['default'] = default
        dir_list.append(curDir)

    return dir_list


class ApiError(Exception):
    "Generic API error"


class IntParseError(Exception):
    "A value could not be parsed into a int. But should be parsable to a int "

#-------------------------------------------------------------------------------------#


class CMD_Help(ApiCall):
    _help = {"desc": "display help information for a given subject/command",
             "optionalParameters": {"subject": {"desc": "command - the top level command"},
                                  }
             }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.subject, args = self.check_params(args, kwargs, "subject", "help", False, "string", _functionMaper.keys())
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ display help information for a given subject/command """
        if self.subject in _functionMaper:
            out = _responds(RESULT_SUCCESS, _functionMaper.get(self.subject)((), {"help": 1}).run())
        else:
            out = _responds(RESULT_FAILURE, msg="No such cmd")
        return out


class CMD_ComingEpisodes(ApiCall):
    _help = {"desc": "display the coming episodes",
             "optionalParameters": {"sort": {"desc": "change the sort order"},
                                   "type": {"desc": "one or more of allowedValues separated by |"},
                                   "paused": {"desc": "0 to exclude paused shows, 1 to include them, or omitted to use the SB default"},
                                   }
             }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.sort, args = self.check_params(args, kwargs, "sort", "date", False, "string", ["date", "show", "network"])
        self.type, args = self.check_params(args, kwargs, "type", "today|missed|soon|later", False, "list", ["missed", "later", "today", "soon"])
        self.paused, args = self.check_params(args, kwargs, "paused", sickbeard.COMING_EPS_DISPLAY_PAUSED, False, "int", [0, 1])
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
        sql_results = myDB.select("SELECT airdate, airs, episode, name AS 'ep_name', description AS 'ep_plot', network, season, showid AS 'tvdbid', show_name, tv_shows.quality AS quality, tv_shows.status AS 'show_status', tv_shows.paused AS 'paused' FROM tv_episodes, tv_shows WHERE season > 0 AND airdate >= ? AND airdate < ? AND tv_shows.tvdb_id = tv_episodes.showid AND tv_episodes.status NOT IN (" + ','.join(['?'] * len(qualList)) + ")", [today, next_week] + qualList)
        for cur_result in sql_results:
            done_show_list.append(int(cur_result["tvdbid"]))

        more_sql_results = myDB.select("SELECT airdate, airs, episode, name AS 'ep_name', description AS 'ep_plot', network, season, showid AS 'tvdbid', show_name, tv_shows.quality AS quality, tv_shows.status AS 'show_status', tv_shows.paused AS 'paused' FROM tv_episodes outer_eps, tv_shows WHERE season > 0 AND showid NOT IN (" + ','.join(['?'] * len(done_show_list)) + ") AND tv_shows.tvdb_id = outer_eps.showid AND airdate = (SELECT airdate FROM tv_episodes inner_eps WHERE inner_eps.season > 0 AND inner_eps.showid = outer_eps.showid AND inner_eps.airdate >= ? ORDER BY inner_eps.airdate ASC LIMIT 1) AND outer_eps.status NOT IN (" + ','.join(['?'] * len(Quality.DOWNLOADED + Quality.SNATCHED)) + ")", done_show_list + [next_week] + Quality.DOWNLOADED + Quality.SNATCHED)
        sql_results += more_sql_results

        more_sql_results = myDB.select("SELECT airdate, airs, episode, name AS 'ep_name', description AS 'ep_plot', network, season, showid AS 'tvdbid', show_name, tv_shows.quality AS quality, tv_shows.status AS 'show_status', tv_shows.paused AS 'paused' FROM tv_episodes, tv_shows WHERE season > 0 AND tv_shows.tvdb_id = tv_episodes.showid AND airdate < ? AND airdate >= ? AND tv_episodes.status = ? AND tv_episodes.status NOT IN (" + ','.join(['?'] * len(qualList)) + ")", [today, recently, WANTED] + qualList)
        sql_results += more_sql_results

        # sort by air date
        sorts = {
            'date': (lambda x, y: cmp(int(x["airdate"]), int(y["airdate"]))),
            'show': (lambda a, b: cmp(a["show_name"], b["show_name"])),
            'network': (lambda a, b: cmp(a["network"], b["network"])),
        }

        sql_results.sort(sorts[self.sort])
        finalEpResults = {}

        # add all requested types or all
        for curType in self.type:
            finalEpResults[curType] = []

        for ep in sql_results:
            """
                Missed:   yesterday... (less than 1week)
                Today:    today
                Soon:     tomorrow till next week
                Later:    later than next week
            """

            if ep["paused"] and not self.paused:
                continue

            status = "soon"
            if ep["airdate"] < today:
                status = "missed"
            elif ep["airdate"] >= next_week:
                status = "later"
            elif ep["airdate"] >= today and ep["airdate"] < next_week:
                if ep["airdate"] == today:
                    status = "today"
                else:
                    status = "soon"

            # skip unwanted
            if self.type != None and not status in self.type:
                continue

            ordinalAirdate = int(ep["airdate"])
            if not ep["network"]:
                ep["network"] = ""
            ep["airdate"] = _ordinal_to_dateForm(ordinalAirdate)
            ep["quality"] = _get_quality_string(ep["quality"])
            # clean up tvdb horrible airs field
            ep["airs"] = str(ep["airs"]).replace('am', ' AM').replace('pm', ' PM').replace('  ', ' ')
            # start day of the week on 1 (monday)
            ep["weekday"] = 1 + datetime.date.fromordinal(ordinalAirdate).weekday()

            # TODO: check if this obsolete
            if not status in finalEpResults:
                finalEpResults[status] = []

            finalEpResults[status].append(ep)
        myDB.connection.close()
        return _responds(RESULT_SUCCESS, finalEpResults)


class CMD_Episode(ApiCall):
    _help = {"desc": "display detailed info about an episode",
             "requiredParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"},
                                   "season": {"desc": "the season number"},
                                   "episode": {"desc": "the episode number"}
                                  },
             "optionalParameters": {"full_path": {"desc": "show the full absolute path (if valid) instead of a relative path for the episode location"}
                                     }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, True, "int", [])
        self.s, args = self.check_params(args, kwargs, "season", None, True, "int", [])
        self.e, args = self.check_params(args, kwargs, "episode", None, True, "int", [])
        # optional
        self.fullPath, args = self.check_params(args, kwargs, "full_path", 0, False, "bool", [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ display detailed info about an episode """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            return _responds(RESULT_FAILURE, msg="Show not found")

        myDB = db.DBConnection(row_type="dict")
        sqlResults = myDB.select("SELECT name, description, airdate, status, location, file_size, release_name FROM tv_episodes WHERE showid = ? AND episode = ? AND season = ?", [self.tvdbid, self.e, self.s])
        if not len(sqlResults) == 1:
            raise ApiError("Episode not found")
        episode = sqlResults[0]
        # handle path options
        # absolute vs relative vs broken
        showPath = None
        try:
            showPath = showObj.location
        except sickbeard.exceptions.ShowDirNotFoundException:
            pass

        if bool(self.fullPath) == True and showPath:
            pass
        elif bool(self.fullPath) == False and showPath:
            # using the length because lstrip removes to much
            showPathLength = len(showPath) + 1  # the / or \ yeah not that nice i know
            episode["location"] = episode["location"][showPathLength:]
        elif not showPath:  # show dir is broken ... episode path will be empty
            episode["location"] = ""
        # convert stuff to human form
        episode["airdate"] = _ordinal_to_dateForm(episode["airdate"])
        status, quality = Quality.splitCompositeStatus(int(episode["status"]))
        episode["status"] = _get_status_Strings(status)
        episode["quality"] = _get_quality_string(quality)
        episode["file_size_human"] = _sizeof_fmt(episode["file_size"])

        myDB.connection.close()
        return _responds(RESULT_SUCCESS, episode)


class CMD_EpisodeSearch(ApiCall):
    _help = {"desc": "search for an episode. the response might take some time",
             "requiredParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"},
                                   "season": {"desc": "the season number"},
                                   "episode": {"desc": "the episode number"}
                                  }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, True, "int", [])
        self.s, args = self.check_params(args, kwargs, "season", None, True, "int", [])
        self.e, args = self.check_params(args, kwargs, "episode", None, True, "int", [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ search for an episode """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            return _responds(RESULT_FAILURE, msg="Show not found")

        # retrieve the episode object and fail if we can't get one
        epObj = showObj.getEpisode(int(self.s), int(self.e))
        if isinstance(epObj, str):
            return _responds(RESULT_FAILURE, msg="Episode not found")

        # make a queue item for it and put it on the queue
        ep_queue_item = search_queue.ManualSearchQueueItem(epObj)
        sickbeard.searchQueueScheduler.action.add_item(ep_queue_item)  # @UndefinedVariable

        # wait until the queue item tells us whether it worked or not
        while ep_queue_item.success == None:  # @UndefinedVariable
            time.sleep(1)

        # return the correct json value
        if ep_queue_item.success:
            status, quality = Quality.splitCompositeStatus(epObj.status)  # @UnusedVariable
            # TODO: split quality and status?
            return _responds(RESULT_SUCCESS, {"quality": _get_quality_string(quality)}, "Snatched (" + _get_quality_string(quality) + ")")

        return _responds(RESULT_FAILURE, msg='Unable to find episode')


class CMD_EpisodeSetStatus(ApiCall):
    _help = {"desc": "set status of an episode or season (when no ep is provided)",
             "requiredParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"},
                                   "season": {"desc": "the season number"},
                                   "status": {"desc": "the status values: wanted, skipped, archived, ignored"}
                                  },
             "optionalParameters": {"episode": {"desc": "the episode number"},
                                    "force": {"desc": "should we replace existing (downloaded) episodes or not"}
                                     }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, True, "int", [])
        self.s, args = self.check_params(args, kwargs, "season", None, True, "int", [])
        self.status, args = self.check_params(args, kwargs, "status", None, True, "string", ["wanted", "skipped", "archived", "ignored"])
        # optional
        self.e, args = self.check_params(args, kwargs, "episode", None, False, "int", [])
        self.force, args = self.check_params(args, kwargs, "force", 0, False, "bool", [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ set status of an episode or a season (when no ep is provided) """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            return _responds(RESULT_FAILURE, msg="Show not found")

        # convert the string status to a int
        for status in statusStrings.statusStrings:
            if str(statusStrings[status]).lower() == str(self.status).lower():
                self.status = status
                break
        # if we dont break out of the for loop we got here.
        else:
            # the allowed values has at least one item that could not be matched against the internal status strings
            raise ApiError("The status string could not be matched to a status. Report to Devs!")

        ep_list = []
        if self.e:
            epObj = showObj.getEpisode(self.s, self.e)
            if epObj == None:
                return _responds(RESULT_FAILURE, msg="Episode not found")
            ep_list = [epObj]
        else:
            # get all episode numbers frome self,season
            ep_list = showObj.getAllEpisodes(season=self.s)

        def _epResult(result_code, ep, msg=""):
            return {'season': ep.season, 'episode': ep.episode, 'status': _get_status_Strings(ep.status), 'result': result_type_map[result_code], 'message': msg}

        ep_results = []
        failure = False
        start_backlog = False
        ep_segment = None
        for epObj in ep_list:
            if ep_segment == None and self.status == WANTED:
                # figure out what segment the episode is in and remember it so we can backlog it
                if showObj.air_by_date:
                    ep_segment = str(epObj.airdate)[:7]
                else:
                    ep_segment = epObj.season

            with epObj.lock:
                # don't let them mess up UNAIRED episodes
                if epObj.status == UNAIRED:
                    # setting the status of a unaired is only considert a failure if we directly wanted this episode, but is ignored on a season request
                    if self.e != None:
                        ep_results.append(_epResult(RESULT_FAILURE, epObj, "Refusing to change status because it is UNAIRED"))
                        failure = True
                    continue

                # allow the user to force setting the status for an already downloaded episode
                if epObj.status in Quality.DOWNLOADED and not self.force:
                    ep_results.append(_epResult(RESULT_FAILURE, epObj, "Refusing to change status because it is already marked as DOWNLOADED"))
                    failure = True
                    continue

                epObj.status = self.status
                epObj.saveToDB()

                if self.status == WANTED:
                    start_backlog = True
                ep_results.append(_epResult(RESULT_SUCCESS, epObj))

        extra_msg = ""
        if start_backlog:
            cur_backlog_queue_item = search_queue.BacklogQueueItem(showObj, ep_segment)
            sickbeard.searchQueueScheduler.action.add_item(cur_backlog_queue_item)  # @UndefinedVariable
            logger.log(u"API :: Starting backlog for " + showObj.name + " season " + str(ep_segment) + " because some episodes were set to WANTED")
            extra_msg = " Backlog started"

        if failure:
            return _responds(RESULT_FAILURE, ep_results, 'Failed to set all or some status. Check data.' + extra_msg)
        else:
            return _responds(RESULT_SUCCESS, msg='All status set successfully.' + extra_msg)


class CMD_Exceptions(ApiCall):
    _help = {"desc": "display scene exceptions for all or a given show",
             "optionalParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"},
                                  }
             }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, False, "int", [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ display scene exceptions for all or a given show """
        myDB = db.DBConnection("cache.db", row_type="dict")

        if self.tvdbid == None:
            sqlResults = myDB.select("SELECT show_name, tvdb_id AS 'tvdbid' FROM scene_exceptions")
            scene_exceptions = {}
            for row in sqlResults:
                tvdbid = row["tvdbid"]
                if not tvdbid in scene_exceptions:
                    scene_exceptions[tvdbid] = []
                scene_exceptions[tvdbid].append(row["show_name"])

        else:
            showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
            if not showObj:
                return _responds(RESULT_FAILURE, msg="Show not found")

            sqlResults = myDB.select("SELECT show_name, tvdb_id AS 'tvdbid' FROM scene_exceptions WHERE tvdb_id = ?", [self.tvdbid])
            scene_exceptions = []
            for row in sqlResults:
                scene_exceptions.append(row["show_name"])

        myDB.connection.close()
        return _responds(RESULT_SUCCESS, scene_exceptions)


class CMD_History(ApiCall):
    _help = {"desc": "display sickbeard downloaded/snatched history",
             "optionalParameters": {"limit": {"desc": "limit returned results"},
                                    "type": {"desc": "only show a specific type of results"},
                                   }
             }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.limit, args = self.check_params(args, kwargs, "limit", 100, False, "int", [])
        self.type, args = self.check_params(args, kwargs, "type", None, False, "string", ["downloaded", "snatched"])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ display sickbeard downloaded/snatched history """

        typeCodes = []
        if self.type == "downloaded":
            self.type = "Downloaded"
            typeCodes = Quality.DOWNLOADED
        elif self.type == "snatched":
            self.type = "Snatched"
            typeCodes = Quality.SNATCHED
        else:
            typeCodes = Quality.SNATCHED + Quality.DOWNLOADED

        myDB = db.DBConnection(row_type="dict")

        ulimit = min(int(self.limit), 100)
        if ulimit == 0:
            sqlResults = myDB.select("SELECT h.*, show_name FROM history h, tv_shows s WHERE h.showid=s.tvdb_id AND action in (" + ','.join(['?'] * len(typeCodes)) + ") ORDER BY date DESC", typeCodes)
        else:
            sqlResults = myDB.select("SELECT h.*, show_name FROM history h, tv_shows s WHERE h.showid=s.tvdb_id AND action in (" + ','.join(['?'] * len(typeCodes)) + ") ORDER BY date DESC LIMIT ?", typeCodes + [ulimit])

        results = []
        for row in sqlResults:
            status, quality = Quality.splitCompositeStatus(int(row["action"]))
            status = _get_status_Strings(status)
            if self.type and not status == self.type:
                continue
            row["status"] = status
            row["quality"] = _get_quality_string(quality)
            row["date"] = _historyDate_to_dateTimeForm(str(row["date"]))
            del row["action"]
            _rename_element(row, "showid", "tvdbid")
            row["resource_path"] = os.path.dirname(row["resource"])
            row["resource"] = os.path.basename(row["resource"])
            results.append(row)

        myDB.connection.close()
        return _responds(RESULT_SUCCESS, results)


class CMD_HistoryClear(ApiCall):
    _help = {"desc": "clear sickbeard's history",
             }

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ clear sickbeard's history """
        myDB = db.DBConnection()
        myDB.action("DELETE FROM history WHERE 1=1")

        myDB.connection.close()
        return _responds(RESULT_SUCCESS, msg="History cleared")


class CMD_HistoryTrim(ApiCall):
    _help = {"desc": "trim sickbeard's history by removing entries greater than 30 days old"
             }

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ trim sickbeard's history """
        myDB = db.DBConnection()
        myDB.action("DELETE FROM history WHERE date < " + str((datetime.datetime.today() - datetime.timedelta(days=30)).strftime(history.dateFormat)))

        myDB.connection.close()
        return _responds(RESULT_SUCCESS, msg="Removed history entries greater than 30 days old")


class CMD_Logs(ApiCall):
    _help = {"desc": "view sickbeard's log",
             "optionalParameters": {"min_level ": {"desc": "the minimum level classification of log entries to show, with each level inherting its above level"} }
             }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.min_level, args = self.check_params(args, kwargs, "min_level", "error", False, "string", ["error", "warning", "info", "debug"])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ view sickbeard's log """
        # 10 = Debug / 20 = Info / 30 = Warning / 40 = Error
        minLevel = logger.reverseNames[str(self.min_level).upper()]

        data = []
        if os.path.isfile(logger.sb_log_instance.log_file_path):
            with ek.ek(open, logger.sb_log_instance.log_file_path) as f:
                data = f.readlines()

        regex = "^(\d\d\d\d)\-(\d\d)\-(\d\d)\s*(\d\d)\:(\d\d):(\d\d)\s*([A-Z]+)\s*(.+?)\s*\:\:\s*(.*)$"

        finalData = []

        numLines = 0
        lastLine = False
        numToShow = min(50, len(data))

        for x in reversed(data):

            x = x.decode('utf-8')
            match = re.match(regex, x)

            if match:
                level = match.group(7)
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
                finalData.append("AA" + x)

            numLines += 1

            if numLines >= numToShow:
                break

        return _responds(RESULT_SUCCESS, finalData)


class CMD_SickBeard(ApiCall):
    _help = {"desc": "display misc sickbeard related information"}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ display misc sickbeard related information """
        data = {"sb_version": sickbeard.version.SICKBEARD_VERSION, "api_version": Api.version, "api_commands": sorted(_functionMaper.keys())}
        return _responds(RESULT_SUCCESS, data)


class CMD_SickBeardAddRootDir(ApiCall):
    _help = {"desc": "add a sickbeard user's parent directory",
             "requiredParameters": {"location": {"desc": "the full path to root (parent) directory"}
                                    },
             "optionalParameters": {"default": {"desc": "make the location passed the default root (parent) directory"}
                                    }
             }

    def __init__(self, args, kwargs):
        # required
        self.location, args = self.check_params(args, kwargs, "location", None, True, "string", [])
        # optional
        self.default, args = self.check_params(args, kwargs, "default", 0, False, "bool", [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ add a parent directory to sickbeard's config """

        self.location = urllib.unquote_plus(self.location)
        location_matched = 0

        # dissallow adding/setting an invalid dir
        if not ek.ek(os.path.isdir, self.location):
            return _responds(RESULT_FAILURE, msg="Location is invalid")

        root_dirs = []

        if sickbeard.ROOT_DIRS == "":
            self.default = 1
        else:
            root_dirs = sickbeard.ROOT_DIRS.split('|')
            index = int(sickbeard.ROOT_DIRS.split('|')[0])
            root_dirs.pop(0)
            # clean up the list - replace %xx escapes by their single-character equivalent
            root_dirs = [urllib.unquote_plus(x) for x in root_dirs]
            for x in root_dirs:
                if(x == self.location):
                    location_matched = 1
                    if (self.default == 1):
                        index = root_dirs.index(self.location)
                    break

        if(location_matched == 0):
            if (self.default == 1):
                index = 0
                root_dirs.insert(0, self.location)
            else:
                root_dirs.append(self.location)

        root_dirs_new = [urllib.unquote_plus(x) for x in root_dirs]
        root_dirs_new.insert(0, index)
        root_dirs_new = '|'.join(unicode(x) for x in root_dirs_new)

        sickbeard.ROOT_DIRS = root_dirs_new
        return _responds(RESULT_SUCCESS, _getRootDirs(), msg="Root directories updated")


class CMD_SickBeardCheckScheduler(ApiCall):
    _help = {"desc": "query the scheduler"}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ query the scheduler """
        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT last_backlog FROM info")

        backlogPaused = sickbeard.searchQueueScheduler.action.is_backlog_paused()  # @UndefinedVariable
        backlogRunning = sickbeard.searchQueueScheduler.action.is_backlog_in_progress()  # @UndefinedVariable
        searchStatus = sickbeard.currentSearchScheduler.action.amActive  # @UndefinedVariable
        nextSearch = str(sickbeard.currentSearchScheduler.timeLeft()).split('.')[0]
        nextBacklog = sickbeard.backlogSearchScheduler.nextRun().strftime(dateFormat).decode(sickbeard.SYS_ENCODING)

        myDB.connection.close()
        data = {"backlog_is_paused": int(backlogPaused), "backlog_is_running": int(backlogRunning), "last_backlog": _ordinal_to_dateForm(sqlResults[0]["last_backlog"]), "search_is_running": int(searchStatus), "next_search": nextSearch, "next_backlog": nextBacklog}
        return _responds(RESULT_SUCCESS, data)


class CMD_SickBeardDeleteRootDir(ApiCall):
    _help = {"desc": "delete a sickbeard user's parent directory",
             "requiredParameters": {"location": {"desc": "the full path to root (parent) directory"} }
             }

    def __init__(self, args, kwargs):
        # required
        self.location, args = self.check_params(args, kwargs, "location", None, True, "string", [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ delete a parent directory from sickbeard's config """
        if sickbeard.ROOT_DIRS == "":
            return _responds(RESULT_FAILURE, _getRootDirs(), msg="No root directories detected")

        root_dirs_new = []
        root_dirs = sickbeard.ROOT_DIRS.split('|')
        index = int(root_dirs[0])
        root_dirs.pop(0)
        # clean up the list - replace %xx escapes by their single-character equivalent
        root_dirs = [urllib.unquote_plus(x) for x in root_dirs]
        old_root_dir = root_dirs[index]
        for curRootDir in root_dirs:
            if not curRootDir == self.location:
                root_dirs_new.append(curRootDir)
            else:
                newIndex = 0

        for curIndex, curNewRootDir in enumerate(root_dirs_new):
            if curNewRootDir is old_root_dir:
                newIndex = curIndex
                break

        root_dirs_new = [urllib.unquote_plus(x) for x in root_dirs_new]
        if len(root_dirs_new) > 0:
            root_dirs_new.insert(0, newIndex)
        root_dirs_new = "|".join(unicode(x) for x in root_dirs_new)

        sickbeard.ROOT_DIRS = root_dirs_new
        # what if the root dir was not found?
        return _responds(RESULT_SUCCESS, _getRootDirs(), msg="Root directory deleted")


class CMD_SickBeardForceSearch(ApiCall):
    _help = {"desc": "force the episode search early"
             }

    def __init__(self, args, kwargs):
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
            return _responds(RESULT_SUCCESS, msg="Episode search forced")
        return _responds(RESULT_FAILURE, msg="Can not search for episode")


class CMD_SickBeardGetDefaults(ApiCall):
    _help = {"desc": "get sickbeard user defaults"}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ get sickbeard user defaults """

        anyQualities, bestQualities = _mapQuality(sickbeard.QUALITY_DEFAULT)

        data = {"status": statusStrings[sickbeard.STATUS_DEFAULT].lower(), "flatten_folders": int(sickbeard.FLATTEN_FOLDERS_DEFAULT), "initial": anyQualities, "archive": bestQualities, "future_show_paused": int(sickbeard.COMING_EPS_DISPLAY_PAUSED) }
        return _responds(RESULT_SUCCESS, data)


class CMD_SickBeardGetMessages(ApiCall):
    _help = {"desc": "get all messages"}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        messages = []
        for cur_notification in ui.notifications.get_notifications():
            messages.append({"title": cur_notification.title,
                           "message": cur_notification.message,
                           "type": cur_notification.type})
        return _responds(RESULT_SUCCESS, messages)


class CMD_SickBeardGetRootDirs(ApiCall):
    _help = {"desc": "get sickbeard user parent directories"}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ get the parent directories defined in sickbeard's config """

        return _responds(RESULT_SUCCESS, _getRootDirs())


class CMD_SickBeardPauseBacklog(ApiCall):
    _help = {"desc": "pause the backlog search",
             "optionalParameters": {"pause ": {"desc": "pause or unpause the global backlog"} }
             }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.pause, args = self.check_params(args, kwargs, "pause", 0, False, "bool", [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ pause the backlog search """
        if self.pause == True:
            sickbeard.searchQueueScheduler.action.pause_backlog()  # @UndefinedVariable
            return _responds(RESULT_SUCCESS, msg="Backlog paused")
        else:
            sickbeard.searchQueueScheduler.action.unpause_backlog()  # @UndefinedVariable
            return _responds(RESULT_SUCCESS, msg="Backlog unpaused")


class CMD_SickBeardPing(ApiCall):
    _help = {"desc": "check to see if sickbeard is running"}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ check to see if sickbeard is running """
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        if sickbeard.started:
            return _responds(RESULT_SUCCESS, {"pid": sickbeard.PID}, "Pong")
        else:
            return _responds(RESULT_SUCCESS, msg="Pong")


class CMD_SickBeardRestart(ApiCall):
    _help = {"desc": "restart sickbeard"}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ restart sickbeard """
        threading.Timer(2, sickbeard.invoke_restart, [False]).start()
        return _responds(RESULT_SUCCESS, msg="SickBeard is restarting...")


class CMD_SickBeardSearchTVDB(ApiCall):
    _help = {"desc": "search for show at tvdb with a given string and language",
             "optionalParameters": {"name": {"desc": "name of the show you want to search for"},
                                   "tvdbid": {"desc": "thetvdb.com unique id of a show"},
                                     "lang": {"desc": "the 2 letter abbreviation lang id"}
                                     }
             }

    valid_languages = {
            'el': 20, 'en': 7, 'zh': 27, 'it': 15, 'cs': 28, 'es': 16, 'ru': 22,
            'nl': 13, 'pt': 26, 'no': 9, 'tr': 21, 'pl': 18, 'fr': 17, 'hr': 31,
            'de': 14, 'da': 10, 'fi': 11, 'hu': 19, 'ja': 25, 'he': 24, 'ko': 32,
            'sv': 8, 'sl': 30}

    def __init__(self, args, kwargs):
        # required
        # optional
        self.name, args = self.check_params(args, kwargs, "name", None, False, "string", [])
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, False, "int", [])
        self.lang, args = self.check_params(args, kwargs, "lang", "en", False, "string", self.valid_languages.keys())
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ search for show at tvdb with a given string and language """
        # only name was given
        if self.name and not self.tvdbid:
            baseURL = "http://thetvdb.com/api/GetSeries.php?"
            params = {"seriesname": str(self.name).encode('utf-8'), 'language': self.lang}
            finalURL = baseURL + urllib.urlencode(params)
            urlData = sickbeard.helpers.getURL(finalURL)

            if urlData is None:
                return _responds(RESULT_FAILURE, msg="Did not get result from tvdb")
            else:
                try:
                    seriesXML = etree.ElementTree(etree.XML(urlData))
                except Exception, e:
                    logger.log(u"API :: Unable to parse XML for some reason: " + ex(e) + " from XML: " + urlData, logger.ERROR)
                    return _responds(RESULT_FAILURE, msg="Unable to read result from tvdb")

                series = seriesXML.getiterator('Series')
                results = []
                for curSeries in series:
                    results.append({"tvdbid": int(curSeries.findtext('seriesid')),
                                    "name": curSeries.findtext('SeriesName'),
                                    "first_aired": curSeries.findtext('FirstAired')})

                lang_id = self.valid_languages[self.lang]
                return _responds(RESULT_SUCCESS, {"results": results, "langid": lang_id})

        elif self.tvdbid:
            # There's gotta be a better way of doing this but we don't wanna
            # change the language value elsewhere
            ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

            lang_id = self.valid_languages[self.lang]
            if self.lang and not self.lang == 'en':
                ltvdb_api_parms['language'] = self.lang

            t = tvdb_api.Tvdb(actors=False, **ltvdb_api_parms)

            try:
                myShow = t[int(self.tvdbid)]
            except (tvdb_exceptions.tvdb_shownotfound, tvdb_exceptions.tvdb_error):
                logger.log(u"API :: Unable to find show with id " + str(self.tvdbid), logger.WARNING)
                return _responds(RESULT_SUCCESS, {"results": [], "langid": lang_id})

            if not myShow.data['seriesname']:
                logger.log(u"API :: Found show with tvdbid " + str(self.tvdbid) + ", however it contained no show name", logger.DEBUG)
                return _responds(RESULT_FAILURE, msg="Show contains no name, invalid result")

            showOut = [{"tvdbid": self.tvdbid,
                       "name": unicode(myShow.data['seriesname']),
                       "first_aired": myShow.data['firstaired']}]

            return _responds(RESULT_SUCCESS, {"results": showOut, "langid": lang_id})
        else:
            return _responds(RESULT_FAILURE, msg="Either tvdbid or name is required")


class CMD_SickBeardSetDefaults(ApiCall):
    _help = {"desc": "set sickbeard user defaults",
             "optionalParameters": {"initial": {"desc": "initial quality for the show"},
                                    "archive": {"desc": "archive quality for the show"},
                                    "flatten_folders": {"desc": "flatten subfolders within the show directory"},
                                    "status": {"desc": "status of missing episodes"}
                                    }
             }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.initial, args = self.check_params(args, kwargs, "initial", None, False, "list", ["sdtv", "sddvd", "hdtv", "rawhdtv", "fullhdtv", "hdwebdl", "fullhdwebdl", "hdbluray", "fullhdbluray", "unknown"])
        self.archive, args = self.check_params(args, kwargs, "archive", None, False, "list", ["sddvd", "hdtv", "rawhdtv", "fullhdtv", "hdwebdl", "fullhdwebdl", "hdbluray", "fullhdbluray"])
        self.future_show_paused, args = self.check_params(args, kwargs, "future_show_paused", None, False, "bool", [])
        self.flatten_folders, args = self.check_params(args, kwargs, "flatten_folders", None, False, "bool", [])
        self.status, args = self.check_params(args, kwargs, "status", None, False, "string", ["wanted", "skipped", "archived", "ignored"])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ set sickbeard user defaults """

        quality_map = {'sdtv': Quality.SDTV,
                       'sddvd': Quality.SDDVD,
                       'hdtv': Quality.HDTV,
                       'rawhdtv': Quality.RAWHDTV,
                       'fullhdtv': Quality.FULLHDTV,
                       'hdwebdl': Quality.HDWEBDL,
                       'fullhdwebdl': Quality.FULLHDWEBDL,
                       'hdbluray': Quality.HDBLURAY,
                       'fullhdbluray': Quality.FULLHDBLURAY,
                       'unknown': Quality.UNKNOWN}

        iqualityID = []
        aqualityID = []

        if self.initial:
            for quality in self.initial:
                iqualityID.append(quality_map[quality])
        if self.archive:
            for quality in self.archive:
                aqualityID.append(quality_map[quality])

        if iqualityID or aqualityID:
            sickbeard.QUALITY_DEFAULT = Quality.combineQualities(iqualityID, aqualityID)

        if self.status:
            # convert the string status to a int
            for status in statusStrings.statusStrings:
                if statusStrings[status].lower() == str(self.status).lower():
                    self.status = status
                    break
            # this should be obsolete bcause of the above
            if not self.status in statusStrings.statusStrings:
                raise ApiError("Invalid Status")
            #only allow the status options we want
            if int(self.status) not in (3, 5, 6, 7):
                raise ApiError("Status Prohibited")
            sickbeard.STATUS_DEFAULT = self.status

        if self.flatten_folders != None:
            sickbeard.FLATTEN_FOLDERS_DEFAULT = int(self.flatten_folders)

        if self.future_show_paused != None:
            sickbeard.COMING_EPS_DISPLAY_PAUSED = int(self.future_show_paused)

        return _responds(RESULT_SUCCESS, msg="Saved defaults")


class CMD_SickBeardShutdown(ApiCall):
    _help = {"desc": "shutdown sickbeard"}

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ shutdown sickbeard """
        threading.Timer(2, sickbeard.invoke_shutdown).start()
        return _responds(RESULT_SUCCESS, msg="SickBeard is shutting down...")


class CMD_Show(ApiCall):
    _help = {"desc": "display information for a given show",
             "requiredParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"},
                                  }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, True, "int", [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ display information for a given show """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            return _responds(RESULT_FAILURE, msg="Show not found")

        showDict = {}
        showDict["season_list"] = CMD_ShowSeasonList((), {"tvdbid": self.tvdbid}).run()["data"]
        showDict["cache"] = CMD_ShowCache((), {"tvdbid": self.tvdbid}).run()["data"]

        genreList = []
        if showObj.genre:
            genreListTmp = showObj.genre.split("|")
            for genre in genreListTmp:
                if genre:
                    genreList.append(genre)
        showDict["genre"] = genreList
        showDict["quality"] = _get_quality_string(showObj.quality)

        anyQualities, bestQualities = _mapQuality(showObj.quality)
        showDict["quality_details"] = {"initial": anyQualities, "archive": bestQualities}

        try:
            showDict["location"] = showObj.location
        except sickbeard.exceptions.ShowDirNotFoundException:
            showDict["location"] = ""

        showDict["language"] = showObj.lang
        showDict["show_name"] = showObj.name
        showDict["paused"] = showObj.paused
        showDict["air_by_date"] = showObj.air_by_date
        showDict["flatten_folders"] = showObj.flatten_folders
        #clean up tvdb horrible airs field
        showDict["airs"] = str(showObj.airs).replace('am', ' AM').replace('pm', ' PM').replace('  ', ' ')
        showDict["tvrage_id"] = showObj.tvrid
        showDict["tvrage_name"] = showObj.tvrname
        showDict["network"] = showObj.network
        if not showDict["network"]:
            showDict["network"] = ""
        showDict["status"] = showObj.status

        nextAirdate = ''
        nextEps = showObj.nextEpisode()
        if (len(nextEps) != 0):
            nextAirdate = _ordinal_to_dateForm(nextEps[0].airdate.toordinal())
        showDict["next_ep_airdate"] = nextAirdate

        return _responds(RESULT_SUCCESS, showDict)


class CMD_ShowAddExisting(ApiCall):
    _help = {"desc": "add a show in sickbeard with an existing folder",
             "requiredParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"},
                                    "location": {"desc": "full path to the existing folder for the show"}
                                },
             "optionalParameters": {"initial": {"desc": "initial quality for the show"},
                                    "archive": {"desc": "archive quality for the show"},
                                    "flatten_folders": {"desc": "flatten subfolders for the show"}
                                    }
             }

    def __init__(self, args, kwargs):
        # required
        self.location, args = self.check_params(args, kwargs, "location", None, True, "string", [])
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, True, "int", [])
        # optional
        self.initial, args = self.check_params(args, kwargs, "initial", None, False, "list", ["sdtv", "sddvd", "hdtv", "rawhdtv", "fullhdtv", "hdwebdl", "fullhdwebdl", "hdbluray", "fullhdbluray", "unknown"])
        self.archive, args = self.check_params(args, kwargs, "archive", None, False, "list", ["sddvd", "hdtv", "rawhdtv", "fullhdtv", "hdwebdl", "fullhdwebdl", "hdbluray", "fullhdbluray"])
        self.flatten_folders, args = self.check_params(args, kwargs, "flatten_folders", str(sickbeard.FLATTEN_FOLDERS_DEFAULT), False, "bool", [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ add a show in sickbeard with an existing folder """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if showObj:
            return _responds(RESULT_FAILURE, msg="An existing tvdbid already exists in the database")

        if not ek.ek(os.path.isdir, self.location):
            return _responds(RESULT_FAILURE, msg='Not a valid location')

        tvdbName = None
        tvdbResult = CMD_SickBeardSearchTVDB([], {"tvdbid": self.tvdbid}).run()

        if tvdbResult['result'] == result_type_map[RESULT_SUCCESS]:
            if not tvdbResult['data']['results']:
                return _responds(RESULT_FAILURE, msg="Empty results returned, check tvdbid and try again")
            if len(tvdbResult['data']['results']) == 1 and 'name' in tvdbResult['data']['results'][0]:
                tvdbName = tvdbResult['data']['results'][0]['name']

        if not tvdbName:
            return _responds(RESULT_FAILURE, msg="Unable to retrieve information from tvdb")

        quality_map = {'sdtv': Quality.SDTV,
                       'sddvd': Quality.SDDVD,
                       'hdtv': Quality.HDTV,
                       'rawhdtv': Quality.RAWHDTV,
                       'fullhdtv': Quality.FULLHDTV,
                       'hdwebdl': Quality.HDWEBDL,
                       'fullhdwebdl': Quality.FULLHDWEBDL,
                       'hdbluray': Quality.HDBLURAY,
                       'fullhdbluray': Quality.FULLHDBLURAY,
                       'unknown': Quality.UNKNOWN}

        #use default quality as a failsafe
        newQuality = int(sickbeard.QUALITY_DEFAULT)
        iqualityID = []
        aqualityID = []

        if self.initial:
            for quality in self.initial:
                iqualityID.append(quality_map[quality])
        if self.archive:
            for quality in self.archive:
                aqualityID.append(quality_map[quality])

        if iqualityID or aqualityID:
            newQuality = Quality.combineQualities(iqualityID, aqualityID)

        sickbeard.showQueueScheduler.action.addShow(int(self.tvdbid), self.location, SKIPPED, newQuality, int(self.flatten_folders))  # @UndefinedVariable
        return _responds(RESULT_SUCCESS, {"name": tvdbName}, tvdbName + " has been queued to be added")


class CMD_ShowAddNew(ApiCall):
    _help = {"desc": "add a new show to sickbeard",
             "requiredParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"}
                                },
             "optionalParameters": {"initial": {"desc": "initial quality for the show"},
                                    "location": {"desc": "base path for where the show folder is to be created"},
                                    "archive": {"desc": "archive quality for the show"},
                                    "flatten_folders": {"desc": "flatten subfolders for the show"},
                                    "status": {"desc": "status of missing episodes"},
                                    "lang": {"desc": "the 2 letter lang abbreviation id"}
                                    }
             }

    valid_languages = {
            'el': 20, 'en': 7, 'zh': 27, 'it': 15, 'cs': 28, 'es': 16, 'ru': 22,
            'nl': 13, 'pt': 26, 'no': 9, 'tr': 21, 'pl': 18, 'fr': 17, 'hr': 31,
            'de': 14, 'da': 10, 'fi': 11, 'hu': 19, 'ja': 25, 'he': 24, 'ko': 32,
            'sv': 8, 'sl': 30}

    def __init__(self, args, kwargs):
        # required
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, True, "int", [])
        # optional
        self.location, args = self.check_params(args, kwargs, "location", None, False, "string", [])
        self.initial, args = self.check_params(args, kwargs, "initial", None, False, "list", ["sdtv", "sddvd", "hdtv", "rawhdtv", "fullhdtv", "hdwebdl", "fullhdwebdl", "hdbluray", "fullhdbluray", "unknown"])
        self.archive, args = self.check_params(args, kwargs, "archive", None, False, "list", ["sddvd", "hdtv", "rawhdtv", "fullhdtv", "hdwebdl", "fullhdwebdl", "hdbluray", "fullhdbluray"])
        self.flatten_folders, args = self.check_params(args, kwargs, "flatten_folders", str(sickbeard.FLATTEN_FOLDERS_DEFAULT), False, "bool", [])
        self.status, args = self.check_params(args, kwargs, "status", None, False, "string", ["wanted", "skipped", "archived", "ignored"])
        self.lang, args = self.check_params(args, kwargs, "lang", "en", False, "string", self.valid_languages.keys())
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ add a show in sickbeard with an existing folder """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if showObj:
            return _responds(RESULT_FAILURE, msg="An existing tvdbid already exists in database")

        if not self.location:
            if sickbeard.ROOT_DIRS != "":
                root_dirs = sickbeard.ROOT_DIRS.split('|')
                root_dirs.pop(0)
                default_index = int(sickbeard.ROOT_DIRS.split('|')[0])
                self.location = root_dirs[default_index]
            else:
                return _responds(RESULT_FAILURE, msg="Root directory is not set, please provide a location")

        if not ek.ek(os.path.isdir, self.location):
            return _responds(RESULT_FAILURE, msg="'" + self.location + "' is not a valid location")

        quality_map = {'sdtv': Quality.SDTV,
                       'sddvd': Quality.SDDVD,
                       'hdtv': Quality.HDTV,
                       'rawhdtv': Quality.RAWHDTV,
                       'fullhdtv': Quality.FULLHDTV,
                       'hdwebdl': Quality.HDWEBDL,
                       'fullhdwebdl': Quality.FULLHDWEBDL,
                       'hdbluray': Quality.HDBLURAY,
                       'fullhdbluray': Quality.FULLHDBLURAY,
                       'unknown': Quality.UNKNOWN}

        # use default quality as a failsafe
        newQuality = int(sickbeard.QUALITY_DEFAULT)
        iqualityID = []
        aqualityID = []

        if self.initial:
            for quality in self.initial:
                iqualityID.append(quality_map[quality])
        if self.archive:
            for quality in self.archive:
                aqualityID.append(quality_map[quality])

        if iqualityID or aqualityID:
            newQuality = Quality.combineQualities(iqualityID, aqualityID)

        # use default status as a failsafe
        newStatus = sickbeard.STATUS_DEFAULT
        if self.status:
            # convert the string status to a int
            for status in statusStrings.statusStrings:
                if statusStrings[status].lower() == str(self.status).lower():
                    self.status = status
                    break
            #TODO: check if obsolete
            if not self.status in statusStrings.statusStrings:
                raise ApiError("Invalid Status")
            # only allow the status options we want
            if int(self.status) not in (3, 5, 6, 7):
                return _responds(RESULT_FAILURE, msg="Status prohibited")
            newStatus = self.status

        tvdbName = None
        tvdbResult = CMD_SickBeardSearchTVDB([], {"tvdbid": self.tvdbid}).run()

        if tvdbResult['result'] == result_type_map[RESULT_SUCCESS]:
            if not tvdbResult['data']['results']:
                return _responds(RESULT_FAILURE, msg="Empty results returned, check tvdbid and try again")
            if len(tvdbResult['data']['results']) == 1 and 'name' in tvdbResult['data']['results'][0]:
                tvdbName = tvdbResult['data']['results'][0]['name']

        if not tvdbName:
            return _responds(RESULT_FAILURE, msg="Unable to retrieve information from tvdb")

        # moved the logic check to the end in an attempt to eliminate empty directory being created from previous errors
        showPath = ek.ek(os.path.join, self.location, helpers.sanitizeFileName(tvdbName))

        # don't create show dir if config says not to
        if sickbeard.ADD_SHOWS_WO_DIR:
            logger.log(u"Skipping initial creation of " + showPath + " due to config.ini setting")
        else:
            dir_exists = helpers.makeDir(showPath)
            if not dir_exists:
                logger.log(u"API :: Unable to create the folder " + showPath + ", can't add the show", logger.ERROR)
                return _responds(RESULT_FAILURE, {"path": showPath}, "Unable to create the folder " + showPath + ", can't add the show")
            else:
                helpers.chmodAsParent(showPath)

        sickbeard.showQueueScheduler.action.addShow(int(self.tvdbid), showPath, newStatus, newQuality, int(self.flatten_folders), self.lang)  # @UndefinedVariable
        return _responds(RESULT_SUCCESS, {"name": tvdbName}, tvdbName + " has been queued to be added")


class CMD_ShowCache(ApiCall):
    _help = {"desc": "check sickbeard's cache to see if the banner or poster image for a show is valid",
             "requiredParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"}
                                    }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, True, "int", [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ check sickbeard's cache to see if the banner or poster image for a show is valid """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            return _responds(RESULT_FAILURE, msg="Show not found")

        #TODO: catch if cache dir is missing/invalid.. so it doesn't break show/show.cache
        #return {"poster": 0, "banner": 0}

        cache_obj = image_cache.ImageCache()

        has_poster = 0
        has_banner = 0

        if ek.ek(os.path.isfile, cache_obj.poster_path(showObj.tvdbid)):
            has_poster = 1
        if ek.ek(os.path.isfile, cache_obj.banner_path(showObj.tvdbid)):
            has_banner = 1

        return _responds(RESULT_SUCCESS, {"poster": has_poster, "banner": has_banner})


class CMD_ShowDelete(ApiCall):
    _help = {"desc": "delete a show in sickbeard",
             "requiredParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"},
                                  }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, True, "int", [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ delete a show in sickbeard """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            return _responds(RESULT_FAILURE, msg="Show not found")

        if sickbeard.showQueueScheduler.action.isBeingAdded(showObj) or sickbeard.showQueueScheduler.action.isBeingUpdated(showObj):  # @UndefinedVariable
            return _responds(RESULT_FAILURE, msg="Show can not be deleted while being added or updated")

        showObj.deleteShow()
        return _responds(RESULT_SUCCESS, msg=u"" + showObj.name + " has been deleted")


class CMD_ShowGetQuality(ApiCall):
    _help = {"desc": "get quality setting for a show in sickbeard",
             "requiredParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"}
                                }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, True, "int", [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ get quality setting for a show in sickbeard """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            return _responds(RESULT_FAILURE, msg="Show not found")

        anyQualities, bestQualities = _mapQuality(showObj.quality)

        return _responds(RESULT_SUCCESS, {"initial": anyQualities, "archive": bestQualities})


class CMD_ShowGetPoster(ApiCall):
    _help = {"desc": "get the poster stored for a show in sickbeard",
             "requiredParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"}
                                }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, True, "int", [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ get the poster for a show in sickbeard """
        return {'outputType': 'image', 'image': webserve.WebInterface().showPoster(self.tvdbid, 'poster')}


class CMD_ShowGetBanner(ApiCall):
    _help = {"desc": "get the banner stored for a show in sickbeard",
             "requiredParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"}
                                }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, True, "int", [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ get the banner for a show in sickbeard """
        return {'outputType': 'image', 'image': webserve.WebInterface().showPoster(self.tvdbid, 'banner')}


class CMD_ShowPause(ApiCall):
    _help = {"desc": "set a show's paused state in sickbeard",
             "requiredParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"},
                                  },
             "optionalParameters": {"pause": {"desc": "set the pause state of the show"}
                                  }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, True, "int", [])
        # optional
        self.pause, args = self.check_params(args, kwargs, "pause", 0, False, "bool", [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ set a show's paused state in sickbeard """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            return _responds(RESULT_FAILURE, msg="Show not found")

        if self.pause == True:
            showObj.paused = 1
            return _responds(RESULT_SUCCESS, msg=u"" + showObj.name + " has been paused")
        else:
            showObj.paused = 0
            return _responds(RESULT_SUCCESS, msg=u"" + showObj.name + " has been unpaused")

        return _responds(RESULT_FAILURE, msg=u"" + showObj.name + " was unable to be paused")


class CMD_ShowRefresh(ApiCall):
    _help = {"desc": "refresh a show in sickbeard",
             "requiredParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"},
                                  }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, True, "int", [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ refresh a show in sickbeard """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            return _responds(RESULT_FAILURE, msg="Show not found")

        try:
            sickbeard.showQueueScheduler.action.refreshShow(showObj)  # @UndefinedVariable
            return _responds(RESULT_SUCCESS, msg=u"" + showObj.name + " has queued to be refreshed")
        except exceptions.CantRefreshException, e:
            logger.log(u"API:: Unable to refresh " + showObj.name + ". " + str(ex(e)), logger.ERROR)
            return _responds(RESULT_FAILURE, msg=u"Unable to refresh " + showObj.name)


class CMD_ShowSeasonList(ApiCall):
    _help = {"desc": "display the season list for a given show",
             "requiredParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"},
                                    },
             "optionalParameters": {"sort": {"desc": "change the sort order from descending to ascending"}
                                     }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, True, "int", [])
        # optional
        self.sort, args = self.check_params(args, kwargs, "sort", "desc", False, "string", ["asc", "desc"])  # "asc" and "desc" default and fallback is "desc"
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ display the season list for a given show """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            return _responds(RESULT_FAILURE, msg="Show not found")

        myDB = db.DBConnection(row_type="dict")
        if self.sort == "asc":
            sqlResults = myDB.select("SELECT DISTINCT season FROM tv_episodes WHERE showid = ? ORDER BY season ASC", [self.tvdbid])
        else:
            sqlResults = myDB.select("SELECT DISTINCT season FROM tv_episodes WHERE showid = ? ORDER BY season DESC", [self.tvdbid])
        # a list with all season numbers
        seasonList = []
        for row in sqlResults:
            seasonList.append(int(row["season"]))

        myDB.connection.close()
        return _responds(RESULT_SUCCESS, seasonList)


class CMD_ShowSeasons(ApiCall):
    _help = {"desc": "display a listing of episodes for all or a given season",
             "requiredParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"},
                                  },
             "optionalParameters": {"season": {"desc": "the season number"},
                                  }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, True, "int", [])
        # optional
        self.season, args = self.check_params(args, kwargs, "season", None, False, "int", [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ display a listing of episodes for all or a given show """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            return _responds(RESULT_FAILURE, msg="Show not found")

        myDB = db.DBConnection(row_type="dict")

        if self.season == None:
            sqlResults = myDB.select("SELECT name, episode, airdate, status, season FROM tv_episodes WHERE showid = ?", [self.tvdbid])
            seasons = {}
            for row in sqlResults:
                status, quality = Quality.splitCompositeStatus(int(row["status"]))
                row["status"] = _get_status_Strings(status)
                row["quality"] = _get_quality_string(quality)
                row["airdate"] = _ordinal_to_dateForm(row["airdate"])
                curSeason = int(row["season"])
                curEpisode = int(row["episode"])
                del row["season"]
                del row["episode"]
                if not curSeason in seasons:
                    seasons[curSeason] = {}
                seasons[curSeason][curEpisode] = row

        else:
            sqlResults = myDB.select("SELECT name, episode, airdate, status FROM tv_episodes WHERE showid = ? AND season = ?", [self.tvdbid, self.season])
            if len(sqlResults) is 0:
                return _responds(RESULT_FAILURE, msg="Season not found")
            seasons = {}
            for row in sqlResults:
                curEpisode = int(row["episode"])
                del row["episode"]
                status, quality = Quality.splitCompositeStatus(int(row["status"]))
                row["status"] = _get_status_Strings(status)
                row["quality"] = _get_quality_string(quality)
                row["airdate"] = _ordinal_to_dateForm(row["airdate"])
                if not curEpisode in seasons:
                    seasons[curEpisode] = {}
                seasons[curEpisode] = row

        myDB.connection.close()
        return _responds(RESULT_SUCCESS, seasons)


class CMD_ShowSetQuality(ApiCall):
    _help = {"desc": "set desired quality of a show in sickbeard. if neither initial or archive are provided then the config default quality will be used",
             "requiredParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"}
                                },
             "optionalParameters": {"initial": {"desc": "initial quality for the show"},
                                    "archive": {"desc": "archive quality for the show"}
                                    }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, True, "int", [])
        # optional
        # this for whatever reason removes hdbluray not sdtv... which is just wrong. reverting to previous code.. plus we didnt use the new code everywhere.
        # self.archive, args = self.check_params(args, kwargs, "archive", None, False, "list", _getQualityMap().values()[1:])
        self.initial, args = self.check_params(args, kwargs, "initial", None, False, "list", ["sdtv", "sddvd", "hdtv", "rawhdtv", "fullhdtv", "hdwebdl", "fullhdwebdl", "hdbluray", "fullhdbluray", "unknown"])
        self.archive, args = self.check_params(args, kwargs, "archive", None, False, "list", ["sddvd", "hdtv", "rawhdtv", "fullhdtv", "hdwebdl", "fullhdwebdl", "hdbluray", "fullhdbluray"])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ set the quality for a show in sickbeard by taking in a deliminated
            string of qualities, map to their value and combine for new values
        """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            return _responds(RESULT_FAILURE, msg="Show not found")

        quality_map = {'sdtv': Quality.SDTV,
                       'sddvd': Quality.SDDVD,
                       'hdtv': Quality.HDTV,
                       'rawhdtv': Quality.RAWHDTV,
                       'fullhdtv': Quality.FULLHDTV,
                       'hdwebdl': Quality.HDWEBDL,
                       'fullhdwebdl': Quality.FULLHDWEBDL,
                       'hdbluray': Quality.HDBLURAY,
                       'fullhdbluray': Quality.FULLHDBLURAY,
                       'unknown': Quality.UNKNOWN}

        #use default quality as a failsafe
        newQuality = int(sickbeard.QUALITY_DEFAULT)
        iqualityID = []
        aqualityID = []

        if self.initial:
            for quality in self.initial:
                iqualityID.append(quality_map[quality])
        if self.archive:
            for quality in self.archive:
                aqualityID.append(quality_map[quality])

        if iqualityID or aqualityID:
            newQuality = Quality.combineQualities(iqualityID, aqualityID)
        showObj.quality = newQuality

        return _responds(RESULT_SUCCESS, msg=showObj.name + " quality has been changed to " + _get_quality_string(showObj.quality))


class CMD_ShowStats(ApiCall):
    _help = {"desc": "display episode statistics for a given show",
             "requiredParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"},
                                  }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, True, "int", [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ display episode statistics for a given show """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            return _responds(RESULT_FAILURE, msg="Show not found")

        # show stats
        episode_status_counts_total = {}
        episode_status_counts_total["total"] = 0
        for status in statusStrings.statusStrings.keys():
            if status in [UNKNOWN, DOWNLOADED, SNATCHED, SNATCHED_PROPER]:
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
        sqlResults = myDB.select("SELECT status, season FROM tv_episodes WHERE season > 0 AND episode > 0 AND airdate > 1 AND showid = ?", [self.tvdbid])
        # the main loop that goes through all episodes
        for row in sqlResults:
            status, quality = Quality.splitCompositeStatus(int(row["status"]))

            episode_status_counts_total["total"] += 1

            if status in Quality.DOWNLOADED:
                episode_qualities_counts_download["total"] += 1
                episode_qualities_counts_download[int(row["status"])] += 1
            elif status in Quality.SNATCHED + Quality.SNATCHED_PROPER:
                episode_qualities_counts_snatch["total"] += 1
                episode_qualities_counts_snatch[int(row["status"])] += 1
            # we dont count NONE = 0 = N/A
            elif status == 0:
                pass
            else:
                episode_status_counts_total[status] += 1

        # the outgoing container
        episodes_stats = {}
        episodes_stats["downloaded"] = {}
        # turning codes into strings
        for statusCode in episode_qualities_counts_download:
            if statusCode is "total":
                episodes_stats["downloaded"]["total"] = episode_qualities_counts_download[statusCode]
                continue
            status, quality = Quality.splitCompositeStatus(int(statusCode))
            quality_string = Quality.qualityStrings[quality].lower().replace(" ", "_").replace("(", "").replace(")", "")
            episodes_stats["downloaded"][quality_string] = episode_qualities_counts_download[statusCode]

        episodes_stats["snatched"] = {}
        # turning codes into strings
        for statusCode in episode_qualities_counts_snatch:
            if statusCode is "total":
                episodes_stats["snatched"]["total"] = episode_qualities_counts_snatch[statusCode]
                continue
            status, quality = Quality.splitCompositeStatus(int(statusCode))
            quality_string = Quality.qualityStrings[quality].lower().replace(" ", "_").replace("(", "").replace(")", "")

            # count qualities for snatched and snatched_proper
            if quality_string in episodes_stats["snatched"]:
                episodes_stats["snatched"][quality_string] += episode_qualities_counts_snatch[statusCode]
            else:
                episodes_stats["snatched"][quality_string] = episode_qualities_counts_snatch[statusCode]

        #episodes_stats["total"] = {}
        for statusCode in episode_status_counts_total:
            if statusCode is "total":
                episodes_stats["total"] = episode_status_counts_total[statusCode]
                continue
            status, quality = Quality.splitCompositeStatus(int(statusCode))
            statusString = statusStrings.statusStrings[statusCode].lower().replace(" ", "_").replace("(", "").replace(")", "")
            episodes_stats[statusString] = episode_status_counts_total[statusCode]

        myDB.connection.close()
        return _responds(RESULT_SUCCESS, episodes_stats)


class CMD_ShowUpdate(ApiCall):
    _help = {"desc": "update a show in sickbeard",
             "requiredParameters": {"tvdbid": {"desc": "thetvdb.com unique id of a show"},
                                  }
             }

    def __init__(self, args, kwargs):
        # required
        self.tvdbid, args = self.check_params(args, kwargs, "tvdbid", None, True, "int", [])
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ update a show in sickbeard """
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(self.tvdbid))
        if not showObj:
            return _responds(RESULT_FAILURE, msg="Show not found")

        try:
            sickbeard.showQueueScheduler.action.updateShow(showObj, True)  # @UndefinedVariable
            return _responds(RESULT_SUCCESS, msg=u"" + showObj.name + " has queued to be updated")
        except exceptions.CantUpdateException, e:
            logger.log(u"API:: Unable to update " + showObj.name + ". " + str(ex(e)), logger.ERROR)
            return _responds(RESULT_FAILURE, msg=u"Unable to update " + showObj.name)


class CMD_Shows(ApiCall):
    _help = {"desc": "display all shows in sickbeard",
             "optionalParameters": {"sort": {"desc": "sort the list of shows by show name instead of tvdbid"},
                                    "paused": {"desc": "only show the shows that are set to paused"},
                                  },
             }

    def __init__(self, args, kwargs):
        # required
        # optional
        self.sort, args = self.check_params(args, kwargs, "sort", "id", False, "string", ["id", "name"])
        self.paused, args = self.check_params(args, kwargs, "paused", None, False, "bool", [])
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ display_is_int_multi( self.tvdbid )shows in sickbeard """
        shows = {}
        for curShow in sickbeard.showList:
            nextAirdate = ''
            nextEps = curShow.nextEpisode()
            if (len(nextEps) != 0):
                nextAirdate = _ordinal_to_dateForm(nextEps[0].airdate.toordinal())

            if self.paused != None and bool(self.paused) != bool(curShow.paused):
                continue

            showDict = {"paused": curShow.paused,
                        "quality": _get_quality_string(curShow.quality),
                        "language": curShow.lang,
                        "air_by_date": curShow.air_by_date,
                        "tvdbid": curShow.tvdbid,
                        "tvrage_id": curShow.tvrid,
                        "tvrage_name": curShow.tvrname,
                        "network": curShow.network,
                        "show_name": curShow.name,
                        "status": curShow.status,
                        "next_ep_airdate": nextAirdate}
            showDict["cache"] = CMD_ShowCache((), {"tvdbid": curShow.tvdbid}).run()["data"]
            if not showDict["network"]:
                showDict["network"] = ""
            if self.sort == "name":
                shows[curShow.name] = showDict
            else:
                shows[curShow.tvdbid] = showDict
        return _responds(RESULT_SUCCESS, shows)


class CMD_ShowsStats(ApiCall):
    _help = {"desc": "display the global shows and episode stats"
             }

    def __init__(self, args, kwargs):
        # required
        # optional
        # super, missing, help
        ApiCall.__init__(self, args, kwargs)

    def run(self):
        """ display the global shows and episode stats """
        stats = {}

        myDB = db.DBConnection()
        today = str(datetime.date.today().toordinal())
        status_quality = '(' + ','.join([str(quality) for quality in Quality.SNATCHED + Quality.SNATCHED_PROPER]) + ')'
        status_download = '(' + ','.join([str(quality) for quality in Quality.DOWNLOADED + [ARCHIVED]]) + ')'

        sql_statement = 'SELECT '

        sql_statement += '(SELECT COUNT(*) FROM tv_episodes WHERE season > 0 AND episode > 0 AND airdate > 1 AND status IN ' + status_quality + ') AS ep_snatched, '
        sql_statement += '(SELECT COUNT(*) FROM tv_episodes WHERE season > 0 AND episode > 0 AND airdate > 1 AND status IN ' + status_download + ') AS ep_downloaded, '

        sql_statement += '(SELECT COUNT(*) FROM tv_episodes WHERE season > 0 AND episode > 0 AND airdate > 1 '
        sql_statement += ' AND ((airdate <= ' + today + ' AND (status = ' + str(SKIPPED) + ' OR status = ' + str(WANTED) + ')) '
        sql_statement += ' OR (status IN ' + status_quality + ') OR (status IN ' + status_download + '))) AS ep_total '

        sql_statement += ' FROM tv_episodes tv_eps LIMIT 1'

        sql_result = myDB.select(sql_statement)

        stats["shows_total"] = len(sickbeard.showList)
        stats["shows_active"] = len([show for show in sickbeard.showList if show.paused == 0 and show.status != "Ended"])

        if sql_result:
            stats["ep_snatched"] = sql_result[0]['ep_snatched']
            stats["ep_downloaded"] = sql_result[0]['ep_downloaded']
            stats["ep_total"] = sql_result[0]['ep_total']
        else:
            stats["ep_snatched"] = 0
            stats["ep_downloaded"] = 0
            stats["ep_total"] = 0

        myDB.connection.close()
        return _responds(RESULT_SUCCESS, stats)

# WARNING: never define a cmd call string that contains a "_" (underscore)
# this is reserved for cmd indexes used while cmd chaining

# WARNING: never define a param name that contains a "." (dot)
# this is reserved for cmd namspaces used while cmd chaining
_functionMaper = {"help": CMD_Help,
                  "future": CMD_ComingEpisodes,
                  "episode": CMD_Episode,
                  "episode.search": CMD_EpisodeSearch,
                  "episode.setstatus": CMD_EpisodeSetStatus,
                  "exceptions": CMD_Exceptions,
                  "history": CMD_History,
                  "history.clear": CMD_HistoryClear,
                  "history.trim": CMD_HistoryTrim,
                  "logs": CMD_Logs,
                  "sb": CMD_SickBeard,
                  "sb.addrootdir": CMD_SickBeardAddRootDir,
                  "sb.checkscheduler": CMD_SickBeardCheckScheduler,
                  "sb.deleterootdir": CMD_SickBeardDeleteRootDir,
                  "sb.forcesearch": CMD_SickBeardForceSearch,
                  "sb.getdefaults": CMD_SickBeardGetDefaults,
                  "sb.getmessages": CMD_SickBeardGetMessages,
                  "sb.getrootdirs": CMD_SickBeardGetRootDirs,
                  "sb.pausebacklog": CMD_SickBeardPauseBacklog,
                  "sb.ping": CMD_SickBeardPing,
                  "sb.restart": CMD_SickBeardRestart,
                  "sb.searchtvdb": CMD_SickBeardSearchTVDB,
                  "sb.setdefaults": CMD_SickBeardSetDefaults,
                  "sb.shutdown": CMD_SickBeardShutdown,
                  "show": CMD_Show,
                  "show.addexisting": CMD_ShowAddExisting,
                  "show.addnew": CMD_ShowAddNew,
                  "show.cache": CMD_ShowCache,
                  "show.delete": CMD_ShowDelete,
                  "show.getquality": CMD_ShowGetQuality,
                  "show.getposter": CMD_ShowGetPoster,
                  "show.getbanner": CMD_ShowGetBanner,
                  "show.pause": CMD_ShowPause,
                  "show.refresh": CMD_ShowRefresh,
                  "show.seasonlist": CMD_ShowSeasonList,
                  "show.seasons": CMD_ShowSeasons,
                  "show.setquality": CMD_ShowSetQuality,
                  "show.stats": CMD_ShowStats,
                  "show.update": CMD_ShowUpdate,
                  "shows": CMD_Shows,
                  "shows.stats": CMD_ShowsStats
                  }
