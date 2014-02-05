# Author: Robert Massa <robertmassa@gmail.com>
# URL: http://code.google.com/p/sickbeard/
#
# This file is based upon tvtorrents.py.
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

import sickbeard
import generic

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import elementtree.ElementTree as etree

from sickbeard import helpers, logger, tvcache
from sickbeard.exceptions import ex, AuthException

from sickbeard.name_parser.parser import NameParser, InvalidNameException
from sickbeard.common import Quality

from bs4 import BeautifulSoup
import urllib, urllib2, cookielib

from time import time

cookies_jar = cookielib.CookieJar()

class TorrentLeechProvider(generic.TorrentProvider):

    def __init__(self):
        generic.TorrentProvider.__init__(self, "TorrentLeech")

        self.supportsBacklog = False
        self.cache = TorrentLeechCache(self)
        self.url = 'http://www.torrentleech.org/'

        handler = urllib2.HTTPCookieProcessor(cookies_jar)
        self.opener = urllib2.build_opener(handler)
        self.logged_in_expiry_time = 0

    def isEnabled(self):
        return sickbeard.TORRENTLEECH

    def imageName(self):
        return 'torrentleech.png'

    def _checkAuth(self):

        if not sickbeard.TORRENTLEECH_KEY:
            raise AuthException("Your authentication credentials for " + self.name + " are missing, check your config.")
        return True

    def _checkAuthFromData(self, parsedXML):

        if parsedXML is None:
            return self._checkAuth()

        description_text = helpers.get_xml_text(parsedXML.find('.//channel/item/description'))

        if "Your RSS key is invalid" in description_text:
            logger.log(u"Incorrect authentication credentials for " + self.name + " : " + str(description_text), logger.DEBUG)
            raise AuthException(u"Your authentication credentials for " + self.name + " are incorrect, check your config")

        return True

    def _get_season_search_strings(self, show, season=None):
        res_ = []

        if show:
            query = helpers.sanitizeSceneName(show.name).replace('.', ' ')
            if season:
                query += " S" + str(season).zfill(2)

            res_.append(query.encode('utf-8'))

        return res_

    def _get_episode_search_strings(self, ep_obj):
        res_ = []

        if ep_obj:
            query = helpers.sanitizeSceneName(ep_obj.show.name).replace('.', ' ')
            
            if ep_obj.show.air_by_date:
                query += " " + str(ep_obj.airdate)
            else:
                query += " S" + str(ep_obj.season).zfill(2) + "E" + str(ep_obj.episode).zfill(2)

            res_.append(query.encode('utf-8'))

        return res_

    def _doSearch(self, search_params, show=None):
        res_ = []

        logger.log(u"Search string: " + search_params, logger.DEBUG)

        if search_params:
            res_ = self.query(search_params)

        return res_

    def _get_title_and_url(self, item):
        title = item.get("name", None)
        url = item.get("url", None)

        if not title or not url:
            logger.log(u"Invalid item: " + str(item), logger.ERROR)

        return (title, url)

    def getURL(self, url, post_data=None, headers=None):
        res_ = ""
        if self.login():
            res_ = self.opener.open(url).read()
    
        return res_            

    def login(self):
        res_ = False

        if not self.logged_in_expiry_time or time() > self.logged_in_expiry_time:
            form_values = {'username': sickbeard.TORRENTLEECH_USERNAME, 'password': sickbeard.TORRENTLEECH_PASSWORD, 'login': 'submit', 'remember_me': 'on'}
            form_data = urllib.urlencode(form_values)

            data = self.opener.open("http://www.torrentleech.org/user/messages", form_data).read()
            html = BeautifulSoup(data)
            if html and html.select(".user_poweruser"):
                self.logged_in_expiry_time = time() + 3600
                res_ = True
        else:
            res_ = True

        return res_

    def query(self, _q):
        res_ = []
        logger.log("Query TorrentLeech: " + str(_q))
        query = "http://www.torrentleech.org/torrents/browse/index/query/" + urllib.quote(_q)
        data = self.getURL(query)
        html = BeautifulSoup(data)
        torrents = html.select("table#torrenttable tbody tr")
        for el in torrents:
            name = el.select("td.name a")[0].string
            url = "http://www.torrentleech.org" + el.select("td.quickdownload a")[0]["href"]
            res_.append({"name": name, "url": url})

        return res_


class TorrentLeechCache(tvcache.TVCache):

    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)

        # only poll every 15 minutes
        self.minTime = 15

    def _getRSSData(self):

        rss_url = 'http://rss.torrentleech.org/' + sickbeard.TORRENTLEECH_KEY
        logger.log(self.provider.name + u" cache update URL: " + rss_url, logger.DEBUG)

        data = self.provider.getURL(rss_url)

        if not data:
            logger.log(u"No data returned from " + rss_url, logger.ERROR)
            return None

        return data

    def _checkAuth(self, parsedXML):
            return self.provider._checkAuthFromData(parsedXML)

provider = TorrentLeechProvider()
