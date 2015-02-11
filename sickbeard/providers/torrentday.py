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
import json
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

class TorrentDayProvider(generic.TorrentProvider):
    
    ###################################################################################################
    def __init__(self):
        generic.TorrentProvider.__init__(self, "TorrentDay")
        self.cache = TorrentDayCache(self)     
        self.name = "TorrentDay"
        self.rsshash = None
        self.rssuid = None
        self.session = None
        self.supportsBacklog = True
        self.url = 'https://www.torrentday.com/'
        self.url_alt = 'https://torrentday.eu'
        logger.log('[' + self.name + '] initializing...')
    
    ###################################################################################################
    
    def isEnabled(self):
        return sickbeard.TORRENTDAY
    
    ###################################################################################################
    
    def imageName(self):
        return 'torrentday.png'
    
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
        search_params = search_params.replace('.',' ')
        logger.log("[" + self.name + "] Performing Search For: {0}".format(search_params))
        searchUrl = self.url + "V3/API/API.php"
        PostData = {'/browse.php?' : None,'cata':'yes', 'jxt':8, 'jxw':'b', 'search':search_params, 'c7':1, 'c14':1,'c26':1}
        
        try:
            data = self.getURL(searchUrl,data=PostData)
            jdata = json.loads(data)
            if jdata.get('Fs', [])[0].get('Fn', {}) == "Oarrive":
                logger.log("[" + self.name + "] _doSearch() search data sent 0 results.")
                return []
            torrents = jdata.get('Fs', [])[0].get('Cn', {}).get('torrents', [])
        except ValueError, e:
            logger.log("[" + self.name + "] _doSearch() invalid json returned.")
            return []

        return self.parseResults(torrents)

    ###################################################################################################
    
    def parseResults(self, torrents): 
        results = []
        
        for torrent in torrents:
            item = (torrent['name'].replace('.',' '), self.url + "download.php/" + str(torrent['id']) + "/" + torrent['fname'] + "?torrent_pass=" + self.rsshash)
            results.append(item)                        
            logger.log("[" + self.name + "] parseResults() Title: " + torrent['name'], logger.DEBUG)
        
        if len(results):
            logger.log("[" + self.name + "] parseResults() Some results found.")
        else:
            logger.log("[" + self.name + "] parseResults() No results found.")
            
        return results
    
    ###################################################################################################
    
    def getURL(self, url, headers=None,data=None):
        response = None
        
        if not self.session:
            if not self._doLogin():
                return response
            
        if not headers:
            headers = []
            
        try:
            if "/torrents/rss" in url:
                response = self.session.get(url, verify=False)
            else:
                response = self.session.post(url, verify=False,data=data)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
            logger.log("[" + self.name + "] getURL() Error loading " + self.name + " URL: " + ex(e), logger.ERROR)
            return None
        
        if response.status_code not in [200,302,303]:
            logger.log("[" + self.name + "] getURL() requested URL - " + url +" returned status code is " + str(response.status_code), logger.ERROR)
            return None
        
        return response.content
    
    ###################################################################################################
    
    def _getPassKey(self):
        logger.log("[" + self.name + "] _getPassKey() Attempting to acquire RSS info")
        rssData = re.findall(r'u=(.*);tp=([0-9A-Fa-f]{32})',self.getURL(self.url + "rss.php",data={'cat[]':'26', 'feed':'direct', 'login':'passkey'}))
        if rssData:
            self.rssuid = rssData[0][0]
            self.rsshash = rssData[0][1]
            return True
        return False
    
    ###################################################################################################
    
    def _doLogin(self):
        login_params  = {
            'username': sickbeard.TORRENTDAY_USERNAME,
            'password': sickbeard.TORRENTDAY_PASSWORD,
            'submit.x' : '0',
            'submit.y' : '0',
            'login': 'submit'
        }

        self.session = requests.Session()
        logger.log("[" + self.name + "] Attempting to Login")
        
        if sickbeard.TORRENTDAY_ALT_URL:
            self.url = self.url_alt

        try:
            response = self.session.post(self.url + "torrents/", data=login_params, timeout=30, verify=False)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
            raise Exception("[" + self.name + "] _doLogin() Error: " + ex(e))
        
        if re.search("Password not correct|<title>Torrentday :: Login|User not found</title>",response.text) \
        or response.status_code in [401,403]:
            raise Exception("[" + self.name + "] Login Failed, Invalid username or password for " + self.name + ". Check your settings.")
        
        if not self._getPassKey() or not self.rssuid or not self.rsshash:
            raise Exception("[" + self.name + "] _doLogin() Could not extract rssHash info... aborting")
        
        return True
    
    ###################################################################################################
    
class TorrentDayCache(tvcache.TVCache):
    
    ###################################################################################################
    
    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        self.minTime = 15

    ###################################################################################################
        
    def _getRSSData(self):
        if not provider.session:
            provider._doLogin()
        
        self.rss_url = "{0}torrents/rss?download;l24;l14;l26;l7;l2;u={1};tp={2}".format(provider.url, provider.rssuid, provider.rsshash)
        logger.log("[" + provider.name + "] RSS URL - {0}".format(self.rss_url))
        return provider.getURL(self.rss_url)
        
    ###################################################################################################    

provider = TorrentDayProvider()