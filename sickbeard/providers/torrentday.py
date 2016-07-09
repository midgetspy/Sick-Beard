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
import json
import urllib
import generic
import datetime
import sickbeard
import exceptions

from lib import requests
from xml.sax.saxutils import escape

from sickbeard import db
from sickbeard import logger
from sickbeard import tvcache
from sickbeard.exceptions import ex
from sickbeard.common import Quality
from sickbeard.common import Overview
from sickbeard import show_name_helpers



class TorrentDayProvider(generic.TorrentProvider):

    ###################################################################################################
    def __init__(self):
        generic.TorrentProvider.__init__(self, "TorrentDay")
        self.cache = TorrentDayCache(self)
        self.name = "TorrentDay"
        self.rss_passkey = None
        self.rss_uid = None
        self.session = None
        self.supportsBacklog = True
        self.url = 'https://www.torrentday.com/'
        self.funcName = lambda n=0: sys._getframe(n + 1).f_code.co_name + "()"
        logger.log('[' + self.name + '] initializing...')
        

    ###################################################################################################

    def isEnabled(self):
        return sickbeard.TORRENTDAY

    ###################################################################################################

    def imageName(self):
        return 'torrentday.png'

    ###################################################################################################

    def getQuality(self, item):
        quality = Quality.nameQuality(item[0])
        return quality

    ###################################################################################################

    def _get_title_and_url(self, item):
        return item

    ###################################################################################################

    def _get_airbydate_season_range(self, season):
        if season is None:
            return ()
        year, month = map(int, season.split('-'))
        min_date = datetime.date(year, month, 1)
        if month == 12:
            max_date = datetime.date(year, month, 31)
        else:
            max_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        return (min_date, max_date)

    ###################################################################################################

    def _get_season_search_strings(self, show, season=None):
        search_string = []

        if not show:
            return []

        myDB = db.DBConnection()

        if show.air_by_date:
            (min_date, max_date) = self._get_airbydate_season_range(season)
            sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND airdate >= ? AND airdate <= ?", [show.tvdbid, min_date.toordinal(), max_date.toordinal()])
        else:
            sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND season = ?", [show.tvdbid, season])

        for sqlEp in sqlResults:
            if show.getOverview(int(sqlEp["status"])) in (Overview.WANTED, Overview.QUAL):
                if show.air_by_date:
                    for show_name in set(show_name_helpers.allPossibleShowNames(show)):
                        ep_string = show_name_helpers.sanitizeSceneName(show_name) + ' ' + str(datetime.date.fromordinal(sqlEp["airdate"])).replace('-', '.')
                        search_string.append(ep_string)
                else:
                    for show_name in set(show_name_helpers.allPossibleShowNames(show)):
                        ep_string = show_name_helpers.sanitizeSceneName(show_name) + ' ' + sickbeard.config.naming_ep_type[2] % {'seasonnumber': season, 'episodenumber': int(sqlEp["episode"])}
                        search_string.append(ep_string)
        return search_string

    ###################################################################################################

    def _get_episode_search_strings(self, ep_obj):
        search_string = []

        if not ep_obj:
            return []
        if ep_obj.show.air_by_date:
            for show_name in set(show_name_helpers.allPossibleShowNames(ep_obj.show)):
                ep_string = show_name_helpers.sanitizeSceneName(show_name) + ' ' + str(ep_obj.airdate).replace('-', '.')
                search_string.append(ep_string)
        else:
            for show_name in set(show_name_helpers.allPossibleShowNames(ep_obj.show)):
                ep_string = show_name_helpers.sanitizeSceneName(show_name) + ' ' + sickbeard.config.naming_ep_type[2] % {'seasonnumber': ep_obj.season, 'episodenumber': ep_obj.episode}
                search_string.append(ep_string)
        return search_string

    ###################################################################################################

    def _doSearch(self, search_params, show=None):
        search_params = search_params.replace('.', ' ')
        logger.log("[" + self.name + "] Performing Search For: {0}".format(search_params))
        searchUrl = self.url + "V3/API/API.php"
        PostData = {'/browse.php?': None, 'cata': 'yes', 'jxt': 8, 'jxw': 'b', 'search': search_params, 'c7': 1, 'c14': 1, 'c24': 1, 'c26': 1, 'c33': 1}

        try:
            data = self.getURL(searchUrl, data=PostData)
            jdata = json.loads(data)
            if jdata.get('Fs', [])[0].get('Fn', {}) == "Oarrive":
                logger.log("[" + self.name + "] " + self.funcName() + " search data sent 0 results.")
                return []
            torrents = jdata.get('Fs', [])[0].get('Cn', {}).get('torrents', [])
        except ValueError, e:
            logger.log("[" + self.name + "] " + self.funcName() + " invalid json returned.")
            return []

        return self.parseResults(torrents)

    ###################################################################################################

    def parseResults(self, torrents):
        results = []

        for torrent in torrents:
            item = (torrent['name'].replace('.', ' '), self.url + "download.php/" + str(torrent['id']) + "/" + torrent['fname'] + "?torrent_pass=" + self.rss_passkey)
            results.append(item)
            logger.log("[" + self.name + "] " + self.funcName() + " Title: " + torrent['name'], logger.DEBUG)

        if len(results):
            logger.log("[" + self.name + "] " + self.funcName() + " Some results found.")
        else:
            logger.log("[" + self.name + "] " + self.funcName() + " No results found.")

        return results

    ###################################################################################################
    
    def checkAuth(self,response):
        if "www.torrentday.com/login.php" in response.url:
            logger.log("[" + self.name + "] " + self.funcName() + " Error: We no longer appear to be authenticated. Aborting..",logger.ERROR)
            sys.tracebacklimit=0 # raise exception to sickbeard but hide the stack trace.
            raise Exception("[" + self.name + "] " + self.funcName() + " Error: We no longer appear to be authenticated. Aborting..")
    
    ###################################################################################################
    
    def checkAuthCookies(self):
        cookies = { 'PHPSESSID': sickbeard.TORRENTDAY_PHPSESSID, 'uid': sickbeard.TORRENTDAY_UID, 'pass': sickbeard.TORRENTDAY_PASS }
        for cookie_name in cookies:
            if cookie_name in requests.utils.dict_from_cookiejar(self.session.cookies):
                if requests.utils.dict_from_cookiejar(self.session.cookies)[cookie_name] != cookies[cookie_name]:
                    logger.log("[" + self.name + "] " + self.funcName() + " Updating Cookie " + cookie_name + " from " + requests.utils.dict_from_cookiejar(self.session.cookies)[cookie_name] + " to " + cookies[cookie_name], logger.DEBUG)
                    self.session.cookies.set(cookie_name,cookies[cookie_name])
            else:
                logger.log("[" + self.name + "] " + self.funcName() + " Adding Cookie " + cookie_name + " with value of " + cookies[cookie_name], logger.DEBUG)
                self.session.cookies.set(cookie_name,cookies[cookie_name])
        
    ###################################################################################################
    
    def getURL(self, url, headers=None, data=None):
        response = None

        if not self.session:
            if not self._doLogin():
                return response
        else:
            self.checkAuthCookies()
        
        if not headers:
            headers = []
        try:
            if "/t.rss" in url:
                response = self.session.get(url, verify=False)
            else:
                response = self.session.post(url, verify=False, data=data)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
            logger.log("[" + self.name + "] " + self.funcName() + " Error loading " + self.name + " URL: " + ex(e), logger.ERROR)
            return None

        self.checkAuth(response)
        
        if response.status_code not in [200, 302, 303]:
            logger.log("[" + self.name + "] " + self.funcName() + " requested URL - " + url + " returned status code is " + str(response.status_code), logger.ERROR)
            return None

        return response.content

    ###################################################################################################

    def _getPassKey(self):
        logger.log("[" + self.name + "] _getPassKey() Attempting to acquire RSS info")
        try:
            self.rss_uid, self.rss_passkey = re.findall(r'u=(.*);tp=([0-9A-Fa-f]{32})', self.getURL(self.url + "rss.php", data={'cat[]': '26', 'feed': 'direct', 'login': 'passkey'}))[0]
        except:
            logger.log("[" + self.name + "] " + self.funcName() + " Failed to scrape authentication parameters for rss.",logger.ERROR)
            return False
                    
        if self.rss_uid == None:
            logger.log("[" + self.name + "] " + self.funcName() + " Can't extract uid from rss authentication scrape.",logger.ERROR)
            return False
        
        if self.rss_passkey == None:
            logger.log("[" + self.name + "] " + self.funcName() + " Can't extract password hash from rss authentication scrape.",logger.ERROR)
            return False
            
        logger.log("[" + self.name + "] " + self.funcName() + " rss_uid = " + self.rss_uid + ", rss_passkey = " + self.rss_passkey,logger.DEBUG)
        return True

    ###################################################################################################

    def _doLogin(self):
        self.session = requests.Session()        
        self.checkAuthCookies()

        if not self._getPassKey() or not self.rss_uid or not self.rss_passkey:
            raise Exception("[" + self.name + "] " + self.funcName() + " Could not extract rss uid/passkey... aborting.")
        
        return True

    ###################################################################################################

class TorrentDayCache(tvcache.TVCache):

    ###################################################################################################

    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        self.minTime = 15

    ###################################################################################################

    def _getRSSData(self):
        if not provider.session:
            provider._doLogin()

        self.rss_url = provider.url + "t.rss?download;7;14;24;26;33;u=" + provider.rss_uid + ";tp=" + provider.rss_passkey
        logger.log("[" + provider.name + "] " + provider.funcName() + " RSS URL - " + self.rss_url)
        xml = provider.getURL(self.rss_url)
        if xml is not None:
            xml = xml.decode('utf8', 'ignore')
        else:
            logger.log("[" + provider.name + "] " + provider.funcName() + " empty RSS data received.", logger.ERROR)
            xml = "<rss xmlns:atom=\"http://www.w3.org/2005/Atom\" version=\"2.0\">" + \
                "<channel>" + \
                "<title>" + provider.name + "</title>" + \
                "<link>" + provider.url + "</link>" + \
                "<description>torrent search</description>" + \
                "<language>en-us</language>" + \
                "<atom:link href=\"" + provider.url + "\" rel=\"self\" type=\"application/rss+xml\"/>" + \
                "</channel></rss>"
        return xml

    ###################################################################################################

provider = TorrentDayProvider()
