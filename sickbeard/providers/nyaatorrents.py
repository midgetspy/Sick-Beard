# Author: Mr_Orange
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

from xml.dom.minidom import parseString

import re
import sys

import sickbeard
import generic

from sickbeard import show_name_helpers, helpers

from sickbeard import logger
from sickbeard.common import Quality
from sickbeard.exceptions import ex
from sickbeard.name_parser.parser import NameParser, InvalidNameException
from sickbeard import tvcache

REMOTE_DBG = False

class NyaaProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "NyaaTorrents")
        
        self.supportsBacklog = True
        
        self.supportsAbsoluteNumbering = True

        self.cache = NyaaCache(self)

        self.url = 'http://www.nyaa.eu/'

    def isEnabled(self):
        return sickbeard.NYAA
        
    def imageName(self):
        return 'nyaatorrents.png'
      
    def getQuality(self, item, anime=False):
        self.debug()
        title = helpers.get_xml_text(item.getElementsByTagName('title')[0]).replace("/"," ")    
        quality = Quality.nameQuality(title, anime)
        return quality        
        
    def findSeasonResults(self, show, season):
        results = {}
        
        results = generic.TorrentProvider.findSeasonResults(self, show, season)
        
        return results
    def _get_season_search_strings(self, show, season=None):
        names = []
        names.extend(show_name_helpers.makeSceneShowSearchStrings(show))
        return names

    def _get_episode_search_strings(self, ep_obj):
        return self._get_season_search_strings(ep_obj.show, ep_obj.season)

    def _doSearch(self, search_string, show=None):
    
        params = {"term" : search_string.encode('utf-8'),
                  "sort" : '2', #Sort Descending By Seeders 
                 }
      
        searchURL = self.url+'?page=rss&'+urllib.urlencode(params)

        logger.log(u"Search string: " + searchURL, logger.DEBUG)

        data = self.getURL(searchURL)

        if not data:
            return []
        
        try:
            parsedXML = parseString(data)
            items = parsedXML.getElementsByTagName('item')
        except Exception, e:
            logger.log(u"Error trying to load NyaaTorrents RSS feed: "+ex(e), logger.ERROR)
            logger.log(u"RSS data: "+data, logger.DEBUG)
            return []
        
        results = []

        for curItem in items:
            
            (title, url) = self._get_title_and_url(curItem)
            
            if not title or not url:
                logger.log(u"The XML returned from the NyaaTorrents RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
                continue
    
            results.append(curItem)
        
        return results

    def _get_title_and_url(self, item):

        return generic.TorrentProvider._get_title_and_url(self, item)

    def findEpisode (self, episode, manualSearch=False):

        self._checkAuth()

        logger.log(u"Searching "+self.name+" for " + episode.prettyName())

        self.cache.updateCache()
        results = self.cache.searchCache(episode, manualSearch)
        logger.log(u"Cache results: "+str(results), logger.DEBUG)

        # if we got some results then use them no matter what.
        # OR
        # return anyway unless we're doing a manual search
        if results or not manualSearch:
            return results

        itemList = []

        for cur_search_string in self._get_episode_search_strings(episode):
            itemList += self._doSearch(cur_search_string, show=episode.show)

        for item in itemList:

            (title, url) = self._get_title_and_url(item)

            # parse the file name
            try:
                myParser = NameParser(show=episode.show)
                parse_result = myParser.parse(title)
            except InvalidNameException:
                logger.log(u"Unable to parse the filename "+title+" into a valid episode", logger.WARNING)
                continue

            if episode.show.air_by_date:
                if parse_result.air_date != episode.airdate:
                    logger.log("Episode "+title+" didn't air on "+str(episode.airdate)+", skipping it", logger.DEBUG)
                    continue
            elif episode.show.anime and episode.show.absolute_numbering:
                if episode.absolute_number not in parse_result.ab_episode_numbers:
                    logger.log("Episode "+title+" isn't "+str(episode.absolute_number)+", skipping it", logger.DEBUG)
                    continue
            elif parse_result.season_number != episode.season or episode.episode not in parse_result.episode_numbers:
                logger.log("Episode "+title+" isn't "+str(episode.season)+"x"+str(episode.episode)+", skipping it", logger.DEBUG)
                continue

            quality = self.getQuality(item, episode.show.anime)

            if not episode.show.wantEpisode(episode.season, episode.episode, quality, manualSearch):
                logger.log(u"Ignoring result "+title+" because we don't want an episode that is "+Quality.qualityStrings[quality], logger.DEBUG)
                continue

            logger.log(u"Found result " + title + " at " + url, logger.DEBUG)

            result = self.getResult([episode])
            result.url = url
            result.name = title
            result.quality = quality

            results.append(result)

        return results

    def _extract_name_from_filename(self, filename):
        name_regex = '(.*?)\.?(\[.*]|\d+\.TPB)\.torrent$'
        logger.log(u"Comparing "+name_regex+" against "+filename, logger.DEBUG)
        match = re.match(name_regex, filename, re.I)
        if match:
            return match.group(1)
        return None

   
class NyaaCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll NyaaTorrents every 15 minutes max
        self.minTime = 15


    def _getRSSData(self):

        params = {
                    "page" : 'rss', # Use RSS page
                    "order" : '1'   #Sort Descending By Date
                  }
      
        url = self.provider.url + '?' + urllib.urlencode(params)        

        logger.log(u"NyaaTorrents cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data

    def _parseItem(self, item):

        (title, url) = self.provider._get_title_and_url(item)

        if not title or not url:
            logger.log(u"The XML returned from the NyaaTorrents RSS feed is incomplete, this result is unusable", logger.ERROR)
            return

        logger.log(u"Adding item from RSS to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = NyaaProvider()