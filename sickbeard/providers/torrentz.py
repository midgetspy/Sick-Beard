# Author: Marcos Almeida Jr. <junalmeida@gmail.com>
# URL: https://github.com/junalmeida/Sick-Beard
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

class TORRENTZProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "Torrentz")
        
        self.supportsBacklog = True

        self.cache = TORRENTZCache(self)

        self.url = 'http://torrentz.eu/'

    def isEnabled(self):
        return sickbeard.TORRENTZ
        
    def imageName(self):
        return 'torrentz.png'
                      
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
        #text = re.sub(r'\([^)]*\)', '', text)
        return sanitizeSceneName(text, ezrss=True).replace('.',' ').replace('-',' ').encode('utf-8')
        
    def _doSearch(self, search_params, show=None):
        try:
            params = { }
        
            if search_params:
                params.update(search_params)

            if not 'episode' in params:
                searchURL = self.url + "feed?q=%(show_name)s S%(season)02d" % params
            else:
                searchURL = self.url + "feed?q=%(show_name)s S%(season)02dE%(episode)02d" % params
                
            searchURL = searchURL.lower().replace(" ", "+")
            
            logger.log(u"Search string: " + searchURL)

            items = []
            for index in [0,1,2,3,4]:
                try:
                    data = self.getURL(searchURL + "&p=%(page)d" % {'page': index })

                    if data and data.startswith("<?xml"):
                        responseSoup = etree.ElementTree(etree.XML(data))
                        newItems = responseSoup.getiterator('item')
                        items.extend(newItems)
                        if len(newItems) < 50:
                            break
                except Exception, e:
                    logger.log((u"Error trying to load " + self.name + " RSS feed for %(show_name)s page %(page)d: " % {'page': index, 'show_name': params['show_name']})+str(e).decode('utf-8'), logger.ERROR)
           
            results = []
            for curItem in items:
                try:
                    (title, url) = self._get_title_and_url(curItem)
                    if not title or not url:
                        logger.log(u"The XML returned from the " + self.name + " RSS feed is incomplete.", logger.ERROR)
                        continue
                    results.append(curItem)
                except Exception, e:
                    logger.log(u"Error trying to load " + self.name + " RSS feed item: "+str(e).decode('utf-8'), logger.ERROR)
               
            logger.log(self.name + " total torrents: %(count)d" % { 'count' : len(results) })
            return results
        except Exception, e:
            logger.log(u"Error trying to load " + self.name + ": "+str(e).decode('utf-8'), logger.ERROR)
            traceback.print_exc()
            raise 
        
    def _get_title_and_url(self, item):
        title = item.findtext('title')
        url = item.findtext('guid')

        return (title, url)

    def _extract_name_from_filename(self, filename):
        name_regex = '(.*?)\.?(\[.*]|\d+\.TPB)\.torrent$'
        logger.log(u"Comparing "+name_regex+" against "+filename, logger.DEBUG)
        match = re.match(name_regex, filename, re.I)
        if match:
            return match.group(1)
        return None
    
    def downloadResult(self, result):
        try:
            result.url = "http://torrage.com/torrent/" + result.url.replace('http://torrentz.eu/','').upper() + '.' + self.providerType
            logger.log(u"Downloading a result from " + self.name + " at " + result.url)
            
            torrentFileName = ek.ek(os.path.join, sickbeard.TORRENT_DIR, helpers.sanitizeFileName(result.name) + '.' + self.providerType)
            #add self referer to get application/x-bittorrent from torrage.com
            data = self.getURL(result.url, [("Referer", result.url)])
            if data == None:
                return False
            fileOut = open(torrentFileName, 'wb')
            logger.log(u"Saving to " + torrentFileName, logger.DEBUG)
            fileOut.write(data)
            fileOut.close()
            helpers.chmodAsParent(torrentFileName)
            return self._verify_download(torrentFileName)
        except Exception, e:
            logger.log("Unable to save the file: "+str(e).decode('utf-8'), logger.ERROR)
            return False
        
class TORRENTZCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll every 15 minutes max
        self.minTime = 15

    def _getRSSData(self):
        url = self.provider.url + 'feedA?q='

        logger.log(self.provider.name + u" cache update URL: " + url)

        data = self.provider.getURL(url)
        return data
    
    def _parseItem(self, item):
        try:      
            title = helpers.get_xml_text(item.getElementsByTagName('title')[0])
            url = helpers.get_xml_text(item.getElementsByTagName('guid')[0])

            if not title or not url:
                logger.log(u"The XML returned from the " + self.provider.name + " RSS feed is incomplete, this result is unusable", logger.ERROR)
                return

            logger.log(u"Adding item from " + self.provider.name + " RSS to cache: "+title, logger.DEBUG)
            
            self._addCacheEntry(title, url)
        
        except Exception, e:
            logger.log(u"Error trying to parse " + self.provider.name + " cache: "+str(e).decode('utf-8'), logger.ERROR)
            raise 

provider = TORRENTZProvider()
