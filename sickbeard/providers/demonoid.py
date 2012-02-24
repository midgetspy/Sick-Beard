# Author: Joshua Kaplan <jkaplan@me.com>
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

import re

import sickbeard
import generic


from sickbeard import logger
from sickbeard.common import Quality
from sickbeard import tvcache

class DemonoidProvider(generic.TorrentProvider):
    
    def __init__(self):
        generic.TorrentProvider.__init__(self,"Demonoid")
        
        self.supportsBacklog = False
        
        self.cache = DemonoidCache(self)
        
        self.url = 'http://www.demonoid.me'
        
    def isEnabled(self):
        return sickbeard.DEMONOID
    
    def imageName(self):
        return 'demonoid.gif'
    
    def getQuality(self, item):
        """Since Demonoid doesn't require a quality in the title, 
        check title for a quality otherwise, 
        use the quality from item description"""
        
        title = item.findtext('title')
        quality = Quality.nameQuality(title)
        
        if quality != Quality.UNKNOWN:
            return quality
        
        description = item.findtext('description')
        quality_regex = r'Quality:\s(\w\w\w*)\s*'
        
        match = re.search(quality_regex, description)
        if match:
            quality = match.group(1)
        else:
            logger.log(u"Cannot parse quality from item description", logger.DEBUG)
            return Quality.UNKNOWN
        
        if "TV" in quality:
            return Quality.SDTV
        elif "DVD" in quality:
            return Quality.SDDVD
        elif "HD" in quality:
            return Quality.HDTV
        else:
            logger.log(u"Unknown quality type in item description: " + quality, logger.DEBUG)
            return Quality.UNKNOWN
        
class DemonoidCache(tvcache.TVCache):
    
    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        
        self.minTime = 15
        
    def _getRSSData(self):
        url = "http://static.demonoid.me/rss/3.xml"
        
        logger.log(u"Demonoid cache update URL: " + url, logger.DEBUG)
        
        data = self.provider.getURL(url)
        
        return data
    
    
    def _parseItem(self, item):
        title = item.findtext('title')
        logger.log('filename :' + title, logger.DEBUG)
        details_url = item.findtext('link')

        if not title or not details_url:
            logger.log(u"The XML returned from the Demonoid RSS feed is incomplete, this result is unusable", logger.ERROR)
            return
        
        url = self._parseDetailsPage(details_url)
        
        if not url:
            logger.log(u"Unable to parse download link from Demonoid details page: " + details_url, logger.ERROR)
            return
        
        logger.log(u"Adding item from RSS to cache: "+title, logger.DEBUG)
        
        quality = self.provider.getQuality(item)
        self._addCacheEntry(title, url, quality=quality)
    
    def _parseDetailsPage(self, url):
        """Needed to extract download link because Demonoid's RSS feed 
           links to a Torrent Details page, not the actual torrent"""
           
        link_regex = r'/files/download/\d+/\d+'
        data = self.provider.getURL(url)
        
        if not data:
            return None
        
        match = re.search(link_regex, data)
        if match:
            return self.provider.url + match.group()
        return None
        
provider = DemonoidProvider()