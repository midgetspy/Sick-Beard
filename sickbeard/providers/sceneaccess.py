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

class SceneAccessProvider(generic.TorrentProvider):
    ###################################################################################################
    def __init__(self):

        generic.TorrentProvider.__init__(self, "SceneAccess")
        self.supportsBacklog = True
        self.cache = SceneAccessCache(self)     
        self.url = 'https://sceneaccess.eu/'
        self.token = None
        logger.log('[SceneAccess] Loading SceneAccess')
    
    ###################################################################################################
    
    def isEnabled(self):
        return sickbeard.SCENEACCESS
        
    ###################################################################################################
    
    def imageName(self):
        return 'sceneaccess.png'
    
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
        logger.log("[SceneAccess] Performing Search: {0}".format(search_params))
        searchUrl = self.url + "browse?search=" + urllib.quote(search_params) + "&method=2&c27=27&c17=17&c11=11"
        return self.parseResults(searchUrl)
    
    ################################################################################################### 

    def _get_title_and_url(self, item):
        return item

    ###################################################################################################
    
    def parseResults(self, searchUrl):
        #logger.log("[SceneAccess] parseResults() Was given Search string: " + searchUrl, logger.DEBUG)
        data = self.getURL(searchUrl)
        results = []
        if data:
            for torrent in re.compile('<td class="ttr_name"><a href="details\?id=\d+" title="(?P<title>.*?)">.*?<td class="td_dl"><a href="(?P<url>.*?)">' , re.MULTILINE|re.DOTALL).finditer(data):
                item = (torrent.group('title').replace('.',' '), self.url + torrent.group('url'))
                results.append(item)
                #logger.log("[SceneAccess] parseResults() Title: " + torrent.group('title'),logger.DEBUG)
                #logger.log("[SceneAccess] parseResults() URL: [" + item[1] + "]", logger.DEBUG)
            if len(results):
                logger.log("[SceneAccess] parseResults() Some results found.")
            else:
                logger.log("[SceneAccess] parseResults() No results found.")
        else:
            logger.log("[SceneAccess] parseResults() Error no data returned!!")
        return results
    
    ###################################################################################################
    
    def getURL(self, url, headers=None):
        self.doLogin()
        if not headers:
            headers = []
        headers.append(('Cookie', self.token))
        
        result = None
        try:
            result = helpers.getURL(url, headers)
            if result.count("<title>SceneAccess | Login</title>") > 0:
                #if session has expired, just try once more.
                logger.log("[SceneAccess] getURL() Session expired loading "+self.name+" URL: " + url +"\nLet's login again.")
                self.token = None
                self.getURL(url, headers)
            else:
                logger.log("[SceneAccess] Got data from SceneAccess!",logger.DEBUG)
        except (urllib2.HTTPError, IOError, Exception), e:
            self.token = None
            logger.log("[SceneAccess] getURL() Error loading "+self.name+" URL: " + str(sys.exc_info()) + " - " + ex(e), logger.ERROR)
            return None
        return result
    
    ###################################################################################################
    
    def doLogin(self):
        if not self.token:
            login_url = self.url + "login"
                      
            data = {
                'username': sickbeard.SCENEACCESS_USERNAME,
                'password': sickbeard.SCENEACCESS_PASSWORD,
                'login': 'submit'
            }
            username = sickbeard.SCENEACCESS_USERNAME
            password = sickbeard.SCENEACCESS_PASSWORD
            
            cookies = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
            urllib2.install_opener(opener)
            response = opener.open(login_url, urllib.urlencode(data))
            result = response.read() 
           
            if result == None or result.count("Invalid Username/password") > 0 or result.count("<title>SceneAccess | Login</title>") > 0:
                response.close()
                logger.log("[SceneAccess] Failed Login", logger.DEBUG)
                raise Exception("Invalid username or password for " + self.name + ". Check your settings.") 
             
            uid = ''
            passw = ''
            for cookie in cookies:
                if cookie.name == "uid" and not cookie.value == "deleted": 
                    uid = "uid=" + cookie.value  + ";"
                if cookie.name == "pass" and not cookie.value == "deleted": 
                    passw = "pass=" + cookie.value  + ";"
            self.token = "%s%s" % (uid, passw)
            logger.log("[SceneAccess] Session: " + self.token, logger.DEBUG)
            logger.log("[SceneAccess] Successfully logged user '%s' in." % sickbeard.SCENEACCESS_USERNAME)
            response.close()
    
    ###################################################################################################
    
class SceneAccessCache(tvcache.TVCache):
    
    ###################################################################################################
    
    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        self.minTime = 15

    ###################################################################################################
        
    def _getRSSData(self):
        xml = ''
        if sickbeard.SCENEACCESS_RSSHASH:
            self.rss_url = "https://sceneaccess.eu/rss?feed=dl&cat=27,17,11&passkey={0}".format(sickbeard.SCENEACCESS_RSSHASH)
            logger.log("[SceneAccess] RSS URL - {0}".format(self.rss_url))
            xml = helpers.getURL(self.rss_url)
        else:
            logger.log("[SceneAccess] WARNING: RSS construction via browse since no hash provided.")
            url = provider.url + "browse?search=&method=2&c27=27&c17=17&c11=11"
            data = provider.parseResults(url)
            xml = "<rss xmlns:atom=\"http://www.w3.org/2005/Atom\" version=\"2.0\">" + \
            "<channel>" + \
            "<title>SceneAccess</title>" + \
            "<link>" + provider.url + "</link>" + \
            "<description>torrent search</description>" + \
            "<language>en-us</language>" + \
            "<atom:link href=\"" + provider.url + "\" rel=\"self\" type=\"application/rss+xml\"/>"
            
            for title, url in data:
                xml += "<item>" + "<title>" + title + "</title>" +  "<link>"+ url + "</link>" + "</item>"
            xml += "</channel></rss>"
        return xml
        
    ###################################################################################################    
        
provider = SceneAccessProvider()   
