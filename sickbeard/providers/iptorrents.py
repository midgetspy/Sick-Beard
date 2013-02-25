# Author: seedboy
# URL: https://github.com/seedboy
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

from sickbeard import logger
from sickbeard import tvcache

class IPTorrentsProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "IPTorrents")

        self.supportsBacklog = False

        self.cache = IPTorrentsCache(self)

        self.url = 'http://www.iptorrents.com/'

    def isEnabled(self):
        return sickbeard.IPTORRENTS

    def imageName(self):
        return 'iptorrents.png'

class IPTorrentsCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll IPTorrents every 10 minutes max
        self.minTime = 10

    def _getRSSData(self):

        url = 'http://www.iptorrents.com/torrents/rss?download;l73;u='+ sickbeard.IPTORRENTS_UID +';tp='+ sickbeard.IPTORRENTS_PASSKEY
        logger.log(u"IPTorrents cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data

    def _parseItem(self, item):

        (title, url) = self.provider._get_title_and_url(item)

        if not title or not url:
            logger.log(u"The XML returned from the IPTorrents RSS feed is incomplete, this result is unusable", logger.ERROR)
            return

        logger.log(u"Adding item from RSS to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = IPTorrentsProvider()
