# Author: Mr_Orange <mr_orange@hotmail.it>
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

import sys
import os
import traceback
import urllib, urllib2
import re
import datetime

import sickbeard
import generic
from sickbeard.common import Quality, Overview
from sickbeard.name_parser.parser import NameParser, InvalidNameException
from sickbeard import logger
from sickbeard import tvcache
from sickbeard import helpers
from sickbeard import db
from sickbeard import classes
from sickbeard.show_name_helpers import allPossibleShowNames, sanitizeSceneName
from sickbeard.exceptions import ex
from sickbeard import encodingKludge as ek
from sickbeard import clients

from lib import requests
from bs4 import BeautifulSoup
from lib.unidecode import unidecode

class PublicHDProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "PublicHD")

        self.supportsBacklog = True

        self.cache = PublicHDCache(self)

        self.url = 'https://publichd.se/'

        self.searchurl = self.url + 'index.php?page=torrents&search=%s&active=0&category=%s&order=5&by=2'  #order by seed

        self.categories = {'Season': ['23'], 'Episode': ['7', '14', '24'], 'RSS': ['7', '14', '23', '24']}

    def isEnabled(self):
        return sickbeard.PUBLICHD

    def imageName(self):
        return 'publichd.png'

    def getQuality(self, item):

        quality = Quality.sceneQuality(item[0])
        return quality

    def _get_season_search_strings(self, show, season=None):

        search_string = {'Episode': []}

        if not show:
            return []

        self.show = show
        seasonEp = show.getAllEpisodes(season)

        wantedEp = [x for x in seasonEp if show.getOverview(x.status) in (Overview.WANTED, Overview.QUAL)]

        #If Every episode in Season is a wanted Episode then search for Season first
        if wantedEp == seasonEp and not show.air_by_date:
            search_string = {'Season': [], 'Episode': []}
            for show_name in set(allPossibleShowNames(show)):
                ep_string = show_name +' S%02d' % int(season)  #1) ShowName SXX -SXXE
                search_string['Season'].append(ep_string)

                ep_string = show_name+' Season '  + str(season) #2) ShowName Season X
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

        self.show = ep_obj.show

        if ep_obj.show.air_by_date:
            for show_name in set(allPossibleShowNames(ep_obj.show)):
                ep_string = sanitizeSceneName(show_name) +' '+ str(ep_obj.airdate)
                search_string['Episode'].append(ep_string)
        else:
            for show_name in set(allPossibleShowNames(ep_obj.show)):
                ep_string = sanitizeSceneName(show_name) + ' ' + \
                sickbeard.config.naming_ep_type[2] % {'seasonnumber': ep_obj.season, 'episodenumber': ep_obj.episode}
                
                for x in add_string.split('|'):
                    to_search = re.sub('\s+', ' ', ep_string + ' %s' %x)
                    search_string['Episode'].append(to_search)

        return [search_string]

    def _doSearch(self, search_params):

        results = []
        items = {'Season': [], 'Episode': [], 'RSS': []}

        for mode in search_params.keys():
            for search_string in search_params[mode]:

                if mode == 'RSS':
                    searchURL = self.url + 'index.php?page=torrents&active=1&category=%s' %(';'.join(self.categories[mode]))
                    logger.log(u"PublicHD cache update URL: "+ searchURL, logger.DEBUG)
                else:
                    searchURL = self.searchurl %(urllib.quote(unidecode(search_string)), ';'.join(self.categories[mode]))
                    logger.log(u"Search string: " + searchURL, logger.DEBUG)

                html = self.getURL(searchURL)
                if not html:
                    continue

                try:
                    soup = BeautifulSoup(html, features=["html5lib", "permissive"])

                    torrent_table = soup.find('table', attrs = {'id' : 'torrbg'})
                    torrent_rows = torrent_table.find_all('tr') if torrent_table else []

                    #Continue only if one Release is found
                    if len(torrent_rows)<2:
                        logger.log(u"The Data returned from " + self.name + " do not contains any torrent", logger.DEBUG)
                        continue

                    for tr in torrent_rows[1:]:

                        try:
                            link = self.url + tr.find(href=re.compile('page=torrent-details'))['href']
                            title = tr.find(lambda x: x.has_attr('title')).text.replace('_','.')
                            url = tr.find(href=re.compile('magnet+'))['href']
                            seeders = int(tr.find_all('td', {'class': 'header'})[4].text)
                            leechers = int(tr.find_all('td', {'class': 'header'})[5].text)
                        except (AttributeError, TypeError):
                            continue

                        if mode != 'RSS' and seeders == 0:
                            continue

                        if not title or not url:
                            continue

                        item = title, url, link, seeders, leechers

                        items[mode].append(item)

                except Exception, e:
                    logger.log(u"Failed to parsing " + self.name + " Traceback: "  + traceback.format_exc(), logger.ERROR)

            #For each search mode sort all the items by seeders
            items[mode].sort(key=lambda tup: tup[3], reverse=True)

            results += items[mode]

        return results

    def _get_title_and_url(self, item):

        title, url, id, seeders, leechers = item

        if url:
            url = url.replace('&amp;','&')

        return (title, url)

    def getURL(self, url, headers=None):

        try:
            r = requests.get(url, verify=False)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
            logger.log(u"Error loading "+self.name+" URL: " + str(sys.exc_info()) + " - " + ex(e), logger.ERROR)
            return None

        if r.status_code != 200:
            logger.log(self.name + u" page requested with url " + url +" returned status code is " + str(r.status_code) + ': ' + clients.http_error_code[r.status_code], logger.WARNING)
            return None

        return r.content

    def downloadResult(self, result):
        """
        Save the result to disk.
        """

        torrent_hash = re.findall('urn:btih:([\w]{32,40})', result.url)[0].upper()

        if not torrent_hash:
           logger.log("Unable to extract torrent hash from link: " + ex(result.url), logger.ERROR)
           return False

        try:
            r = requests.get('http://torcache.net/torrent/' + torrent_hash + '.torrent')
        except Exception, e:
            logger.log("Unable to connect to Torcache: " + ex(e), logger.ERROR)
            return False

        if not r.status_code == 200:
            return False

        magnetFileName = ek.ek(os.path.join, sickbeard.TORRENT_DIR, helpers.sanitizeFileName(result.name) + '.' + self.providerType)
        magnetFileContent = r.content

        try:
            fileOut = open(magnetFileName, 'wb')
            fileOut.write(magnetFileContent)
            fileOut.close()
            helpers.chmodAsParent(magnetFileName)
        except IOError, e:
            logger.log("Unable to save the file: " + ex(e), logger.ERROR)
            return False
        logger.log(u"Saved magnet link to " + magnetFileName + " ", logger.MESSAGE)
        return True

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


class PublicHDCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll ThePirateBay every 10 minutes max
        self.minTime = 20

    def updateCache(self):

        if not self.shouldUpdate():
            return

        search_params = {'RSS': ['rss']}
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

provider = PublicHDProvider()
