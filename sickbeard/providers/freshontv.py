# Author: Damien Churchill <damoxc@gmail.com>
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

from sickbeard import common
from sickbeard import logger
from sickbeard import tvcache

class FreshOnTvProvider(generic.TorrentProvider):

    def __init__(self):
        generic.TorrentProvider.__init__(self, "FreshOnTv")
        self.supportsBacklog = False
        self.cache = FreshOnTvCache(self)
        self.url = 'http://freshon.tv/'

    def isEnabled(self):
        return sickbeard.FRESHONTV

    def imageName(self):
        return 'freshontv.ico'

class FreshOnTvCache(tvcache.TVCache):

    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)

        # only poll TvTorrents every 15 minutes max
        self.minTime = 15

    def _getRSSData(self):
        passkey = sickbeard.FRESHONTV_PASSKEY
        if not passkey:
            logger.log("No passkey has been specified, cannot search",
                       logger.ERROR)
            return

        url = self.provider.url + 'rss.php?feed=dl&passkey=' + passkey

        logger.log("FreshOnTV cache update URL: " + url, logger.DEBUG)
        return self.provider.getURL(url)

    def _parseItem(self, item):
        title = item.findtext('title')
        url = item.findtext('link')

        if not title or not url:
            logger.log("The XML returned from the FreshOnTV RSS feed is incomplete, this result is unusable", logger.ERROR)
            return

        logger.log("Adding item from RSS to cache: " + title, logger.DEBUG)
        self._addCacheEntry(title, url,
                            quality=common.Quality.nameQuality(title))

provider = FreshOnTvProvider()
