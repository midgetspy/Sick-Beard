# Author: Robert Massa <robertmassa@gmail.com>
# URL: http://code.google.com/p/sickbeard/
#
# This file is based upon tvtorrents.py.
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


class ThorsLandProvider(generic.TorrentProvider):

    def __init__(self):
        generic.TorrentProvider.__init__(self, "ThorsLand")

        self.supportsBacklog = False
        self.cache = ThorsLandCache(self)
        self.url = 'http://ethor.net/'

    def isEnabled(self):
        return sickbeard.THORSLAND

    def imageName(self):
        return 'thorsland.png'

    def _checkAuth(self):

        if not sickbeard.THORSLAND_KEY:
            raise AuthException("Your authentication credentials for " + self.name + " are missing, check your config.")
        return True

    def _checkAuthFromData(self, parsedXML):

        if parsedXML is None:
            return self._checkAuth()

        description_text = helpers.get_xml_text(parsedXML.find('.//channel/item/description'))

        if "Your RSS key is invalid" in description_text:
            logger.log(u"Incorrect authentication credentials for " + self.name + " : " + str(description_text), logger.DEBUG)
            raise AuthException(u"Your authentication credentials for " + self.name + " are incorrect, check your config")

        return True


class ThorsLandCache(tvcache.TVCache):

    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)

        # only poll every 15 minutes
        self.minTime = 15

    def _getRSSData(self):
	# rss_url = 'http://ethor.net/rss.php?feed=sdl&cat=all&rsskey=' + sickbeard.THORSLAND_KEY 
        rss_url = 'http://ethor.net/rss.php?feed=sdl&cat=48,45,43,7&rsskey=' + sickbeard.THORSLAND_KEY
	logger.log(self.provider.name + u" cache update URL: " + rss_url, logger.DEBUG)

        data = self.provider.getURL(rss_url)

        if not data:
            logger.log(u"No data returned from " + rss_url, logger.ERROR)
            return None

        return data

    def _checkAuth(self, parsedXML):
            return self.provider._checkAuthFromData(parsedXML)

provider = ThorsLandProvider()
