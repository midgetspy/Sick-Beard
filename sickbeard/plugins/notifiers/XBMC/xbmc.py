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

import urllib
import urllib2
import socket
import base64
import time

import sickbeard

from sickbeard import logger
from sickbeard import common
from sickbeard.exceptions import ex
from sickbeard.encodingKludge import fixStupidEncodings

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

try:
    import json
except ImportError:
    from lib import simplejson as json

from sickbeard.INotifierPlugin import INotifierPlugin
from sickbeard.config import CheckSection, check_setting_int, check_setting_str, ConfigMigrator

from sickbeard.webserve import Home
import cherrypy
import os

class XBMCNotifier(INotifierPlugin):

    def _get_json_version(self, host, username, password):
        """Returns XBMC JSON-RPC API version (odd # = dev, even # = stable)

        Sends a request to the XBMC host using the JSON-RPC to determine if
        the legacy API or if the JSON-RPC API functions should be used.

        Args:
            host: XBMC webserver host:port
            username: XBMC webserver username
            password: XBMC webserver password

        Returns:
            Returns API number or False

            List of possible known values:
                API | XBMC Version
               -----+---------------
                 2  | v10 (Dharma)
                 3  | (pre Eden)
                 4  | v11 (Eden)
                 5  | (pre Frodo)
                 6  | v12 (Frodo)

        """

        # since we need to maintain python 2.5 compatability we can not pass a timeout delay to urllib2 directly (python 2.6+)
        # override socket timeout to reduce delay for this call alone
        socket.setdefaulttimeout(10)

        checkCommand = '{"jsonrpc":"2.0","method":"JSONRPC.Version","id":1}'
        result = self._send_to_xbmc_json(checkCommand, host, username, password)

        # revert back to default socket timeout
        socket.setdefaulttimeout(sickbeard.SOCKET_TIMEOUT)

        if result:
            return result["result"]["version"]
        else:
            return False

    def _notify_xbmc(self, message, title="Sick Beard", host=None, username=None, password=None, force=False):
        """Internal wrapper for the notify_snatch and notify_download functions

        Detects JSON-RPC version then branches the logic for either the JSON-RPC or legacy HTTP API methods.

        Args:
            message: Message body of the notice to send
            title: Title of the notice to send
            host: XBMC webserver host:port
            username: XBMC webserver username
            password: XBMC webserver password
            force: Used for the Test method to override config saftey checks

        Returns:
            Returns a list results in the format of host:ip:result
            The result will either be 'OK' or False, this is used to be parsed by the calling function.

        """

        # fill in omitted parameters
        if not host:
            host = self.XBMC_HOST
        if not username:
            username = self.XBMC_USERNAME
        if not password:
            password = self.XBMC_PASSWORD

        # suppress notifications if the notifier is disabled but the notify options are checked
        if not self.USE_XBMC and not force:
            logger.log("Notification for XBMC not enabled, skipping this notification", logger.DEBUG)
            return False

        result = ''
        for curHost in [x.strip() for x in host.split(",")]:
            logger.log(u"Sending XBMC notification to '" + curHost + "' - " + message, logger.MESSAGE)

            xbmcapi = self._get_json_version(curHost, username, password)
            if xbmcapi:
                if (xbmcapi <= 4):
                    logger.log(u"Detected XBMC version <= 11, using XBMC HTTP API", logger.DEBUG)
                    command = {'command': 'ExecBuiltIn', 'parameter': 'Notification(' + title.encode("utf-8") + ',' + message.encode("utf-8") + ')'}
                    notifyResult = self._send_to_xbmc(command, curHost, username, password)
                    if notifyResult:
                        result += curHost + ':' + str(notifyResult)
                else:
                    logger.log(u"Detected XBMC version >= 12, using XBMC JSON API", logger.DEBUG)
                    command = '{"jsonrpc":"2.0","method":"GUI.ShowNotification","params":{"title":"%s","message":"%s"},"id":1}' % (title.encode("utf-8"), message.encode("utf-8"))
                    notifyResult = self._send_to_xbmc_json(command, curHost, username, password)
                    if notifyResult:
                        result += curHost + ':' + notifyResult["result"].decode(sickbeard.SYS_ENCODING)
            else:
                logger.log(u"Failed to detect XBMC version for '" + curHost + "', check configuration and try again.", logger.DEBUG)

        return result

