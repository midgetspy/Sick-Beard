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

import re
import sys
import urllib
import generic
import datetime
import sickbeard

from lib import requests

from sickbeard import db
from sickbeard import logger
from sickbeard import tvcache
from sickbeard.common import Quality
from sickbeard.common import Overview
from sickbeard import show_name_helpers

class SpeedProvider(generic.TorrentProvider):
    ###################################################################################################
    def __init__(self):
        generic.TorrentProvider.__init__(self, "Speed")
        self.cache = SpeedCache(self)
        self.funcName = lambda n=0: sys._getframe(n + 1).f_code.co_name + "()"
        self.name = "Speed"
        self.remove_tags = re.compile(r'<[^>]+>')
        self.rss_passkey = None
        self.rss_uid = None
        self.session = None
        self.supportsBacklog = True
        self.url = 'https://speed.cd/'
        logger.log("[" + self.name + "] initializing...")

    ###################################################################################################

    def isEnabled(self):
        return sickbeard.SPEED

    ###################################################################################################

    def imageName(self):
        return 'speed.png'

    ###################################################################################################

    def getQuality(self, item):
        quality = Quality.nameQuality(item[0])
        return quality

    ###################################################################################################

    def _get_title_and_url(self, item):
        return item

    ###################################################################################################

    def _get_airbydate_season_range(self, season=None):
        if season is None:
            return ()
        year, month = map(int, season.split('-'))
        min_date = datetime.date(year, month, 1)
        if month == 12:
            max_date = datetime.date(year, month, 31)
        else:
            max_date = datetime.date(year, month+1, 1) - datetime.timedelta(days=1)

        return (min_date, max_date)

    ###################################################################################################

    def _get_season_search_strings(self, show, season=None):
        search_string = []

        if not show:
            return []

        myDB = db.DBConnection()

        if show.air_by_date:
            (min_date, max_date) = self._get_airbydate_season_range(season)
            sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND airdate >= ? AND airdate <= ?", [show.tvdbid,  min_date.toordinal(), max_date.toordinal()])
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
        logger.log("[{}] {} Performing Search: {}".format(self.name, self.funcName(), search_params), logger.DEBUG)
        data = self.getURL(
            '{}browse.php'.format(self.url),
            params={
                'c': [2,30,41,49,52,55],
                'search': search_params
            }
        )
        return self.parseResults(data)

    ###################################################################################################

    def parseResults(self, data):
        results = []
        if data:
            for torrent in re.compile("<div><a href=\"\/t\/(?P<id>\d+)\"><b>(?P<title>.*?)<\/b>.*?<td>(<b>|)(?P<seeds>\d+)(<\/b>|)<\/td><td>(<b>|)(?P<peers>\d+)(<\/b>|)<\/td><\/tr>", re.MULTILINE | re.DOTALL).finditer(data):
                if int(torrent.group('seeds')) > 0:
                    item = (self.remove_tags.sub('', torrent.group('title')), '{}download.php?torrent={}'.format(self.url, torrent.group('id')))
                    results.append(item)
            if len(results):
                logger.log("[{}] {} Some results found.".format(self.name, self.funcName()))
            else:
                logger.log("[{}] {} No results found.".format(self.name, self.funcName()))
        else:
            logger.log("[{}] {} Error no data returned!!".format(self.name, self.funcName()))
        return results

    ###################################################################################################

    def getURL(self, url, params={}):
        response = None

        if not self.session and not self._doLogin():
            return response

        try:
            response = self.session.get(url, params=params, verify=False, timeout=30)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
            logger.log("[{}] {} Error loading {} URL: {}".format(
                    self.name,
                    self.funcName(),
                    self.name,
                    ex(e)
                ),
                logger.ERROR
            )
            return None

        if hasattr(response, 'status_code') and response.status_code not in [200, 302, 303]:
            logger.log("[{}] {} requested URL - {} returned status code is {}".format(
                    self.name,
                    self.funcName(),
                    url,
                    response.status_code
                ),
                logger.ERROR
            )
            return None

        return response.content

    ###################################################################################################

    def _doLogin(self):
        login_params = {
            'username': sickbeard.SPEED_USERNAME,
            'password': sickbeard.SPEED_PASSWORD
        }

        self.session = requests.Session()
        logger.log("[{}] Attempting to Login".format(self.name))

        try:
            response = self.session.post("{}takelogin.php".format(self.url), data=login_params, timeout=30, verify=False)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
            logger.log("[{}] {} Error loading {} URL: {}".format(
                    self.name,
                    self.funcName(),
                    self.name,
                    ex(e)
                ),
                logger.ERROR
            )

        if "No page exists at your destination address" in response.content:
            self.session = None
            sys.tracebacklimit = 0    # raise exception to sickbeard but hide the stack trace.
            raise Exception("[" + self.name + "] Login attempt returned 404 page.")

        if "We could not recognize your account properly. Mind if we double check that? It's for your own security." in response.content:
            self.session = None
            sys.tracebacklimit = 0    # raise exception to sickbeard but hide the stack trace.
            logger.log("[{}] {} Login Failed,  Login attempt blocked, You have not logged into website via a browser from this ip address before, please do so to have this ip whitelisted.".format(
                self.name,
                self.funcName()
                ),
                logger.ERROR
            )

        if re.search("Incorrect username or Password|<title>SPEED\.CD \:\: You're home now", response.content) \
        or response.status_code in [401, 403]:
            self.session = None
            logger.log("[{}] {} Login Failed, Invalid username or password for {}. Check your settings.".format(
                    self.name,
                    self.funcName(),
                    self.name
                ),
                logger.ERROR
            )
            return False

        if not self._getPassKey() or not self.rss_passkey:
            self.session = None
            logger.log("[{}] {} Could not extract rssHash info... aborting.".format(
                    self.name,
                    self.funcName()
                ),
                logger.ERROR
            )
            return False
        
        return True

    ###################################################################################################

    def _getPassKey(self):
        logger.log("[{}] {} Attempting to acquire RSS authentication details.".format(
                self.name,
                self.funcName()
            ),
            logger.DEBUG
        )
        try:
            self.rss_uid, self.rss_passkey = re.findall(
                r'name=\"user\" value=\"(.*)\" />.*?name=\"passkey\" value=\"([0-9A-Fa-f]{32})\"',
                self.getURL(
                    '{}rss.php'.format(self.url)
                )
            )[0]
        except:
            logger.log("[{}] {} Failed to scrape authentication parameters for rss.".format(
                    self.name,
                    self.funcName()
                ),
                logger.ERROR
            )
            return False

        if not self.rss_uid:
            logger.log("[{}] {} Can't extract uid from rss authentication scrape.".format(
                    self.name,
                    self.funcName()
                ),
                logger.ERROR
            )
            return False

        if not self.rss_passkey:
            logger.log("[{}] {} Can't extract password hash from rss authentication scrape.".format(
                    self.name,
                    self.funcName()
                ),
                logger.ERROR
            )
            return False

        logger.log("[{}] {} Scraped RSS passkey {}".format(
                self.name,
                self.funcName(),
                self.rss_passkey
            ),
            logger.DEBUG
        )
        return True

    ###################################################################################################

class SpeedCache(tvcache.TVCache):

    ###################################################################################################

    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        self.minTime = 15

    ###################################################################################################

    def _getRSSData(self):
        if not provider.session:
            provider._doLogin()

        xml = None
        if provider.rss_uid and provider.rss_passkey:
            self.rss_url = "{}get_rss.php?cat=2,30,41,49,52,55&feed=dl&user={}&passkey={}".format(provider.url, provider.rss_uid, provider.rss_passkey)
            logger.log("[{}] {} RSS URL - {}".format(provider.name, provider.funcName(), self.rss_url))
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

provider = SpeedProvider()
