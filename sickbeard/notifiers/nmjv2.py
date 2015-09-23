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

import urllib2
from xml.dom.minidom import parseString
import sickbeard
import time

from sickbeard import logger

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree


class NMJv2Notifier:

    def notify_settings(self, host, dbloc, instance):
        """
        Retrieves the NMJv2 database location from Popcorn Hour

        host: The hostname/IP of the Popcorn Hour server
        dbloc: 'local' for PCH internal harddrive. 'network' for PCH network shares
        instance: Allows for selection of different DB in case of multiple databases

        Returns: True if the settings were retrieved successfully, False otherwise
        """
        try:
            url_loc = "http://" + host + ":8008/file_operation?arg0=list_user_storage_file&arg1=&arg2=" + instance + "&arg3=20&arg4=true&arg5=true&arg6=true&arg7=all&arg8=name_asc&arg9=false&arg10=false"
            req = urllib2.Request(url_loc)
            handle1 = urllib2.urlopen(req)
            response1 = handle1.read()
            # TODO: convert to etree?
            xml = parseString(response1)
            time.sleep(0.5)
            for node in xml.getElementsByTagName('path'):
                xmlTag = node.toxml()
                xmlData = xmlTag.replace('<path>', '').replace('</path>', '').replace('[=]', '')
                url_db = "http://" + host + ":8008/metadata_database?arg0=check_database&arg1=" + xmlData
                reqdb = urllib2.Request(url_db)
                handledb = urllib2.urlopen(reqdb)
                responsedb = handledb.read()
                xmldb = parseString(responsedb)
                returnvalue = xmldb.getElementsByTagName('returnValue')[0].toxml().replace('<returnValue>', '').replace('</returnValue>', '')
                if returnvalue == "0":
                    DB_path = xmldb.getElementsByTagName('database_path')[0].toxml().replace('<database_path>', '').replace('</database_path>', '').replace('[=]', '')
                    if dbloc == "local" and DB_path.find("localhost") > -1:
                        sickbeard.NMJv2_HOST = host
                        sickbeard.NMJv2_DATABASE = DB_path
                        return True
                    if dbloc == "network" and DB_path.find("://") > -1:
                        sickbeard.NMJv2_HOST = host
                        sickbeard.NMJv2_DATABASE = DB_path
                        return True
        except IOError, e:
            logger.log(u"NMJv2: Could not contact Popcorn Hour on host %s: %s" % (host, e), logger.WARNING)
            return False

        return False

    def _sendNMJ(self, host):
        """
        Sends a NMJ update command to the specified machine

        host: The hostname/IP to send the request to (no port)
        database: The database to send the request to
        mount: The mount URL to use (optional)

        Returns: True if the request succeeded, False otherwise
        """

        #if a host is provided then attempt to open a handle to that URL
        try:
            url_scandir = "http://" + host + ":8008/metadata_database?arg0=update_scandir&arg1=" + sickbeard.NMJv2_DATABASE + "&arg2=&arg3=update_all"
            logger.log(u"NMJv2: Scan update command send to host: %s" % (host), logger.DEBUG)
            url_updatedb = "http://" + host + ":8008/metadata_database?arg0=scanner_start&arg1=" + sickbeard.NMJv2_DATABASE + "&arg2=background&arg3="
            logger.log(u"NMJv2: Try to mount network drive via url: %s" % (host), logger.DEBUG)
            prereq = urllib2.Request(url_scandir)
            req = urllib2.Request(url_updatedb)
            handle1 = urllib2.urlopen(prereq)
            response1 = handle1.read()
            time.sleep(0.5)
            handle2 = urllib2.urlopen(req)
            response2 = handle2.read()
        except IOError, e:
            logger.log(u"NMJv2: Could not contact Popcorn Hour on host %s: %s" % (host, e), logger.WARNING)
            return False

        try:
            et = etree.fromstring(response1)
            result1 = et.findtext("returnValue")
        except SyntaxError, e:
            logger.log(u"NMJv2: Unable to parse XML returned from the Popcorn Hour: update_scandir, %s" % (e), logger.ERROR)
            return False

        try:
            et = etree.fromstring(response2)
            result2 = et.findtext("returnValue")
        except SyntaxError, e:
            logger.log(u"NMJv2: Unable to parse XML returned from the Popcorn Hour: scanner_start, %s" % (e), logger.ERROR)
            return False

        # if the result was a number then consider that an error
        error_codes = ["8", "11", "22", "49", "50", "51", "60"]
        error_messages = ["Invalid parameter(s)/argument(s)",
                        "Invalid database path",
                        "Insufficient size",
                        "Database write error",
                        "Database read error",
                        "Open fifo pipe failed",
                        "Read only file system"]

        if int(result1) > 0:
            index = error_codes.index(result1)
            logger.log(u"NMJv2: Popcorn Hour returned an error: %s" % (error_messages[index]), logger.ERROR)
            return False
        else:
            if int(result2) > 0:
                index = error_codes.index(result2)
                logger.log(u"NMJv2: Popcorn Hour returned an error: %s" % (error_messages[index]), logger.ERROR)
                return False
            else:
                logger.log(u"NMJv2: Started background scan.", logger.MESSAGE)
                return True

    def _notifyNMJ(self, host=None, force=False):
        """
        Sends a NMJ update command based on the SB config settings

        host: The host to send the command to (optional, defaults to the host in the config)
        database: The database to use (optional, defaults to the database in the config)
        mount: The mount URL (optional, defaults to the mount URL in the config)
        force: If True then the notification will be sent even if NMJ is disabled in the config
        """
        # suppress notifications if the notifier is disabled but the notify options are checked
        if not sickbeard.USE_NMJv2 and not force:
            return False

        # fill in omitted parameters
        if not host:
            host = sickbeard.NMJv2_HOST

        logger.log(u"NMJv2: Sending scan command.", logger.DEBUG)

        return self._sendNMJ(host)

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        pass

    def notify_download(self, ep_name):
        pass

    def test_notify(self, host):
        return self._notifyNMJ(host, force=True)

    def update_library(self, ep_obj=None):
        if sickbeard.USE_NMJv2:
            self._notifyNMJ()

notifier = NMJv2Notifier
