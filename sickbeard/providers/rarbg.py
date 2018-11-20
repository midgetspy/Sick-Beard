###########################################################################
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
###########################################################################

import json
import sys
import time
import urllib
import generic
import sickbeard
import exceptions


from lib import requests
from datetime import datetime, timedelta
from xml.sax.saxutils import escape

from sickbeard import db
from sickbeard import logger
from sickbeard import tvcache
from sickbeard.exceptions import ex
from sickbeard.common import Quality
from sickbeard.common import Overview
from sickbeard import show_name_helpers

###########################################################################


class RarbgProvider(
    generic.TorrentProvider
):

    ###########################################################################

    def __init__(self):
        generic.TorrentProvider.__init__(self, "Rarbg")
        self.cache = RarbgCache(self)
        self.name = "Rarbg"
        self.session = None
        self.token = {}
        self.supportsBacklog = True
        self.url = 'https://torrentapi.org/pubapi_v2.php'
        self.funcName = lambda n=0: sys._getframe(n + 1).f_code.co_name + "()"
        logger.log(
            "[{0}] initializing...".format(
                self.name
            )
        )

    ###########################################################################

    def isEnabled(self):
        return sickbeard.RARBG

    ###########################################################################

    def imageName(self):
        return 'rarbg.png'

    ###########################################################################

    def getQuality(self, item):
        quality = Quality.nameQuality(item[0])
        return quality

    ###########################################################################

    def _get_title_and_url(self, item):
        return item

    ###########################################################################

    def _get_airbydate_season_range(self, season):
        if season is None:
            return ()
        year, month = map(int, season.split('-'))
        min_date = datetime.date(year, month, 1)
        if month == 12:
            max_date = datetime.date(year, month, 31)
        else:
            max_date = datetime.date(
                year,
                month + 1,
                1
            ) - datetime.timedelta(days=1)
        return (min_date, max_date)

    ###########################################################################

    def _get_season_search_strings(self, show, season=None):
        search_string = []

        if not show:
            return []

        myDB = db.DBConnection()

        if show.air_by_date:
            (min_date, max_date) = self._get_airbydate_season_range(season)
            sqlResults = myDB.select(
                "SELECT * FROM tv_episodes WHERE showid = ? AND airdate >= ? AND airdate <= ?",
                [
                    show.tvdbid,
                    min_date.toordinal(),
                    max_date.toordinal()
                ]
            )
        else:
            sqlResults = myDB.select(
                "SELECT * FROM tv_episodes WHERE showid = ? AND season = ?",
                [
                    show.tvdbid,
                    season
                ]
            )

        for sqlEp in sqlResults:
            if show.getOverview(int(sqlEp["status"])) in (
                Overview.WANTED,
                Overview.QUAL
            ):
                if show.air_by_date:
                    for show_name in set(show_name_helpers.allPossibleShowNames(show)):
                        search_string.append(
                            "{0} {1}".format(
                                show_name_helpers.sanitizeSceneName(show_name),
                                str(datetime.date.fromordinal(sqlEp["airdate"])).replace('-', '.')
                            )
                        )
                else:
                    for show_name in set(show_name_helpers.allPossibleShowNames(show)):
                        search_string.append(
                            "{0} {1}".format(
                                show_name_helpers.sanitizeSceneName(show_name),
                                sickbeard.config.naming_ep_type[2] % {
                                    'seasonnumber': season,
                                    'episodenumber': int(sqlEp["episode"])
                                }
                            )
                        )
        return search_string

    ###########################################################################

    def _get_episode_search_strings(self, ep_obj):
        search_string = []

        if not ep_obj:
            return []

        if ep_obj.show.air_by_date:
            for show_name in set(show_name_helpers.allPossibleShowNames(ep_obj.show)):
                search_string.append(
                    "{0} {1}".format(
                        show_name_helpers.sanitizeSceneName(show_name),
                        str(ep_obj.airdate).replace('-', '.')
                    )
                )
        else:
            for show_name in set(show_name_helpers.allPossibleShowNames(ep_obj.show)):
                search_string.append(
                    "{0} {1}".format(
                        show_name_helpers.sanitizeSceneName(show_name),
                        sickbeard.config.naming_ep_type[2] % {
                            'seasonnumber': ep_obj.season,
                            'episodenumber':  ep_obj.episode
                        }
                    )
                )
        return search_string

    ###########################################################################

    def _doSearch(self, search_params, show=None):
        payload = {
            "app_id": "sickbeard-torrentProviders",
            "category": "tv",
            "min_seeders": 1,
            "min_leechers": 0,
            "limit": 100,
            "format": "json_extended",
            "token": self.token.get('token'),
            "search_string": search_params,
            "mode": "search"
        }

        if not search_params:
            payload['mode'] = 'list'
        
        response = self.getURL(
            self.url,
            data=payload
        )

        # Retry if there was an invalid token response.
        if response.get('error_code') == 4:
            time.sleep(20)
            response = self.getURL(
                self.url,
                data=payload
            )

        if response and response.get('torrent_results'):
            torrents = []
            for torrent in response.get('torrent_results'):
                torrents.append(
                    (
                        torrent.get('title'),
                        torrent.get('download')
                    )
                )

            logger.log(
                "[{0}] {1} Found {2} entries.".format(
                    self.name,
                    self.funcName(),
                    len(torrents),
                )
            )

            return torrents

        return []

    ###########################################################################

    def getURL(self, url, headers=[], data={}):
        if not self._doLogin():
            return {}

        if not data.get('token'):
            data['token'] = self.token.get('token')

        if self.token.get('last_request') >= int(time.time()):
            time.sleep(self.token.get('last_request') - int(time.time()))

        try:
            self.token['last_request'] = int(time.time())+5
            response = self.session.get(url, params=data, verify=False)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
            logger.log(
                "[{0}] {1} Error loading URL: {2}, with params: {3}, Error: {4}".format(
                    self.name,
                    self.funcName(),
                    self.url,
                    data,
                    e
                ),
                logger.ERROR
            )
            return {}

        if response.status_code not in [200, 302, 303]:
            if response.status_code == 429:
                logger.log(
                    "[{0}] {1} requested URL: {2}, with params: {3}, returned status code is {4}, with a Retry-After of {5}".format(
                        self.name,
                        self.funcName(),
                        self.url,
                        data,
                        response.status_code,
                        response.headers.get('Retry-After')
                    ),
                    logger.ERROR
                )
            else:
                logger.log(
                    "[{0}] {1} requested URL: {2}, with params: {3}, returned status code is {4}".format(
                        self.name,
                        self.funcName(),
                        self.url,
                        data,
                        response.status_code
                    ),
                    logger.ERROR
                )
            return {}

        try:
            if response.json().get('error') and response.json().get('error_code') != 20:
                # error_code 4, Invalid token. Use get_token for a new one!
                if response.json().get('error_code') == 4:
                    logger.log(
                        "[{0}] {1} Invalid token response returned, {2}".format(
                            self.name,
                            self.funcName(),
                            response.json().get('error'),
                        ),
                        logger.WARNING
                    )
                    self.token = {}
                    return response.json()
                
                logger.log(
                    "[{0}] {1} requested URL: {2}, with params: {3}, returned error code #{4} / {5}".format(
                        self.name,
                        self.funcName(),
                        self.url,
                        data,
                        response.json().get('error_code'),
                        response.json().get('error'),
                    ),
                    logger.ERROR
                )
                return {}
        except ValueError:
            logger.log(
                "[{0}] {1} Can't get json payload from {2} with params {3}.".format(
                    self.name,
                    self.funcName(),
                    self.url,
                    data
                ),
                logger.ERROR
            )
            return {}

        return response.json()


    ###########################################################################

    def _isValidToken(self):
        if all([self.token.get('token'), self.token.get('token_expires')]) and datetime.now() < self.token.get('token_expires'):
            return True
        return False

    ###########################################################################

    def _doLogin(self):
        if not self.session:
            self.session = requests.Session()

        if self._isValidToken():
            return True

        response = self.session.get(
            self.url,
            params={
                'app_id': 'sickbeard-torrentProviders',
                'get_token': 'get_token',
                'format': 'json'
            },
            verify=False,
            timeout=30
        )

        if response.status_code not in [200, 302, 303]:
            logger.log(
                "[{0}] {1} requested URL: {2} , requesting token, returned status code {3}".format(
                    self.name,
                    self.funcName(),
                    self.url,
                    response.status_code
                ),
                logger.ERROR
            )
            return False

        try:
            self.token = {
                'token': response.json().get('token'),
                'token_expires': datetime.now() + timedelta(minutes=10),
                'last_request': int(time.time())+5
            }
        except ValueError:
            logger.log(
                "[{0}] {1} Can't get token from {2}.".format(
                    self.name,
                    self.funcName(),
                    self.url
                ),
                logger.ERROR
            )
            return False

        return True

    ###########################################################################

class RarbgCache(tvcache.TVCache):

    ###########################################################################

    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        self.minTime = 15

    ###########################################################################

    def _getRSSData(self):
        xml = "<rss xmlns:atom=\"http://www.w3.org/2005/Atom\" version=\"2.0\">" + \
            "<channel>" + \
            "<title>" + provider.name + "</title>" + \
            "<link>" + provider.url + "</link>" + \
            "<description>torrent search</description>" + \
            "<language>en-us</language>" + \
            "<atom:link href=\"" + provider.url + "\" rel=\"self\" type=\"application/rss+xml\"/>"

        search_ret = provider._doSearch("")
        if search_ret:
            for title, url in search_ret:
                xml += "<item>" + "<title>" + escape(title) + "</title>" +  "<link>"+ urllib.quote(url, '/,:') + "</link>" + "</item>"

        xml += "</channel> </rss>"
        return xml

    ###########################################################################

provider = RarbgProvider()
