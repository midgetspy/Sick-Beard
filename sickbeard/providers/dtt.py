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

import urllib
import re

import xml.etree.cElementTree as etree

import sickbeard
import generic

from sickbeard.common import Quality
from sickbeard import logger
from sickbeard import tvcache
from sickbeard.helpers import sanitizeSceneName
from sickbeard.exceptions import ex

class DTTProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "DailyTvTorrents")
        
        self.supportsBacklog = True

        self.cache = DTTCache(self)

        self.url = 'http://www.dailytvtorrents.org/rss/'

    def isEnabled(self):
        return sickbeard.DTT
        
    def imageName(self):
        return 'dtt.gif'
      
    def getQuality(self, item):
        url = item.find('enclosure').get('url')
        quality = Quality.nameQuality(url)
        return quality

    def findSeasonResults(self, show, season):
        if show.air_by_date:
            logger.log(u"DTT doesn't support air-by-date backlog because of limitations on their RSS search.", logger.WARNING)
            return {}
        
        return generic.TorrentProvider.findSeasonResults(self, show, season)
    
    def _dtt_show_id(self, show_name):
        return sanitizeSceneName(show_name).replace('.','-').lower()

    def _get_episode_search_strings(self, episode):
        return self._get_season_search_strings(episode.show, episode.season)

    def _get_season_search_strings(self, show, season):
        seasons = show.episodes.keys()
        if len(seasons) and season < max(seasons):
            return [{'items': 'all'}]
    
        return [{}]

    def _doSearch(self, params, show=None):
        if show == None:
            raise exceptions.ShowNotFoundException("Tried to search for a show with no name")

        show_id = self._dtt_show_id(show.name)

        search_params = {"single": "yes"}

        if params:
            search_params.update(params)

        searchURL = self.url + "show/" + show_id + "?" + urllib.urlencode(search_params)

        logger.log(u"Search string: " + searchURL, logger.DEBUG)

        data = self.getURL(searchURL)

        if not data:
            return []
        
        try:
            response = etree.ElementTree(etree.XML(data))
            return response.getiterator('item')
        except Exception, e:
            logger.log(u"Error trying to load DTT RSS feed: "+ex(e), logger.ERROR)
            logger.log(u"RSS data: "+data, logger.DEBUG)
            return []

    def _get_title_and_url(self, item):
        title = item.findtext('description').replace("_", ".").split(" (")[0]
        url = item.find('enclosure').get('url')

        return (title, url)

class DTTCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll DTT every 30 minutes max
        self.minTime = 30


    def _getRSSData(self):
        url = self.provider.url + 'allshows?single=yes'

        logger.log(u"DTT cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data

    def _parseItem(self, item):
        title, url = self.provider._get_title_and_url(item)

        logger.log(u"Adding item from RSS to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = DTTProvider()