##############################################################################
# Legacy HTTP API (pre XBMC 12) methods
##############################################################################

    def _send_to_xbmc(self, command, host=None, username=None, password=None):
        """Handles communication to XBMC servers via HTTP API

        Args:
            command: Dictionary of field/data pairs, encoded via urllib and passed to the XBMC API via HTTP
            host: XBMC webserver host:port
            username: XBMC webserver username
            password: XBMC webserver password

        Returns:
            Returns response.result for successful commands or False if there was an error

        """

        # fill in omitted parameters
        if not username:
            username = self.XBMC_USERNAME
        if not password:
            password = self.XBMC_PASSWORD

        if not host:
            logger.log(u'No XBMC host passed, aborting update', logger.DEBUG)
            return False

        for key in command:
            if type(command[key]) == unicode:
                command[key] = command[key].encode('utf-8')

        enc_command = urllib.urlencode(command)
        logger.log(u"XBMC encoded API command: " + enc_command, logger.DEBUG)

        url = 'http://%s/xbmcCmds/xbmcHttp/?%s' % (host, enc_command)
        try:
            req = urllib2.Request(url)
            # if we have a password, use authentication
            if password:
                base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
                authheader = "Basic %s" % base64string
                req.add_header("Authorization", authheader)
                logger.log(u"Contacting XBMC (with auth header) via url: " + fixStupidEncodings(url), logger.DEBUG)
            else:
                logger.log(u"Contacting XBMC via url: " + fixStupidEncodings(url), logger.DEBUG)

            response = urllib2.urlopen(req)
            result = response.read().decode(sickbeard.SYS_ENCODING)
            response.close()

            logger.log(u"XBMC HTTP response: " + result.replace('\n', ''), logger.DEBUG)
            return result

        except (urllib2.URLError, IOError), e:
            logger.log(u"Warning: Couldn't contact XBMC HTTP at " + fixStupidEncodings(url) + " " + ex(e), logger.WARNING)
            return False

    def _update_library(self, host=None, showName=None):
        """Handles updating XBMC host via HTTP API

        Attempts to update the XBMC video library for a specific tv show if passed,
        otherwise update the whole library if enabled.

        Args:
            host: XBMC webserver host:port
            showName: Name of a TV show to specifically target the library update for

        Returns:
            Returns True or False

        """

        if not host:
            logger.log(u'No XBMC host passed, aborting update', logger.DEBUG)
            return False

        logger.log(u"Updating XMBC library via HTTP method for host: " + host, logger.DEBUG)

        # if we're doing per-show
        if showName:
            logger.log(u"Updating library in XBMC via HTTP method for show " + showName, logger.DEBUG)

            pathSql = 'select path.strPath from path, tvshow, tvshowlinkpath where ' \
                'tvshow.c00 = "%s" and tvshowlinkpath.idShow = tvshow.idShow ' \
                'and tvshowlinkpath.idPath = path.idPath' % (showName)

            # use this to get xml back for the path lookups
            xmlCommand = {'command': 'SetResponseFormat(webheader;false;webfooter;false;header;<xml>;footer;</xml>;opentag;<tag>;closetag;</tag>;closefinaltag;false)'}
            # sql used to grab path(s)
            sqlCommand = {'command': 'QueryVideoDatabase(%s)' % (pathSql)}
            # set output back to default
            resetCommand = {'command': 'SetResponseFormat()'}

            # set xml response format, if this fails then don't bother with the rest
            request = self._send_to_xbmc(xmlCommand, host)
            if not request:
                return False

            sqlXML = self._send_to_xbmc(sqlCommand, host)
            request = self._send_to_xbmc(resetCommand, host)

            if not sqlXML:
                logger.log(u"Invalid response for " + showName + " on " + host, logger.DEBUG)
                return False

            encSqlXML = urllib.quote(sqlXML, ':\\/<>')
            try:
                et = etree.fromstring(encSqlXML)
            except SyntaxError, e:
                logger.log(u"Unable to parse XML returned from XBMC: " + ex(e), logger.ERROR)
                return False

            paths = et.findall('.//field')

            if not paths:
                logger.log(u"No valid paths found for " + showName + " on " + host, logger.DEBUG)
                return False

            for path in paths:
                # Don't need it double-encoded, gawd this is dumb
                unEncPath = urllib.unquote(path.text).decode(sickbeard.SYS_ENCODING)
                logger.log(u"XBMC Updating " + showName + " on " + host + " at " + unEncPath, logger.DEBUG)
                updateCommand = {'command': 'ExecBuiltIn', 'parameter': 'XBMC.updatelibrary(video, %s)' % (unEncPath)}
                request = self._send_to_xbmc(updateCommand, host)
                if not request:
                    logger.log(u"Update of show directory failed on " + showName + " on " + host + " at " + unEncPath, logger.ERROR)
                    return False
                # sleep for a few seconds just to be sure xbmc has a chance to finish each directory
                if len(paths) > 1:
                    time.sleep(5)
        # do a full update if requested
        else:
            logger.log(u"Doing Full Library XBMC update on host: " + host, logger.DEBUG)
            updateCommand = {'command': 'ExecBuiltIn', 'parameter': 'XBMC.updatelibrary(video)'}
            request = self._send_to_xbmc(updateCommand, host)

            if not request:
                logger.log(u"XBMC Full Library update failed on: " + host, logger.ERROR)
                return False

        return True

