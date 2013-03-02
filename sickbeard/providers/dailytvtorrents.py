# Author: Jason Lane
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

import urllib
from xml.dom.minidom import parseString

import sickbeard
import generic

from sickbeard.common import Quality
from sickbeard import logger
from sickbeard import tvcache
from sickbeard import show_name_helpers
from sickbeard.helpers import get_xml_text
from sickbeard.exceptions import ex


class DailyTvTorrentsProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "DailyTvTorrents")

        self.supportsBacklog = True

        self.cache = DailyTvTorrentsCache(self)

        self.url = 'http://www.dailytvtorrents.org/rss/'

    def isEnabled(self):
        return sickbeard.DAILYTVTORRENTS

    def imageName(self):
        return 'dailytvtorrents.png'

    def getQuality(self, item):

        url = item.getElementsByTagName('enclosure')[0].getAttribute('url')
        quality = Quality.nameQuality(url)

        return quality

    def _get_title_and_url(self, item):

        title = get_xml_text(item.getElementsByTagName('title')[0])

        url = item.getElementsByTagName('enclosure')[0].getAttribute('url')

        return (title, url)

    def _get_rss_feed_options(self, show=None):

        query_params = {}

        # Start by checking the user-configured options

        prefer_or_only = sickbeard.DAILYTVTORRENTS_PREFER_OR_ONLY
        prefer_quality = sickbeard.DAILYTVTORRENTS_PREFER_QUALITY  # Current options are '720' or 'hd'
        minage = sickbeard.DAILYTVTORRENTS_MINAGE
        wait = sickbeard.DAILYTVTORRENTS_WAIT
        norar = sickbeard.DAILYTVTORRENTS_NORAR
        single = sickbeard.DAILYTVTORRENTS_SINGLE

        if prefer_or_only and prefer_quality:
            query_params[prefer_or_only] = prefer_quality

        if minage:
            query_params['minage'] = minage

        if wait:
            query_params['wait'] = wait

        if norar and "1" == norar:
            query_params['norar'] = 'yes'

        if single and "1" == single:
            query_params['single'] = 'yes'

        # The rest aren't user-configured

        # If we're looking for a specific show (backlog search)
        if show:
            # Request all episodes from all seasons of this show...
            query_params['items'] = 'all'
        else:
            # ... otherwise we're doing a normal scheduled search using the combined RSS feed (allshows)
            # and we're only interested in new episodes
            query_params['onlynew'] = 'yes'

        # This could be improved if DailyTvTorrents adds 'season' and 'episode' parameters for their feed or api

        return query_params

    def _get_season_search_strings(self, show, season=None):

        if not show:
            return [{}]

        searches = []

        query_params = self._get_rss_feed_options(show)

        # The show_name parameter is needed because when _doSearch() is called from within GenericProvider.findSeasonResults()
        # no show object is passed as a parameter.
        # We need to exclude the show_name from the query string in _getRSSData() later

        all_possible_show_names = set(show_name_helpers.makeSceneShowSearchStrings(show))

        for show_name in all_possible_show_names:
            search = query_params.copy()
            search['show_name'] = show_name.replace('.', '-').encode('utf-8').lower()
            searches.append(search)

        return searches

    def _get_episode_search_strings(self, ep_obj):

        # DailyTvTorrents currently doesn't support searching for a specifc episode
        return self._get_season_search_strings(ep_obj.show, ep_obj.season)

    def _doSearch(self, search_params, show=None):

        data = self._getRSSData(search_params, show)

        if not data:
            return []

        try:
            parsedXML = parseString(data)
            items = parsedXML.getElementsByTagName('item')
        except Exception, e:
            logger.log(u"Error trying to parse DailyTvTorrents RSS feed: " + ex(e), logger.ERROR)
            logger.log(u"RSS data: " + data, logger.DEBUG)
            return []

        results = []

        for curItem in items:

            (title, url) = self._get_title_and_url(curItem)

            if not title or not url:
                logger.log(u"The XML returned from the DailyTvTorrents RSS feed is incomplete, this result is unusable: " + data, logger.ERROR)
                continue

            results.append(curItem)

        return results

    def _getRSSData(self, search_params=None, show=None):

        if not search_params:
            url = self.url + 'allshows'
            query_params = self._get_rss_feed_options()
        else:
            show_name = search_params.pop('show_name')
            url = self.url + 'show/' + show_name
            query_params = search_params

        if query_params:
            url += "?" + urllib.urlencode(query_params)

        logger.log(u"DailyTvTorrents feed URL: " + url, logger.DEBUG)

        data = self.getURL(url)

        return data


class DailyTvTorrentsCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll DailyTvTorrents every 30 minutes max
        self.minTime = 30

    def _getRSSData(self):

        data = self.provider._getRSSData()

        return data

    def _parseItem(self, item):

        (title, url) = self.provider._get_title_and_url(item)

        quality = self.provider.getQuality(item)

        if not title or not url:
            logger.log(u"The XML returned from the DailyTvTorrents RSS feed is incomplete, this result is unusable", logger.ERROR)
            return

        logger.log(u"Adding item from RSS to cache: " + title, logger.DEBUG)

        self._addCacheEntry(title, url, quality=quality)

provider = DailyTvTorrentsProvider()
