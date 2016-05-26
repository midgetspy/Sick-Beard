# Author: Arvin Singla <arvin.singla@gmail.com>
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


class BitMeTVProvider(generic.TorrentProvider):

    def __init__(self):
        generic.TorrentProvider.__init__(self, "BitMeTV")

        self.supportsBacklog = False
        self.cache = BitMeTVCache(self)
        self.url = 'http://www.bitmetv.org/'

    def isEnabled(self):
        return sickbeard.BITMETV

    def imageName(self):
        return 'bitmetv.png'

    def getURL(self, url, post_data=None, headers=None):

        if not headers:
            headers = [('Cookie', 'uid=' + sickbeard.BITMETV_UID + ';pass=' + sickbeard.BITMETV_PASS + ';')]

        data = helpers.getURL(url, post_data, headers)

        if not data:
            logger.log(u"Error loading " + self.name + " URL: " + url + " Your User id and/or key may be incorrect", logger.ERROR)
            return None

        return data

    def _checkAuth(self):

        if not sickbeard.BITMETV_UID:
            raise AuthException("Your User ID for " + self.name + " is missing, check your config.")

        if not sickbeard.BITMETV_KEY:
            raise AuthException("Your key for " + self.name + " is missing, check your config.")

        if not sickbeard.BITMETV_PASS:
            raise AuthException("Your pass for " + self.name + " is missing, check your config.")

        return True

    def _checkAuthFromData(self, parsedXML):

        if parsedXML is None:
            return self._checkAuth()

        return True


class BitMeTVCache(tvcache.TVCache):

    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)

        # only poll every 15 minutes
        self.minTime = 15

    def _getRSSData(self):

        rss_url = 'http://www.bitmetv.org/rss.php?uid=' + sickbeard.BITMETV_UID + '&passkey=' + sickbeard.BITMETV_KEY

        logger.log(self.provider.name + u" cache update URL: " + rss_url, logger.DEBUG)

        data = self.provider.getURL(rss_url)

        if not data:
            logger.log(u"No data returned from " + rss_url, logger.ERROR)
            return None

        return data

    def _checkAuth(self, parsedXML):
            return self.provider._checkAuthFromData(parsedXML)

provider = BitMeTVProvider()
