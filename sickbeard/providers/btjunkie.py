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

class BTJunkieUtils:
	regex_seeds = '\[([0-9]+)/[0-9]+\]'

	@staticmethod
	def getTorrentTitleAndUrl(item):
	    	title = re.sub(BTJunkieUtils.regex_seeds, '', item.findtext('title')) # Remove seeds portion of title (seems to confuse Quality.nameQuality method)
	    	url = item.findtext('link').replace('&amp;','&') + '/download.torrent'

		return (title, url)

class BTJunkieProvider(generic.TorrentProvider):
    def __init__(self):
        generic.TorrentProvider.__init__(self, "BTJunkie")
        self.supportsBacklog = True
        self.cache = BTJunkieCache(self)
        self.url = 'http://www.btjunkie.org/'

    def isEnabled(self):
        return sickbeard.BTJUNKIE
        
    def imageName(self):
        return 'btjunkie.gif'

    def getQuality(self, item):
	(title, url) = BTJunkieUtils.getTorrentTitleAndUrl(item)

        quality = Quality.nameQuality(title)

        return quality

    def _get_season_search_strings(self, show, season=None):
        params = {}
    
        if not show:
            return params
        
        params['show_name'] = sanitizeSceneName(show.name, ezrss=True).replace('.',' ').encode('utf-8')
          
        if season != None:
            params['season'] = season
    
        return [params]

    def _get_episode_search_strings(self, ep_obj):
        params = {}
        
        if not ep_obj:
            return params
                   
        params['show_name'] = sanitizeSceneName(ep_obj.show.name, ezrss=True).replace('.',' ').encode('utf-8')
        
        if ep_obj.show.air_by_date:
            params['date'] = str(ep_obj.airdate)
        else:
            params['season'] = ep_obj.season
            params['episode'] = ep_obj.episode
    
        return [params]

    def findSeasonResults(self, show, season):
	result = {}
	
	if show.air_by_date:
    	    logger.log(u"BTJunkie doesn't support air-by-date backlog searches", logger.ERROR)
	    return results

	results = generic.TorrentProvider.findSeasonResults(self, show, season)

	return results

    def _getXmlItems(self, url):
        logger.log(u"Searching BTJunkie with URL: " + url, logger.DEBUG)

	data = self.getURL(url)
	
        if not data:
            return []
        
        try:
            responseSoup = etree.ElementTree(etree.XML(data))
            items = responseSoup.getiterator('item')
        except Exception, e:
            logger.log(u"Error trying to load BTJunkie RSS feed: "+ex(e), logger.ERROR)
            logger.log(u"RSS data: "+data, logger.DEBUG)
            return []

	return items

    def _doSearch(self, search_params, show=None):
	showName = ''
	season = ''
	episode = ''

	if 'show_name' in search_params:
	    showName = search_params['show_name']

	if 'season' in search_params:
	    season = 'S' + '%(season)02d' % search_params
	    if season is 'S00':
		logger.log(u"BTJunkie does not usually have specials listed in the correct format (i.e. S00E01)", logger.WARNING)

	if 'episode' in search_params:
	    epsiode = 'E' + '%(episode)02d' % search_params

	params = {}
	params['q'] = showName + ' ' + season + ' ' + episode # Search string
	params['o'] = '52' # Sort by number of seeders

        searchURL = self.url + 'rss.xml?'

	# Execute search
        items = self._getXmlItems(searchURL + urllib.urlencode(params))
	if items:
		results = self._parseXmlItems(items)
	else:
		results = []

	return results 

    def _parseXmlItems(self, items):
        results = []

        for curItem in items:
	    try:
		rawTitle = curItem.findtext('title')

		if not rawTitle:
		    logger.log(u"The XML returned from the BTJunkie RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
		    continue

	        logger.log("Comparing seeds regex " + BTJunkieUtils.regex_seeds + " against " + rawTitle, logger.DEBUG)
    
    	        match = re.search(BTJunkieUtils.regex_seeds, rawTitle, re.I)
	        if match:
	 	    seeds = match.group(1)
		    logger.log("Torrent had " + seeds + " seeds", logger.DEBUG)
		    if int(seeds) >= 10:	# Minimum number of seeds
		        results.append(curItem)
	    except Exception, e:
	        logger.log("Exception parsing XML item: " + ex(e), logger.ERROR)
            
        return results

    def _get_title_and_url(self, item):
	return BTJunkieUtils.getTorrentTitleAndUrl(item)

class BTJunkieCache(tvcache.TVCache):

    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)

	# Update BTJunkie latest releases as often as every 15 minutes
        self.minTime = 15

    def _getRSSData(self):
        url = self.provider.url + 'rss.xml?c=4' # TV list

	data = self.provider.getURL(url)

        logger.log(u"BTJunkie cache update URL for latest TV shows: " + url, logger.DEBUG)

        data = self.provider.getURL(url)
        
        return data

    def _parseItem(self, item):
	(title, url) = BTJunkieUtils.getTorrentTitleAndUrl(item)

        if not title or not url:
            logger.log(u"The XML returned from the BTJunkie RSS feed is incomplete, this result is unusable", logger.ERROR)
            return

        logger.log(u"Adding item from RSS to cache: " + title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = BTJunkieProvider()
