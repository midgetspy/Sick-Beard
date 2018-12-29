###################################################################################################
# Author: Jodi Jones <venom@gen-x.co.nz>
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
from sickbeard.exceptions import ex
from sickbeard.common import Quality
from sickbeard.common import Overview
from sickbeard import show_name_helpers

class IPTorrentsProvider(generic.TorrentProvider):
    ###################################################################################################
    def __init__(self):
        generic.TorrentProvider.__init__(self, "IPTorrents")
        self.supportsBacklog = True
        self.cache = IPTorrentsCache(self)
        self.url = 'https://iptorrents.com/'
        self.rss_uid = None
        self.rss_passkey = None
        self.name = "IPTorrents"
        self.session = None
        self.funcName = lambda n=0: sys._getframe(n + 1).f_code.co_name + "()"
        logger.log("[{}] initializing...".format(self.name))

    ###################################################################################################

    def isEnabled(self):
        return sickbeard.IPTORRENTS

    ###################################################################################################

    def imageName(self):
        return 'iptorrents.png'

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

    def switchURL(self):
        new_url = 'https://iptorrents.com/' if not getattr(sickbeard, 'IPTORRENTS_EU', False) else 'https://iptorrents.eu/'
        # Reset auth session , different domain.
        if new_url != self.url:
            self.session = None
            self.url = new_url

    ###################################################################################################

    def _doSearch(self, search_params, show=None):
        logger.log("[{}] {} Performing Search: {}".format(self.name, self.funcName(), search_params), logger.DEBUG)
        self.switchURL()
        return self.parseResults("{}t?99=&78=&23=&25=&65=&79=&22=&5=&q={}&qf=#torrents".format(
                self.url,
                urllib.quote(search_params)
            )
        )

    ###################################################################################################

    def parseResults(self, searchUrl):
        logger.log("[{}] {} URL: {}".format(self.name, self.funcName(), searchUrl))
        data = self.getURL(searchUrl)
        results = []
        if data:
            for torrent in re.compile(
                    '<a class="b" href="/details\.php\?id=\d+">(?P<title>.*?)</a>.*?<a href="/download\.php/(?P<url>.*?)"><',
                    re.MULTILINE | re.DOTALL
                ).finditer(data):
                item = (torrent.group('title').replace('.', ' '), self.url + "download.php/" + torrent.group('url'))
                logger.log("[{}] {} Title: {}".format(
                        self.name,
                        self.funcName(),
                        torrent.group('title').replace('.', ' ')
                    ),
                    logger.DEBUG
                )
                results.append(item)
            if len(results):
                logger.log("[{}] {} Some results found.".format(self.name, self.funcName()))
            else:
                logger.log("[{}] {} No results found.".format(self.name, self.funcName()))
        else:
            logger.log("[{}] {} Error no data returned!!".format(self.name, self.funcName()))
        return results

    ###################################################################################################

    def _CloudFlareError(self, response):
        if getattr(response, 'status_code', 0) in [520, 521]:
            self.session = None
            logger.log("[{}] {} Site down/overloaded cloudflare status code: {}".format(
                    self.name,
                    self.funcName(),
                    response.status_code
                ),
                logger.ERROR
            )
            return True
        return False
    
    ###################################################################################################
    
    def getURL(self, url, data=None):
        response = None

        if not self.session and not self._doLogin():
            return response

        try:
            if 'getrss.php' in url:
                response = self.session.post(url, data=data, timeout=30, verify=False)
            else:
                response = self.session.get(url, timeout=30, verify=False)
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

        if self._CloudFlareError(response):
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

        return getattr(response, 'content', None)

    ###################################################################################################

    def _getPassKey(self):
        logger.log("[{}] {} Attempting to acquire RSS authentication details.".format(
                self.name,
                self.funcName()
            ),
            logger.DEBUG
        )
        try:
            post_params = {
                's0': '',
                's1': '',
                'cat[]': '5',
                'feed': 'direct',
            }
            (self.rss_uid, self.rss_passkey) = re.findall(
                r'\/t\.rss\?u=(\d+);tp=([0-9A-Fa-f]{32});',
                self.getURL(
                    "{}getrss.php".format(self.url),
                    post_params
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

    def _doLogin(self):
        login_params = {
            'username': sickbeard.IPTORRENTS_USERNAME,
            'password': sickbeard.IPTORRENTS_PASSWORD,
            'login': 'submit'
        }

        self.switchURL()

        self.session = requests.Session()
        logger.log("[{}] Attempting to Login".format(self.name))

        try:
            response = self.session.post(
                "{}/take_login.php".format(self.url),
                data=login_params,
                timeout=30,
                verify=False
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
            self.session = None
            logger.log("[{}] {} Error: {}".foramt(self.name, self.funcName(), str(e)), logger.ERROR)
            return False

        if self._CloudFlareError(response):
            return False
        
        if re.search("take_login\.php|Password not correct|<title>IPT</title>", response.content) \
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

class IPTorrentsCache(tvcache.TVCache):

    ###################################################################################################

    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        self.minTime = 15

    ###################################################################################################

    def _getRSSData(self):
        xml = None
        
        provider.switchURL()
 
        if not provider.session:
            provider._doLogin()
        
        if provider.rss_passkey:
            try:
                self.rss_url = "{}t.rss?u={};tp={};99;79;78;65;25;23;22;5;download".format(
                    provider.url,
                    provider.rss_uid,
                    provider.rss_passkey
                )
                logger.log("[{}] {} RSS URL - {}".format(provider.name, provider.funcName(), self.rss_url), logger.DEBUG)
                xml = provider.getURL(self.rss_url)
                if xml is not None:
                    xml = xml.decode('utf8', 'ignore')
            except:
                pass
        
        if not xml:
            logger.log("[{}] {} empty RSS data received.".format(provider.name, provider.funcName()), logger.ERROR)
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

provider = IPTorrentsProvider()
