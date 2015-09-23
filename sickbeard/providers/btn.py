# coding=utf-8
# Author: Dani�l Heimans
# URL: http://code.google.com/p/sickbeard
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

import sickbeard
import generic

from sickbeard import classes
from sickbeard import scene_exceptions
from sickbeard import logger
from sickbeard import tvcache
from sickbeard.helpers import sanitizeSceneName
from sickbeard.common import Quality
from sickbeard.exceptions import ex, AuthException

from lib import jsonrpclib
from datetime import datetime
import time
import socket
import math


class BTNProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "BTN")

        self.supportsBacklog = True
        self.cache = BTNCache(self)

        self.url = "http://broadcasthe.net"

    def isEnabled(self):
        return sickbeard.BTN

    def imageName(self):
        return 'btn.png'

    def _checkAuth(self):
        if not sickbeard.BTN_API_KEY:
            raise AuthException("Your authentication credentials for " + self.name + " are missing, check your config.")

        return True

    def _checkAuthFromData(self, parsedJSON):

        if parsedJSON is None:
            return self._checkAuth()

        if 'api-error' in parsedJSON:
                    logger.log(u"Incorrect authentication credentials for " + self.name + " : " + parsedJSON['api-error'], logger.DEBUG)
                    raise AuthException("Your authentication credentials for " + self.name + " are incorrect, check your config.")

        return True

    def _doSearch(self, search_params, show=None, age=0):

        self._checkAuth()

        params = {}
        apikey = sickbeard.BTN_API_KEY

        # age in seconds
        if age:
            params['age'] = "<=" + str(int(age))

        if search_params:
            params.update(search_params)

        parsedJSON = self._api_call(apikey, params)

        if not parsedJSON:
            logger.log(u"No data returned from " + self.name, logger.ERROR)
            return []

        if self._checkAuthFromData(parsedJSON):

            if 'torrents' in parsedJSON:
                found_torrents = parsedJSON['torrents']
            else:
                found_torrents = {}

            # We got something, we know the API sends max 1000 results at a time.
            # See if there are more than 1000 results for our query, if not we
            # keep requesting until we've got everything.
            # max 150 requests per hour so limit at that. Scan every 15 minutes. 60 / 15 = 4.
            max_pages = 35
            results_per_page = 1000

            if 'results' in parsedJSON and int(parsedJSON['results']) >= results_per_page:
                pages_needed = int(math.ceil(int(parsedJSON['results']) / results_per_page))
                if pages_needed > max_pages:
                    pages_needed = max_pages

                # +1 because range(1,4) = 1, 2, 3
                for page in range(1, pages_needed + 1):
                    parsedJSON = self._api_call(apikey, params, results_per_page, page * results_per_page)
                    # Note that this these are individual requests and might time out individually. This would result in 'gaps'
                    # in the results. There is no way to fix this though.
                    if 'torrents' in parsedJSON:
                        found_torrents.update(parsedJSON['torrents'])

            results = []

            for torrentid, torrent_info in found_torrents.iteritems():  # @UnusedVariable
                (title, url) = self._get_title_and_url(torrent_info)

                if title and url:
                    results.append(torrent_info)

            return results

        return []

    def _api_call(self, apikey, params={}, results_per_page=1000, offset=0):

        server = jsonrpclib.Server('http://api.btnapps.net')
        parsedJSON = {}

        try:
            parsedJSON = server.getTorrents(apikey, params, int(results_per_page), int(offset))

        except jsonrpclib.jsonrpc.ProtocolError, error:
            logger.log(u"JSON-RPC protocol error while accessing " + self.name + ": " + ex(error), logger.ERROR)
            parsedJSON = {'api-error': ex(error)}
            return parsedJSON

        except socket.timeout:
            logger.log(u"Timeout while accessing " + self.name, logger.WARNING)

        except socket.error, error:
            # Note that sometimes timeouts are thrown as socket errors
            logger.log(u"Socket error while accessing " + self.name + ": " + error[1], logger.ERROR)

        except Exception, error:
            errorstring = str(error)
            if(errorstring.startswith('<') and errorstring.endswith('>')):
                errorstring = errorstring[1:-1]
            logger.log(u"Unknown error while accessing " + self.name + ": " + errorstring, logger.ERROR)

        return parsedJSON

    def _get_title_and_url(self, parsedJSON):

        # The BTN API gives a lot of information in response,
        # however Sick Beard is built mostly around Scene or
        # release names, which is why we are using them here.

        if 'ReleaseName' in parsedJSON and parsedJSON['ReleaseName']:
            title = parsedJSON['ReleaseName']

        else:
            # If we don't have a release name we need to get creative
            title = u''
            if 'Series' in parsedJSON:
                title += parsedJSON['Series']
            if 'GroupName' in parsedJSON:
                title += '.' + parsedJSON['GroupName'] if title else parsedJSON['GroupName']
            if 'Resolution' in parsedJSON:
                title += '.' + parsedJSON['Resolution'] if title else parsedJSON['Resolution']
            if 'Source' in parsedJSON:
                title += '.' + parsedJSON['Source'] if title else parsedJSON['Source']
            if 'Codec' in parsedJSON:
                title += '.' + parsedJSON['Codec'] if title else parsedJSON['Codec']
            if title:
                title = title.replace(' ', '.')

        url = None
        if 'DownloadURL' in parsedJSON:
            url = parsedJSON['DownloadURL']
            if url:
                # unescaped / is valid in JSON, but it can be escaped
                url = url.replace("\\/", "/")

        return (title, url)

    def _get_season_search_strings(self, show, season=None):
        if not show:
            return [{}]

        search_params = []

        name_exceptions = scene_exceptions.get_scene_exceptions(show.tvdbid) + [show.name]

        for name in name_exceptions:

            current_params = {}

            if show.tvdbid:
                current_params['tvdb'] = show.tvdbid

            elif show.tvrid:
                current_params['tvrage'] = show.tvrid

            else:
                # Search by name if we don't have tvdb or tvrage id
                current_params['series'] = sanitizeSceneName(name)

            if season is not None:
                whole_season_params = current_params.copy()
                partial_season_params = current_params.copy()
                # Search for entire seasons: no need to do special things for air by date shows
                whole_season_params['category'] = 'Season'
                whole_season_params['name'] = 'Season ' + str(season)

                if whole_season_params not in search_params:
                    search_params.append(whole_season_params)

                # Search for episodes in the season
                partial_season_params['category'] = 'Episode'

                if show.air_by_date:
                    # Search for the year of the air by date show
                    partial_season_params['name'] = str(season.split('-')[0]) + "%"
                else:
                    # Search for any result which has Sxx in the name
                    partial_season_params['name'] = "S" + str(season).zfill(2) + "%"

                if partial_season_params not in search_params:
                    search_params.append(partial_season_params)

            else:
                if current_params not in search_params:
                    search_params.append(current_params)

        return search_params

    def _get_episode_search_strings(self, ep_obj):

        if not ep_obj:
            return [{}]

        search_params = {'category': 'Episode'}

        if ep_obj.show.tvdbid:
            search_params['tvdb'] = ep_obj.show.tvdbid
        elif ep_obj.show.tvrid:
            search_params['tvrage'] = ep_obj.show.rid
        else:
            search_params['series'] = sanitizeSceneName(ep_obj.show_name)

        if ep_obj.show.air_by_date:
            date_str = str(ep_obj.airdate)

            # BTN uses dots in dates, we just search for the date since that
            # combined with the series identifier should result in just one episode
            search_params['name'] = date_str.replace('-', '.')

        else:
            # Do a general name search for the episode, formatted like SXXEYY
            search_params['name'] = "S%02dE%02d" % (ep_obj.season, ep_obj.episode)

        to_return = [search_params]

        # only do scene exceptions if we are searching by name
        if 'series' in search_params:

            # add new query string for every exception
            name_exceptions = scene_exceptions.get_scene_exceptions(ep_obj.show.tvdbid)
            for cur_exception in name_exceptions:

                # don't add duplicates
                if cur_exception == ep_obj.show.name:
                    continue

                # copy all other parameters before setting the show name for this exception
                cur_return = search_params.copy()
                cur_return['series'] = sanitizeSceneName(cur_exception)
                to_return.append(cur_return)

        return to_return

    def _doGeneralSearch(self, search_string):
        # 'search' looks as broad is it can find. Can contain episode overview and title for example,
        # use with caution!
        return self._doSearch({'search': search_string})

    def findPropers(self, search_date=None):
        results = []

        search_terms = ['%.proper.%', '%.repack.%']

        for term in search_terms:
            for item in self._doSearch({'release': term}, age=4 * 24 * 60 * 60):
                if item['Time']:
                    try:
                        result_date = datetime.fromtimestamp(float(item['Time']))
                    except TypeError:
                        result_date = None

                    if result_date:
                        if not search_date or result_date > search_date:
                            title, url = self._get_title_and_url(item)
                            results.append(classes.Proper(title, url, result_date))

        return results


class BTNCache(tvcache.TVCache):

    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)

        # At least 15 minutes between queries
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

            if self._checkAuth(data):
                # By now we know we've got data and no auth errors, all we need to do is put it in the database
                for item in data:
                    self._parseItem(item)

            else:
                raise AuthException("Your authentication info for " + self.provider.name + " is incorrect, check your config")

        else:
            return []

    def _getRSSData(self):
        # Get the torrents uploaded since last check.
        seconds_since_last_update = math.ceil(time.time() - time.mktime(self._getLastUpdate().timetuple()))

        # default to 15 minutes
        seconds_minTime = self.minTime * 60
        if seconds_since_last_update < seconds_minTime:
            seconds_since_last_update = seconds_minTime

        # Set maximum to 24 hours (24 * 60 * 60 = 86400 seconds) of "RSS" data search, older things will need to be done through backlog
        if seconds_since_last_update > 86400:
            logger.log(u"The last known successful update on " + self.provider.name + " was more than 24 hours ago, only trying to fetch the last 24 hours!", logger.WARNING)
            seconds_since_last_update = 86400

        data = self.provider._doSearch(search_params=None, age=seconds_since_last_update)

        return data

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

provider = BTNProvider()
