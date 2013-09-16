# Author: Nic Wolfe <nic@wolfeden.ca>
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
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import urllib
import generic
import sickbeard

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

from sickbeard import exceptions, logger
from sickbeard import tvcache, show_name_helpers


class NINJACENTRALProvider(generic.NZBProvider):

    def __init__(self):
        generic.NZBProvider.__init__(self, "ninjacentral")
        self.cache = NINJACENTRALCache(self)
        self.url = 'http://127.0.0.1/'
        self.supportsBacklog = True

    def isEnabled(self):
        return sickbeard.NINJACENTRAL

    def _checkAuth(self):
        if sickbeard.NINJACENTRAL_UID in (None, "") or sickbeard.NINJACENTRAL_HASH in (None, ""):
            raise exceptions.AuthException("Ninjacentral's authentication details are empty, check your config")

    def _get_season_search_strings(self, show, season):
        return [x for x in show_name_helpers.makeSceneSeasonSearchString(show, season)]

    def _get_episode_search_strings(self, ep_obj):
        return [x for x in show_name_helpers.makeSceneSearchString(ep_obj)]

	#These parameters need to reflect in the api
    def _doSearch(self, search, show=None):
        params = {'uid': sickbeard.NINJACENTRAL_UID,
                  'passkey': sickbeard.NINJACENTRAL_HASH,
                  'xml': 1,
                  'maxage': sickbeard.USENET_RETENTION,
                  'cat': '5030,5040,5050,5060',     # TV:HD
                  'limit': 100,
                  't': 'tv',
                  'q': search}

        if not params['maxage']:
            params['maxage'] = 500

        searchURL = self.url + 'api.php?' + urllib.urlencode(params)
        logger.log(u"Ninjacentral's search url: " + searchURL, logger.DEBUG)

        data = self.getURL(searchURL)
        if not data:
            return []
		
		#if data is not an xml document, return error displayed if it's a single line
        if not data.startswith('<?xml'):  # Error will be a single line of text
            logger.log(u"Ninjacentral error: " + data, logger.ERROR)
            return []

        root = etree.fromstring(data)
        if root is None:
            logger.log(u"Error trying to parse Ninjacentral XML data.", logger.ERROR)
            logger.log(u"RSS data: " + data, logger.DEBUG)
            return []
        return root.findall('./rss/channel')

	
    def _get_title_and_url(self, element):
        if element.find('title'):  # RSS feed
            title = element.find('title').text
            url = element.find('link').text.replace('&amp;', '&')
        return (title, url)


class NINJACENTRALCache(tvcache.TVCache):

    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        # only poll NC every 15 minutes max
        self.minTime = 15
	
    def _getRSSData(self):
        url = self.provider.url + 'api.php?'
        urlArgs = {'uid': sickbeard.NINJACENTRAL_UID,
                  'passkey': sickbeard.NINJACENTRAL_HASH,
                  'xml': 1,
                  'maxage': sickbeard.USENET_RETENTION,
                  'cat': '5030,5040,5050,5060',     # TV:HD
                  'limit': 500,
                  't': 'tv'}

        url += urllib.urlencode(urlArgs)
        logger.log(u"Ninjacentral's cache update URL: " + url, logger.DEBUG)

        data = self.provider.getURL(url)
        return data

    def _checkAuth(self, data):
        return data != 'Invalid Link'

provider = NINJACENTRALProvider()
