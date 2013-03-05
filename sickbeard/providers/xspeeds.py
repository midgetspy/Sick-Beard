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

class XSpeedsProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "XSpeeds")
        
        self.supportsBacklog = False

        self.cache = XSpeedsCache(self)

        self.url = 'http://xspeeds.eu/'

    def isEnabled(self):
        return sickbeard.XSPEEDS
        
    def imageName(self):
        return 'tvtorrents.png'

class XSpeedsCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll TvTorrents every 15 minutes max
        self.minTime = 15


    def _getRSSData(self):
        # These will be ignored on the serverside.
    
        url = 'http://xspeeds.eu/rss.php?secret_key='+ sickbeard.XSPEEDS_KEY +'&showrows=50&feedtype=download&timezone='+sickbeard.XSPEEDS_TIMEZONE +'&categories='+ sickbeard.XSPEEDS_CATEGORIES
        logger.log(u"XSpeeds cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)
        
        parsedXML = parseString(data)
        channel = parsedXML.getElementsByTagName('channel')[0]
        description = channel.getElementsByTagName('description')[0]

        description_text = helpers.get_xml_text(description)

        if "Invalid Hash" in description_text:
            logger.log(u"XSpeeds invalid hash, check your config", logger.ERROR)

        return data

    def _parseItem(self, item):

        (title, url) = self.provider._get_title_and_url(item)

        if not title or not url:
            logger.log(u"The XML returned from the XSPeeds RSS feed is incomplete, this result is unusable", logger.ERROR)
            return

        logger.log(u"Adding item from RSS to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = XSpeedsProvider()
