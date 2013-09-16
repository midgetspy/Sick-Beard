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

import urllib
import generic
import sickbeard

from sickbeard import logger, tvcache, exceptions
from sickbeard import helpers
from sickbeard.exceptions import ex, AuthException

try:
    import json
except ImportError:
    from lib import simplejson as json


class HDBitsProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "HDBits")

        self.supportsBacklog = False

        self.cache = HDBitsCache(self)

        self.url = 'https://hdbits.org'
        self.rss_url = 'https://hdbits.org/api/torrents'
        self.download_url = 'http://hdbits.org/download.php?'

    def isEnabled(self):
        return sickbeard.HDBITS

    def _checkAuth(self):

        if not sickbeard.HDBITS_USERNAME  or not sickbeard.HDBITS_PASSKEY:
            raise AuthException("Your authentication credentials for " + self.name + " are missing, check your config.")

        return True

    def _checkAuthFromData(self, parsedJSON):

        if parsedJSON is None:
            return self._checkAuth()

        if 'status' in parsedJSON and 'message' in parsedJSON:
            if parsedJSON.get('status') == 5:
                logger.log(u"Incorrect authentication credentials for " + self.name + " : " + parsedJSON['message'], logger.DEBUG)
                raise AuthException("Your authentication credentials for " + self.name + " are incorrect, check your config.")

        return True

    def _get_title_and_url(self, item):

        title = item['name']
        url = self.download_url + urllib.urlencode({'id': item['id'], 'passkey': sickbeard.HDBITS_PASSKEY})

        return (title, url)

    def _make_post_data_JSON(self, show=None, episode=None, season=None):

        post_data = {
            'username': sickbeard.HDBITS_USERNAME,
            'passkey': sickbeard.HDBITS_PASSKEY,
            'category': [2],  # TV Category
            'medium': [3]  # x264
        }

        if episode:
            post_data['tvdb'] = {
                'id': show.tvdbid,
                'season': episode.season,
                'episode': episode.episode
            }

        if season:
            post_data['tvdb'] = {
                'id': show.tvdbid,
                'season': season,
            }

        return json.dumps(post_data)


class HDBitsCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll HDBits every 15 minutes max
        self.minTime = 15

    def updateCache(self):

        if not self.shouldUpdate():
            return

        if self._checkAuth(None):

            data = self._getRSSData()

            # As long as we got something from the provider we count it as an update
            if data:
                self.setLastUpdate()
            else:
                return []

            logger.log(u"Clearing " + self.provider.name + " cache and updating with new information")
            self._clearCache()

            parsedJSON = helpers.parse_json(data)

            if parsedJSON is None:
                logger.log(u"Error trying to load " + self.provider.name + " JSON feed", logger.ERROR)
                return []

            if self._checkAuth(parsedJSON):
                if parsedJSON and 'data' in parsedJSON:

                    items = parsedJSON['data']

                else:
                    logger.log(u"Resulting JSON from " + self.provider.name + " isn't correct, not parsing it", logger.ERROR)
                    return []

                for item in items:
                    self._parseItem(item)

            else:
                raise exceptions.AuthException("Your authentication info for " + self.provider.name + " is incorrect, check your config")

        else:
            return []

    def _getRSSData(self):
        return self.provider.getURL(self.provider.rss_url, post_data=self.provider._make_post_data_JSON())

    def _parseItem(self, item):

        (title, url) = self.provider._get_title_and_url(item)

        if title and url:
            logger.log(u"Adding item to results: " + title, logger.DEBUG)
            self._addCacheEntry(title, url)
        else:
            logger.log(u"The data returned from the " + self.provider.name + " is incomplete, this result is unusable", logger.ERROR)
            return

    def _checkAuth(self, data):
        return self.provider._checkAuthFromData(data)

provider = HDBitsProvider()
