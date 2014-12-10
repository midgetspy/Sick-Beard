# Author: Matthew Zera <mattzera@gmail.com>
# URL: http://code.google.com/p/sickbeard/
#
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

import sickbeard
import generic

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import elementtree.ElementTree as etree

from sickbeard import helpers, logger, tvcache
from sickbeard.exceptions import ex, AuthException


class IPTorrentsProvider(generic.TorrentProvider):

    def __init__(self):
        generic.TorrentProvider.__init__(self, "IPTorrents")

        self.supportsBacklog = False
        self.cache = IPTorrentsCache(self)
        self.url = 'http://www.iptorrents.com'

    def isEnabled(self):
        return sickbeard.IPTORRENTS

    def imageName(self):
        return 'iptorrents.png'

    def getURL(self, url, post_data=None, headers=None):

        if not headers:
            headers = []

        data = helpers.getURL(url, post_data, headers)

        if not data:
            logger.log(u"Error loading " + self.name + " URL: " + url + " Your User Number and/or Torrent Pass may be incorrect", logger.ERROR)
            return None

        return data

    def _checkAuth(self):

        if not sickbeard.IPTORRENTS_U:
            raise AuthException("Your User Number for " + self.name + " are missing, check your config.")

        if not sickbeard.IPTORRENTS_TP:
            raise AuthException("Your Torrent Pass for " + self.name + " are missing, check your config.")

        return True

    def _checkAuthFromData(self, parsedXML):

        if parsedXML is None:
            return self._checkAuth()

        return True


class IPTorrentsCache(tvcache.TVCache):

    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)

        # only poll every 15 minutes
        self.minTime = 15

    def _getRSSData(self):

        rss_url = 'https://iptorrents.com/torrents/rss?u=' + sickbeard.IPTORRENTS_U + ';tp=' + sickbeard.IPTORRENTS_TP + ';l23;l24;l25;l78;l66;l79;l22;l5;l4;download'

        logger.log(self.provider.name + u" cache update URL: " + rss_url, logger.DEBUG)

        data = self.provider.getURL(rss_url)

        if not data:
            logger.log(u"No data returned from " + rss_url, logger.ERROR)
            return None

        return data

    def _checkAuth(self, parsedXML):
            return self.provider._checkAuthFromData(parsedXML)

provider = IPTorrentsProvider()
