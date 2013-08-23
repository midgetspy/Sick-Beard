# Author: Jordon Smith <smith@jordon.me.uk>
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard. If not, see <http://www.gnu.org/licenses/>.

import urllib
import generic
import sickbeard

from sickbeard import helpers
from sickbeard import tvcache
from sickbeard import logger
from sickbeard import classes
from sickbeard import show_name_helpers
from datetime import datetime

try:
    import json
except ImportError:
    from lib import simplejson as json


class NzbXProvider(generic.NZBProvider):

    def __init__(self):
        generic.NZBProvider.__init__(self, "nzbX")
        self.cache = NzbXCache(self)
        self.url = 'https://nzbx.co/'
        self.supportsBacklog = True

    def isEnabled(self):
        return sickbeard.NZBX

    def _get_season_search_strings(self, show, season):
        return [x + '*' for x in show_name_helpers.makeSceneSeasonSearchString(show, season)]

    def _get_episode_search_strings(self, ep_obj):
        return [x for x in show_name_helpers.makeSceneSearchString(ep_obj)]

    def _get_title_and_url(self, item):
        title = item['name']
        url = self.url + 'nzb?' + str(item['guid']) + '*|*' + urllib.quote_plus(title.encode("utf-8"))
        return (title, url)

    def _doSearch(self, search, show=None, age=0):

        self._checkAuth()

        params = {'age': sickbeard.USENET_RETENTION,
                  'completion': sickbeard.NZBX_COMPLETION,
                  'cat': 'tv-hd|tv-sd',
                  'limit': 250,
                  'q': search}

        if age or not params['age']:
            params['age'] = age

        if not params['completion']:
            params['completion'] = 100

        search_url = self.url + 'api/sickbeard?' + urllib.urlencode(params)
        logger.log(u"Search url: " + search_url, logger.DEBUG)

        data = self.getURL(search_url)

        if not data:
            logger.log(u"No data returned from " + search_url, logger.ERROR)
            return []

        parsedJSON = helpers.parse_json(data)

        if parsedJSON is None:
            logger.log(u"Error trying to load " + self.name + " JSON data", logger.ERROR)
            return []

        results = []
        for item in parsedJSON:
            if item['name'] and item['guid']:
                results.append(item)

        return results

    def findPropers(self, search_date=None):
        results = []
        for item in self._doSearch('.proper.|.repack.', age=4):
            if item['postdate']:
                name, url = self._get_title_and_url(item)
                results.append(classes.Proper(name, url, datetime.fromtimestamp(item['postdate'])))

        return results


class NzbXCache(tvcache.TVCache):

    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        self.minTime = 20

    def _parseItem(self, item):
        title, url = self.provider._get_title_and_url(item)
        logger.log(u"Adding item from RSS to cache: " + title, logger.DEBUG)
        self._addCacheEntry(title, url)

    def updateCache(self):

        if not self.shouldUpdate():
            return

        items = self.provider._doSearch('')
        if not items:
            return
        self.setLastUpdate()

        # now that we've got the latest releases lets delete the old cache
        logger.log(u"Clearing " + self.provider.name + " cache and updating with new information")
        self._clearCache()

        for item in items:
            self._parseItem(item)

provider = NzbXProvider()
