# Author: Daniel Pavel <daniel.pavel@gmail.com>
# Mostly copied from tvtorrents.py
#
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

class FreshOnTvProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "FreshOnTv")
        
        self.supportsBacklog = False

        self.cache = FreshOnTVCache(self)

        self.url = 'http://freshon.tv/'

    def isEnabled(self):
        return sickbeard.FRESHONTV
        
    def imageName(self):
        return 'freshontv.gif'

class FreshOnTVCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll freshon.tv every 30 minutes max
        self.minTime = 30


    def _getRSSData(self):
        url = 'http://freshon.tv/rss.php?feed=dl&passkey='+ sickbeard.FRESHONTV_PASSKEY
        logger.log(u"FreshOn.tv cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)
        if not data:
            logger.log(u"FreshOn.tv invalid passkey, check your config", logger.ERROR)

        return data

    def _parseItem(self, item):
        (title, url) = self.provider._get_title_and_url(item)

        if not title or not url:
            logger.log(u"The XML returned from the FreshOn.tv RSS feed is incomplete, this result is unusable", logger.ERROR)
            return

        logger.log(u"Adding item from RSS to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = FreshOnTvProvider()