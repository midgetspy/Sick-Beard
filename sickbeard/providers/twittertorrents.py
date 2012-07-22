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

from xml.dom.minidom import parseString

import sickbeard
import generic

from sickbeard import helpers
from sickbeard import logger
from sickbeard import tvcache

class TwitterTorrentsProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "TwitterTorrents")

        self.supportsBacklog = False

        self.cache = TwitterTorrentsCache(self)

        self.url = 'http://twitter.com/'

    def isEnabled(self):
        return sickbeard.TWITTERTORRENTS

    def imageName(self):
        return 'tvtorrents.gif'

    def _get_title_and_url(self, item):
        (title, url) = generic.TorrentProvider._get_title_and_url(self, item)
        if not 'http://twitter.com' in url:
            logger.log(u"Twitter url not found in item", logger.Error)
            return (title, url)

        # handle if it's a twiiter feed
        title, url = title.rsplit('http://',1)
        url = 'http://'+url
        id = sickbeard.TWITTERTORRENTS_ID if sickbeard.TWITTERTORRENTS_ID else 'eztv_it'
        title = title.replace(id,'')
        title = title.strip(':').strip().strip('-').strip()
        logger.log(u"Extracted the name "+title+" from the torrent link", logger.DEBUG)

        return (title, url)


class TwitterTorrentsCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll Twitter every 5 minutes max
        self.minTime = 5

    def _getRSSData(self):
        # can also support http://search.twitter.com/search.rss?q=daily+from:eztv_it

        id = sickbeard.TWITTERTORRENTS_ID if sickbeard.TWITTERTORRENTS_ID else 'eztv_it'

        url = 'http://api.twitter.com/1/statuses/user_timeline.rss?screen_name=%s'%id

        logger.log(u"Twitter (torrents) cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data

    def _parseItem(self, item):

        (title, url) = self.provider._get_title_and_url(item)

        if not title or not url:
            logger.log(u"The XML returned from the TvTorrents RSS feed is incomplete, this result is unusable", logger.ERROR)
            return

        logger.log(u"Adding item from RSS to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = TwitterTorrentsProvider()