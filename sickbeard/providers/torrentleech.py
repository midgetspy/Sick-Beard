# Author: Idan Gutman
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
import urllib, urllib2
import sys
import os
import gzip
import traceback
import cookielib
from StringIO import StringIO
from lib import MultipartPostHandler
from urlparse import urlparse
from bs4 import BeautifulSoup
from encoding import tryUrlencode

import sickbeard
import generic
from sickbeard.common import Quality
from sickbeard.name_parser.parser import NameParser, InvalidNameException
from sickbeard import logger
from sickbeard import tvcache
from sickbeard import helpers
from sickbeard import show_name_helpers
from sickbeard.common import Overview 
from sickbeard.exceptions import ex
from sickbeard import encodingKludge as ek

def tryInt(s):
    try: return int(s)
    except: return 0

class TorrentLeechProvider(generic.TorrentProvider):

    urls = {
        'test' : 'http://torrentleech.org/',
        'login' : 'http://torrentleech.org/user/account/login/',
        'detail' : 'http://torrentleech.org/torrent/%s',
        'search' : 'http://torrentleech.org/torrents/browse/index/query/%s/categories/%s',
        'download' : 'http://torrentleech.org%s',
    }

    http_time_between_calls = 1 #seconds
    cat_backup_id = None

    def __init__(self):

        generic.TorrentProvider.__init__(self, "TorrentLeech")
        
        self.supportsBacklog = True
        self.login_opener = None

        self.cache = TorrentLeechCache(self)
        
        self.categories = "2,26,32"
        
    def login(self):

        try:
            cookiejar = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))
            urllib2.install_opener(opener)
            logger.log(u"Logging into "+ self.urls['login'])
            f = opener.open(self.urls['login'], self.getLoginParams())
            f.read()
            f.close()
            self.login_opener = opener
            return True
        except:
            logger.log(u"Failed to login to "+self.name+":"+traceback.format_exc(), logger.ERROR)

        return False

    def getLoginParams(self):
        return tryUrlencode({
            'username': sickbeard.TORRENTLEECH_USERNAME,
            'password': sickbeard.TORRENTLEECH_PASSWORD,
            'remember_me': 'on',
            'login': 'submit',
        })

    def loginDownload(self, url = ''):

        try:
            if not self.login_opener and not self.login():
                logger.log(u"Failed downloading from "+self.name, logger.ERROR)
            return self.urlopen(url, opener = self.login_opener)
        except:
            logger.log(u"Failed downloading from "+self.name+": "+traceback.format_exc())

    def urlopen(self, url, timeout = 30, params = None, headers = None, opener = None, multipart = False, show_error = True):

        if not headers: headers = {}
        if not params: params = {}

        # Fill in some headers
        headers['Referer'] = headers.get('Referer', urlparse(url).hostname)
        headers['Host'] = headers.get('Host', urlparse(url).hostname)
        headers['User-Agent'] = headers.get('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:10.0.2) Gecko/20100101 Firefox/10.0.2')
        headers['Accept-encoding'] = headers.get('Accept-encoding', 'gzip')

        host = urlparse(url).hostname

        #self.wait(host)
        try:

            if multipart:
                logger.log(u"Opening multipart url: "+url+", params: "+[x for x in params.iterkeys()] if isinstance(params, dict) else 'with data', logger.DEBUG)
                request = urllib2.Request(url, params, headers)

                cookies = cookielib.CookieJar()
                opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies), MultipartPostHandler)

                response = opener.open(request, timeout = timeout)
            else:
                logger.log(u"Opening url: "+url+", params: "+str([x for x in params.iterkeys()]), logger.DEBUG)
                data = tryUrlencode(params) if len(params) > 0 else None
                request = urllib2.Request(url, data, headers)

                if opener:
                    response = opener.open(request, timeout = timeout)
                else:
                    response = urllib2.urlopen(request, timeout = timeout)

            # unzip if needed
            encoding = response.info().get('Content-Encoding')
            if encoding in ('gzip', 'x-gzip', 'deflate'):
                content = response.read()
                if encoding == 'deflate':
                    processed = StringIO(zlib.decompress(content))
                else:
                    processed = gzip.GzipFile('', 'rb', 9, StringIO(content))
                data = processed.read()

            else:
                data = response.read()

        except urllib2.HTTPError, e:
            logger.log(u"HTTP error " + str(e.code) + " while loading URL " + url, logger.WARNING)
            return None
        except urllib2.URLError, e:
            logger.log(u"URL error " + str(e.reason) + " while loading URL " + url, logger.WARNING)
            return None
        except Exception:
            logger.log(u"Unknown exception while loading URL " + url + ": " + traceback.format_exc(), logger.WARNING)
            return None

        return data

    def isEnabled(self):
        return sickbeard.TORRENTLEECH
        
    def imageName(self):
        return 'torrentleech.png'
    
    def getQuality(self, item):
        
        quality = Quality.nameQuality(item[0])
        return quality    

    def _get_season_search_strings(self, show, season=None):

        search_string = {'Episode': []}
    
        if not show:
            return []

        seasonEp = show.getAllEpisodes(season)

        wantedEp = [x for x in seasonEp if show.getOverview(x.status) in (Overview.WANTED, Overview.QUAL)]          

        #If Every episode in Season is a wanted Episode then search for Season first
        if wantedEp == seasonEp:
            search_string = {'Season': [], 'Episode': []}
            for show_name in set(show_name_helpers.allPossibleShowNames(show)):
                ep_string = show_name +' S%02d' % int(season) #1) ShowName SXX   
                search_string['Season'].append(ep_string)
                      
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

        for mode in search_params.keys():
            for search_string in search_params[mode]:
                
                searchURL = self.urls['search'] % (urllib.quote(search_string), self.categories)

                logger.log(u"Search string: " + searchURL, logger.DEBUG)
        
                data = self.getURL(searchURL)
                if not data:
                    return []

                html = BeautifulSoup(data)
                
                # Check if session ended and login required.
                try:
                    result_table = html.find('div', attrs = {'id' : 'login'})
                    if result_table:

                        if not self.login():
                            return []
                        
                        data = self.getURL(searchURL)
                        if not data:
                            return []

                        html = BeautifulSoup(data)
                except:
                    pass

                try:
                    result_table = html.find('table', attrs = {'id' : 'torrenttable'})
                    if result_table:

                        entries = result_table.find_all('tr')

                        for result in entries[1:]:

                            link = result.find('td', attrs = {'class' : 'name'}).find('a')
                            url = result.find('td', attrs = {'class' : 'quickdownload'}).find('a')
                            details = result.find('td', attrs = {'class' : 'name'}).find('a')

                            title = link.string
                            download_url = self.urls['download'] % url['href']
                            id = int(link['href'].replace('/torrent/', ''))
                            seeders = tryInt(result.find('td', attrs = {'class' : 'seeders'}).string)
                            leechers = tryInt(result.find('td', attrs = {'class' : 'leechers'}).string)

                            #Filter unseeded torrent
                            if seeders == 0:
                                continue 

                            if not show_name_helpers.filterBadReleases(title):
                                continue

                            if not title:
                                continue

                            item = title, download_url, id, seeders, leechers
                            logger.log(u"Found result: " + title + "(" + searchURL + ")", logger.DEBUG)

                            items[mode].append(item)

                except:
                    logger.log(u"Failed to parsing "+self.name+": "+traceback.format_exc(), logger.ERROR)

            #For each search mode sort all the items by seeders
            items[mode].sort(key=lambda tup: tup[3], reverse=True)        

            results += items[mode]  
                
        return results

    def _get_title_and_url(self, item):
        
        title, url, id, seeders, leechers = item
        
        if url:
            url = str(url).replace('&amp;','&')

        return (title, url)

    def getURL(self, url, headers=None):

        if not headers:
            headers = []

        result = None

        if not self.login_opener and not self.login():
            logger.log(u"Failed logging in to "+self.name, logger.ERROR)

        try:
            result = self.urlopen(url, headers=headers, opener=self.login_opener)
        except (urllib2.HTTPError, IOError), e:
            logger.log(u"Error loading "+self.name+" URL: " + str(sys.exc_info()) + " - " + ex(e), logger.ERROR)
            return None

        return result

    def verifyResult(self, result):
    
        result.content = self.getURL(result.url)
        return True
        
class TorrentLeechCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll TorrentLeech every 20 minutes max
        self.minTime = 20

    def _getData(self):
       
        #url for the last 50 tv-show
        url = self.provider.urls['search'] % ("", self.provider.categories )

        logger.log(u"TorrentLeech cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data

    def _parseItem(self, item):

        (title, url) = item

        if not title or not url:
            return

        logger.log(u"Adding item to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = TorrentLeechProvider()