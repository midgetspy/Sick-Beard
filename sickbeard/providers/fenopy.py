# Author: Cameron Currie <me@cameroncurrie.net>
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

import urllib2
import re

import xml.etree.cElementTree as etree

import sickbeard
import rssbacklogtorrent

from sickbeard.common import Quality
from sickbeard import logger
from sickbeard import tvcache
from sickbeard import helpers
from sickbeard.helpers import sanitizeSceneName
from sickbeard.exceptions import ex

class FenopyProvider(rssbacklogtorrent.RSSBacklogProvider):
    def __init__(self):
        rssbacklogtorrent.RSSBacklogProvider.__init__(self, "Fenopy", "http://fenopy.eu/module/search/api.php?keyword=%s&sort=peer&category=78")

        self.cache = FenopyRSSCache(self)

        self.torrent_element = 'result'

    def isEnabled(self):
        return sickbeard.FENOPY
        
    def imageName(self):
        return 'fenopy.ico'
       
    def _get_search_url(self, show_snippet):
        return self.url % urllib2.quote(show_snippet.strip())
       
    def _get_title_and_url(self, item):
        return self._get_torrent_title_and_url(item)

    def _get_torrent_title_and_url(self, item):
        title = item.findtext('name')
        url = item.findtext('torrent')

        return (title, url)

    def _is_valid_item(self, item):
        rawTitle = item.findtext('name')

        if not rawTitle:
            logger.log(u"The XML returned from the Fenopy RSS feed is incomplete, this result is unusable: " + data, logger.ERROR)
            return false

        seeds = item.findtext('seeder')
        logger.log(rawTitle + " had " + seeds + " seeds", logger.DEBUG)
        return int(seeds) >= sickbeard.FENOPY_MINIMUM_SEEDS # Minimum number of seeds

class FenopyRSSCache(rssbacklogtorrent.RSSCache):
    def __init__(self, provider):
        rssbacklogtorrent.RSSCache.__init__(self, provider)

        self.url = 'http://fenopy.eu/rss.xml?row=50&cat=78&type=2' # TV List

    def _parseItem(self, item):
        title = helpers.get_xml_text(item.getElementsByTagName('title')[0])
        url = helpers.get_xml_text(item.getElementsByTagName('link')[0])

        if not title or not url:
            logger.log(u"The XML returned from the "+self.provider.name+" feed is incomplete, this result is unusable", logger.ERROR)
            return

        url = self._translateLinkURL(url)

        logger.log(u"Adding item from RSS to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = FenopyProvider()
