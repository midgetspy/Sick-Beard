# Author: Mr_Orange <l.dimarino@gmail.com>
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
import datetime
import urllib

import sickbeard
import generic

from sickbeard.common import Quality
from sickbeard import logger
from sickbeard import tvcache
from sickbeard import sceneHelpers
from sickbeard import db
from sickbeard import sceneHelpers
from sickbeard.common import Overview


class ThePirateBayProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "ThePirateBay")
        
        self.supportsBacklog = True

        self.cache = ThePirateBayCache(self)

        #A proxy server for thepiratebay.org usefull for people living in countries blocking TPB
        #Countries blocking TPB access are Italy, Denmark, Germany, Ireland, Netherlands. 
        #http://en.wikipedia.org/wiki/The_Pirate_Bay#Blocking
        self.url = 'http://labaia.ws/'
        
        self.searchurl = 'http://labaia.ws/search/%s/0/7/200'  # order by seed       

        self.regex = '\t<td>.+?"/torrent/\d+/(?P<title>.*?)".+?<a href="(?P<url>.+?)".*?</td>' 
        
    def isEnabled(self):
        return sickbeard.THEPIRATEBAY
        
    def imageName(self):
        return 'thepiratebay.gif'
    
    def getQuality(self, item):
        
        quality = Quality.nameQuality(item[0])
        return quality    

    def _get_airbydate_season_range(self, season):
        
            if season == None:
                return ()
        
            year, month = map(int, season.split('-'))
            min_date = datetime.date(year, month, 1)
            if month == 12:
                max_date = datetime.date(year, month, 31)
            else:    
                max_date = datetime.date(year, month+1, 1) -  datetime.timedelta(days=1)

            return (min_date, max_date)    
      
    def _get_season_search_strings(self, show, season=None):
    
        search_string = []
    
        if not show:
            return []

        #Building the search string with the episodes we need         
        myDB = db.DBConnection()
        
        if show.air_by_date:
            (min_date, max_date) = self._get_airbydate_season_range(season)
            sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND airdate >= ? AND airdate <= ?", [show.tvdbid,  min_date.toordinal(), max_date.toordinal()])
        else:
            sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND season = ?", [show.tvdbid, season])
            
        for sqlEp in sqlResults:
            if show.getOverview(int(sqlEp["status"])) in (Overview.WANTED, Overview.QUAL):
                
                if show.air_by_date:
                    for show_name in set(sceneHelpers.allPossibleShowNames(show)):
                        ep_string = sceneHelpers.sanitizeSceneName(show_name) +' '+ str(datetime.date.fromordinal(sqlEp["airdate"])).replace('-', '.')
                        search_string.append(ep_string)
                else:
                    for show_name in set(sceneHelpers.allPossibleShowNames(show)):
                        ep_string = sceneHelpers.sanitizeSceneName(show_name) +' '+ sickbeard.config.naming_ep_type[2] % {'seasonnumber': season, 'episodenumber': int(sqlEp["episode"])}
                        search_string.append(ep_string)                       
        
        return search_string

    def _get_episode_search_strings(self, ep_obj):
       
        search_string = []
       
        if not ep_obj:
            return []
                
        if ep_obj.show.air_by_date:
            for show_name in set(sceneHelpers.allPossibleShowNames(ep_obj.show)):
                ep_string = sceneHelpers.sanitizeSceneName(show_name) +' '+ str(ep_obj.airdate).replace('-', '.')
                search_string.append(ep_string)
        else:
            for show_name in set(sceneHelpers.allPossibleShowNames(ep_obj.show)):
                ep_string = sceneHelpers.sanitizeSceneName(show_name) +' '+ sickbeard.config.naming_ep_type[2] % {'seasonnumber': ep_obj.season, 'episodenumber': ep_obj.episode}
                search_string.append(ep_string)
    
        return search_string

    def _doSearch(self, search_params, show=None):
    
        results = []
    
        searchURL = self.searchurl %(urllib.quote(search_params))    
        logger.log(u"Search string: " + searchURL, logger.DEBUG)
                    
        data = self.getURL(searchURL)
        if not data:
            return []

        #Extracting torrent information from searchURL                   
        match = re.compile(self.regex, re.DOTALL ).finditer(data)
        for torrent in match:
           
            #Accept Torrent only from Good People
            if sickbeard.THEPIRATEBAY_TRUSTED and re.search('(VIP|Trusted|Helpers)',torrent.group(0))== None:
                logger.log(u"ThePirateBay Provider found result "+torrent.group('title')+" but that doesn't seem like a trusted result so I'm ignoring it",logger.DEBUG)
                continue
            
            #Do not know why but Sick Beard skip release with a '_' in name
            item = (torrent.group('title').replace('_','.'),torrent.group('url'))
            results.append(item)
        
        return results

    def _get_title_and_url(self, item):
        (title, url) = item
        if url:
            url = url.replace('&amp;','&')

        return (title, url)

class ThePirateBayCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll ThePirateBay every 10 minutes max
        self.minTime = 10
        
        self.regex = '\t<td>.+?"/torrent/\d+/(?P<title>.*?)".+?<a href="(?P<url>.+?)".*?</td>' 
        
    def updateCache(self):
        
        if not self.shouldUpdate():
            return

        data = self._getData()

        # as long as the http request worked we count this as an update
        if data:
            self.setLastUpdate()
        else:
            return []

        # now that we've loaded the current RSS feed lets delete the old cache
        logger.log(u"Clearing "+self.provider.name+" cache and updating with new information")
        self._clearCache()

        match = re.compile(self.regex, re.DOTALL).finditer(data)
        if not match:
            logger.log(u"The Data returned from the ThePirateBay is incomplete, this result is unusable", logger.ERROR)
            return []
                
        for torrent in match:
           
            #accept torrent only from Trusted people
            if sickbeard.THEPIRATEBAY_TRUSTED and re.search('(VIP|Trusted|Helpers)',torrent.group(0))== None:
                logger.log(u"ThePirateBay Provider found result "+torrent.group('title')+" but that doesn't seem like a trusted result so I'm ignoring it",logger.DEBUG)
                continue
            
            item = (torrent.group('title').replace('_','.'),torrent.group('url'))
            self._parseItem(item)

    def _getData(self):
       
        url = 'http://labaia.ws/tv/latest/' #url for the last 50 tv-show

        logger.log(u"ThePirateBay cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data

    def _parseItem(self, item):

        (title, url) = item

        if not title or not url:
            return

        logger.log(u"Adding item to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = ThePirateBayProvider()
