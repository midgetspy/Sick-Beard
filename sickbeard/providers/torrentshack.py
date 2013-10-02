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

from xml.sax.saxutils import escape
from sickbeard.common import Quality
from sickbeard import logger
from sickbeard import tvcache
from sickbeard import helpers
from sickbeard import show_name_helpers
from sickbeard import db
from sickbeard.common import Overview
from sickbeard.exceptions import ex

class TorrentShackProvider(generic.TorrentProvider):
    ###################################################################################################
    def __init__(self):
        generic.TorrentProvider.__init__(self, "TorrentShack")
        self.supportsBacklog = True
        self.cache = TorrentShackCache(self)     
        self.url = 'https://torrentshack.net/'
        self.token = None
        logger.log('[TorrentShack] Loading TorrentShack')
    
    ###################################################################################################
    
    def isEnabled(self):
        return sickbeard.TORRENTSHACK
    
    ###################################################################################################
    
    def imageName(self):
        return 'torrentshack.png'
    
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
        search_params = search_params.replace('.',' ')
        logger.log("[TorrentShack] Performing Search: {0}".format(search_params))
        searchUrl = self.url + "torrents.php?searchstr=" + urllib.quote(search_params) + "&filter_cat[600]=1&filter_cat[620]=1&filter_cat[700]=1&filter_cat[980]=1&filter_cat[981]=1"
        return self.parseResults(searchUrl)
    
    ################################################################################################### 

    def _get_title_and_url(self, item):
        return item

    ###################################################################################################
    
    def parseResults(self, searchUrl):
        data = self.getURL(searchUrl)
        results = []
        if data:
            logger.log("[TorrentShack] parseResults() URL: " + searchUrl, logger.DEBUG)

            for torrent in re.compile('torrent_handle_links">\[<a href="(?P<url>.*?)" title="Download".*?class="torrent_name_link">(?P<title>.*?)</span>',re.MULTILINE|re.DOTALL).finditer(data):
                item = (torrent.group('title').replace('.',' '), self.url + torrent.group('url').replace('&amp;','&'))
                results.append(item)                        
                logger.log("[TorrentShack] parseResults() Title: " + torrent.group('title'), logger.DEBUG)
            if len(results):
                logger.log("[TorrentShack] parseResults() Some results found.")
            else:
                logger.log("[TorrentShack] parseResults() No results found.")
        else:
            logger.log("[TorrentShack] parseResults() Error no data returned!!")
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
                if re.search("Your username or password was incorrect|<title>Login :: Torrent Shack</title>",response):
                    logger.log("[TorrentShack] getURL() Session expired loading " + self.name + " URL: " + url +" Let's login again.")
                    self.token = None
                    self.getURL(url, headers)
            except (urllib2.HTTPError, IOError, Exception), e:
                self.token = None
                logger.log("[TorrentShack] getURL() Error loading " + self.name + " URL: " + str(sys.exc_info()) + " - " + ex(e), logger.ERROR)
                return None
        return response
    
    ###################################################################################################
    
    def doLogin(self):
        if not self.token:
            login_params  = {
                'username': sickbeard.TORRENTSHACK_USERNAME,
                'password': sickbeard.TORRENTSHACK_PASSWORD,
                'login': 'submit'
            }
            result = None
            
            cookies = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
            try:
                logger.log("[TorrentShack] Attempting to Login")
                urllib2.install_opener(opener)
                response = opener.open(self.url + "login.php", urllib.urlencode(login_params))
                result = response.read()
            except (urllib2.HTTPError, IOError, Exception), e:
                raise Exception("[TorrentShack] doLogin() Error: " + str(e.code) + " " + str(e.reason), logger.ERROR)
                return None
            if re.search("Your username or password was incorrect|<title>Login :: Torrent Shack</title>",result):
                response.close()
                logger.log("[TorrentShack] Failed Login")
                raise Exception("Invalid username or password for " + self.name + ". Check your settings.")
                return None
            self.token = ""
            for cookie in cookies:
                if not cookie.value == "deleted":
                    self.token += str(cookie.name) + "=" + str(cookie.value) + ";"
            logger.log("[TorrentShack] Successfully logged user '{0}' in.".format(sickbeard.TORRENTSHACK_USERNAME))
            response.close()
        return True
    
    ###################################################################################################
    
class TorrentShackCache(tvcache.TVCache):
    
    ###################################################################################################
    
    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        self.minTime = 15

    ###################################################################################################
        
    def _getRSSData(self):
        
        if sickbeard.TORRENTSHACK_UID and sickbeard.TORRENTSHACK_AUTH and sickbeard.TORRENTSHACK_PASS_KEY and sickbeard.TORRENTSHACK_AUTH_KEY:
            self.rss_url = "{0}feeds.php?feed=torrents&cat=600,620,700,980,981&user={1}&auth={2}&passkey={3}&authkey={4}".format(provider.url,sickbeard.TORRENTSHACK_UID, sickbeard.TORRENTSHACK_AUTH, sickbeard.TORRENTSHACK_PASS_KEY, sickbeard.TORRENTSHACK_AUTH_KEY)
            logger.log("[TorrentShack] RSS URL - {0}".format(self.rss_url))
            xml = helpers.getURL(self.rss_url)
        else:
            logger.log("[TorrentShack] WARNING: RSS construction via browse since no RSS variables provided.") 
            xml = "<rss xmlns:atom=\"http://www.w3.org/2005/Atom\" version=\"2.0\">" + \
            "<channel>" + \
            "<title>TorrentShack</title>" + \
            "<link>" + provider.url + "</link>" + \
            "<description>torrent search</description>" + \
            "<language>en-us</language>" + \
            "<atom:link href=\"" + provider.url + "\" rel=\"self\" type=\"application/rss+xml\"/>"

            for title, url in provider._doSearch(""):
                xml += "<item>" + "<title>" + escape(title) + "</title>" +  "<link>"+ urllib.quote(url,'/,:') + "</link>" + "</item>"
            xml += "</channel></rss>"
        return xml    
        
    ###################################################################################################    

provider = TorrentShackProvider()