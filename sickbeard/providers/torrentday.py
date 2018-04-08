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


class TorrentDayProvider(
    generic.TorrentProvider
):

    ###########################################################################

    def __init__(self):
        generic.TorrentProvider.__init__(self, "TorrentDay")
        self.cache = TorrentDayCache(self)
        self.name = "TorrentDay"
        self.rss_passkey = None
        self.rss_uid = None
        self.session = None
        self.supportsBacklog = True
        self.url = 'https://www.torrentday.com/'
        self.categories = { '7': 1, '14': 1, '24': 1, '26': 1, '33': 1, '34':1 }
        self.funcName = lambda n=0: sys._getframe(n + 1).f_code.co_name + "()"
        logger.log(
            "[{0}] initializing...".format(
                self.name
            )
        )
        
    ###########################################################################

    def isEnabled(self):
        return sickbeard.TORRENTDAY

    ###########################################################################

    def imageName(self):
        return 'torrentday.png'

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
        
        search_params = search_params.replace('.', ' ')
        logger.log(
            "[{0}] {1} Performing Search For: {2}".format(
                self.name,
                self.funcName(),
                search_params
            )
        )
                   
        query = { 'q': search_params }
        query.update(self.categories)

        try:
            jdata = json.loads(
                self.getURL(
                    '{0}/t.json'.format(self.url),
                    data=query
                )
            )
            if not jdata:
                logger.log(
                    "[{0}] {1} search data sent 0 results.".format(
                        self.name,
                        self.funcName(),
                    ),
                    logger.MESSAGE
                )
                return []
            
            torrents = []
            for torrent in jdata:
                if torrent.get('t') and torrent.get('name'):
                    torrents.append(
                        {
                            'id': torrent.get('t'),
                            'name': torrent.get('name')
                        }
                    )
        except ValueError, e:
            logger.log(
                "[{0}] {1} invalid json returned.".format(
                    self.name,
                    self.funcName(),
                ),
                logger.ERROR
            )
            return []

        return self.parseResults(torrents)

    ###########################################################################

    def parseResults(self, torrents):
        results = []

        for torrent in torrents:
            results.append(
                (
                    torrent.get('name').replace('.', ' '),
                    "{0}download.php/{1}/{2}.torrent?torrent_pass={3}".format(
                        self.url,
                        torrent.get('id'),
                        torrent.get('name'),
                        self.rss_passkey
                    )
                )
            )

            logger.log(
                "[{0}] {1} Title: {2}".format(
                    self.name,
                    self.funcName(),
                    torrent.get('name')
                ),
                logger.DEBUG
            )

        if len(results):
            logger.log(
                "[{0}] {1} Some results found.".format(
                    self.name,
                    self.funcName()
                ),
                logger.DEBUG
            )
        else:
            logger.log("[{0}] {1} No results found.".format(
                    self.name,
                    self.funcName()
                ),
                logger.DEBUG
            )

        return results

    ###########################################################################

    def getURL(self, url, headers=[], data=None):
        response = None

        if not self.session or not sickbeard.TORRENTDAY_UID or not sickbeard.TORRENTDAY_PASS:
            if not self._doLogin():
                return response
        try:
            response = self.session.get(url, params=data, verify=False)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
            logger.log(
                "[{0}] {1} Error loading URL: {2}, Error: {3}".format(
                    self.name,
                    self.funcName(),
                    self.url,
                    e
                ),
                logger.ERROR
            )
            return None

        self.checkAuth(response)

        if response.status_code not in [200, 302, 303]:
            logger.log(
                "[{0}] {1} requested URL: {2} returned status code is {3}".format(
                    self.name,
                    self.funcName(),
                    self.url,
                    response.status_code
                ),
                logger.ERROR
            )
            return None

        return response.content

    ###########################################################################

    def _getPassKey(self):
        logger.log(
            "[{0}] {1} Attempting to acquire RSS info".format(
                self.name,
                self.funcName(),
            )
        )

        try:
            self.rss_uid, self.rss_passkey = re.findall(
                r'u=(.*);tp=([0-9A-Fa-f]{32})',
                self.getURL(
                    self.url + "rss.php",
                    data={
                        'cat[]': '26',
                        'feed': 'direct',
                        'login': 'passkey'
                    }
                )
            )[0]
        except:
            logger.log(
                "[{0}] {1} Failed to scrape authentication parameters for rss.".format(
                    self.name,
                    self.funcName(),
                ),
                logger.ERROR
            )
            return False

        if self.rss_uid is None:
            logger.log(
                "[{0}] {1} Can't extract uid from rss authentication scrape.".format(
                    self.name,
                    self.funcName(),
                ),
                logger.ERROR
            )
            return False

        if self.rss_passkey is None:
            logger.log(
                "[{0}] {1} Can't extract password hash from rss authentication scrape.".format(
                    self.name,
                    self.funcName(),
                ),
                logger.ERROR
            )
            return False

        logger.log(
            "[{0}] {1} rss_uid = {2}, rss_passkey = {3}".format(
                self.name,
                self.funcName(),
                self.rss_uid,
                self.rss_passkey
            )
        )

        return True

    ###########################################################################

    def checkAuth(self, response):
        if "www.torrentday.com/login.php" in response.url:
            logger.log(
                "[{0}] {1} Error: We no longer appear to be authenticated. Aborting.".format(
                    self.name,
                    self.funcName()
                ),
                logger.MESSAGE
            )
            # raise exception to sickbeard but hide the stack trace.
            sys.tracebacklimit = 0
            raise Exception(
                "[{0}] {1} Error: We no longer appear to be authenticated. Aborting..".format(
                    self.name,
                    self.funcName()
                )
            )

    ###########################################################################

    def checkAuthCookies(self, cookies={}):
        if not cookies:
            cookies = {
                'uid': sickbeard.TORRENTDAY_UID,
                'pass': sickbeard.TORRENTDAY_PASS
            }

        existing_cookies = requests.utils.dict_from_cookiejar(self.session.cookies)
        for cookie_name in cookies:
            if cookie_name in existing_cookies:
                if existing_cookies.get(cookie_name) != cookies.get(cookie_name):
                    logger.log(
                        "[{0}] {1} Updating Cookie {2} from {3} to {4}".format(
                            self.name,
                            self.funcName(),
                            cookie_name,
                            existing_cookies.get(cookie_name),
                            cookies.get(cookie_name)
                        ),
                        logger.DEBUG
                    )
            else:
                logger.log(
                    "[{0}] {1} Adding Cookie {2} with value of {3}".format(
                        self.name,
                        self.funcName(),
                        cookie_name,
                        cookies.get(cookie_name)
                    ),
                    logger.DEBUG
                )
            self.session.cookies.set(cookie_name, cookies.get(cookie_name))

    ###########################################################################

    def _handleEmailLink(self):
        passcode = None

        logger.log(
            "[{0}] {1} Attempting to extract authentication code from Email link provided.".format(
                self.name,
                self.funcName()
            ),
            logger.DEBUG
        )

        if len(sickbeard.TORRENTDAY_EMAIL_URL) == 32:
            passcode = sickbeard.TORRENTDAY_EMAIL_URL
        else:
            try:
                passcode = re.search(
                    'torrentday\.com\/sign-in\.php\?code=([0-9A-Fa-f]{32})',
                    sickbeard.TORRENTDAY_EMAIL_URL
                ).group(1)
            except AttributeError:
                logger.log(
                    "[{0}] {1} Failed to extract authentication code from Email link, erasing link from config.".format(
                        self.name,
                        self.funcName()
                    ),
                    logger.ERROR
                )
                sickbeard.TORRENTDAY_EMAIL_URL = None
                sickbeard.save_config()
                return False

        if passcode:
            logger.log(
                "[{0}] {1} Extracted pass code, Requesting authentication via Email link.".format(
                    self.name,
                    self.funcName()
                )
            )

            response = self.session.get(
                self.url + '/sign-in.php',
                params={
                    'code': passcode
                },
                verify=False
            )

            if 'sign-in.php' in response.url:
                logger.log(
                    "[{0}] {1} pass code {2}, is not valid, erasing it from the config as not to trigger again.".format(
                        self.name,
                        self.funcName(),
                        passcode
                    )
                )
                sickbeard.TORRENTDAY_EMAIL_URL = None
                sickbeard.save_config()
                return False

            if response.status_code not in [200, 302, 303]:
                logger.log(
                    "[{0}] {1} requested URL: {2}/sign-in.php with pass code {3}, returned status code {4}".format(
                        self.name,
                        self.funcName(),
                        self.url,
                        passcode,
                        response.status_code
                    ),
                    logger.ERROR
                )
                return False

            cookies = requests.utils.dict_from_cookiejar(self.session.cookies)
            if cookies.get('uid') and cookies.get('pass'):
                logger.log(
                    "[{0}] {1} Appears we authenticated with TorrentDay, storing away session for later use.".format(
                        self.name,
                        self.funcName()
                    )
                )
                sickbeard.TORRENTDAY_UID = cookies.get('uid')
                sickbeard.TORRENTDAY_PASS = cookies.get('pass')
                sickbeard.TORRENTDAY_EMAIL_URL = None
                sickbeard.save_config()
                return True

        logger.log(
            "[{0}] {1} Technically we shouldn't be here... yet we are?".format(
                self.name,
                self.funcName()
            ),
            logger.ERROR
        )
        return False

    ###########################################################################

    def _bypassCaptcha(self):
        sitekey = None
        
        sickbeard.TORRENTDAY_UID = None
        sickbeard.TORRENTDAY_PASS = None
        sickbeard.save_config()
        
        from lib.python_anticaptcha import AnticaptchaClient, NoCaptchaTaskProxylessTask, AnticaptchaException

        client = AnticaptchaClient(sickbeard.TORRENTDAY_ANTICAPTCHA_KEY)
        
        logger.log(
            "[{0}] {1} Anti-Captcha.com Balance: {2}".format(
                self.name,
                self.funcName(),
                client.getBalance()
            )
        )

        try:
            ret = self.session.get(self.url + '/login.php', verify=False)
            sitekey = re.search('data-sitekey="(.+?)"', ret.content).group(1)
        except AttributeError:
            logger.log(
                "[{0}] {1} Can't extract sitekey from {2}/login.php.".format(
                    self.name,
                    self.funcName(),
                    self.url
                ),
                logger.ERROR
            )
            return False

        if sitekey is None:
            return False

        logger.log(
            "[{0}] {1} Requesting Anti-Captcha.com Job.".format(
                self.name,
                self.funcName()
            )
        )

        try:
            task = NoCaptchaTaskProxylessTask(self.url + "/login.php", sitekey)
            job = client.createTask(task)
            job.join()
        except AnticaptchaException, e:
            logger.log(
                "[{0}] {1} Error Attempting anti-captcha.com job: {2}".format(
                    self.name,
                    self.funcName(),
                    e
                )
            )
            return False

        logger.log(
            "[{0}] {1} Attempting to authenicate with TorrentDay with response from Anti-Capthca.com, clearing away any old cookies.".format(
                self.name,
                self.funcName()
            )
        )

        self.session.cookies.clear()
        response = self.session.post(
            self.url + "/tak3login.php",
            data={
                'username': sickbeard.TORRENTDAY_USERNAME,
                'password': sickbeard.TORRENTDAY_PASSWORD,
                'g-recaptcha-response': job.get_solution_response()
            }
        )

        self.checkAuth(response)

        if response.status_code not in [200, 302, 303]:
            logger.log("[{0}] {1} requested URL: {2}/tak3login.php, returned status code {3}".format(
                    self.name,
                    self.funcName(),
                    self.url,
                    response.status_code
                ),
                logger.ERROR
            )
            return False

        cookies = requests.utils.dict_from_cookiejar(self.session.cookies)
        if cookies.get('uid') and cookies.get('pass'):
            logger.log(
                "[{0}] {1} Appears we authenicated with TorrentDay, storing away session for later use.".format(
                    self.name,
                    self.funcName()
                )
            )
            sickbeard.TORRENTDAY_UID = cookies.get('uid')
            sickbeard.TORRENTDAY_PASS = cookies.get('pass')
            sickbeard.save_config()
            return True

        return False

    ###########################################################################

    def _doLogin(self):
        if not self.session:
            self.session = requests.Session()

        if sickbeard.TORRENTDAY_EMAIL_URL:
            self._handleEmailLink()

        if sickbeard.TORRENTDAY_UID and sickbeard.TORRENTDAY_PASS:
            self.checkAuthCookies()

        response = self.session.get(self.url + '/browse.php')
        if 'login.php' in response.url:
            if sickbeard.TORRENTDAY_ANTICAPTCHA_KEY and sickbeard.TORRENTDAY_USERNAME and sickbeard.TORRENTDAY_PASSWORD:
                if not self._bypassCaptcha():
                    return False
            else:
                logger.log(
                    "[{0}] {1} Appears we cannot authenicate with TorrentDay.".format(
                        self.name,
                        self.funcName()
                    ),
                    logger.ERROR
                )
                return False

        if not self._getPassKey() or not self.rss_uid or not self.rss_passkey:
            logger.log(
                "[{0}] {1} Could not extract rss uid/passkey... aborting.".format(
                    self.name,
                    self.funcName()
                ),
                logger.ERROR
            )
            return False

        return True

    ###########################################################################


class TorrentDayCache(tvcache.TVCache):

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
                "<atom:link href=\"" + provider.url + "\" rel=\"self\" type=\"application/rss+xml\"/>" + \
                "</channel></rss>"

        if not provider.rss_uid or not provider.rss_passkey:
            if not provider._doLogin():
                return xml

        self.rss_url = "{0}t.rss?download;{1};u={2};tp={3}".format(
            provider.url,
            ';'.join('{0}'.format(
                    key
                ) for key in provider.categories.keys()
            ),
            provider.rss_uid,
            provider.rss_passkey
        )

        logger.log(
            "[{0}] {1} RSS URL: {2}".format(
                provider.name,
                provider.funcName(),
                self.rss_url
            ),
            logger.DEBUG
        )

        provider_xml = provider.getURL(self.rss_url)
        if provider_xml:
            xml = provider_xml.decode('utf8', 'ignore')
        else:
            logger.log(
                "[{0}] {1} empty RSS data received.".format(
                    provider.name,
                    provider.funcName()
                ),
                logger.ERROR
            )
        return xml

    ###########################################################################

provider = TorrentDayProvider()
