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
import base64

import sickbeard

from sickbeard import logger
from sickbeard import common
from sickbeard.exceptions import ex
from sickbeard.encodingKludge import fixStupidEncodings

# TODO: switch over to using ElementTree
from xml.dom import minidom

from sickbeard.INotifierPlugin import INotifierPlugin
from sickbeard.config import CheckSection, check_setting_int, check_setting_str, ConfigMigrator

from sickbeard.webserve import Home
import cherrypy
import os

class PLEXNotifier(INotifierPlugin):

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
            username = self.PLEX_USERNAME
        if not password:
            password = self.PLEX_PASSWORD

        if not host:
            logger.log(u"No Plex host specified, check your settings", logger.DEBUG)
            return False

        for key in command:
            if type(command[key]) == unicode:
                command[key] = command[key].encode('utf-8')

        enc_command = urllib.urlencode(command)
        logger.log(u"Plex encoded API command: " + enc_command, logger.DEBUG)

        url = 'http://%s/xbmcCmds/xbmcHttp/?%s' % (host, enc_command)
        try:
            req = urllib2.Request(url)
            # if we have a password, use authentication
            if password:
                base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
                authheader = "Basic %s" % base64string
                req.add_header("Authorization", authheader)
                logger.log(u"Contacting Plex (with auth header) via url: " + url, logger.DEBUG)
            else:
                logger.log(u"Contacting Plex via url: " + url, logger.DEBUG)

            response = urllib2.urlopen(req)

            result = response.read().decode(sickbeard.SYS_ENCODING)
            response.close()

            logger.log(u"Plex HTTP response: " + result.replace('\n', ''), logger.DEBUG)
            # could return result response = re.compile('<html><li>(.+\w)</html>').findall(result)
            return 'OK'

        except (urllib2.URLError, IOError), e:
            logger.log(u"Warning: Couldn't contact Plex at " + fixStupidEncodings(url) + " " + ex(e), logger.WARNING)
            return False

    def _notify_pmc(self, message, title="Sick Beard", host=None, username=None, password=None, force=False):
        """Internal wrapper for the notify_snatch and notify_download functions

        Args:
            message: Message body of the notice to send
            title: Title of the notice to send
            host: Plex Media Client(s) host:port
            username: Plex username
            password: Plex password
            force: Used for the Test method to override config saftey checks

        Returns:
            Returns a list results in the format of host:ip:result
            The result will either be 'OK' or False, this is used to be parsed by the calling function.

        """

        # fill in omitted parameters
        if not host:
            host = self.PLEX_HOST
        if not username:
            username = self.PLEX_USERNAME
        if not password:
            password = self.PLEX_PASSWORD

        # suppress notifications if the notifier is disabled but the notify options are checked
        if not self.USE_PLEX and not force:
            logger.log("Notification for Plex not enabled, skipping this notification", logger.DEBUG)
            return False

        result = ''
        for curHost in [x.strip() for x in host.split(",")]:
            logger.log(u"Sending Plex notification to '" + curHost + "' - " + message, logger.MESSAGE)

            command = {'command': 'ExecBuiltIn', 'parameter': 'Notification(' + title.encode("utf-8") + ',' + message.encode("utf-8") + ')'}
            notifyResult = self._send_to_plex(command, curHost, username, password)
            if notifyResult:
                result += curHost + ':' + str(notifyResult)

        return result

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        if self.PLEX_NOTIFY_ONSNATCH:
            self._notify_pmc(ep_name, common.notifyStrings[common.NOTIFY_SNATCH])

    def notify_download(self, ep_name):
        if self.PLEX_NOTIFY_ONDOWNLOAD:
            self._notify_pmc(ep_name, common.notifyStrings[common.NOTIFY_DOWNLOAD])

    def test_notify(self, host, username, password):
        return self._notify_pmc("Testing Plex notifications from Sick Beard", "Test Notification", host, username, password, force=True)

    def update_library(self, ep_obj, add = True):
        """Handles updating the Plex Media Server host via HTTP API

        Plex Media Server currently only supports updating the whole video library and not a specific path.

        Returns:
            Returns True or False

        """
        if add:
            if self.USE_PLEX and self.PLEX_UPDATE_LIBRARY:
                if not self.PLEX_SERVER_HOST:
                    logger.log(u"No Plex Server host specified, check your settings", logger.DEBUG)
                    return False

                logger.log(u"Updating library for the Plex Media Server host: " + self.PLEX_SERVER_HOST, logger.MESSAGE)

                url = "http://%s/library/sections" % self.PLEX_SERVER_HOST
                try:
                    xml_sections = minidom.parse(urllib.urlopen(url))
                except IOError, e:
                    logger.log(u"Error while trying to contact Plex Media Server: " + ex(e), logger.ERROR)
                    return False

                sections = xml_sections.getElementsByTagName('Directory')
                if not sections:
                    logger.log(u"Plex Media Server not running on: " + self.PLEX_SERVER_HOST, logger.MESSAGE)
                    return False

                for s in sections:
                    if s.getAttribute('type') == "show":
                        url = "http://%s/library/sections/%s/refresh" % (self.PLEX_SERVER_HOST, s.getAttribute('key'))
                        try:
                            urllib.urlopen(url)
                        except Exception, e:
                            logger.log(u"Error updating library section for Plex Media Server: " + ex(e), logger.ERROR)
                            return False

                return True

    def __init__(self):
        INotifierPlugin .__init__(self)
        
        self.USE_PLEX = False
        self.PLEX_NOTIFY_ONSNATCH = False
        self.PLEX_NOTIFY_ONDOWNLOAD = False
        self.PLEX_UPDATE_LIBRARY = False
        self.PLEX_SERVER_HOST = None
        self.PLEX_HOST = None
        self.PLEX_USERNAME = None
        self.PLEX_PASSWORD = None
        self.type = INotifierPlugin.NOTIFY_HOMETHEATER
    
    def _addMethod(self):
        def testPLEX(newself, host=None, username=None, password=None):
            cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

            finalResult = ''
            for curHost in [x.strip() for x in host.split(",")]:
                curResult = self.test_notify(urllib.unquote_plus(curHost), username, password)
                if len(curResult.split(":")) > 2 and 'OK' in curResult.split(":")[2]:
                    finalResult += "Test Plex notice sent successfully to " + urllib.unquote_plus(curHost)
                else:
                    finalResult += "Test Plex notice failed to " + urllib.unquote_plus(curHost)
                finalResult += "<br />\n"

            return finalResult
        
        testPLEX.exposed = True
        Home.testPLEX = testPLEX
        
        # TODO
        def updatePLEX(newself):
            if self.update_library(None):
                ui.notifications.message("Library update command sent to Plex Media Server host: " + self.PLEX_SERVER_HOST)
            else:
                ui.notifications.error("Unable to contact Plex Media Server host: " + self.PLEX_SERVER_HOST)
            redirect('/home')
            
        updatePLEX.exposed = True
        Home.updatePLEX = updatePLEX

    def _addStatic(self):
        app = cherrypy.tree.apps[sickbeard.WEB_ROOT]
        app.merge({
             '/images/notifiers/plex.png': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/images/plex.png'),
             },
             '/js/configPlex.js': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/notification.js'),
             }
        })

    def _removeMethod(self):
        if hasattr(Home, 'testPLEX'):
            del Home.testPLEX
        if hasattr(Home, 'updatePLEX'):
            del Home.updatePLEX

    def _removeStatic(self):
        pass

    def updateConfig(self, **kwargs):
        default = {
            'use_plex': 0,
            'plex_notify_onsnatch' : 0,
            'plex_notify_ondownload' : 0,
            'plex_update_library': 0,
            'plex_server_host': '',
            'plex_host': '',
            'plex_username': None,
            'plex_password': None
            }
        
        for key, defval in default.items():
            value = kwargs.get(key, defval)
            val = 1 if value == "on" else value
            
            if hasattr(self, key.upper()):
                setattr(self, key.upper(), val)
            else:
                logger.log("Unknown notification setting: " + key, logger.ERROR)
    
    def readConfig(self, config):
        CheckSection(config, 'Plex')
        self.USE_PLEX = bool(check_setting_int(config, 'Plex', 'use_plex', 0))
        self.PLEX_NOTIFY_ONSNATCH = bool(check_setting_int(config, 'Plex', 'plex_notify_onsnatch', 0))
        self.PLEX_NOTIFY_ONDOWNLOAD = bool(check_setting_int(config, 'Plex', 'plex_notify_ondownload', 0))
        self.PLEX_UPDATE_LIBRARY = bool(check_setting_int(config, 'Plex', 'plex_update_library', 0))
        self.PLEX_SERVER_HOST = check_setting_str(config, 'Plex', 'plex_server_host', '')
        self.PLEX_HOST = check_setting_str(config, 'Plex', 'plex_host', '')
        self.PLEX_USERNAME = check_setting_str(config, 'Plex', 'plex_username', '')
        self.PLEX_PASSWORD = check_setting_str(config, 'Plex', 'plex_password', '')
        
    def writeConfig(self, new_config):        
        new_config['Plex'] = {}
        new_config['Plex']['use_plex'] = int(self.USE_PLEX)
        new_config['Plex']['plex_notify_onsnatch'] = int(self.PLEX_NOTIFY_ONSNATCH)
        new_config['Plex']['plex_notify_ondownload'] = int(self.PLEX_NOTIFY_ONDOWNLOAD)
        new_config['Plex']['plex_update_library'] = int(self.PLEX_UPDATE_LIBRARY)
        new_config['Plex']['plex_server_host'] = self.PLEX_SERVER_HOST
        new_config['Plex']['plex_host'] = self.PLEX_HOST
        new_config['Plex']['plex_username'] = self.PLEX_USERNAME
        new_config['Plex']['plex_password'] = self.PLEX_PASSWORD
    
        return new_config
    
    def activateHook(self):
        self._addMethod()
        self._addStatic()

    def deactivateHook(self):
        self._removeMethod()
        self._removeStatic()

