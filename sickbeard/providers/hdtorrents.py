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

class HDTorrentsProvider(generic.TorrentProvider):

    urls = {'base_url' : 'https://hdts.ru/index.php',
            'login' : 'https://hdts.ru/login.php',
            'detail' : 'https://www.hdts.ru/details.php?id=%s',
            'search' : 'https://hdts.ru/torrents.php?search=%s&active=1&options=0%s',
            'home' : 'https://www.hdts.ru/%s'
            }

    def __init__(self):

        generic.TorrentProvider.__init__(self, "HDTorrents")

        self.supportsBacklog = True

        self.cache = HDTorrentsCache(self)

        self.url = self.urls['base_url']

        self.categories = "&category[]=59&category[]=60&category[]=30&category[]=38"

        self.session = requests.Session()

        self.cookies = None

    def isEnabled(self):
        return sickbeard.HDTORRENTS

    def imageName(self):
        return 'hdtorrents.png'

    def getQuality(self, item):

        quality = Quality.sceneQuality(item[0])
        return quality

    def _doLogin(self):

        if any(requests.utils.dict_from_cookiejar(self.session.cookies).values()):
            return True

        if sickbeard.HDTORRENTS_UID and sickbeard.HDTORRENTS_HASH:

            requests.utils.add_dict_to_cookiejar(self.session.cookies, self.cookies)

        else:

            login_params = {'uid': sickbeard.HDTORRENTS_USERNAME,
                            'pwd': sickbeard.HDTORRENTS_PASSWORD,
                            'submit': 'Confirm',
                            }

            try:
                response = self.session.post(self.urls['login'],  data=login_params, timeout=30)
            except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
                logger.log(u'Unable to connect to ' + self.name + ' provider: ' + ex(e), logger.ERROR)
                return False

            if re.search('You need cookies enabled to log in.', response.text) \
            or response.status_code == 401:
                logger.log(u'Invalid username or password for ' + self.name + ' Check your settings', logger.ERROR)
                return False

            sickbeard.HDTORRENTS_UID = requests.utils.dict_from_cookiejar(self.session.cookies)['uid']
            sickbeard.HDTORRENTS_HASH = requests.utils.dict_from_cookiejar(self.session.cookies)['pass']

            self.cookies = {'uid': sickbeard.HDTORRENTS_UID,
                            'pass': sickbeard.HDTORRENTS_HASH
                            }

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

                if search_string == '':
                    continue
                search_string = str(search_string).replace('.',' ')
                searchURL = self.urls['search'] % (search_string, self.categories)

                logger.log(u"Search string: " + searchURL, logger.DEBUG)

                data = self.getURL(searchURL)
                if not data:
                    continue

                # Remove HDTorrents NEW list
                split_data = data.partition('<!-- Show New Torrents After Last Visit -->\n\n\n\n')
                data = split_data[2]

                try:
                    html = BeautifulSoup(data, features=["html5lib", "permissive"])

                    #Get first entry in table
                    entries = html.find_all('td', attrs={'align' : 'center'})

                    if len(entries) < 22:
                        logger.log(u"The Data returned from " + self.name + " do not contains any torrent", logger.DEBUG)
                        continue

                    try:
                        title = entries[22].find('a')['title'].replace('History - ', '').replace('Blu-ray', 'bd50')
                        url = self.urls['home'] % entries[15].find('a')['href']
                        download_url = self.urls['home'] % entries[15].find('a')['href']
                        id = entries[23].find('div')['id']
                        seeders = int(entries[20].get_text())
                        leechers = int(entries[21].get_text())
                    except (AttributeError, TypeError):
                        continue

                    if mode != 'RSS' and seeders == 0:
                            continue

                    if not title or not download_url:
                            continue

                    item = title, download_url, id, seeders, leechers
                    logger.log(u"Found result: " + title + "(" + searchURL + ")", logger.DEBUG)

                    items[mode].append(item)

                    #Now attempt to get any others
                    result_table = html.find('table', attrs = {'class' : 'mainblockcontenttt'})

                    if not result_table:
                        continue

                    entries = result_table.find_all('td', attrs={'align' : 'center', 'class' : 'listas'})

                    if not entries:
                        continue

                    for result in entries:

                        try:
                            cells = result.find_parent('tr').find_next_sibling('tr').find_all('td')
                            title = cells[2].find('b').get_text().strip('\t ').replace('Blu-ray', 'bd50')
                            url = self.urls['home'] % cells[4].find('a')['href']
                            download_url = self.urls['home'] % cells[4].find('a')['href']
                            detail = cells[2].find('a')['href']
                            id = detail.replace('details.php?id=', '')
                            seeders = int(cells[9].get_text())
                            leechers = int(cells[10].get_text())
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
            headers = []

        try:
            response = self.session.get(url, verify=False)
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


class HDTorrentsCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll HDTorrents every 10 minutes max
        self.minTime = 20

    def updateCache(self):

        if not self.shouldUpdate():
            return

        search_params = {'RSS': []}
        rss_results = self.provider._doSearch(search_params)

        if rss_results:
            self.setLastUpdate()
        else:
            return []

        logger.log(u"Clearing " + self.provider.name + " cache and updating with new information")
        self._clearCache()

        ql = []
        for result in rss_results:
            ci = self._parseItem(result)
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

provider = HDTorrentsProvider()
