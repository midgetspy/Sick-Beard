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

# Modified: Marcos Almeida Jr. <junalmeida@gmail.com>
# URL: https://github.com/junalmeida/Sick-Beard

import traceback
import urllib
import re

import xml.etree.cElementTree as etree

import sickbeard
import generic

from sickbeard.common import *
from sickbeard import logger
from sickbeard import tvcache
from sickbeard.helpers import sanitizeSceneName

class KICKASSProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "KICKASS")
        
        self.supportsBacklog = False

        self.cache = KICKASSCache(self)

        self.url = 'http://www.kat.ph/'

    def isEnabled(self):
        return sickbeard.KICKASS
        
    def imageName(self):
        return 'kickass.gif'
    
    def findSeasonResults(self, show, season):
        
        results = {}
       
        results = generic.TorrentProvider.findSeasonResults(self, show, season)
        
        return results
        
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
    
    def _doSearch(self, search_params, show=None):
        try:
            params = {"rss": "1"}
        
            if search_params:
                params.update(search_params)

            searchURL = ''
            if not 'episode' in params:
                ep_number = "S%(seasonnumber)02d" % {'seasonnumber': params['season']}
                searchURL = self.url +'search/'+params['show_name'] + ' ' + ep_number
            else:
                ep_number = "S%(seasonnumber)02dE%(episodenumber)02d" % {'seasonnumber': params['season'], 'episodenumber': params['episode']}
                searchURL = self.url +'search/'+params['show_name'] + ' ' + ep_number 
            searchURL = searchURL + '/?rss=1&field=seeders&sorder=desc'

            logger.log(u"Search string: " + searchURL)
            #data = self.getURL(searchURL)

            items = []
            for index in [1,2,3,4]:
                try:
                    data = self.getURL(searchURL + "&page=%(page)d" % {'page': index })
                    if data and data.startswith("<?xml"):
                        responseSoup = etree.ElementTree(etree.XML(data))
                        newItems = responseSoup.getiterator('item')
                        items.extend(newItems)
                        if len(newItems) < 25:
                            break
                except Exception, e:
                    logger.log(u"Error trying to load KICKASS RSS feed: "+str(e).decode('utf-8'), logger.ERROR)
                    logger.log(u"RSS data: "+data, logger.DEBUG)
           
            results = []
            for curItem in items:
                (title, url) = self._get_title_and_url(curItem)
                if not title or not url:
                    logger.log(u"The XML returned from the KICKASS RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
                    continue
        
                results.append(curItem)
            logger.log("KICKASS total torrents: %(count)d" % { 'count' : len(results) })
            return results
        except Exception, e:
            logger.log(u"Error trying to load KICKASS: "+str(e).decode('utf-8'), logger.ERROR)
            traceback.print_exc()
            raise 
        
    def _get_title_and_url(self, item):
        title = item.findtext('title')
        url = item.findtext('torrentLink').replace('&amp;','&')

        return (title, url)

    def _extract_name_from_filename(self, filename):
        name_regex = '(.*?)\.?(\[.*]|\d+\.TPB)\.torrent$'
        logger.log(u"Comparing "+name_regex+" against "+filename, logger.DEBUG)
        match = re.match(name_regex, filename, re.I)
        if match:
            return match.group(1)
        return None    

class KICKASSCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll KICKASS every 15 minutes max
        self.minTime = 15


    def _getRSSData(self):
    
        url = 'http://www.kickasstorrents.com/new/?rss=1'
        logger.log(u"KICKASS cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)
        
        xml_content = etree.fromstring(data)
        description = xml_content.findtext('channel/description')

        if "Invalid Hash" in description:
            logger.log(u"KICKASS invalid hash, check your config", logger.ERROR)

        return data

    def _parseItem(self, item):

        title = item.findtext('title')
        url = item.findtext('torrentLink')

        if not title or not url:
            logger.log(u"The XML returned from the KICKASS RSS feed is incomplete, this result is unusable", logger.ERROR)
            return

        logger.log(u"Adding item from RSS to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = KICKASSProvider()
