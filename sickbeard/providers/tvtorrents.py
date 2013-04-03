# Author: Nic Wolfe <nic@wolfeden.ca>
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

from xml.dom.minidom import parseString
import re

import sickbeard
import generic

from sickbeard import helpers
from sickbeard import logger
from sickbeard import tvcache
from sickbeard.common import Quality
from sickbeard import show_name_helpers
from sickbeard.common import Overview 
from sickbeard.exceptions import ex
from lib import requests
from bs4 import BeautifulSoup

class TvTorrentsProvider(generic.TorrentProvider):

    urls = {'base_url' : 'http://www.tvtorrents.com/',
            'login' : 'http://www.tvtorrents.com/login.do',
            'detail' : 'http://www.tvtorrents.com/loggedin/torrent.do%s',
            'search' : 'http://www.tvtorrents.com/loggedin/search.do?search=%s',
            'download' : 'http://torrent.tvtorrents.com/FetchTorrentServlet%s',
            }

    def __init__(self):

        generic.TorrentProvider.__init__(self, "TvTorrents")
        
        self.supportsBacklog = True

        self.cache = TvTorrentsCache(self)

        self.url = self.urls['base_url']

        self.session = None

    def isEnabled(self):
        return sickbeard.TVTORRENTS
        
    def imageName(self):
        return 'tvtorrents.png'

    def getQuality(self, item):
        
        #logger.log("Trying to get quality from: " +item[0])
        name = item[0]
        if re.search("BluRay", name) and re.search("720p", name) and re.search("\\.mkv", name):
            return Quality.HDBLURAY
        elif re.search("BluRay", name) and re.search("1080p", name) and re.search("\\.mkv", name):
            return Quality.FULLHDBLURAY
        elif re.search("1080p", name) and re.search("\\.mkv", name):
            return Quality.FULLHDTV
        elif re.search("720p", name) and re.search("\\.mkv", name):
            return Quality.HDTV
        if re.search("DVDRip", name) or re.search("BDRip", name):
            return Quality.SDDVD
        else:
            return Quality.SDTV
        #quality = Quality.nameQuality(item[0])
        #return quality    

    def _doLogin(self):

        login_params = {'username': sickbeard.TVTORRENTS_USERNAME,
                        'password': sickbeard.TVTORRENTS_PASSWORD,
                        'cookie': 'on',
                        'posted': 'true',
                        'login': 'submit',
                        }
        
        self.session = requests.Session()
        
        try:
            response = self.session.post(self.urls['login'], data=login_params, timeout=30)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
            logger.log(u'Unable to connect to ' + self.name + ' provider: ' +ex(e), logger.ERROR)
            return False
        
        if re.search('Username and/or password is not correct.', response.text):
            logger.log(u'Invalid username or password for ' + self.name + ' Check your settings', logger.ERROR)       
            return False

        return True

    def _get_season_search_strings(self, show, season=None):

        search_string = {'Episode': []}
    
        if not show:
            return []

        if season != None and not show.air_by_date:
            search_string = {'Season': [], 'Episode': []}
            for show_name in set(show_name_helpers.allPossibleShowNames(show)):
                ep_string = show_name +' Season %d Complete' % int(season) #1) ShowName Season X Complete   
                search_string['Season'].append(ep_string)
        else:
            #Building the search string with the episodes we need         
            for ep_obj in wantedEp:
                search_string['Episode'] += self._get_episode_search_strings(ep_obj)[0]['Episode']
        
            #If no Episode is needed then return an empty list
            if not search_string['Episode']:
                return []
       
        return [search_string]

    def _get_episode_search_strings(self, ep_obj):
       
        search_string = {'Episode': []}
       
        if not ep_obj:
            return []
                
        if ep_obj.show.air_by_date:
            for show_name in set(show_name_helpers.allPossibleShowNames(ep_obj.show)):
                ep_string = show_name_helpers.sanitizeSceneName(show_name) +' '+ str(ep_obj.airdate)
                search_string['Episode'].append(ep_string)
        else:
            for show_name in set(show_name_helpers.allPossibleShowNames(ep_obj.show)):
                ep_string = show_name_helpers.sanitizeSceneName(show_name) +' '+ \
                sickbeard.config.naming_ep_type[2] % {'seasonnumber': ep_obj.season, 'episodenumber': ep_obj.episode}

                search_string['Episode'].append(ep_string)
    
        return [search_string]

    def _doSearch(self, search_params, show=None):
    
        results = []
        items = {'Season': [], 'Episode': []}
        
        if not self._doLogin():
            return 
        
        for mode in search_params.keys():
            for search_string in search_params[mode]:
                
                searchURL = self.urls['search'] % (search_string)

                logger.log(u"Search string: " + searchURL, logger.DEBUG)
        
                data = self.getURL(searchURL)
                if not data:
                    return []

                items[mode] += self.parseResults(data)

            results += items[mode]  
                
        return results

    def _get_title_and_url(self, item):
        
        #title, url, id, seeders, leechers = item
        title, url = item
        
        if url:
            url = str(url).replace('&amp;','&')

        return (title, url)


    def parseResults(self, data):
        results = []
        if data:
            allItems = re.findall(">(.+) <br><a href=\\\"[A-Za-z0-9/\\.\\?]+info_hash=([a-f0-9]+)\\\">(.+)</a>", data)
            for name, infoHash, release in allItems:
                title = '%s %s' % (name, release)
                urlParams = '?info_hash=%s&digest=%s&hash=%s' % (infoHash, sickbeard.TVTORRENTS_DIGEST, sickbeard.TVTORRENTS_HASH)
                url = self.urls['download'] % (urlParams)
                #logger.log("Title: " + title + ", Infohash: " + infoHash + ", Url: " + url)
                results.append((title, url))
        else:
            logger.log(u"Nothing found for " + searchUrl, logger.DEBUG)

        return results

    def getURL(self, url, headers=None):

        if not self.session:
            self._doLogin()

        if not headers:
            headers = []

        try:
            response = self.session.get(url)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
            logger.log(u"Error loading "+self.name+" URL: " + ex(e), logger.ERROR)
            return None

        return response.content
 
class TvTorrentsCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll TvTorrents every 15 minutes max
        self.minTime = 15


    def _getRSSData(self):
        # These will be ignored on the serverside.
        ignore_regex = "all.month|month.of|season[\s\d]*complete"
    
        url = 'http://www.tvtorrents.com/RssServlet?digest='+ sickbeard.TVTORRENTS_DIGEST +'&hash='+ sickbeard.TVTORRENTS_HASH +'&fname=true&exclude=(' + ignore_regex + ')'
        logger.log(u"TvTorrents cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)
        if not data:
            return None
        
        parsedXML = parseString(data)
        channel = parsedXML.getElementsByTagName('channel')[0]
        description = channel.getElementsByTagName('description')[0]

        description_text = helpers.get_xml_text(description)

        if "User can't be found" in description_text:
            logger.log(u"TvTorrents invalid digest, check your config", logger.ERROR)

        if "Invalid Hash" in description_text:
            logger.log(u"TvTorrents invalid hash, check your config", logger.ERROR)

        return data

    def _parseItem(self, item):

        (title, url) = self.provider._get_title_and_url(item)

        if not title or not url:
            logger.log(u"The XML returned from the TvTorrents RSS feed is incomplete, this result is unusable", logger.ERROR)
            return

        logger.log(u"Adding item from RSS to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = TvTorrentsProvider()
