# Author: seedboy
# URL: https://github.com/seedboy
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

import traceback
import urllib2
import urllib
import time
import re
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


class NextGenProvider(generic.TorrentProvider):
    urls = {'base_url': 'https://nxtgn.org/',
            'search': 'https://nxtgn.org/browse.php?search=%s&cat=0&incldead=0&modes=%s',
            'login_page': 'https://nxtgn.org/login.php',
            'detail': 'https://nxtgn.org/details.php?id=%s',
            'download': 'https://nxtgn.org/download.php?id=%s',
            'takelogin': 'https://nxtgn.org/takelogin.php?csrf=',
    }

    def __init__(self):

        generic.TorrentProvider.__init__(self, "NextGen")

        self.supportsBacklog = True

        self.cache = NextGenCache(self)

        self.url = self.urls['base_url']

        self.categories = '&c7=1&c24=1&c17=1&c22=1&c42=1&c46=1&c26=1&c28=1&c43=1&c4=1&c31=1&c45=1&c33=1'

        self.last_login_check = None
        self.login_opener = None

    def isEnabled(self):
        return sickbeard.NEXTGEN

    def imageName(self):
        return 'nextgen.png'

    def getQuality(self, item):

        quality = Quality.sceneQuality(item[0])
        return quality

    def getLoginParams(self):
        return {
            'username': sickbeard.NEXTGEN_USERNAME,
            'password': sickbeard.NEXTGEN_PASSWORD,
            }

    def loginSuccess(self, output):
        if "<title>NextGen - Login</title>" in output:
            return False
        else:
            return True

    def _doLogin(self):

        now = time.time()

        if self.login_opener and self.last_login_check < (now - 3600):
            try:
                output = self.login_opener.open(self.urls['test'])
                if self.loginCheckSuccess(output):
                    self.last_login_check = now
                    return True
                else:
                    self.login_opener = None
            except:
                self.login_opener = None

        if self.login_opener:
            return True

        try:
            login_params = self.getLoginParams()
            self.session = requests.Session()
            self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:24.0) Gecko/20130519 Firefox/24.0)'})
            data = self.session.get(self.urls['login_page'])
            bs = BeautifulSoup(data.content.decode('iso-8859-1'))
            csrfraw = bs.find('form', attrs = {'id': 'login'})['action']
            output = self.session.post(self.urls['base_url']+csrfraw, data=login_params)            
            
            if self.loginSuccess(output):
                self.last_login_check = now
                self.login_opener = self.session
                return True

            error = 'unknown'
        except:
            error = traceback.format_exc()
            self.login_opener = None

        self.login_opener = None
        logger.log(u'Failed to login:' + str(error), logger.ERROR)
        return False

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
                ep_string = show_name + ' S%02d' % int(season) #1) ShowName SXX
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
                ep_string = show_name_helpers.sanitizeSceneName(show_name) + ' ' + str(ep_obj.airdate)
                search_string['Episode'].append(ep_string)
        else:
            for show_name in set(show_name_helpers.allPossibleShowNames(ep_obj.show)):
                ep_string = show_name_helpers.sanitizeSceneName(show_name) + ' ' + \
                            sickbeard.config.naming_ep_type[2] % {'seasonnumber': ep_obj.season,
                                                                  'episodenumber': ep_obj.episode}

                search_string['Episode'].append(re.sub('\s+', ' ', ep_string))

        return [search_string]

    def _doSearch(self, search_params):

        results = []
        items = {'Season': [], 'Episode': [], 'RSS': []}

        if not self._doLogin():
            return []

        for mode in search_params.keys():

            for search_string in search_params[mode]:

                searchURL = self.urls['search'] % (search_string, self.categories)
                logger.log(u"" + self.name + " search page URL: " + searchURL, logger.DEBUG)

                data = self.getURL(searchURL)

                if data:

                    try:
                        html = BeautifulSoup(data.decode('iso-8859-1'), features=["html5lib", "permissive"])
                        resultsTable = html.find('div', attrs = {'id' : 'torrent-table-wrapper'})

                        if not resultsTable:
                            logger.log(u"The Data returned from " + self.name + " do not contains any torrent", logger.DEBUG)
                            continue

                        # Collecting entries
                        entries_std = html.find_all('div' , attrs = {'id' : 'torrent-std'})
                        entries_sticky = html.find_all('div' , attrs = {'id' : 'torrent-sticky'})
                        
                        entries = entries_std + entries_sticky

                        #Xirg STANDARD TORRENTS
                        #Continue only if one Release is found
                        if len(entries) > 0:

                            for result in entries:
    
                                try:
                                    torrentName = ((result.find('div', attrs = {'id' :'torrent-udgivelse2-users'})).find('a'))['title']
                                    torrentId = (((result.find('div', attrs = {'id' :'torrent-download'})).find('a'))['href']).replace('download.php?id=','')
                                    torrent_name = str(torrentName)
                                    torrent_download_url = (self.urls['download'] % torrentId).encode('utf8')
                                    torrent_details_url = (self.urls['detail'] % torrentId).encode('utf8')
                                    #torrent_seeders = int(result.find('div', attrs = {'id' : 'torrent-seeders'}).find('a')['class'][0])
                                    ## Not used, perhaps in the future ##
                                    #torrent_id = int(torrent['href'].replace('/details.php?id=', ''))
                                    #torrent_leechers = int(result.find('td', attrs = {'class' : 'ac t_leechers'}).string)
                                except (AttributeError, TypeError):
                                    continue
    
                                # Filter unseeded torrent and torrents with no name/url
                                #if mode != 'RSS' and torrent_seeders == 0:
                                #    continue
    
                                if not torrent_name or not torrent_download_url:
                                    continue
    
                                item = torrent_name, torrent_download_url
                                logger.log(u"Found result: " + torrent_name + " (" + torrent_details_url + ")", logger.DEBUG)
                                items[mode].append(item)
                        
                        else:
                            logger.log(u"The Data returned from " + self.name + " do not contains any torrent", logger.WARNING)
                            continue


                    except Exception, e:
                        logger.log(u"Failed parsing " + self.name + " Traceback: " + traceback.format_exc(), logger.ERROR)

            results += items[mode]

        return results

    def _get_title_and_url(self, item):

        title, url = item

        if url:
            url = str(url).replace('&amp;', '&')

        return title, url

    def getURL(self, url, headers=None):

        if not self.session:
            self._doLogin()

        if not headers:
            headers = []

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


class NextGenCache(tvcache.TVCache):
    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # Only poll NextGen every 10 minutes max
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


provider = NextGenProvider()
