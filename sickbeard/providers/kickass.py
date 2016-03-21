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

import json
from urllib import urlencode, quote
from urlparse import urlsplit, urlunsplit
import generic
import datetime
import sickbeard

from xml.sax.saxutils import escape

import xml.etree.cElementTree as etree

from sickbeard import db
from sickbeard import logger
from sickbeard import tvcache
from sickbeard.common import Quality
from sickbeard.common import Overview
from sickbeard import show_name_helpers

class KickAssProvider(generic.TorrentProvider):

    def __init__(self):
        generic.TorrentProvider.__init__(self, "Kickass")
        self.cache = KickAssCache(self)     
        self.supportsBacklog = True
        self.url = self._getDefaultURL()
        logger.log("[" + self.name + "] initializing...")
    
    def _getDefaultURL(self):
        """
        Retrieve the default URL for this provider
        """
        return "kat.cr"
    
    def isEnabled(self):
        return sickbeard.KICKASS

    def imageName(self):
        return 'kickass.png'
    
    def getQuality(self, item):        
        quality = Quality.nameQuality(item[0])
        return quality 
    
    def _get_title_and_url(self, item):
        return item

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
        logger.log("[" + self.name + "] Performing Search: {0}".format(search_params))
        for page in range(1,3):
            searchData = None
            SearchParameters = {}
            
            if len(sickbeard.KICKASS_ALT_URL):
                self.url = sickbeard.KICKASS_ALT_URL
            else:
                self.url = self._getDefaultURL()
            
            SearchParameters["order"] = "desc"
            SearchParameters["page"] = str(page)
            SearchParameters["rss"] = 1
            
            if len(search_params):
                SearchParameters["field"] = "seeders"
            else:
                SearchParameters["field"] = "time_add"
            
            # Make sure the URL is correctly formatted by parsing it (defaults to using https URLs)
            scheme, netloc, path, query, fragment = urlsplit(self.url, scheme="https")
            # Make sure netloc is available, without a scheme in the parsed string it is 
            # recognized as path without a netloc
            if not netloc:
                netloc = path
            path = quote("usearch/" + (search_params + " category:tv/").strip())
            query = urlencode(SearchParameters)
            searchURL = urlunsplit((scheme, netloc, path, query, fragment))
            logger.log("[" + self.name + "] _doSearch() Search URL: "+searchURL, logger.DEBUG)
            searchData = self.getURL(searchURL)
 
            if searchData and searchData.startswith("<?xml"):
                try:
                    responseXML = etree.ElementTree(etree.XML(searchData))
                    torrents = responseXML.getiterator('item')
                except Exception, e:
                    logger.log("[" + self.name + "] _doSearch() XML error: " + str(e), logger.ERROR)
                    continue
                
                if type(torrents) is list:
                    for torrent in torrents:
                        if torrent.findtext("title") and torrent.find("enclosure") is not None:
                            results.append((show_name_helpers.sanitizeSceneName(torrent.findtext("title")),torrent.find("enclosure").get("url")))
                    
        if not len(results):
            logger.log("[" + self.name + "] _doSearch() No results found.", logger.DEBUG)
        return results


class KickAssCache(tvcache.TVCache):
    
    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        # only poll KAT every 15 minutes max
        self.minTime = 15
        
    def _getRSSData(self):
        logger.log("[" + provider.name + "] Retrieving RSS")
        
        xml = "<rss xmlns:atom=\"http://www.w3.org/2005/Atom\" version=\"2.0\">" + \
            "<channel>" + \
            "<title>" + provider.name + "</title>" + \
            "<link>" + provider.url + "</link>" + \
            "<description>torrent search</description>" + \
            "<language>en-us</language>" + \
            "<atom:link href=\"" + provider.url + "\" rel=\"self\" type=\"application/rss+xml\"/>"
        data = provider._doSearch("")
        if data:
            for title, url in data:
                xml += "<item>" + "<title>" + escape(title) + "</title>" +  "<link>"+ url + "</link>" + "</item>"
        xml += "</channel></rss>"
        return xml
    
provider = KickAssProvider()
