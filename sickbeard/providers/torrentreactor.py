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

class TorrentReactorProvider(rssbacklogtorrent.RSSBacklogProvider):
    def __init__(self):
        rssbacklogtorrent.RSSBacklogProvider.__init__(self, "TorrentReactor", "http://www.torrentreactor.net/rss.php?search=")

        self.cache = TorrentReactorRSSCache(self)

    def isEnabled(self):
        return sickbeard.TORRENTREACTOR
        
    def imageName(self):
        return 'torrentreactor.png'
       
    def _get_search_url(self, show_snippet):
        return self.url + urllib2.quote(show_snippet.strip())
       
    def _get_title_and_url(self, item):
        return self._get_torrent_title_and_url(item)

    def _get_torrent_title_and_url(self, item):
        title = item.findtext('title')
        url = item.findtext('link')

        return (title, url)

    def _is_valid_item(self, item):
        rawTitle = item.findtext('title')

        if not rawTitle:
            logger.log(u"The XML returned from the TorrentReactor RSS feed is incomplete, this result is unusable: " + data, logger.ERROR)
            return false

        seeds = re.findall('(\\b\\d+\\b) seeders', item.findtext('description'))[0]
        logger.log(rawTitle + " had " + seeds + " seeds", logger.DEBUG)
        return int(seeds) >= sickbeard.TORRENTREACTOR_MINIMUM_SEEDS # Minimum number of seeds

class TorrentReactorRSSCache(rssbacklogtorrent.RSSCache):
    def __init__(self, provider):
        rssbacklogtorrent.RSSCache.__init__(self, provider)

        self.url = 'http://www.torrentreactor.net/rss.php?cid=8' # TV list

provider = TorrentReactorProvider()
