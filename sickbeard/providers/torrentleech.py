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

class TorrentLeechProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "TorrentLeech")
        
        self.supportsBacklog = True
        self.cache = TorrentLeechCache(self)
        self.token = None
        self.url = 'http://www.torrentleech.org/'
        
    def isEnabled(self):
        return sickbeard.TORRENTLEECH
        
    def imageName(self):
        return 'torrentleech.png'
    
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
        baseUrl = self.url + "torrents/browse/index/query/%s/categories/2,26,27,32"

        searchUrl = baseUrl % search_params
        #logger.log(u"Search string: " + searchUrl) #, logger.DEBUG)
                

        logger.log(u"Search string: " + searchUrl, logger.DEBUG)
        return self.parseResults(searchUrl)
    
    def _get_title_and_url(self, item):
        return item
    
    def parseResults(self, searchUrl):
        data = self.getURL(searchUrl)
        results = []
        if data:
            allItems = re.findall("<a\\s(?:[^\\s>]*?\\s)*?href=\"(?:mailto:)?(.*?)\".*?>(.+?)</a>", data)
            for url, title in allItems:
                if url.startswith("/torrent/") and url.count("#") == 0:
                    url = self.url + url
                    url = url.replace("//torrent/", "/download/") + "/" + title.replace(" ", ".") + ".torrent"
                    results.append((title, url))
        else:
            logger.log("Nothing found for " + searchUrl, logger.DEBUG)
            
        return results


    def getURL(self, url, headers=None):

        self.doLogin()
        if not headers:
            headers = []
        headers.append(('Cookie', self.token))

        result = None
        try:
            result = helpers.getURL(url, headers)
            if result.count("<title>Login :: TorrentLeech.org</title>") > 0:
                #if session has expired, just try once more.
                logger.log(u"Session expired loading "+self.name+" URL: " + url +"\nLet's login again.", logger.DEBUG)
                self.token = None
                self.getURL(url, headers)
        except (urllib2.HTTPError, IOError, Exception), e:
            self.token = None
            logger.log(u"Error loading "+self.name+" URL: " + str(sys.exc_info()) + " - " + ex(e), logger.ERROR)
            return None

        return result
    
    def doLogin(self):
        if not self.token:
            login_url = self.url + "user/account/login"
            #headers = {
            #    'User-Agent': helpers.USER_AGENT,
            #    'Referer': login_url,
            #    'Origin': self.url,
            #    'Accept': 'text/html',
            #    'Accept-Encoding': '', #'gzip,deflate',
            #    'Content-type': 'application/x-www-form-urlencoded'
            #}
            data = {
                'username': sickbeard.TORRENTLEECH_USERNAME,
                'password': sickbeard.TORRENTLEECH_PASSWORD,
                'remember_me': 'on',
                'login': 'submit'
            }
    
            cookies = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
            urllib2.install_opener(opener)
            #request = urllib2.Request(login_url, urllib.urlencode(data), headers) 
            response = opener.open(login_url, urllib.urlencode(data))
            result = response.read()

            
            if result.count("Invalid Username/password") > 0 or result.count("<title>Login :: TorrentLeech.org</title>") > 0:
                response.close()
                raise Exception("Invalid username or password for " + self.name + ". Check your settings.") 
             
            #cookies = response.info().getheaders("set-cookie")
            phpsessid = ''
            member_id = ''
            pass_hash = ''
            tluid = ''
            tlpass = ''
            for cookie in cookies:
                if cookie.name == "PHPSESSID" and not cookie.value == "deleted": 
                    phpsessid = "PHPSESSID=" + cookie.value  + ";"
                if cookie.name == "member_id" and not cookie.value == "deleted": 
                    member_id = "member_id=" + cookie.value  + ";"
                if cookie.name == "pass_hash" and not cookie.value == "deleted": 
                    pass_hash = "pass_hash=" + cookie.value  + ";"
                if cookie.name == "tluid" and not cookie.value == "deleted": 
                    tluid = "tluid=" + cookie.value  + ";"
                if cookie.name == "tlpass" and not cookie.value == "deleted": 
                    tlpass = "tlpass=" + cookie.value  + ";"
            self.token = "%s%s%s%s%s" % (phpsessid, member_id, pass_hash, tluid, tlpass)
            logger.log("TorrentLeech session: " + self.token, logger.DEBUG)
            logger.log("TorrentLeech successfully logged user '%s' in." % sickbeard.TORRENTLEECH_USERNAME)
            response.close()
        

class TorrentLeechCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        self.url = "torrents/browse/index/categories/2,26,27,32"
        # only poll TorrentLeech every 15 minutes max
        self.minTime = 15

    def _getRSSData(self):
        url = provider.url + self.url
        logger.log(u"TorrentLeech cache update URL: " + url, logger.DEBUG)
        data = provider.parseResults(url)
        
        rss = "<rss xmlns:atom=\"http://www.w3.org/2005/Atom\" version=\"2.0\">" + \
"<channel>" + \
"<title>" + provider.name + "</title>" + \
"<link>" + provider.url + "</link>" + \
"<description>torrent search</description>" + \
"<language>en-us</language>" + \
"<atom:link href=\"" + provider.url + "\" rel=\"self\" type=\"application/rss+xml\"/>"

        for title, url in data:
            rss = rss + \
                    "<item>" + \
                    "<title>" + title + "</title>" + \
                    "<link>"+ url + "</link>" + \
                    "</item>"
        rss = rss + "</channel></rss>"
        
        return rss
        
provider = TorrentLeechProvider()