##############################################################################
# JSON-RPC API (XBMC 12+) methods
##############################################################################

    def _send_to_xbmc_json(self, command, host=None, username=None, password=None):
        """Handles communication to XBMC servers via JSONRPC

        Args:
            command: Dictionary of field/data pairs, encoded via urllib and passed to the XBMC JSON-RPC via HTTP
            host: XBMC webserver host:port
            username: XBMC webserver username
            password: XBMC webserver password

        Returns:
            Returns response.result for successful commands or False if there was an error

        """

        # fill in omitted parameters
        if not username:
            username = self.XBMC_USERNAME
        if not password:
            password = self.XBMC_PASSWORD

        if not host:
            logger.log(u'No XBMC host passed, aborting update', logger.DEBUG)
            return False

        command = command.encode('utf-8')
        logger.log(u"XBMC JSON command: " + command, logger.DEBUG)

        url = 'http://%s/jsonrpc' % (host)
        try:
            req = urllib2.Request(url, command)
            req.add_header("Content-type", "application/json")
            # if we have a password, use authentication
            if password:
                base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
                authheader = "Basic %s" % base64string
                req.add_header("Authorization", authheader)
                logger.log(u"Contacting XBMC (with auth header) via url: " + fixStupidEncodings(url), logger.DEBUG)
            else:
                logger.log(u"Contacting XBMC via url: " + fixStupidEncodings(url), logger.DEBUG)

            try:
                response = urllib2.urlopen(req)
            except urllib2.URLError, e:
                logger.log(u"Error while trying to retrieve XBMC API version for " + host + ": " + ex(e), logger.WARNING)
                return False

            # parse the json result
            try:
                result = json.load(response)
                response.close()
                logger.log(u"XBMC JSON response: " + str(result), logger.DEBUG)
                return result # need to return response for parsing
            except ValueError, e:
                logger.log(u"Unable to decode JSON: " + response, logger.WARNING)
                return False

        except IOError, e:
            logger.log(u"Warning: Couldn't contact XBMC JSON API at " + fixStupidEncodings(url) + " " + ex(e), logger.WARNING)
            return False

    def _update_library_json(self, host=None, showName=None):
        """Handles updating XBMC host via HTTP JSON-RPC

        Attempts to update the XBMC video library for a specific tv show if passed,
        otherwise update the whole library if enabled.

        Args:
            host: XBMC webserver host:port
            showName: Name of a TV show to specifically target the library update for

        Returns:
            Returns True or False

        """

        if not host:
            logger.log(u'No XBMC host passed, aborting update', logger.DEBUG)
            return False

        logger.log(u"Updating XMBC library via JSON method for host: " + host, logger.MESSAGE)

        # if we're doing per-show
        if showName:
            tvshowid = -1
            logger.log(u"Updating library in XBMC via JSON method for show " + showName, logger.DEBUG)

            # get tvshowid by showName
            showsCommand = '{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShows","id":1}'
            showsResponse = self._send_to_xbmc_json(showsCommand, host)
            if (showsResponse == False):
                return False
            shows = showsResponse["result"]["tvshows"]

            for show in shows:
                if (show["label"] == showName):
                    tvshowid = show["tvshowid"]
                    break # exit out of loop otherwise the label and showname will not match up

            # this can be big, so free some memory
            del shows

            # we didn't find the show (exact match), thus revert to just doing a full update if enabled
            if (tvshowid == -1):
                logger.log(u'Exact show name not matched in XBMC TV show list', logger.DEBUG)
                return False

            # lookup tv-show path
            pathCommand = '{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShowDetails","params":{"tvshowid":%d, "properties": ["file"]},"id":1}' % (tvshowid)
            pathResponse = self._send_to_xbmc_json(pathCommand, host)

            path = pathResponse["result"]["tvshowdetails"]["file"]
            logger.log(u"Received Show: " + show["label"] + " with ID: " + str(tvshowid) + " Path: " + path, logger.DEBUG)

            if (len(path) < 1):
                logger.log(u"No valid path found for " + showName + " with ID: " + str(tvshowid) + " on " + host, logger.WARNING)
                return False

            logger.log(u"XBMC Updating " + showName + " on " + host + " at " + path, logger.DEBUG)
            updateCommand = '{"jsonrpc":"2.0","method":"VideoLibrary.Scan","params":{"directory":%s},"id":1}' % (json.dumps(path))
            request = self._send_to_xbmc_json(updateCommand, host)
            if not request:
                logger.log(u"Update of show directory failed on " + showName + " on " + host + " at " + path, logger.ERROR)
                return False

            # catch if there was an error in the returned request
            for r in request:
                if 'error' in r:
                    logger.log(u"Error while attempting to update show directory for " + showName + " on " + host + " at " + path, logger.ERROR)
                    return False

        # do a full update if requested
        else:
            logger.log(u"Doing Full Library XBMC update on host: " + host, logger.MESSAGE)
            updateCommand = '{"jsonrpc":"2.0","method":"VideoLibrary.Scan","id":1}'
            request = self._send_to_xbmc_json(updateCommand, host, self.XBMC_USERNAME, self.XBMC_PASSWORD)

            if not request:
                logger.log(u"XBMC Full Library update failed on: " + host, logger.ERROR)
                return False

        return True

