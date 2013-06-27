###################################################################################################
# Author: Jodi Jones <venom@gen-x.co.nz>
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
###################################################################################################

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


class IPTorrentsProvider(generic.TorrentProvider):
    ###################################################################################################
    def __init__(self):
        generic.TorrentProvider.__init__(self, "IPTorrents")
        self.supportsBacklog = True
        self.cache = IPTorrentsCache(self)     
        self.url = 'https://www.iptorrents.com/'
        self.token = None
        logger.log('[IPTorrents] Loading IPTorrents')
    
    ###################################################################################################
    
    def isEnabled(self):
        return sickbeard.IPTORRENTS
    
    ###################################################################################################
    
    def imageName(self):
        return 'iptorrents.png'
    
    ###################################################################################################

    def getQuality(self, item):        
        quality = Quality.nameQuality(item[0])
        return quality 
    
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
        logger.log("[IPTorrents] Performing Search: {0}".format(search_params))
        searchUrl = self.url + "torrents/?l78=&l79=&l5=&q=" + urllib.quote(search_params)
        return self.parseResults(searchUrl)
    
    ################################################################################################### 

    def _get_title_and_url(self, item):
        return item

    ###################################################################################################
    
    def parseResults(self, searchUrl):
        data = self.getURL(searchUrl)
        results = []
        if data:
            logger.log("[IPTorrents] parseResults() URL: " + searchUrl, logger.DEBUG)
            for torrent in re.compile('<a class="t_title" href="/details\.php\?id=\d+">(?P<title>.*?)</a>.*?<a href="/download\.php/(?P<url>.*?)"><',re.MULTILINE|re.DOTALL).finditer(data):
                item = (torrent.group('title').replace('.',' '), self.url + "download.php/" + torrent.group('url'))
                results.append(item)                        
                logger.log("[IPTorrents] parseResults() Title: " + torrent.group('title'), logger.DEBUG)
            if len(results):
                logger.log("[IPTorrents] parseResults() Some results found.")
            else:
                logger.log("[IPTorrents] parseResults() No results found.")
        else:
            logger.log("[IPTorrents] parseResults() Error no data returned!!")
        return results
    
    ###################################################################################################
    
    def getURL(self, url, headers=None):
        response = None
        if self.doLogin():        
            if not headers:
                headers = []
            headers.append(('Cookie', self.token))          
            try:
                response = helpers.getURL(url, headers)
                if response.count("<title>IPT</title>") > 0:
                    logger.log("[IPTorrents] getURL() Session expired loading " + self.name + " URL: " + url +" Let's login again.")
                    self.token = None
                    self.getURL(url, headers)
            except (urllib2.HTTPError, IOError, Exception), e:
                self.token = None
                logger.log("[IPTorrents] getURL() Error loading " + self.name + " URL: " + str(sys.exc_info()) + " - " + ex(e), logger.ERROR)
                return None
        return response
    
    ###################################################################################################
    
    def doLogin(self):
        if not self.token:
            login_params  = {
                'username': sickbeard.IPTORRENTS_USERNAME,
                'password': sickbeard.IPTORRENTS_PASSWORD,
                'login': 'submit'
            }
            result = None
            
            cookies = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
            try:
                logger.log("[IPTorrents] Attempting to Login")
                urllib2.install_opener(opener)
                response = opener.open(self.url + "torrents/", urllib.urlencode(login_params))
                result = response.read()
            except (urllib2.HTTPError, IOError, Exception), e:
                raise Exception("[IPTorrents] doLogin() Error: " + str(e.code) + " " + str(e.reason), logger.ERROR)
                return None
            if re.search("Password not correct|<title>IPT</title>",result):
                response.close()
                logger.log("[IPTorrents] Failed Login")
                raise Exception("Invalid username or password for " + self.name + ". Check your settings.")
                return None
            self.token = ""
            for cookie in cookies:
                if not cookie.value == "deleted":
                    self.token += str(cookie.name) + "=" + str(cookie.value) + ";"
            logger.log("[IPTorrents] Successfully logged user '%s' in." % sickbeard.IPTORRENTS_USERNAME)
            response.close()
        return True
    
    ###################################################################################################
    
class IPTorrentsCache(tvcache.TVCache):
    
    ###################################################################################################
    
    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        self.minTime = 15

    ###################################################################################################
        
    def _getRSSData(self):
        xml = ''
        if sickbeard.IPTORRENTS_UID and sickbeard.IPTORRENTS_RSSHASH:
            self.rss_url = provider.url + "torrents/rss?download;l78;l79;l5;u={0};tp={1}".format(sickbeard.IPTORRENTS_UID,sickbeard.IPTORRENTS_RSSHASH)
            logger.log("[IPTorrents] RSS URL - {0}".format(self.rss_url))
            xml = helpers.getURL(self.rss_url)
        else:
            logger.log("[IPTorrents] WARNING: RSS construction via browse since no hash or uid provided.")
            url = provider.url + "torrents/?l78=&l79=&l5=&q=&qf="
            data = provider.parseResults(url)
            xml =   "<rss xmlns:atom=\"http://www.w3.org/2005/Atom\" version=\"2.0\">" + \
                    "<channel>" + \
                    "<title>IPTorrents</title>" + \
                    "<link>" + provider.url + "</link>" + \
                    "<description>torrent search</description>" + \
                    "<language>en-us</language>" + \
                    "<atom:link href=\"" + provider.url + "\" rel=\"self\" type=\"application/rss+xml\"/>"
            
            for title, url in data:
                xml += "<item>" + "<title>" + title + "</title>" +  "<link>"+ url + "</link>" + "</item>"
            xml += "</channel> </rss>"
        return xml
        
    ###################################################################################################    
        
provider = IPTorrentsProvider()   
