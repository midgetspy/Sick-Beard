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

import time

from lib import requests
from xml.sax.saxutils import escape

import xml.etree.cElementTree as etree

from sickbeard import db
from sickbeard import logger
from sickbeard import tvcache
from sickbeard.exceptions import ex
from sickbeard.common import Quality
from sickbeard.common import Overview
from sickbeard import show_name_helpers

class TORRENTZProvider(generic.TorrentProvider):
    ###################################################################################################

    def __init__(self):
        generic.TorrentProvider.__init__(self, "Torrentz")
        self.cache = TORRENTZCache(self)
        self.url = 'https://torrentz.eu/'
        self.name = "Torrentz"
        self.supportsBacklog = True
        self.rss = False
        self.session = None
        
        logger.log("[" + self.name + "] initializing...")
        
        if not self.session:
            self.session = requests.Session()
                
    ###################################################################################################
    
    def isEnabled(self):
        return sickbeard.TORRENTZ
        
    ###################################################################################################
    
    def imageName(self):
        return 'torrentz.png'
    
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
    
    def switchSearchType(self):
        # sigh... we do this just to keep _doSearch() params standard, stupid rss...
        if sickbeard.TORRENTZ_VERIFIED:
            if self.rss is True:
                search_type = "feed_verifiedA"
            else:
                search_type = "feed_verifiedP"
        else:
            if self.rss is True:
                search_type = "feedA"
            else:
                search_type = "feedP"
        
        # race condition between rss and back log searching if both were to run at same time, best to disable.
        if self.rss is True:
            self.rss = False
            
        return search_type
    
    ###################################################################################################
    
    def _doSearch(self, search_params, show=None):
        results = []
        logger.log("[" + self.name + "] _doSearch() Performing Search: {0}".format(search_params,show))
        
        search_type = self.switchSearchType()
        
        for page in range(0,2):
            searchData = None
            
            logger.log("[" + self.name + "] _doSearch() - " + self.url + search_type + "?q=" + urllib.quote(search_params) + "&p=" + str(page),logger.DEBUG)
            searchData = self.getURL(self.url + search_type + "?q=" + urllib.quote(search_params) + "&p=" + str(page))
            
            if searchData and searchData.startswith("<?xml"):    
                try:
                    responseSoup = etree.ElementTree(etree.XML(searchData))
                except Exception, e:
                    logger.log("[" + self.name + "] _doSearch() XML error: " + str(e), logger.ERROR)
                    continue

                torrents = responseSoup.getiterator('item')
                if type(torrents) is list:
                    for torrent in torrents:
                        if torrent.findtext('guid') and torrent.findtext('title'):
                            title = torrent.findtext('title').encode('ascii',errors='ignore')
                            magnet = "magnet:?xt=urn:btih:" + re.sub(self.url + '|' + self.url.replace('s:',':'),'',torrent.findtext('guid')) + "&dn=" + title + ".torrent"
                            results.append((title,magnet))
            time.sleep(1)
        return results
        
    ###################################################################################################
    
    def _sanitizeName(self, text):
        return show_name_helpers.sanitizeSceneName(text, ezrss=True).replace('.',' ').replace('-',' ').encode('utf-8')

    ###################################################################################################
    
    def getURL(self, url, headers=None):
        logger.log("[" + self.name + "] getURL() retrieving URL: " + url, logger.DEBUG)
        response = None
            
        if not headers:
            headers = {}
         
        headers['User-Agent']="SickBeard Torrent Edition."
        
        try:
            response = self.session.get(url, verify=False,headers=headers)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
            logger.log("[" + self.name + "] getURL() Error loading " + self.name + " URL: " + ex(e), logger.ERROR)
            return None
        
        if response.status_code not in [200,302,303,404]:
            # response did not return an acceptable result
            logger.log("[" + self.name + "] getURL() requested URL - " + url +" returned status code is " + str(response.status_code), logger.ERROR)
            return None
        if response.status_code in [404]:
            # response returned an empty result
            return None

        return response.content
    
    ###################################################################################################
    
class TORRENTZCache(tvcache.TVCache):
    
    ###################################################################################################
    
    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        # only poll Torrentz every 15 minutes max
        self.minTime = 15
    
    ###################################################################################################
    
    def _getRSSData(self):
        logger.log("[" + provider.name + "] Retriving RSS")

        self.provider.rss = True
        searchData = self.provider._doSearch("")
        
        xml = "<rss xmlns:atom=\"http://www.w3.org/2005/Atom\" version=\"2.0\">" + \
        "<channel>" + \
        "<title>" + provider.name + "</title>" + \
        "<link>" + provider.url + "</link>" + \
        "<description>torrent search</description>" + \
        "<language>en-us</language>" + \
        "<atom:link href=\"" + provider.url + "\" rel=\"self\" type=\"application/rss+xml\"/>"
        
        for title, url in searchData:
            xml += "<item>" + "<title>" + escape(title) + "</title>" +  "<link>"+ urllib.quote(url,'/,:') + "</link>" + "</item>"
        xml += "</channel></rss>"
        return xml

    ###################################################################################################
    
provider = TORRENTZProvider()