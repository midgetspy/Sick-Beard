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
        url = self.url + 'nzb?' + str(item['guid']) + '*|*' + urllib.quote_plus(title)
        return (title, url)

    def _doSearch(self, search, show=None):
        params = {'age': sickbeard.USENET_RETENTION,
                  'completion': sickbeard.NZBX_COMPLETION,
                  'cat': 'tv-hd|tv-sd',
                  'limit': 250,
                  'q': search}

        if not params['age']:
            params['age'] = 500

        if not params['completion']:
            params['completion'] = 100

        url = self.url + 'api/sickbeard?' + urllib.urlencode(params)
        logger.log(u"nzbX search url: " + url, logger.DEBUG)

        data = self.getURL(url)
        try:
            items = json.loads(data)
        except ValueError:
            logger.log(u"Error trying to decode " + self.provider.name + " RSS feed", logger.ERROR)
            return[]

        results = []
        for item in items:
            if item['name'] and item['guid']:
                results.append(item)
            else:
                logger.log(u"Partial result from " + self.provider.name, logger.DEBUG)
        return results

    def findPropers(self, date=None):
        params = {'completion': 100,
                  'cat': 'tv-hd|tv-sd',
                  'age': 4,
                  'q': '.proper.|.repack.'}

        url = self.url + 'api/sickbeard?' + urllib.urlencode(params)
        logger.log(u"nzbX proper search url: " + url, logger.DEBUG)

        data = self.getURL(url)
        try:
            items = json.loads(data)
        except ValueError:
            logger.log(u"Error trying to decode " + self.provider.name + " RSS feed", logger.ERROR)
            return[]

        results = []
        for item in items:
            if item['name'] and item['guid'] and item['postdate']:
                name, url = self._get_title_and_url(item)
                results.append(classes.Proper(name, url, datetime.fromtimestamp(item['postdate'])))
            else:
                logger.log(u"Partial result from " + self.provider.name, logger.DEBUG)
        return results


class NzbXCache(tvcache.TVCache):

    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        self.minTime = 20

    def _getRSSData(self):
        params = {'q': '',
                  'completion': sickbeard.NZBX_COMPLETION,
                  'cat': 'tv-hd|tv-sd',
                  'limit': 250}

        if not params['completion']:
            params['completion'] = 100

        url = self.provider.url + 'api/sickbeard?' + urllib.urlencode(params)
        logger.log(u"nzbX cache update URL: " + url, logger.DEBUG)
        return self.provider.getURL(url)

    def _parseItem(self, item):
        title, url = self.provider._get_title_and_url(item)
        logger.log(u"Adding item from RSS to cache: " + title, logger.DEBUG)
        self._addCacheEntry(title, url)

    def updateCache(self):
        if not self.shouldUpdate():
            return

        data = self._getRSSData()
        # as long as the http request worked we count this as an update
        if data:
            self.setLastUpdate()
        else:
            return

        # now that we've loaded the current RSS feed lets delete the old cache
        logger.log(u"Clearing " + self.provider.name + " cache and updating with new information")
        self._clearCache()

        try:
            items = json.loads(data)
        except ValueError:
            logger.log(u"Error trying to decode " + self.provider.name + " RSS feed", logger.ERROR)
            return

        for item in items:
            if item['name'] and item['guid']:
                self._parseItem(item)
            else:
                logger.log(u"Partial result from " + self.provider.name, logger.DEBUG)

provider = NzbXProvider()