##############################################################################
# Public functions which will call the JSON or Legacy HTTP API methods
##############################################################################

    def notify_snatch(self, ep_name):
        if self.XBMC_NOTIFY_ONSNATCH:
            self._notify_xbmc(ep_name, common.notifyStrings[common.NOTIFY_SNATCH])

    def notify_download(self, ep_name):
        if self.XBMC_NOTIFY_ONDOWNLOAD:
            self._notify_xbmc(ep_name, common.notifyStrings[common.NOTIFY_DOWNLOAD])

    def test_notify(self, host, username, password):
        return self._notify_xbmc("Testing XBMC notifications from Sick Beard", "Test Notification", host, username, password, force=True)

    def update_library(self, ep_obj, add=True):
        """Public wrapper for the update library functions to branch the logic for JSON-RPC or legacy HTTP API

        Checks the XBMC API version to branch the logic to call either the legacy HTTP API or the newer JSON-RPC over HTTP methods.
        Do the ability of accepting a list of hosts deliminated by comma, we split off the first host to send the update to.
        This is a workaround for SQL backend users as updating multiple clients causes duplicate entries.
        Future plan is to revist how we store the host/ip/username/pw/options so that it may be more flexible.

        Args:
            showName: Name of a TV show to specifically target the library update for

        Returns:
            Returns True or False

        """

        if self.USE_XBMC and self.XBMC_UPDATE_LIBRARY:
            if add:
                showName = ep_obj.show.name
                if not self.XBMC_HOST:
                    logger.log(u"No XBMC hosts specified, check your settings", logger.DEBUG)
                    return False

                # only send update to first host in the list -- workaround for xbmc sql backend users
                host = self.XBMC_HOST.split(",")[0].strip()

                logger.log(u"Sending request to update library for XBMC host: '" + host + "'", logger.MESSAGE)

                xbmcapi = self._get_json_version(host, self.XBMC_USERNAME, self.XBMC_PASSWORD)
                if xbmcapi:
                    if (xbmcapi <= 4):
                        # try to update for just the show, if it fails, do full update if enabled
                        if not self._update_library(host, showName) and self.XBMC_UPDATE_FULL:
                            logger.log(u"Single show update failed, falling back to full update", logger.WARNING)
                            return self._update_library(host)
                        else:
                            return True
                    else:
                        # try to update for just the show, if it fails, do full update if enabled
                        if not self._update_library_json(host, showName) and self.XBMC_UPDATE_FULL:
                            logger.log(u"Single show update failed, falling back to full update", logger.WARNING)
                            return self._update_library_json(host)
                        else:
                            return True
                else:
                    logger.log(u"Failed to detect XBMC version for '" + host + "', check configuration and try again.", logger.DEBUG)
                    return False

                return True

    def __init__(self):
        INotifierPlugin .__init__(self)
        
        self.USE_XBMC = False
        self.XBMC_NOTIFY_ONSNATCH = False
        self.XBMC_NOTIFY_ONDOWNLOAD = False
        self.XBMC_UPDATE_LIBRARY = False
        self.XBMC_UPDATE_FULL = False
        self.XBMC_HOST = ''
        self.XBMC_USERNAME = None
        self.XBMC_PASSWORD = None
        self.type = INotifierPlugin.NOTIFY_HOMETHEATER
    
    def _addMethod(self):
        def testXBMC(newself, host=None, username=None, password=None):
            cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

            finalResult = ''
            for curHost in [x.strip() for x in host.split(",")]:
                curResult = self.test_notify(urllib.unquote_plus(curHost), username, password)
                if len(curResult.split(":")) > 2 and 'OK' in curResult.split(":")[2]:
                    finalResult += "Test XBMC notice sent successfully to " + urllib.unquote_plus(curHost)
                else:
                    finalResult += "Test XBMC notice failed to " + urllib.unquote_plus(curHost)
                finalResult += "<br />\n"

            return finalResult
        
        testXBMC.exposed = True
        Home.testXBMC = testXBMC
        
        # TODO
        def updateXBMC(newself, showName=None):
            # TODO: configure that each host can have different options / username / pw
            # only send update to first host in the list -- workaround for xbmc sql backend users
            firstHost = self.XBMC_HOST.split(",")[0].strip()
            if self.update_library(showName=showName):
                ui.notifications.message("Library update command sent to XBMC host: " + firstHost)
            else:
                ui.notifications.error("Unable to contact XBMC host: " + firstHost)
            redirect('/home')
            
        updateXBMC.exposed = True
        Home.updateXBMC = updateXBMC

    def _addStatic(self):
        app = cherrypy.tree.apps[sickbeard.WEB_ROOT]
        app.merge({
             '/images/notifiers/xbmc.png': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/images/xbmc.png'),
             },
             '/js/configXBMC.js': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/notification.js'),
             }
        })

    def _removeMethod(self):
        if hasattr(Home, 'testXBMC'):
            del Home.testXBMC
        
        if hasattr(Home, 'updateXBMC'):
            del Home.updateXBMC

    def _removeStatic(self):
        pass

    def updateConfig(self, **kwargs):
        default = {
            'use_xbmc': 0,
            'xbmc_notify_onsnatch': 0,
            'xbmc_notify_ondownload': 0,
            'xbmc_update_library': 0,
            'xbmc_update_full': 0,
            'xbmc_host': '',
            'xbmc_username': None,
            'xbmc_password' : None
            }
        
        for key, defval in default.items():
            value = kwargs.get(key, defval)
            val = 1 if value == "on" else value
            
            if hasattr(self, key.upper()):
                setattr(self, key.upper(), val)
            else:
                logger.log("Unknown notification setting: " + key, logger.ERROR)
    
    def readConfig(self, config):
        CheckSection(config, 'XBMC')
        self.USE_XBMC = bool(check_setting_int(config, 'XBMC', 'use_xbmc', 0))
        self.XBMC_NOTIFY_ONSNATCH = bool(check_setting_int(config, 'XBMC', 'xbmc_notify_onsnatch', 0))
        self.XBMC_NOTIFY_ONDOWNLOAD = bool(check_setting_int(config, 'XBMC', 'xbmc_notify_ondownload', 0))
        self.XBMC_UPDATE_LIBRARY = bool(check_setting_int(config, 'XBMC', 'xbmc_update_library', 0))
        self.XBMC_UPDATE_FULL = bool(check_setting_int(config, 'XBMC', 'xbmc_update_full', 0))
        self.XBMC_HOST = check_setting_str(config, 'XBMC', 'xbmc_host', '')
        self.XBMC_USERNAME = check_setting_str(config, 'XBMC', 'xbmc_username', '')
        self.XBMC_PASSWORD = check_setting_str(config, 'XBMC', 'xbmc_password', '')
        
    def writeConfig(self, new_config):        
        new_config['XBMC'] = {}
        new_config['XBMC']['use_xbmc'] = int(self.USE_XBMC)
        new_config['XBMC']['xbmc_notify_onsnatch'] = int(self.XBMC_NOTIFY_ONSNATCH)
        new_config['XBMC']['xbmc_notify_ondownload'] = int(self.XBMC_NOTIFY_ONDOWNLOAD)
        new_config['XBMC']['xbmc_update_library'] = int(self.XBMC_UPDATE_LIBRARY)
        new_config['XBMC']['xbmc_update_full'] = int(self.XBMC_UPDATE_FULL)
        new_config['XBMC']['xbmc_host'] = self.XBMC_HOST
        new_config['XBMC']['xbmc_username'] = self.XBMC_USERNAME
        new_config['XBMC']['xbmc_password'] = self.XBMC_PASSWORD
    
        return new_config
    
    def activateHook(self):
        self._addMethod()
        self._addStatic()

    def deactivateHook(self):
        self._removeMethod()
        self._removeStatic()
