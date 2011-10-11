# Author: bwq/bbyte
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
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import re
import datetime
import urllib
import urllib2
import cookielib

import sickbeard
import generic

from sickbeard.common import Quality
from sickbeard import logger
from sickbeard import tvcache
from sickbeard import show_name_helpers
from sickbeard import db
from sickbeard.common import Overview

class TeeVeeProvider(generic.NZBProvider):

    def __init__(self):

        generic.NZBProvider.__init__(self, "TeeVee")

        self.supportsBacklog = True

        self.cache = TeeVeeCache(self)

        self.url = 'http://abTeeVee.allfilled.com/'

        self.searchurl = 'http://abTeeVee.allfilled.com/search.php?q=%s&Search=Search' 
   
        self.downloadurl = 'http://85.214.105.230/get_nzb.php?id=%s&section=teevee'
         
        self.regex = '<td class="cell_reqid">(?P<reqid>.*?)</td>.+?<td class="cell_request">(?P<title>.*?)</td>'

    def isEnabled(self):
        return sickbeard.TEEVEE

    def imageName(self):
        return 'teevee.gif'
    
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
                    for show_name in set(show_name_helpers.allPossibleShowNames(show)):
                        ep_string = show_name_helpers.sanitizeSceneName(show_name) +' '+ str(datetime.date.fromordinal(sqlEp["airdate"])).replace('-', '.')
                        search_string.append(ep_string)
                else:
                    for show_name in set(show_name_helpers.allPossibleShowNames(show)):
                        ep_string = show_name_helpers.sanitizeSceneName(show_name) +' '+ sickbeard.config.naming_ep_type[2] % {'seasonnumber': season, 'episodenumber': int(sqlEp["episode"])}
                        search_string.append(ep_string)                       
        
        return search_string

    def _get_episode_search_strings(self, ep_obj):
       
        search_string = []
       
        if not ep_obj:
            return []
                
        if ep_obj.show.air_by_date:

            for show_name in set(show_name_helpers.allPossibleShowNames(ep_obj.show)):
                ep_string = show_name_helpers.sanitizeSceneName(show_name) +' '+ str(ep_obj.airdate).replace('-', '.')
                search_string.append(ep_string)
        else:
            for show_name in set(show_name_helpers.allPossibleShowNames(ep_obj.show)):
                ep_string = show_name_helpers.sanitizeSceneName(show_name) +' '+ sickbeard.config.naming_ep_type[2] % {'seasonnumber': ep_obj.season, 'episodenumber': ep_obj.episode}
                search_string.append(ep_string)
    
        return search_string

    def _doSearch(self, search_params, show=None):
    
        results = []
        searchURL = self.searchurl %(urllib.quote(search_params))    
        logger.log(u"Search string: " + searchURL, logger.DEBUG)

        try:
			cookiejar = cookielib.CookieJar()
			opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
			urllib2.install_opener(opener)
			f = opener.open(searchURL)
			data = f.read()
			f.close()
			if not data:
				return []


        except (IOError):
		logger.log(u"TeeVee website is down", logger.DEBUG)
                  
        #Extracting torrent information from searchURL 
        match = re.compile(self.regex, re.DOTALL ).finditer(data)
        for nzb in match:
            downloadURL = self.downloadurl % (urllib.quote(nzb.group('reqid')))
            item = (nzb.group('title').replace('_','.'), downloadURL)
            results.append(item)

        return results

    def _get_title_and_url(self, item):
        (title, url) = item
        if url:
            url = url.replace('&amp;','&')

        return (title, url)

class TeeVeeCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll TeeVee every 3 minutes max
        self.minTime = 3
        
        self.regex = '<td class="cell_reqid">(?P<reqid>.*?)</td>.+?<td class="cell_request">(?P<title>.*?)</td>'
        
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
            logger.log(u"The Data returned from TeeVee is incomplete, this result is unusable", logger.ERROR)
            return []
                
        for nzb in match:
                       
            item = (nzb.group('title').replace('_','.'),nzb.group('reqid'))
            self._parseItem(item)

    def _getData(self):
       
        url = 'http://abTeeVee.allfilled.com/search.php?q=*&Search=Search'

        logger.log(u"TeeVee cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data

    def _parseItem(self, item):

        (title, url) = item

        if not title or not url:
            return

        logger.log(u"Adding item to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = TeeVeeProvider()
