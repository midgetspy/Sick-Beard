# Author: Taylor Raack <traack@raack.info>
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

class KATProvider(rssbacklogtorrent.RSSBacklogProvider):
    def __init__(self):
        rssbacklogtorrent.RSSBacklogProvider.__init__(self, "KAT", "http://www.kat.ph/")

        self.cache = KATRSSCache(self)

    def isEnabled(self):
        return sickbeard.KAT
        
    def imageName(self):
        return 'kat.gif'
       
    def _get_search_url(self, show_snippet):
        return self.url + 'search/' + urllib2.quote(show_snippet.strip()) + '/?rss=1'
       
    def _get_title_and_url(self, item):
        return self._get_torrent_title_and_url(item)

    def _get_torrent_title_and_url(self, item):
        title = item.findtext('title')
        url = item.findtext('torrentLink')

        return (title, url)

    def _is_valid_item(self, item):
        rawTitle = item.findtext('title')

        if not rawTitle:
            logger.log(u"The XML returned from the KAT RSS feed is incomplete, this result is unusable: " + data, logger.ERROR)
            return false

        seeds = item.findtext('seeds')
        logger.log(rawTitle + " had " + seeds + " seeds", logger.DEBUG)
        return int(seeds) >= sickbeard.KAT_MINIMUM_SEEDS # Minimum number of seeds

    def getURL(self, url, headers=None):
        """
        Overridden because KAT's site yields an HTTPError if zero results are returned
        """

        if not headers:
            headers = []

        result = None

        try:
            result = helpers.getURL(url, headers)
        except urllib2.HTTPError as e:
            logger.log(u"KAT returned HTTPError, interpreting as zero result search " + ex(e), logger.DEBUG)
            logger.log(u"No results found on KickassTorrents")
        except IOError as e:
            logger.log(u"Error loading "+self.name+" URL: " + str(sys.exc_info()) + " - " + ex(e))

        return result

class KATRSSCache(rssbacklogtorrent.RSSCache):
    def __init__(self, provider):
        rssbacklogtorrent.RSSCache.__init__(self, provider)

        self.url += 'tv/?rss=1' #TV list

provider = KATProvider()
