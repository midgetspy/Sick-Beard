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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import urllib
import urllib2
import sickbeard

from sickbeard import logger
from sickbeard import common
from sickbeard.exceptions import ex
from sickbeard.encodingKludge import fixStupidEncodings

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import elementtree.ElementTree as etree


class PLEXNotifier:

    def _send_to_plex(self, command, host, username=None, password=None):
        """Handles communication to Plex hosts via HTTP API

        Args:
            command: Dictionary of field/data pairs, encoded via urllib and passed to the legacy xbmcCmds HTTP API
            host: Plex host:port
            username: Plex API username
            password: Plex API password

        Returns:
            Returns 'OK' for successful commands or False if there was an error

        """

        # fill in omitted parameters
        if not username:
            username = sickbeard.PLEX_USERNAME
        if not password:
            password = sickbeard.PLEX_PASSWORD

        if not host:
            logger.log(u"PLEX: No host specified, check your settings", logger.ERROR)
            return False

        for key in command:
            if type(command[key]) == unicode:
                command[key] = command[key].encode('utf-8')

        enc_command = urllib.urlencode(command)
        logger.log(u"PLEX: Encoded API command: " + enc_command, logger.DEBUG)

        url = 'http://%s/xbmcCmds/xbmcHttp/?%s' % (host, enc_command)
        try:
            req = urllib2.Request(url)
            # if we have a password, use authentication
            if password:
                pw_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
                pw_mgr.add_password(None, url, username, password)
            else:
                pw_mgr = None

            response = sickbeard.helpers.getURLFileLike(req, password_mgr=pw_mgr)

            result = response.read().decode(sickbeard.SYS_ENCODING)
            response.close()

            logger.log(u"PLEX: HTTP response: " + result.replace('\n', ''), logger.DEBUG)
            # could return result response = re.compile('<html><li>(.+\w)</html>').findall(result)
            return 'OK'

        except (urllib2.URLError, IOError), e:
            logger.log(u"PLEX: Warning: Couldn't contact Plex at " + fixStupidEncodings(url) + " " + ex(e), logger.WARNING)
            return False

    def _notify(self, message, title="Sick Beard", host=None, username=None, password=None, force=False):
        """Internal wrapper for the notify_snatch and notify_download functions

        Args:
            message: Message body of the notice to send
            title: Title of the notice to send
            host: Plex Media Client(s) host:port
            username: Plex username
            password: Plex password
            force: Used for the Test method to override config safety checks

        Returns:
            Returns a list results in the format of host:ip:result
            The result will either be 'OK' or False, this is used to be parsed by the calling function.

        """

        # suppress notifications if the notifier is disabled but the notify options are checked
        if not sickbeard.USE_PLEX and not force:
            return False

        # fill in omitted parameters
        if not host:
            host = sickbeard.PLEX_HOST
        if not username:
            username = sickbeard.PLEX_USERNAME
        if not password:
            password = sickbeard.PLEX_PASSWORD

        result = ''
        for curHost in [x.strip() for x in host.split(",")]:
            logger.log(u"PLEX: Sending notification to '" + curHost + "' - " + message, logger.MESSAGE)

            command = {'command': 'ExecBuiltIn', 'parameter': 'Notification(' + title.encode("utf-8") + ',' + message.encode("utf-8") + ')'}
            notifyResult = self._send_to_plex(command, curHost, username, password)
            if notifyResult:
                result += curHost + ':' + str(notifyResult)

        return result

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        if sickbeard.PLEX_NOTIFY_ONSNATCH:
            self._notify(ep_name, common.notifyStrings[common.NOTIFY_SNATCH])

    def notify_download(self, ep_name):
        if sickbeard.PLEX_NOTIFY_ONDOWNLOAD:
            self._notify(ep_name, common.notifyStrings[common.NOTIFY_DOWNLOAD])

    def test_notify(self, host, username, password):
        return self._notify("This is a test notification from Sick Beard", "Test", host, username, password, force=True)

    def update_library(self, ep_obj=None, host=None, username=None, password=None):
        """Handles updating the Plex Media Server host via HTTP API

        Plex Media Server currently only supports updating the whole video library and not a specific path.

        Returns:
            Returns True or False

        """

        # fill in omitted parameters
        if not host:
            host = sickbeard.PLEX_SERVER_HOST
        if not username:
            username = sickbeard.PLEX_USERNAME
        if not password:
            password = sickbeard.PLEX_PASSWORD

        if sickbeard.USE_PLEX and sickbeard.PLEX_UPDATE_LIBRARY:
            if not sickbeard.PLEX_SERVER_HOST:
                logger.log(u"PLEX: No Plex Media Server host specified, check your settings", logger.DEBUG)
                return False

            logger.log(u"PLEX: Updating library for the Plex Media Server host: " + host, logger.MESSAGE)

            # if username and password were provided, fetch the auth token from plex.tv
            token_arg = ""
            if username and password:

                logger.log(u"PLEX: fetching credentials for Plex user: " + username, logger.DEBUG)
                url = "https://plex.tv/users/sign_in.xml"            
                req = urllib2.Request(url, data="")
                pw_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
                pw_mgr.add_password(None, url, username, password)
                req.add_header("X-Plex-Product", "Sick Beard Notifier")
                req.add_header("X-Plex-Client-Identifier", "5f48c063eaf379a565ff56c9bb2b401e")
                req.add_header("X-Plex-Version", "1.0")
                
                try:
                    response = sickbeard.helpers.getURLFileLike(req, throw_exc=True)
                    auth_tree = etree.parse(response)
                    token = auth_tree.findall(".//authentication-token")[0].text
                    token_arg = "?X-Plex-Token=" + token
                
                except urllib2.URLError as e:
                    logger.log(u"PLEX: Error fetching credentials from from plex.tv for user %s: %s" % (username, ex(e)), logger.MESSAGE)
                
                except (ValueError, IndexError) as e:
                    logger.log(u"PLEX: Error parsing plex.tv response: " + ex(e), logger.MESSAGE)

            url = "http://%s/library/sections%s" % (sickbeard.PLEX_SERVER_HOST, token_arg)
            try:
                xml_tree = etree.parse(sickbeard.helpers.getURLFileLike(url))
                media_container = xml_tree.getroot()
            except IOError, e:
                logger.log(u"PLEX: Error while trying to contact Plex Media Server: " + ex(e), logger.ERROR)
                return False

            sections = media_container.findall('.//Directory')
            if not sections:
                logger.log(u"PLEX: Plex Media Server not running on: " + sickbeard.PLEX_SERVER_HOST, logger.MESSAGE)
                return False

            for section in sections:
                if section.attrib['type'] == "show":
                    url = "http://%s/library/sections/%s/refresh%s" % (sickbeard.PLEX_SERVER_HOST, section.attrib['key'], token_arg)
                    if sickbeard.helpers.getURLFileLike(url) is None:
                        logger.log(u"PLEX: Error updating library section for Plex Media Server", logger.ERROR)
                        return False
            return True

notifier = PLEXNotifier
