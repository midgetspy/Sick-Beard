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
from sickbeard.common import Quality
from sickbeard.exceptions import ex, AuthException
from sickbeard.name_parser.parser import NameParser, InvalidNameException

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
        self.search_url = 'https://hdbits.org/api/torrents'
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

    def findEpisode(self, episode, manualSearch=False):

        logger.log(u"Searching " + self.name + " for " + episode.prettyName())

        self.cache.updateCache()
        results = self.cache.searchCache(episode, manualSearch)
        logger.log(u"Cache results: " + str(results), logger.DEBUG)

        # if we got some results then use them no matter what.
        # OR
        # return anyway unless we're doing a manual search
        if results or not manualSearch:
            return results

        data = self.getURL(self.search_url, post_data=self._make_post_data_JSON(show=episode.show, episode=episode))

        if not data:
            logger.log(u"No data returned from " + self.search_url, logger.ERROR)
            return []

        parsedJSON = helpers.parse_json(data)

        if parsedJSON is None:
            logger.log(u"Error trying to load " + self.name + " JSON data", logger.ERROR)
            return []

        if self._checkAuthFromData(parsedJSON):
            results = []

            if parsedJSON and 'data' in parsedJSON:
                items = parsedJSON['data']
            else:
                logger.log(u"Resulting JSON from " + self.name + " isn't correct, not parsing it", logger.ERROR)
                items = []

            for item in items:

                (title, url) = self._get_title_and_url(item)

                # parse the file name
                try:
                    myParser = NameParser()
                    parse_result = myParser.parse(title)
                except InvalidNameException:
                    logger.log(u"Unable to parse the filename " + title + " into a valid episode", logger.WARNING)
                    continue

                if episode.show.air_by_date:
                    if parse_result.air_date != episode.airdate:
                        logger.log(u"Episode " + title + " didn't air on " + str(episode.airdate) + ", skipping it", logger.DEBUG)
                        continue
                elif parse_result.season_number != episode.season or episode.episode not in parse_result.episode_numbers:
                    logger.log(u"Episode " + title + " isn't " + str(episode.season) + "x" + str(episode.episode) + ", skipping it", logger.DEBUG)
                    continue

                quality = self.getQuality(item)

                if not episode.show.wantEpisode(episode.season, episode.episode, quality, manualSearch):
                    logger.log(u"Ignoring result " + title + " because we don't want an episode that is " + Quality.qualityStrings[quality], logger.DEBUG)
                    continue

                logger.log(u"Found result " + title + " at " + url, logger.DEBUG)

                result = self.getResult([episode])
                result.url = url
                result.name = title
                result.quality = quality

                results.append(result)

        return results

    def _get_title_and_url(self, item):

        title = item['name']
        url = self.download_url + urllib.urlencode({'id': item['id'], 'passkey': sickbeard.HDBITS_PASSKEY})

        return (title, url)

    def _make_post_data_JSON(self, show=None, episode=None, season=None):

        post_data = {
            'username': sickbeard.HDBITS_USERNAME,
            'passkey': sickbeard.HDBITS_PASSKEY,
            'category': [2],  # TV Category
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
