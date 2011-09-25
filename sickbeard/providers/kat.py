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

import urllib
import re

import xml.etree.cElementTree as etree

import sickbeard
import rssbacklogtorrent

from sickbeard.common import Quality
from sickbeard import logger
from sickbeard import tvcache
from sickbeard.helpers import sanitizeSceneName
from sickbeard.exceptions import ex

class KATProvider(rssbacklogtorrent.RSSBacklogProvider):
    def __init__(self):
        rssbacklogtorrent.RSSBacklogProvider.__init__(self, "KAT", "http://www.kat.ph/")

    def isEnabled(self):
        return sickbeard.KAT
        
    def imageName(self):
        return 'kat.gif'
       
    def _get_search_url(self, show_snippet):
		return self.url + 'search/' + urllib.quote(show_snippet) + '/?rss=1'
       
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
		logger.log("Torrent had " + seeds + " seeds", logger.DEBUG)
		return int(seeds) >= 10	# Minimum number of seeds

class KATRSSCache(rssbacklogtorrent.RSSCache):

	def _get_rss_uri(self):
	   return 'tv/?rss=1' #TV list

provider = KATProvider()