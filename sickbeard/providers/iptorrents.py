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

import sickbeard
import generic
from sickbeard.common import Quality
from sickbeard import logger
from sickbeard import tvcache
from sickbeard import show_name_helpers
from sickbeard.common import Overview 
from sickbeard.exceptions import ex
from lib import requests
from bs4 import BeautifulSoup


class IPTorrentsProvider(generic.TorrentProvider):

    urls = {'base_url' : 'http://www.iptorrents.com/',
            'login' : 'http://www.iptorrents.com/torrents/',
            'detail' : 'http://www.iptorrents.com/details.php?id=%s',
            'search' : 'http://www.iptorrents.com/torrents/?l%d=1%s&q=%s&qf=ti',
            'download' : 'http://www.iptorrents.com/download.php/%s/%s.torrent',
            }

    def __init__(self):

        generic.TorrentProvider.__init__(self, "IPTorrents")
        
        self.supportsBacklog = True

        self.cache = IPTorrentsCache(self)
        
        self.url = self.urls['base_url']
        
        self.session = None

        self.categories = 73

    def isEnabled(self):
        return sickbeard.IPTORRENTS
        
    def imageName(self):
        return 'iptorrents.png'
    
    def getQuality(self, item):
        
        quality = Quality.nameQuality(item[0])
        return quality    

    def _doLogin(self):

        login_params = {'username': sickbeard.IPTORRENTS_USERNAME,
                        'password': sickbeard.IPTORRENTS_PASSWORD,
                        'login': 'submit',
                        }
        
        self.session = requests.Session()
        
        try:
            response = self.session.post(self.urls['login'], data=login_params, timeout=30)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
            logger.log(u'Unable to connect to ' + self.name + ' provider: ' +ex(e), logger.ERROR)
            return False
        
        if re.search('tries left', response.text) \
        or re.search('<title>IPT</title>', response.text) \
        or response.status_code == 401:
            logger.log(u'Invalid username or password for ' + self.name + ' Check your settings', logger.ERROR)       
            return False
        
        return True

    def _get_season_search_strings(self, show, season=None):

        search_string = {'Episode': []}
    
        if not show:
            return []

        seasonEp = show.getAllEpisodes(season)

        wantedEp = [x for x in seasonEp if show.getOverview(x.status) in (Overview.WANTED, Overview.QUAL)]          

        #If Every episode in Season is a wanted Episode then search for Season first
        if wantedEp == seasonEp and not show.air_by_date:
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
        
        if not self._doLogin():
            return 

        freeleech = '&free=on' if sickbeard.IPTORRENTS_FREELEECH else ''
        
        for mode in search_params.keys():
            for search_string in search_params[mode]:

                searchURL = self.urls['search'] % (self.categories, freeleech, search_string)

                logger.log(u"Search string: " + searchURL, logger.DEBUG)
        
                data = self.getURL(searchURL)
                if not data:
                    return []

                html = BeautifulSoup(data)
                
                try:
                    if html.find(text='Nothing found!'):
                        logger.log(u"No results found for: " + search_string + "(" + searchURL + ")", logger.DEBUG)
                        return []
                    
                    result_table = html.find('table', attrs = {'class' : 'torrents'})
                    
                    if not result_table:
                        logger.log(u"No results found for: " + search_string + "(" + searchURL + ")", logger.DEBUG)
                        return []
                    
                    entries = result_table.find_all('tr')

                    for result in entries[1:]:

                        torrent = result.find_all('td')[1].find('a')
                        
                        torrent_id = int(torrent['href'].replace('/details.php?id=', ''))
                        torrent_name = torrent.string
                        torrent_download_url = self.urls['download'] % (torrent_id, torrent_name.replace(' ', '.'))
                        torrent_details_url = self.urls['detail'] % (torrent_id)
                        torrent_seeders = int(result.find('td', attrs = {'class' : 'ac t_seeders'}).string)
                        torrent_leechers = int(result.find('td', attrs = {'class' : 'ac t_leechers'}).string)

                        #Filter unseeded torrent
                        if torrent_seeders == 0 or not torrent_name \
                        or not show_name_helpers.filterBadReleases(torrent_name):
                            continue 

                        item = torrent_name, torrent_download_url, torrent_id, torrent_seeders, torrent_leechers
                        logger.log(u"Found result: " + torrent_name + "(" + searchURL + ")", logger.DEBUG)
                        items[mode].append(item)

                except:
                    logger.log(u"Failed to parsing " + self.name + " page url: " + searchURL, logger.ERROR)

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
       
class IPTorrentsCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll IPTorrents every 20 minutes max
        self.minTime = 20

    def _getData(self):
       
        freeleech = '&free=on' if sickbeard.IPTORRENTS_FREELEECH else ''
       
        #url for the last 50 tv-show
        url = self.provider.urls['search'] % (self.provider.categories, freeleech, "")

        logger.log(u"IPTorrents cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data

    def _parseItem(self, item):

        (title, url) = item

        if not title or not url:
            return

        logger.log(u"Adding item to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = IPTorrentsProvider()
