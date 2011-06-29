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

import xml.etree.cElementTree as etree

import sickbeard
import generic

from sickbeard import logger
from sickbeard import tvcache
from sickbeard import common

class TVTorrentzProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "TVTorrentz")
        self.supportsBacklog = False
        self.cache = TVTorrentzCache(self)
        self.url = 'http://www.tvtorrentz.org/'

    def isEnabled(self):
        return sickbeard.TVTORRENTZ
        
    def imageName(self):
        return 'tvtorrentz.gif'

class TVTorrentzCache(tvcache.TVCache):

    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        # only poll TvTorrentz every 15 minutes max
        self.minTime = 15

    def _getRSSData(self):
        url = self.provider.url + 'rss.php?pk='+sickbeard.TVTORRENTZ_PASSKEY
        logger.log(u"TvTorrentz cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)
        
        return data

    def _parseItem(self, item):

        title = item.findtext('title')
        url = item.findtext('link')

        if not title or not url:
            logger.log(u"The XML returned from the TVTorrentz RSS feed is incomplete, this result is unusable", logger.ERROR)
            return

        logger.log(u"Adding item from RSS to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = TVTorrentzProvider()
