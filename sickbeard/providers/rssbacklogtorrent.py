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
import generic

from sickbeard.common import Quality
from sickbeard import logger
from sickbeard import tvcache
from sickbeard.helpers import sanitizeSceneName
from sickbeard.exceptions import ex

class RSSBacklogProvider(generic.TorrentProvider):

    def __init__(self, name, url):

        generic.TorrentProvider.__init__(self, name)
        
        self.provider_name = name
        
        self.supportsBacklog = True

        self.cache = RSSCache(self)

        self.url = url

      
    def getQuality(self, item):
        
        (title,url) = self._get_title_and_url(item)
        quality = Quality.nameQuality(title)
        return quality

    def findSeasonResults(self, show, season):
        
        results = {}
        
        if show.air_by_date:
            message = self.provider_name + " doesn't support air-by-date backlog because of limitations on their RSS search."
            logger.log(message, logger.WARNING)
            return results
        
        results = generic.TorrentProvider.findSeasonResults(self, show, season)
        
        return results

    def _get_season_search_strings(self, show, season=None):
    
        params = {}
    
        if not show:
            return params
        
        params['show_name'] = sanitizeSceneName(show.name, ezrss=True).replace('.', ' ').encode('utf-8')
          
        if season != None:
            params['season'] = season
    
        return [params]

    def _get_episode_search_strings(self, ep_obj):
    
        params = {}
        
        if not ep_obj:
            return params
                   
        params['show_name'] = sanitizeSceneName(ep_obj.show.name, ezrss=True).replace('.', ' ').encode('utf-8')
        
        if ep_obj.show.air_by_date:
            params['date'] = str(ep_obj.airdate)
        else:
            params['season'] = ep_obj.season
            params['episode'] = ep_obj.episode
    
        return [params]

    def _doSearch(self, search_params, show=None):
        showName = ''
        season = ''
        episode = ''
    
        if 'show_name' in search_params:
            showName = search_params['show_name']
    
        if 'season' in search_params:
            season = 'S' + '%(season)02d' % search_params
            
        if 'episode' in search_params:
            epsiode = 'E' + '%(episode)02d' % search_params
    
        showText = showName.replace('-', ' ') + ' ' + season + ' ' + episode
        
        searchURL = self._get_search_url(showText)

        logger.log(u"Search string: " + searchURL, logger.DEBUG)

        data = self.getURL(searchURL)

        if not data:
            return []
        
        try:
            responseSoup = etree.ElementTree(etree.XML(data))
            items = responseSoup.getiterator('item')
        except Exception, e:
            logger.log(u"Error trying to load RSS feed: " + ex(e), logger.ERROR)
            logger.log(u"RSS data: " + data, logger.DEBUG)
            return []
        
        results = []

        for curItem in items:
            (title, url) = self._get_title_and_url(curItem)
            
            if not title or not url:
                logger.log(u"The XML returned from the EZRSS RSS feed is incomplete, this result is unusable: " + data, logger.ERROR)
                continue
            
            if self._is_valid_item(curItem):
                results.append(curItem)

        return results

class RSSCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll every 15 minutes max
        self.minTime = 15

    def _getRSSData(self):
        url = self.provider.url + 'feed/'

        logger.log(u"cache update URL: " + url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data

    def _parseItem(self, item):
        (title, url) = self.provider._get_torrent_title_and_url(item)

        if not title or not url:
            logger.log(u"The XML returned from the KAT RSS feed is incomplete, this result is unusable", logger.ERROR)
            return

        logger.log(u"Adding item from RSS to cache: " + title, logger.DEBUG)

        self._addCacheEntry(title, url)
