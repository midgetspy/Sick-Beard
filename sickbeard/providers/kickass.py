# Modified by: Marcos Almeida Jr. <junalmeida@gmail.com>
# URL: https://github.com/junalmeida/Sick-Beard
#
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



import traceback
import urllib
import re

import xml.etree.cElementTree as etree

import sickbeard
import generic

from sickbeard import encodingKludge as ek
from sickbeard.common import *
from sickbeard import logger, helpers
from sickbeard import tvcache
from sickbeard.helpers import sanitizeSceneName

class KICKASSProvider(generic.TorrentProvider):

    def __init__(self):
        generic.TorrentProvider.__init__(self, "Kickass")
        
        self.supportsBacklog = True

        self.cache = KICKASSCache(self)

        self.url = 'http://www.kat.ph/'

    def isEnabled(self):
        return sickbeard.KICKASS
        
    def imageName(self):
        return 'kickass.png'
    
    def findSeasonResults(self, show, season):
        
        results = {}
       
        results = generic.TorrentProvider.findSeasonResults(self, show, season)
        
        return results
        
    def _get_season_search_strings(self, show, season=None):
    
        params = {}
    
        if not show:
            return params

        params['show_name'] = self._sanitizeNameToSearch(show.name)
          
        if season != None:
            params['season'] = season
    
        return [params]    
    
    def _get_episode_search_strings(self, ep_obj):
    
        params = {}
        
        if not ep_obj:
            return params
                   
        params['show_name'] = self._sanitizeNameToSearch(ep_obj.show.name)
        
        if ep_obj.show.air_by_date:
            params['date'] = str(ep_obj.airdate)
        else:
            params['season'] = ep_obj.season
            params['episode'] = ep_obj.episode
    
        return [params]
    def _sanitizeNameToSearch(self, text):
        text = re.sub(r'\([^)]*\)', '', text)
        return sanitizeSceneName(text, ezrss=True).replace('.',' ').replace('-',' ').encode('utf-8')
                  
    def _doSearch(self, search_params, show=None):
        try:
            params = {"rss": "1"}
        
            if search_params:
                params.update(search_params)

            searchURL = ''
            
            if not 'episode' in params:
                ep_number = "S%(seasonnumber)02d" % {'seasonnumber': params['season']}
                searchURL = self.url +'search/' + params['show_name'] + ' ' + ep_number
            else:
                ep_number = "S%(seasonnumber)02dE%(episodenumber)02d" % {'seasonnumber': params['season'], 'episodenumber': params['episode']}
                searchURL = self.url +'search/' + params['show_name'] + ' ' + ep_number 
            searchURL = searchURL + '/?rss=1&field=seeders&sorder=desc'
            searchURL = searchURL.lower()
            
            logger.log(u"Search string: " + searchURL)
            #data = self.getURL(searchURL)

            items = []
            for index in [1,2,3,4,5]:
                try:
                    data = self.getURL(searchURL + "&page=%(page)d" % {'page': index })
                    if data and data.startswith("<?xml"):
                        responseSoup = etree.ElementTree(etree.XML(data))
                        newItems = responseSoup.getiterator('item')
                        oldCount = len(items)
                        items.extend(newItems)
                        if len(items) - oldCount < 25:
                            break
                except Exception, e:
                    logger.log(u"Error trying to load " + self.name + " RSS feed: "+str(e).decode('utf-8'), logger.ERROR)
                    traceback.print_exc()
           
            results = []
            for curItem in items:
                try:
                    (title, url) = self._get_title_and_url(curItem)
                    if not title or not url:
                        logger.log(u"The XML returned from the KICKASS RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
                        continue
                    results.append(curItem)
                except Exception, e:
                    logger.log(u"Error trying to load KICKASS RSS feed item: "+str(e).decode('utf-8'), logger.ERROR)
               
            logger.log("KICKASS total torrents: %(count)d" % { 'count' : len(results) })
            
            return results
        except Exception, e:
            logger.log(u"Error trying to load KICKASS: "+str(e).decode('utf-8'), logger.ERROR)
            traceback.print_exc()
            raise 
        
    def _get_title_and_url(self, item):
        title = item.findtext('title')
        url = item.find('enclosure').attrib["url"].replace('&amp;','&')

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
        url = self.provider.url + 'tv/?rss=1'

        logger.log(u"KICKASS cache update URL: " + url)

        data = self.provider.getURL(url)
        return data
    
    def _parseItem(self, item):
        try:      
            title = helpers.get_xml_text(item.getElementsByTagName('title')[0])
            url = item.getElementsByTagName('enclosure')[0].getAttribute("url").replace('&amp;','&')

            if not title or not url:
                logger.log(u"The XML returned from the KICKASS RSS feed is incomplete, this result is unusable", logger.ERROR)
                return

            logger.log(u"Adding item from KICKASS RSS to cache: "+title, logger.DEBUG)
            
            self._addCacheEntry(title, url)
        
        except Exception, e:
            logger.log(u"Error trying to parse KICKASS cache: "+str(e).decode('utf-8'), logger.ERROR)
            traceback.print_exc()
            raise 
provider = KICKASSProvider()