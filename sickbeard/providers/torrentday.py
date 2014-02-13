# Author: Mr_Orange <mr_orange@hotmail.it>
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

import json
import re
import traceback
import datetime

import sickbeard
import generic
from sickbeard.common import Quality
from sickbeard import logger
from sickbeard import tvcache
from sickbeard import db
from sickbeard import classes
from sickbeard import helpers
from sickbeard import show_name_helpers
from sickbeard.common import Overview 
from sickbeard.exceptions import ex
from sickbeard import clients
from lib import requests
from bs4 import BeautifulSoup
from lib.unidecode import unidecode

class TorrentDayProvider(generic.TorrentProvider):

    urls = {'base_url' : 'http://www.torrentday.com',
            'login' : 'http://www.torrentday.com/torrents/',
            'search' : 'http://www.torrentday.com/V3/API/API.php',
            'download': 'http://www.torrentday.com/download.php/%s/%s'
            }

    def __init__(self):

        generic.TorrentProvider.__init__(self, "TorrentDay")
        
        self.supportsBacklog = True

        self.cache = TorrentDayCache(self)
        
        self.url = self.urls['base_url']
        
        self.session = requests.Session()
        
        self.cookies = None

        self.categories = {'Season': {'c14':1}, 'Episode': {'c2':1, 'c26':1, 'c7':1, 'c24':1}, 'RSS': {'c2':1, 'c26':1, 'c7':1, 'c24':1, 'c14':1}}

    def isEnabled(self):
        return sickbeard.TORRENTDAY
        
    def imageName(self):
        return 'torrentday.png'
    
    def getQuality(self, item):
        
        quality = Quality.sceneQuality(item[0])
        return quality    

    def _doLogin(self):

        if any(requests.utils.dict_from_cookiejar(self.session.cookies).values()):
            return True
        
        if sickbeard.TORRENTDAY_UID and sickbeard.TORRENTDAY_HASH:
            
            requests.utils.add_dict_to_cookiejar(self.session.cookies, self.cookies)
        
        else:    

            login_params = {'username': sickbeard.TORRENTDAY_USERNAME,
                            'password': sickbeard.TORRENTDAY_PASSWORD,
                            'submit.x': 0, 
                            'submit.y': 0
                            }
                                         
            try:
                response = self.session.post(self.urls['login'],  data=login_params, timeout=30)
            except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
                logger.log(u'Unable to connect to ' + self.name + ' provider: ' + ex(e), logger.ERROR)
                return False
            
            if re.search('You tried too often', response.text):
                logger.log(u'Too many login access for ' + self.name + ', can''t retrive any data', logger.ERROR)
                return False
            
            if response.status_code == 401:
                logger.log(u'Invalid username or password for ' + self.name + ', Check your settings!', logger.ERROR)       
                return False
            
            sickbeard.TORRENTDAY_UID = requests.utils.dict_from_cookiejar(self.session.cookies)['uid']
            sickbeard.TORRENTDAY_HASH = requests.utils.dict_from_cookiejar(self.session.cookies)['pass']
  
            self.cookies = {'uid': sickbeard.TORRENTDAY_UID,
                            'pass': sickbeard.TORRENTDAY_HASH
                            }
               
        return True

    def _get_season_search_strings(self, show, season=None):

        search_string = {'Episode': []}
    
        if not show:
            return []

        seasonEp = show.getAllEpisodes(season)

        wantedEp = [x for x in seasonEp if show.getOverview(x.status) in (Overview.WANTED, Overview.QUAL)]          

        # If Every episode in Season is a wanted Episode then search for Season first
        if wantedEp == seasonEp and not show.air_by_date:
            search_string = {'Season': [], 'Episode': []}
            for show_name in set(show_name_helpers.allPossibleShowNames(show)):
                ep_string = show_name +' S%02d' % int(season) #1) ShowName SXX   
                search_string['Season'].append(ep_string)
                      
        # Building the search string with the episodes we need         
        for ep_obj in wantedEp:
            search_string['Episode'] += self._get_episode_search_strings(ep_obj)[0]['Episode']
        
        # If no Episode is needed then return an empty list
        if not search_string['Episode']:
            return []
        
        return [search_string]

    def _get_episode_search_strings(self, ep_obj, add_string=''):
       
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

                search_string['Episode'].append(re.sub('\s+', ' ', ep_string))
    
        return [search_string]

    def _doSearch(self, search_params):
    
        results = []
        items = {'Season': [], 'Episode': [], 'RSS': []}

        freeleech = '&free=on' if sickbeard.TORRENTDAY_FREELEECH else ''
        
        if not self._doLogin():
            return []        
        
        for mode in search_params.keys():
            for search_string in search_params[mode]:

                logger.log(u"Search string: " + search_string, logger.DEBUG)
                
                search_string = '+'.join(search_string.split())
                
                post_data  = dict({'/browse.php?' : None,'cata':'yes','jxt':8,'jxw':'b','search':search_string}, **self.categories[mode])
                
                if sickbeard.TORRENTDAY_FREELEECH:
                    post_data.update({'free':'on'})

                data = self.session.post(self.urls['search'], data=post_data).json()

                try:
                    torrents = data.get('Fs', [])[0].get('Cn', {}).get('torrents', [])
                except:
                    continue

                for torrent in torrents:
                    
                    title = re.sub(r"\[.*\=.*\].*\[/.*\]", "", torrent['name'])
                    url = self.urls['download'] %( torrent['id'], torrent['fname'] )
                    seeders = int(torrent['seed'])
                    leechers = int(torrent['leech'])
                                   
                    if mode != 'RSS' and seeders == 0:
                        continue
                    
                    if not title or not url:
                        continue

                    item = title, url, seeders, leechers
                    items[mode].append(item)

            results += items[mode]  
                
        return results

    def _get_title_and_url(self, item):
        
        title, url = item[0], item[1]
        
        if url:
            url = str(url).replace('&amp;','&')

        return (title, url)

    def getURL(self, url,  headers=None):

        if not self.session:
            self._doLogin()
        
        try:
            response = self.session.get(url)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
            logger.log(u"Error loading " + self.name + " URL: " + ex(e), logger.ERROR)
            return None

        if response.status_code != 200:
            logger.log(self.name + u" page requested with url " + url +" returned status code is " + str(response.status_code) + ': ' + clients.http_error_code[response.status_code], logger.WARNING)
            return None

        return response.content

    def findPropers(self, search_date=None):

        results = []

        sqlResults = db.DBConnection().select('SELECT s.show_name, e.showid, e.season, e.episode, e.status, e.airdate FROM tv_episodes AS e INNER JOIN tv_shows AS s ON (e.showid = s.tvdb_id) WHERE e.airdate >= ? AND (e.status IN ('+','.join([str(x) for x in Quality.DOWNLOADED])+') OR (e.status IN ('+','.join([str(x) for x in Quality.SNATCHED ])+')))', [search_date.toordinal()])
        if not sqlResults:
            return []
        
        for sqlShow in sqlResults:
            curShow = helpers.findCertainShow(sickbeard.showList, int(sqlShow["showid"]))
            curEp = curShow.getEpisode(int(sqlShow["season"]),int(sqlShow["episode"]))
            searchString = self._get_episode_search_strings(curEp, add_string='PROPER|REPACK')

            for item in self._doSearch(searchString[0]):
                title, url = self._get_title_and_url(item)
                results.append(classes.Proper(title, url, datetime.datetime.today().toordinal()))

        return results


class TorrentDayCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # Only poll IPTorrents every 10 minutes max
        self.minTime = 10

    def updateCache(self):

        if not self.shouldUpdate():
            return

        search_params = {'RSS': ['']}
        rss_results = self.provider._doSearch(search_params)
        
        if rss_results:
            self.setLastUpdate()
        else:
            return []
        
        logger.log(u"Clearing " + self.provider.name + " cache and updating with new information")
        self._clearCache()

        for result in rss_results:
            item = (result[0], result[1])
            self._parseItem(item)
            
    def _parseItem(self, item):

        (title, url) = item

        if not title or not url:
            return

        logger.log(u"Adding item to cache: " + title, logger.DEBUG)

        self._addCacheEntry(title, url)            

provider = TorrentDayProvider()
