# Author: Marcos Almeida Jr <junalmeida@gmail.com>
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
import urllib, urllib2, cookielib
import sys
import datetime
import os
import exceptions
import sickbeard
import generic

from sickbeard.common import Quality
from sickbeard import logger
from sickbeard import tvcache
from sickbeard import helpers
from sickbeard import show_name_helpers
from sickbeard import db
from sickbeard.common import Overview
from sickbeard.exceptions import ex
from sickbeard import encodingKludge as ek

class PublicHDProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "PublicHD")
        
        self.supportsBacklog = True
        self.cache = PublicHDCache(self)
        self.token = None
        self.url = 'http://publichd.se/'
        
    def isEnabled(self):
        return sickbeard.PUBLICHD
        
    def imageName(self):
        return 'publichd.png'
    
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

        #Building the search string with the season we need
        #1) ShowName SXX 
        #2) ShowName Season X
        for show_name in set(show_name_helpers.allPossibleShowNames(show)):
            ep_string = show_name + ' ' + 'S%02d' % int(season)   
            search_string.append(ep_string)
          
            ep_string = show_name + ' ' + 'Season' + ' ' + str(season)   
            search_string.append(ep_string)

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
        baseUrl = self.url + "index.php?page=torrents&search=%s&active=0&category=2;5;8;9;20;7;24;14;23&order=5&by=2&pages="

        searchUrl = baseUrl % search_params
        #logger.log(u"Search string: " + searchUrl) #, logger.DEBUG)       
        
        data = []
        for index in [1,2,3,4,5]:
            newItems = self.parseResults(searchUrl + str(index))
            data = data + newItems
            #logger.log(str(len(newItems)) + " - " + str(len(data)))
            if len(newItems) < 30:
                break;
        
        logger.log(provider.name + u" found " + str(len(data)) + " results at " + searchUrl, logger.DEBUG)

        return data
    
    def _get_title_and_url(self, item):
        return item
    
    def parseResults(self, searchUrl):
        data = self.getURL(searchUrl)
        results = []
        if data:
            allItems = re.findall("<a\\s(?:[^\\s>]*?\\s)*?href=\"(?:mailto:)?(.*?)\".*?>(.+?)</a>", data)
            for url, title in allItems:
                if url and url.startswith("index.php?page=torrent-details&amp;id="):
                    url = self.url + url
                    url = url.replace("index.php?page=torrent-details&amp;id=", "download.php?id=") + "&f=" + title.replace(" ", ".") + ".torrent"
                    #logger.log(title + " - " + url)
                    results.append((title, url))
        else:
            logger.log("Nothing found for " + searchUrl, logger.DEBUG)
        return results


class PublicHDCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        self.url = "index.php?page=torrents&active=0&category=2;5;8;9;20;7;24;14;23&order=3&by=2&pages="
        # only poll TorrentLeech every 15 minutes max
        self.minTime = 15

    def _getRSSData(self):
        url = provider.url + self.url
        
        rss = "<rss xmlns:atom=\"http://www.w3.org/2005/Atom\" version=\"2.0\">" + \
"<channel>" + \
"<title>" + provider.name + "</title>" + \
"<link>" + provider.url + "</link>" + \
"<description>torrent search</description>" + \
"<language>en-us</language>" + \
"<atom:link href=\"" + provider.url + "\" rel=\"self\" type=\"application/rss+xml\"/>"

        logger.log(provider.name + u" cache update URL: " + url, logger.DEBUG)
        for index in [1,2,3,4,5]:
            data = provider.parseResults(url + str(index))
                
            for title, url in data:
                rss = rss + \
                    "<item>" + \
                    "   <title>" + title + "</title>" + \
                    "   <link>"+ url.replace("&", "&amp;") + "</link>" + \
                    "</item>"
            if len(data) <30:
                break;
                    
        rss = rss + "</channel></rss>"

        return rss
        
provider = PublicHDProvider()