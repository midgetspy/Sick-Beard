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


class XBMCNotifier:

    sb_logo_url = "http://www.sickbeard.com/notify.png"

    def _get_xbmc_version(self, host, username, password):
        """Returns XBMC JSON-RPC API version (odd # = dev, even # = stable)

        Sends a request to the XBMC host using the JSON-RPC to determine if
        the legacy API or if the JSON-RPC API functions should be used.

        Fallback to testing legacy HTTPAPI before assuming it is just a badly configured host.

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
                 6  | v12 (Frodo) / v13 (Gotham)

        """

        # since we need to maintain python 2.5 compatibility we can not pass a timeout delay to urllib2 directly (python 2.6+)
        # override socket timeout to reduce delay for this call alone
        socket.setdefaulttimeout(10)

        checkCommand = '{"jsonrpc":"2.0","method":"JSONRPC.Version","id":1}'
        result = self._send_to_xbmc_json(checkCommand, host, username, password)

        # revert back to default socket timeout
        socket.setdefaulttimeout(sickbeard.SOCKET_TIMEOUT)

        if result:
            return result["result"]["version"]
        else:
            # fallback to legacy HTTPAPI method
            testCommand = {'command': 'Help'}
            request = self._send_to_xbmc(testCommand, host, username, password)
            if request:
                # return a fake version number, so it uses the legacy method
                return 1
            else:
                return False

    def _notify(self, message, title="Sick Beard", host=None, username=None, password=None, force=False):
        """Internal wrapper for the notify_snatch and notify_download functions

        Detects JSON-RPC version then branches the logic for either the JSON-RPC or legacy HTTP API methods.

        Args:
            message: Message body of the notice to send
            title: Title of the notice to send
            host: XBMC webserver host:port
            username: XBMC webserver username
            password: XBMC webserver password
            force: Used for the Test method to override config safety checks

        Returns:
            Returns a list results in the format of host:ip:result
            The result will either be 'OK' or False, this is used to be parsed by the calling function.

        """

        # suppress notifications if the notifier is disabled but the notify options are checked
        if not sickbeard.USE_XBMC and not force:
            return False

        # fill in omitted parameters
        if not host:
            host = sickbeard.XBMC_HOST
        if not username:
            username = sickbeard.XBMC_USERNAME
        if not password:
            password = sickbeard.XBMC_PASSWORD

        result = ''
        for curHost in [x.strip() for x in host.split(",")]:
            logger.log(u"XBMC: Sending XBMC notification to '" + curHost + "' - " + message, logger.MESSAGE)

            xbmcapi = self._get_xbmc_version(curHost, username, password)
            if xbmcapi:
                if (xbmcapi <= 4):
                    logger.log(u"XBMC: Detected XBMC version <= 11, using XBMC HTTP API", logger.DEBUG)
                    command = {'command': 'ExecBuiltIn', 'parameter': 'Notification(' + title.encode("utf-8") + ',' + message.encode("utf-8") + ')'}
                    notifyResult = self._send_to_xbmc(command, curHost, username, password)
                    if notifyResult:
                        result += curHost + ':' + str(notifyResult)
                else:
                    logger.log(u"XBMC: Detected XBMC version >= 12, using XBMC JSON API", logger.DEBUG)
                    command = '{"jsonrpc":"2.0","method":"GUI.ShowNotification","params":{"title":"%s","message":"%s", "image": "%s"},"id":1}' % (title.encode("utf-8"), message.encode("utf-8"), self.sb_logo_url)
                    notifyResult = self._send_to_xbmc_json(command, curHost, username, password)
                    if notifyResult:
                        result += curHost + ':' + notifyResult["result"].decode(sickbeard.SYS_ENCODING)
            else:
                if sickbeard.XBMC_ALWAYS_ON or force:
                    logger.log(u"XBMC: Failed to detect XBMC version for '" + curHost + "', check configuration and try again.", logger.ERROR)
                result += curHost + ':False'

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
            username = sickbeard.XBMC_USERNAME
        if not password:
            password = sickbeard.XBMC_PASSWORD

        if not host:
            logger.log(u"XBMC: No host specified, check your settings", logger.DEBUG)
            return False

        for key in command:
            if type(command[key]) == unicode:
                command[key] = command[key].encode('utf-8')

        enc_command = urllib.urlencode(command)
        logger.log(u"XBMC: Encoded API command: " + enc_command, logger.DEBUG)

        url = 'http://%s/xbmcCmds/xbmcHttp/?%s' % (host, enc_command)
        try:
            req = urllib2.Request(url)
            # if we have a password, use authentication
            if password:
                base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
                authheader = "Basic %s" % base64string
                req.add_header("Authorization", authheader)

            response = urllib2.urlopen(req)
            result = response.read().decode(sickbeard.SYS_ENCODING)
            response.close()

            logger.log(u"XBMC: HTTP response: " + result.replace('\n', ''), logger.DEBUG)
            return result

        except (urllib2.URLError, IOError), e:
            logger.log(u"XBMC: Could not contact XBMC HTTP at " + fixStupidEncodings(url) + " " + ex(e), logger.WARNING)
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
            logger.log(u"XBMC: No host specified, check your settings", logger.DEBUG)
            return False

        # if we're doing per-show
        if showName:
            logger.log(u"XBMC: Updating library via HTTP method for show " + showName, logger.MESSAGE)

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
                logger.log(u"XBMC: Invalid response for " + showName + " on " + host, logger.DEBUG)
                return False

            encSqlXML = urllib.quote(sqlXML, ':\\/<>')
            try:
                et = etree.fromstring(encSqlXML)
            except SyntaxError, e:
                logger.log(u"XBMC: Unable to parse XML returned from XBMC: " + ex(e), logger.ERROR)
                return False

            paths = et.findall('.//field')

            if not paths:
                logger.log(u"XBMC: No valid paths found for " + showName + " on " + host, logger.DEBUG)
                return False

            for path in paths:
                # we do not need it double-encoded, gawd this is dumb
                unEncPath = urllib.unquote(path.text).decode(sickbeard.SYS_ENCODING)
                logger.log(u"XBMC: Updating " + showName + " on " + host + " at " + unEncPath, logger.MESSAGE)
                updateCommand = {'command': 'ExecBuiltIn', 'parameter': 'XBMC.updatelibrary(video, %s)' % (unEncPath)}
                request = self._send_to_xbmc(updateCommand, host)
                if not request:
                    logger.log(u"XBMC: Update of show directory failed on " + showName + " on " + host + " at " + unEncPath, logger.WARNING)
                    return False
                # sleep for a few seconds just to be sure xbmc has a chance to finish each directory
                if len(paths) > 1:
                    time.sleep(5)
        # do a full update if requested
        else:
            logger.log(u"XBMC: Doing Full Library update via HTTP method for host: " + host, logger.MESSAGE)
            updateCommand = {'command': 'ExecBuiltIn', 'parameter': 'XBMC.updatelibrary(video)'}
            request = self._send_to_xbmc(updateCommand, host)

            if not request:
                logger.log(u"XBMC: Full Library update failed on: " + host, logger.ERROR)
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
            username = sickbeard.XBMC_USERNAME
        if not password:
            password = sickbeard.XBMC_PASSWORD

        if not host:
            logger.log(u"XBMC: No host specified, check your settings", logger.DEBUG)
            return False

        command = command.encode('utf-8')
        logger.log(u"XBMC: JSON command: " + command, logger.DEBUG)

        url = 'http://%s/jsonrpc' % (host)
        try:
            req = urllib2.Request(url, command)
            req.add_header("Content-type", "application/json")
            # if we have a password, use authentication
            if password:
                base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
                authheader = "Basic %s" % base64string
                req.add_header("Authorization", authheader)

            try:
                response = urllib2.urlopen(req)
            except urllib2.URLError, e:
                logger.log(u"XBMC: Error while trying to retrieve XBMC API version for " + host + ": " + ex(e), logger.WARNING)
                return False

            # parse the json result
            try:
                result = json.load(response)
                response.close()
                logger.log(u"XBMC: JSON response: " + str(result), logger.DEBUG)
                return result  # need to return response for parsing
            except ValueError, e:
                logger.log(u"XBMC: Unable to decode JSON: " + response, logger.WARNING)
                return False

        except IOError, e:
            logger.log(u"XBMC: Could not contact XBMC JSON API at " + fixStupidEncodings(url) + " " + ex(e), logger.WARNING)
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
            logger.log(u"XBMC: No host specified, check your settings", logger.DEBUG)
            return False

        # if we're doing per-show
        if showName:
            tvshowid = -1
            logger.log(u"XBMC: Updating library via JSON method for show " + showName, logger.MESSAGE)

            # get tvshowid by showName
            showsCommand = '{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShows","id":1}'
            showsResponse = self._send_to_xbmc_json(showsCommand, host)

            if showsResponse and "result" in showsResponse and "tvshows" in showsResponse["result"]:
                shows = showsResponse["result"]["tvshows"]
            else:
                logger.log(u"XBMC: No tvshows in XBMC TV show list", logger.DEBUG)
                return False

            for show in shows:
                if (show["label"] == showName):
                    tvshowid = show["tvshowid"]
                    break  # exit out of loop otherwise the label and showname will not match up

            # this can be big, so free some memory
            del shows

            # we didn't find the show (exact match), thus revert to just doing a full update if enabled
            if (tvshowid == -1):
                logger.log(u"XBMC: Exact show name not matched in XBMC TV show list", logger.DEBUG)
                return False

            # lookup tv-show path
            pathCommand = '{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShowDetails","params":{"tvshowid":%d, "properties": ["file"]},"id":1}' % (tvshowid)
            pathResponse = self._send_to_xbmc_json(pathCommand, host)

            path = pathResponse["result"]["tvshowdetails"]["file"]
            logger.log(u"XBMC: Received Show: " + show["label"] + " with ID: " + str(tvshowid) + " Path: " + path, logger.DEBUG)

            if (len(path) < 1):
                logger.log(u"XBMC: No valid path found for " + showName + " with ID: " + str(tvshowid) + " on " + host, logger.WARNING)
                return False

            logger.log(u"XBMC: Updating " + showName + " on " + host + " at " + path, logger.MESSAGE)
            updateCommand = '{"jsonrpc":"2.0","method":"VideoLibrary.Scan","params":{"directory":%s},"id":1}' % (json.dumps(path))
            request = self._send_to_xbmc_json(updateCommand, host)
            if not request:
                logger.log(u"XBMC: Update of show directory failed on " + showName + " on " + host + " at " + path, logger.WARNING)
                return False

            # catch if there was an error in the returned request
            for r in request:
                if 'error' in r:
                    logger.log(u"XBMC: Error while attempting to update show directory for " + showName + " on " + host + " at " + path, logger.ERROR)
                    return False

        # do a full update if requested
        else:
            logger.log(u"XBMC: Doing Full Library update via JSON method for host: " + host, logger.MESSAGE)
            updateCommand = '{"jsonrpc":"2.0","method":"VideoLibrary.Scan","id":1}'
            request = self._send_to_xbmc_json(updateCommand, host, sickbeard.XBMC_USERNAME, sickbeard.XBMC_PASSWORD)

            if not request:
                logger.log(u"XBMC: Full Library update failed on: " + host, logger.ERROR)
                return False

        return True

