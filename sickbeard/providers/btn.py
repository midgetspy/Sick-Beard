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

class BTNProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "BroadcasThe.Net")
        
        self.supportsBacklog = False

        self.cache = BTNCache(self)

        self.url = 'http://www.broadcasthe.net/'

    def isEnabled(self):
        return True
        
    def imageName(self):
        return 'btn.gif'

class BTNCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll BTN every 15 minutes max
        self.minTime = 15
		

    def _getRSSData(self):
        # These will be ignored on the serverside.
        ignore_regex = "all.month|month.of|season[\s\d]*complete"
    
        
        url = 'https://broadcasthe.net/feeds.php?feed=torrents_all&user='+ sickbeard.BTN_USER_ID +'&auth='+ sickbeard.BTN_AUTH_TOKEN +'&passkey='+ sickbeard.BTN_PASSKEY +'&authkey='+ sickbeard.BTN_AUTHKEY
        logger.log(u"BTN cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)
        
        xml_content = etree.fromstring(data)
        description = xml_content.findtext('channel/description')

		# [TODO] Error handling
        # if "User can't be found" in description:
        #     logger.log(u"TvTorrents invalid digest, check your config", logger.ERROR)
        # 
        # if "Invalid Hash" in description:
        #     logger.log(u"TvTorrents invalid hash, check your config", logger.ERROR)

        return data

    def _parseItem(self, item):

        title = item.findtext('title')
        url = item.findtext('link')

        if not title or not url:
            logger.log(u"The XML returned from the BTN RSS feed is incomplete, this result is unusable", logger.ERROR)
            return

        logger.log(u"Adding item from RSS to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = BTNProvider()