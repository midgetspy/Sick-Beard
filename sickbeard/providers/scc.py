# Author: Idan Gutman
# Modified by jkaberg, https://github.com/jkaberg for SceneAccess
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

class SCCProvider(generic.TorrentProvider):

    urls = {'base_url' : 'https://sceneaccess.eu',
            'login' : 'https://sceneaccess.eu/login',
            'detail' : 'https://www.sceneaccess.eu/details?id=%s',
            'search' : 'https://sceneaccess.eu/browse?search=%s&method=1&%s',
            'archive' : 'https://sceneaccess.eu/archive?search=%s&method=1&c26=26',
            'download' : 'https://www.sceneaccess.eu/%s',
            }

    def __init__(self):

        generic.TorrentProvider.__init__(self, "SceneAccess")

        self.supportsBacklog = True

        self.cache = SCCCache(self)

        self.url = self.urls['base_url']

        self.categories = "c27=27&c17=17&c11=11"

        self.session = None

    def isEnabled(self):
        return sickbeard.SCC

    def imageName(self):
        return 'scc.png'

    def getQuality(self, item):

        quality = Quality.sceneQuality(item[0])
        return quality    

    def _doLogin(self):

        login_params = {'username': sickbeard.SCC_USERNAME,
                        'password': sickbeard.SCC_PASSWORD,
                        'submit': 'come on in',
                        }

        self.session = requests.Session()

        try:
            response = self.session.post(self.urls['login'], data=login_params, timeout=30, verify=False)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
            logger.log(u'Unable to connect to ' + self.name + ' provider: ' +ex(e), logger.ERROR)
            return False

        if re.search('Username or password incorrect', response.text) \
        or re.search('<title>SceneAccess \| Login</title>', response.text) \
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

    def _doSearch(self, search_params, show=None):

        results = []
        items = {'Season': [], 'Episode': [], 'RSS': []}

        if not self._doLogin():
            return []

        for mode in search_params.keys():
            for search_string in search_params[mode]:

                if isinstance(search_string, unicode):
                    search_string = unidecode(search_string)
                
                if mode == 'Season':
                    searchURL = self.urls['archive'] % (search_string)
                else:     
                    searchURL = self.urls['search'] % (search_string, self.categories)

                logger.log(u"Search string: " + searchURL, logger.DEBUG)

                data = self.getURL(searchURL)
                if not data:
                    continue

                try:
                    html = BeautifulSoup(data, features=["html5lib", "permissive"])

                    torrent_table = html.find('table', attrs = {'id' : 'torrents-table'})
                    torrent_rows = torrent_table.find_all('tr') if torrent_table else []

                    #Continue only if one Release is found
                    if len(torrent_rows)<2:
                        logger.log(u"The Data returned from " + self.name + " do not contains any torrent", logger.DEBUG)
                        continue

                    for result in torrent_table.find_all('tr')[1:]:

                        try:
                            link = result.find('td', attrs = {'class' : 'ttr_name'}).find('a')
                            url = result.find('td', attrs = {'class' : 'td_dl'}).find('a')
                            title = link.string
                            download_url = self.urls['download'] % url['href']
                            id = int(link['href'].replace('details?id=', ''))
                            seeders = int(result.find('td', attrs = {'class' : 'ttr_seeders'}).string)
                            leechers = int(result.find('td', attrs = {'class' : 'ttr_leechers'}).string)
                        except (AttributeError, TypeError):
                            continue

                        if mode != 'RSS' and seeders == 0:
                            continue 

                        if not title or not download_url:
                            continue

                        item = title, download_url, id, seeders, leechers
                        logger.log(u"Found result: " + title + "(" + searchURL + ")", logger.DEBUG)

                        items[mode].append(item)

                except Exception, e:
                    logger.log(u"Failed parsing " + self.name + " Traceback: "  + traceback.format_exc(), logger.ERROR)

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
            headers = {'user-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1700.107 Safari/537.36'}

        try:
            response = self.session.get(url, headers=headers, verify=False)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
            logger.log(u"Error loading "+self.name+" URL: " + ex(e), logger.ERROR)
            return None

        if response.status_code != 200:
            logger.log(self.name + u" page requested with url " + url +" returned status code is " + str(response.status_code) + ': ' + clients.http_error_code[response.status_code], logger.WARNING)
            return None

        return response.content

    def findPropers(self, search_date=datetime.datetime.today()):

        results = []

        sqlResults = db.DBConnection().select('SELECT s.show_name, e.showid, e.season, e.episode, e.status, e.airdate FROM tv_episodes AS e' +
                                              ' INNER JOIN tv_shows AS s ON (e.showid = s.tvdb_id)' +
                                              ' WHERE e.airdate >= ' + str(search_date.toordinal()) +
                                              ' AND (e.status IN (' + ','.join([str(x) for x in Quality.DOWNLOADED]) + ')' +
                                              ' OR (e.status IN (' + ','.join([str(x) for x in Quality.SNATCHED]) + ')))'
                                              )
        if not sqlResults:
            return []

        for sqlShow in sqlResults:
            curShow = helpers.findCertainShow(sickbeard.showList, int(sqlShow["showid"]))
            curEp = curShow.getEpisode(int(sqlShow["season"]), int(sqlShow["episode"]))
            searchString = self._get_episode_search_strings(curEp, add_string='PROPER|REPACK')

            for item in self._doSearch(searchString[0]):
                title, url = self._get_title_and_url(item)
                results.append(classes.Proper(title, url, datetime.datetime.today()))

        return results


class SCCCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll SCC every 10 minutes max
        self.minTime = 20

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

        ql = []
        for result in rss_results:
            item = (result[0], result[1])
            ci = self._parseItem(item)
            if ci is not None:
                ql.append(ci)

        myDB = self._getDB()
        myDB.mass_action(ql)

    def _parseItem(self, item):

        (title, url) = item

        if not title or not url:
            return None

        logger.log(u"Adding item to cache: " + title, logger.DEBUG)

        return self._addCacheEntry(title, url)

provider = SCCProvider()
