# Author: Nico Berlee http://nico.berlee.nl/
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

import urllib, urllib2
import sickbeard
import telnetlib
import re

from sickbeard import logger

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

from sickbeard.INotifierPlugin import INotifierPlugin
from sickbeard.config import CheckSection, check_setting_int, check_setting_str, ConfigMigrator

from sickbeard.webserve import Home
import cherrypy
import os

class NMJNotifier(INotifierPlugin):
    def notify_settings(self, host):
        """
        Retrieves the settings from a NMJ/Popcorn hour
        
        host: The hostname/IP of the Popcorn Hour server
        
        Returns: True if the settings were retrieved successfully, False otherwise
        """
        
        # establish a terminal session to the PC
        terminal = False
        try:
            terminal = telnetlib.Telnet(host)
        except Exception:
            logger.log(u"Warning: unable to get a telnet session to %s" % (host), logger.ERROR)
            return False

        # tell the terminal to output the necessary info to the screen so we can search it later
        logger.log(u"Connected to %s via telnet" % (host), logger.DEBUG)
        terminal.read_until("sh-3.00# ")
        terminal.write("cat /tmp/source\n")
        terminal.write("cat /tmp/netshare\n")
        terminal.write("exit\n")
        tnoutput = terminal.read_all()

        database = ""
        device = ""
        match = re.search(r"(.+\.db)\r\n?(.+)(?=sh-3.00# cat /tmp/netshare)", tnoutput)

        # if we found the database in the terminal output then save that database to the config
        if match:
            database = match.group(1)
            device = match.group(2)
            logger.log(u"Found NMJ database %s on device %s" % (database, device), logger.DEBUG)
            self.NMJ_DATABASE = database
        else:
            logger.log(u"Could not get current NMJ database on %s, NMJ is probably not running!" % (host), logger.ERROR)
            return False
        
        # if the device is a remote host then try to parse the mounting URL and save it to the config
        if device.startswith("NETWORK_SHARE/"):
            match = re.search(".*(?=\r\n?%s)" % (re.escape(device[14:])), tnoutput)

            if match:
                mount = match.group().replace("127.0.0.1", host)
                logger.log(u"Found mounting url on the Popcorn Hour in configuration: %s" % (mount), logger.DEBUG)
                self.NMJ_MOUNT = mount
            else:
                logger.log(u"Detected a network share on the Popcorn Hour, but could not get the mounting url", logger.DEBUG)
                return False

        return True
    
    def notify_snatch(self, ep_name):
        return False
        #Not implemented: Start the scanner when snatched does not make any sense

    def notify_download(self, ep_name):
        if self.USE_NMJ:
            self._notifyNMJ()

    def test_notify(self, host, database, mount):
        return self._sendNMJ(host, database, mount)

    def _sendNMJ(self, host, database, mount=None):
        """
        Sends a NMJ update command to the specified machine
        
        host: The hostname/IP to send the request to (no port)
        database: The database to send the requst to
        mount: The mount URL to use (optional)
        
        Returns: True if the request succeeded, False otherwise
        """
        
        # if a mount URL is provided then attempt to open a handle to that URL
        if mount:
            try:
                req = urllib2.Request(mount)
                logger.log(u"Try to mount network drive via url: %s" % (mount), logger.DEBUG)
                handle = urllib2.urlopen(req)
            except IOError, e:
                logger.log(u"Warning: Couldn't contact popcorn hour on host %s: %s" % (host, e))
                return False

        # build up the request URL and parameters
        UPDATE_URL = "http://%(host)s:8008/metadata_database?%(params)s"
        params = {
            "arg0": "scanner_start",
            "arg1": database,
            "arg2": "background",
            "arg3": ""}
        params = urllib.urlencode(params)
        updateUrl = UPDATE_URL % {"host": host, "params": params}

        # send the request to the server
        try:
            req = urllib2.Request(updateUrl)
            logger.log(u"Sending NMJ scan update command via url: %s" % (updateUrl), logger.DEBUG)
            handle = urllib2.urlopen(req)
            response = handle.read()
        except IOError, e:
            logger.log(u"Warning: Couldn't contact Popcorn Hour on host %s: %s" % (host, e))
            return False

        # try to parse the resulting XML
        try:
            et = etree.fromstring(response)
            result = et.findtext("returnValue")
        except SyntaxError, e:
            logger.log(u"Unable to parse XML returned from the Popcorn Hour: %s" % (e), logger.ERROR)
            return False
        
        # if the result was a number then consider that an error
        if int(result) > 0:
            logger.log(u"Popcorn Hour returned an errorcode: %s" % (result))
            return False
        else:
            logger.log(u"NMJ started background scan")
            return True

    def _notifyNMJ(self, host=None, database=None, mount=None, force=False):
        """
        Sends a NMJ update command based on the SB config settings
        
        host: The host to send the command to (optional, defaults to the host in the config)
        database: The database to use (optional, defaults to the database in the config)
        mount: The mount URL (optional, defaults to the mount URL in the config)
        force: If True then the notification will be sent even if NMJ is disabled in the config
        """
        if not self.USE_NMJ and not force:
            logger.log("Notification for NMJ scan update not enabled, skipping this notification", logger.DEBUG)
            return False

        # fill in omitted parameters
        if not host:
            host = self.NMJ_HOST
        if not database:
            database = self.NMJ_DATABASE
        if not mount:
            mount = self.NMJ_MOUNT

        logger.log(u"Sending scan command for NMJ ", logger.DEBUG)

        return self._sendNMJ(host, database, mount)

    def __init__(self):
        INotifierPlugin .__init__(self)
        
        self.USE_NMJ = False
        self.NMJ_HOST = None
        self.NMJ_DATABASE = None
        self.NMJ_MOUNT = None
        self.type = INotifierPlugin.NOTIFY_HOMETHEATER
    
    def _addMethod(self):
        def testNMJ(newself, host=None, database=None, mount=None):
            cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

            result = self.test_notify(urllib.unquote_plus(host), database, mount)
            if result:
                return "Successfull started the scan update"
            else:
                return "Test failed to start the scan update"
        
        testNMJ.exposed = True
        Home.testNMJ = testNMJ
        
        def settingsNMJ(newself, host=None):
            cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

            result = self.notify_settings(urllib.unquote_plus(host))
            if result:
                return '{"message": "Got settings from %(host)s", "database": "%(database)s", "mount": "%(mount)s"}' % {"host": host, "database": self.NMJ_DATABASE, "mount": self.NMJ_MOUNT}
            else:
                return '{"message": "Failed! Make sure your Popcorn is on and NMJ is running. (see Log & Errors -> Debug for detailed info)", "database": "", "mount": ""}'
        
        settingsNMJ.exposed = True
        Home.settingsNMJ = settingsNMJ

    def _addStatic(self):
        app = cherrypy.tree.apps[sickbeard.WEB_ROOT]
        app.merge({
             '/images/notifiers/nmj.png': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/images/nmj.png'),
             },
             '/js/configNMJ.js': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/notification.js'),
             }
        })

    def _removeMethod(self):
        if hasattr(Home, 'testNMJ'):
            del Home.testNMJ
        if hasattr(Home, 'settingsNMJ'):
            del Home.settingsNMJ

    def _removeStatic(self):
        pass

    def updateConfig(self, **kwargs):
        default = {
            'use_nmj': 0,
            'nmj_host' : None,
            'nmj_database' : None,
            'nmj_mount': None
            }
        
        for key, defval in default.items():
            value = kwargs.get(key, defval)
            val = 1 if value == "on" else value
            
            if hasattr(self, key.upper()):
                setattr(self, key.upper(), val)
            else:
                logger.log("Unknown notification setting: " + key, logger.ERROR)
    
    def readConfig(self, config):
        CheckSection(config, 'NMJ')
        self.USE_NMJ = bool(check_setting_int(config, 'NMJ', 'use_nmj', 0))
        self.NMJ_HOST = check_setting_str(config, 'NMJ', 'nmj_host', '')
        self.NMJ_DATABASE = check_setting_str(config, 'NMJ', 'nmj_database', '')
        self.NMJ_MOUNT = check_setting_str(config, 'NMJ', 'nmj_mount', '')
        
    def writeConfig(self, new_config):        
        new_config['NMJ'] = {}
        new_config['NMJ']['use_nmj'] = int(self.USE_NMJ)
        new_config['NMJ']['nmj_host'] = self.NMJ_HOST
        new_config['NMJ']['nmj_database'] = self.NMJ_DATABASE
        new_config['NMJ']['nmj_mount'] = self.NMJ_MOUNT
    
        return new_config
    
    def activateHook(self):
        self._addMethod()
        self._addStatic()

    def deactivateHook(self):
        self._removeMethod()
        self._removeStatic()
