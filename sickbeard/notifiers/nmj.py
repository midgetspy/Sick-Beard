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


class NMJNotifier:
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
            sickbeard.NMJ_DATABASE = database
        else:
            logger.log(u"Could not get current NMJ database on %s, NMJ is probably not running!" % (host), logger.ERROR)
            return False
        
        # if the device is a remote host then try to parse the mounting URL and save it to the config
        if device.startswith("NETWORK_SHARE/"):
            match = re.search(".*(?=\r\n?%s)" % (re.escape(device[14:])), tnoutput)

            if match:
                mount = match.group().replace("127.0.0.1", host)
                logger.log(u"Found mounting url on the Popcorn Hour in configuration: %s" % (mount), logger.DEBUG)
                sickbeard.NMJ_MOUNT = mount
            else:
                logger.log(u"Detected a network share on the Popcorn Hour, but could not get the mounting url", logger.DEBUG)
                return False

        return True
    
    def notify_snatch(self, ep_name):
        return False
        #Not implemented: Start the scanner when snatched does not make any sense

    def notify_download(self, ep_name):
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
        if not sickbeard.USE_NMJ and not force:
            logger.log("Notification for NMJ scan update not enabled, skipping this notification", logger.DEBUG)
            return False

        # fill in omitted parameters
        if not host:
            host = sickbeard.NMJ_HOST
        if not database:
            database = sickbeard.NMJ_DATABASE
        if not mount:
            mount = sickbeard.NMJ_MOUNT

        logger.log(u"Sending scan command for NMJ ", logger.DEBUG)

        return self._sendNMJ(host, database, mount)

notifier = NMJNotifier
