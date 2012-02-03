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
import sickbeard

from sickbeard import logger, common
from sickbeard.notifiers.xbmc import XBMCNotifier 
from sickbeard.exceptions import ex

from xml.dom import minidom

class PLEXNotifier(XBMCNotifier):

    def notify_snatch(self, ep_name):
        if sickbeard.PLEX_NOTIFY_ONSNATCH:
            self._notifyXBMC(ep_name, common.notifyStrings[common.NOTIFY_SNATCH])

    def notify_download(self, ep_name):
        if sickbeard.PLEX_NOTIFY_ONDOWNLOAD:
            self._notifyXBMC(ep_name, common.notifyStrings[common.NOTIFY_DOWNLOAD])

    def test_notify(self, host, username, password):
        return self._update_library() 
        
    def update_library(self):
        if sickbeard.PLEX_UPDATE_LIBRARY:
            self._update_library()

    def _username(self):
        return sickbeard.PLEX_USERNAME

    def _password(self):
        return sickbeard.PLEX_PASSWORD

    def _use_me(self):
        return sickbeard.USE_PLEX

    def _hostname(self):
        return sickbeard.PLEX_HOST


    def _update_library(self):
        if not sickbeard.USE_PLEX:
            logger.log(u"Notifications for Plex Media Server not enabled, skipping library update", logger.DEBUG)
            return False

        logger.log(u"Updating Plex Media Server library", logger.DEBUG)

        if not sickbeard.PLEX_SERVER_HOST:
            logger.log(u"No host specified, no updates done", logger.DEBUG)
            return False

        logger.log(u"Plex Media Server updating " + sickbeard.PLEX_SERVER_HOST, logger.DEBUG)

        url = "http://%s/library/sections" % sickbeard.PLEX_SERVER_HOST
        try:
            xml_sections = minidom.parse(urllib.urlopen(url))
        except IOError, e:
            logger.log(u"Error while trying to contact your plex server: "+ex(e), logger.ERROR)
            return False

        sections = xml_sections.getElementsByTagName('Directory')

        for s in sections:
            if s.getAttribute('type') == "show":
                url = "http://%s/library/sections/%s/refresh" % (sickbeard.PLEX_SERVER_HOST, s.getAttribute('key'))

                try:
                    urllib.urlopen(url)
                except Exception, e:
                    logger.log(u"Error updating library section: "+ex(e), logger.ERROR)
                    return False

        return True

notifier = PLEXNotifier
