###################################################################################################
# Author: Jodi Jones <venom@gen-x.co.nz>
# URL: https://github.com/VeNoMouS/Sick-Beard
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
###################################################################################################

import os
import re
import sys
import urllib
import generic
import datetime
import sickbeard
import exceptions

from lib import requests
from xml.sax.saxutils import escape

from sickbeard import db
from sickbeard import logger
from sickbeard import tvcache
from sickbeard.exceptions import ex
from sickbeard.common import Quality
from sickbeard.common import Overview
from sickbeard import show_name_helpers

class BitHDTVProvider(generic.TorrentProvider):
    
    ###################################################################################################
    
    def __init__(self):
        generic.TorrentProvider.__init__(self, "BitHDTV")
        self.cache = BitHDTVCache(self)
        self.name = "BitHDTV"
        self.session = None
        self.supportsBacklog = True
        self.url = 'https://www.bit-hdtv.com/'
        logger.log("[" + self.name + "] initializing...")
        
    ###################################################################################################
    
    def isEnabled(self):
        return sickbeard.BITHDTV
    
    ###################################################################################################
    
    def imageName(self):
        return 'bithdtv.png'
    
    ###################################################################################################

    def getQuality(self, item):
        quality = Quality.nameQuality(item[0])
        return quality 
    
    ###################################################################################################
        
    def _get_title_and_url(self, item):
        return item
    
    ################################################################################################### 

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

    ###################################################################################################

    def _get_season_search_strings(self, show, season=None):
        search_string = []
    
        if not show:
            return []
      
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

    ###################################################################################################

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
 
    ###################################################################################################

    def _doSearch(self, search_params, show=None):
        self.search_results = []
        logger.log("[" + self.name + "] Performing Search: {0}".format(search_params))
        search_params = search_params.replace(" ","+")
        
        logger.log("[" + self.name + "] Searching TV Section")
        self.parseResults(self.url + "torrents.php?search=" + urllib.quote(search_params) + "&cat=10")
        
        logger.log("[" + self.name + "] Searching TV Pack Section")
        self.parseResults(self.url + "torrents.php?search=" + urllib.quote(search_params) + "&cat=12")
        
        if len(self.search_results):
            logger.log("[" + self.name + "] parseResults() Some results found.")
        else:
            logger.log("[" + self.name + "] parseResults() No results found.")
        return self.search_results

    ###################################################################################################
    
    def parseResults(self, searchUrl):
        data = self.getURL(searchUrl)
        if data:
            logger.log("[" + self.name + "] parseResults() URL: " + searchUrl, logger.DEBUG)
            for torrent in re.compile("<td class=detail align=left><a title=\"(?P<title>.*?)\" href.*?<font class=small></font><a href=\"/(?P<url>.*?)\.torrent\"></a>",re.MULTILINE|re.DOTALL).finditer(data):
                item = (torrent.group('title').replace('.',' ').decode('utf-8', 'ignore'), self.url + torrent.group('url') + ".torrent")
                self.search_results.append(item)
                logger.log("[" + self.name + "] parseResults() Title: " + torrent.group('title').decode('utf-8', 'ignore'), logger.DEBUG)
        else:
            logger.log("[" + self.name + "] parseResults() Error no data returned!!")
        return self.search_results
    
    ###################################################################################################
    
    def getURL(self, url, headers=None):
        response = None
        
        if not self.session:
             if not self._doLogin():
                return response
            
        if not headers:
            headers = []
            
        try:
            response = self.session.get(url, verify=False)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
            logger.log("[" + self.name + "] getURL() Error loading " + self.name + " URL: " + ex(e), logger.ERROR)
            return None
        
        if response.status_code not in [200,302,303]:
            logger.log("[" + self.name + "] getURL() requested URL - " + url +" returned status code is " + str(response.status_code), logger.ERROR)
            return None

        return response.content
    
    ###################################################################################################
    
    def _doLogin(self):
        login_params  = {
            'username': sickbeard.BITHDTV_USERNAME,
            'password': sickbeard.BITHDTV_PASSWORD,
            'login': 'submit'
        }
            
        self.session = requests.Session()
        logger.log("[" + self.name + "] Attempting to Login")
        
        try:
            response = self.session.post(self.url + "takelogin.php", data=login_params, timeout=30, verify=False)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
            raise Exception("[" + self.name + "] _doLogin() Error: " + ex(e))
            return False
        
        if re.search("Password not correct|<title>Login</title>",response.text) \
        or response.status_code in [401,403]:
            raise Exception("[" + self.name + "] Login Failed, Invalid username or password for " + self.name + ". Check your settings.")
            return False
        return True
    
    ###################################################################################################
    
class BitHDTVCache(tvcache.TVCache):
    
    ###################################################################################################
    
    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        self.minTime = 15

    ###################################################################################################
        
    def _getRSSData(self):
        provider.search_results = []
        provider.parseResults(provider.url + "torrents.php?cat=10")
        provider.parseResults(provider.url + "torrents.php?cat=12")
        
        xml =   "<rss xmlns:atom=\"http://www.w3.org/2005/Atom\" version=\"2.0\">" + \
                "<channel>" + \
                "<title>" + provider.name + "</title>" + \
                "<link>" + provider.url + "</link>" + \
                "<description>torrent search</description>" + \
                "<language>en-us</language>" + \
                "<atom:link href=\"" + provider.url + "\" rel=\"self\" type=\"application/rss+xml\"/>"
            
        for title, url in provider.search_results:
            xml += "<item>" + "<title>" + escape(title) + "</title>" +  "<link>" + urllib.quote(url,'/,:?') + "</link>" + "</item>"
        xml += "</channel> </rss>"
        return xml
        
    ###################################################################################################    
        
provider = BitHDTVProvider()   