##############################################################################
# Public functions which will call the JSON or Legacy HTTP API methods
##############################################################################

    def notify_snatch(self, ep_name):
        if sickbeard.XBMC_NOTIFY_ONSNATCH:
            self._notify(ep_name, common.notifyStrings[common.NOTIFY_SNATCH])

    def notify_download(self, ep_name):
        if sickbeard.XBMC_NOTIFY_ONDOWNLOAD:
            self._notify(ep_name, common.notifyStrings[common.NOTIFY_DOWNLOAD])

    def test_notify(self, host, username, password):
        return self._notify("This is a test notification from Sick Beard", "Test", host, username, password, force=True)

    def update_library(self, ep_obj=None, show_obj=None):
        """Public wrapper for the update library functions to branch the logic for JSON-RPC or legacy HTTP API

        Checks the XBMC API version to branch the logic to call either the legacy HTTP API or the newer JSON-RPC over HTTP methods.
        Do the ability of accepting a list of hosts delimited by comma, we split off the first host to send the update to.
        This is a workaround for SQL backend users as updating multiple clients causes duplicate entries.
        Future plan is to revisit how we store the host/ip/username/pw/options so that it may be more flexible.

        Args:
            showName: Name of a TV show to specifically target the library update for

        Returns:
            Returns True or False

        """

        if ep_obj:
            showName = ep_obj.show.name
        elif show_obj:
            showName = show_obj.name
        else:
            showName = None

        if sickbeard.USE_XBMC and sickbeard.XBMC_UPDATE_LIBRARY:
            if not sickbeard.XBMC_HOST:
                logger.log(u"XBMC: No host specified, check your settings", logger.DEBUG)
                return False

            if sickbeard.XBMC_UPDATE_ONLYFIRST:
                # only send update to first host in the list if requested -- workaround for xbmc sql backend users
                host = sickbeard.XBMC_HOST.split(",")[0].strip()
            else:
                host = sickbeard.XBMC_HOST

            result = 0
            for curHost in [x.strip() for x in host.split(",")]:
                logger.log(u"XBMC: Sending request to update library for host: '" + curHost + "'", logger.MESSAGE)

                xbmcapi = self._get_xbmc_version(curHost, sickbeard.XBMC_USERNAME, sickbeard.XBMC_PASSWORD)
                if xbmcapi:
                    if (xbmcapi <= 4):
                        # try to update for just the show, if it fails, do full update if enabled
                        if not self._update_library(curHost, showName):
                            if showName and sickbeard.XBMC_UPDATE_FULL:
                                self._update_library(curHost)
                    else:
                        # try to update for just the show, if it fails, do full update if enabled
                        if not self._update_library_json(curHost, showName):
                            if showName and sickbeard.XBMC_UPDATE_FULL:
                                self._update_library_json(curHost)
                else:
                    if sickbeard.XBMC_ALWAYS_ON:
                        logger.log(u"XBMC: Failed to detect XBMC version for '" + curHost + "', check configuration and try again.", logger.ERROR)
                    result = result + 1

            # needed for the 'update xbmc' submenu command
            # as it only cares of the final result vs the individual ones
            if result == 0:
                return True
            else:
                return False

notifier = XBMCNotifier
