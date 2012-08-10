# Author: Jasper Lanting
# Based on nmj.py by Nico Berlee: http://nico.berlee.nl/
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
import time

from sickbeard import logger

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree


class NMJv2Notifier:
    
    def notify_snatch(self, ep_name):
        return False
        #Not implemented: Start the scanner when snatched does not make any sense

    def notify_download(self, ep_name):
        self._notifyNMJ()

    def test_notify(self, host):
        return self._sendNMJ(host)

    def notify_settings(self, host):
        """
        Retrieves the NMJv2 database location from Popcorn hour
        
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
        terminal.write("cd opt\n")
        terminal.write("cd sybhttpd\n")
        terminal.write("cd localhost.drives\n")
        terminal.write("find . -type f | grep -i \"/nmj_database/.*\.db$\"\n")
        terminal.write("exit\n")
        terminal.read_until(".db$")
        tnoutput = terminal.read_all()
        if tnoutput.find("media.db") > 0:
            tnoutput_split=tnoutput.split('\r\n')
            tnoutput_split[1] = tnoutput_split[1][1:]
            sickbeard.NMJv2_HOST=host
            sickbeard.NMJv2_DATABASE="/opt/sybhttpd/localhost.drives"+tnoutput_split[1]
        else:
            return False
        return True

    def _sendNMJ(self, host):
        """
        Sends a NMJ update command to the specified machine
        
        host: The hostname/IP to send the request to (no port)
        database: The database to send the requst to
        mount: The mount URL to use (optional)
        
        Returns: True if the request succeeded, False otherwise
        """
        
        # if a mount URL is provided then attempt to open a handle to that URL
        if host:
            try:
                url_scandir = "http://" + host + ":8008/metadata_database?arg0=update_scandir&arg1="+ sickbeard.NMJv2_DATABASE +"&arg2=&arg3=update_all"
                logger.log(u"NMJ scan update command send to host: %s" % (host))
                url_updatedb = "http://" + host + ":8008/metadata_database?arg0=scanner_start&arg1="+ sickbeard.NMJv2_DATABASE +"&arg2=background&arg3="
                logger.log(u"Try to mount network drive via url: %s" % (host), logger.DEBUG)
                prereq = urllib2.Request(url_scandir)
                req = urllib2.Request(url_updatedb)
                handle1 = urllib2.urlopen(prereq)
                response1 = handle1.read()
                time.sleep (300.0 / 1000.0)
                handle2 = urllib2.urlopen(req)
                response2 = handle2.read()
                # searching for string directly instead of parsing XML due to syntax error in XML response
                return1 = response1.find("<returnValue>0</returnValue>")
                return2 = response2.find("<returnValue>0</returnValue>")
                if return1 > 0 and return2 > 0:
                    logger.log(u"NMJ scan update command send to host: %s" % (host))
                    return True
                else:
                    logger.log(u"Warning: Couldn't contact popcorn hour on host %s: %s" % (host, e))
                    return False
            except:
                pass

    def _notifyNMJ(self, host=None, force=False):
        """
        Sends a NMJ update command based on the SB config settings
        
        host: The host to send the command to (optional, defaults to the host in the config)
        database: The database to use (optional, defaults to the database in the config)
        mount: The mount URL (optional, defaults to the mount URL in the config)
        force: If True then the notification will be sent even if NMJ is disabled in the config
        """
        if not sickbeard.USE_NMJv2 and not force:
            logger.log("Notification for NMJ scan update not enabled, skipping this notification", logger.DEBUG)
            return False

        # fill in omitted parameters
        if not host:
            host = sickbeard.NMJv2_HOST

        logger.log(u"Sending scan command for NMJ ", logger.DEBUG)

        return self._sendNMJ(host)

notifier = NMJv2Notifier
