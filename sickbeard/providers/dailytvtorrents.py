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
from sickbeard.helpers import sanitizeSceneName, get_xml_text
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
        return 'dailytvtorrents.gif'

    def getQuality(self, item):

        url = item.getElementsByTagName('enclosure')[0].getAttribute('url')
        quality = Quality.nameQuality(url)

        return quality

    def get_rss_feed_parameters(self, show=None, season=None):

        feed_params = {}

        prefer_or_only = sickbeard.DAILYTVTORRENTS_PREFER_OR_ONLY
        prefer_type = sickbeard.DAILYTVTORRENTS_PREFER_TYPE
        minage = sickbeard.DAILYTVTORRENTS_MINAGE
        wait = sickbeard.DAILYTVTORRENTS_WAIT
        norar = sickbeard.DAILYTVTORRENTS_NORAR
        single = sickbeard.DAILYTVTORRENTS_SINGLE

        if prefer_or_only and prefer_type:
            feed_params[prefer_or_only] = prefer_type

        if minage:
            feed_params['minage'] = minage

        if wait:
            feed_params['wait'] = wait

        if norar and "1" == norar:
            feed_params['norar'] = 'yes'

        if single and "1" == single:
            feed_params['single'] = 'yes'

        # DailyTvTorrents currently doesn't support specifying a season for backlog searches.

        # If we're looking for a specific show (backlog search)
        if show:
            # Request all episodes from all seasons of this show...
            feed_params['items'] = 'all'
        else:
            # ... otherwise we're doing a normal scheduled search using the combined RSS feed (allshows)
            # and we're only interested in new episodes
            feed_params['onlynew'] = 'yes'

        # This could be improved if DailyTvTorrents would add 'season' and 'episode' feed parameters

        return feed_params

    def _get_show_name_for_feeds(self, show):

        if show.dailytvtorrents_show_name:
            return sanitizeSceneName(show.dailytvtorrents_show_name, ezrss=False).replace('.', '-').encode('utf-8').lower()
        else:
            return sanitizeSceneName(show.name, ezrss=False).replace('.', '-').encode('utf-8').lower()

    def _get_season_search_strings(self, show, season=None):

        params = self.get_rss_feed_parameters(show, season)

        if not show:
            return params

        # The show_name parameter is needed because when _doSearch() is called from within GenericProvider.findSeasonResults()
        # no show object is passed as a parameter (is that a bug?)
        # but we need to strip this out in _doSearch() before using the parameters in the RSS query string
        params['show_name'] = self._get_show_name_for_feeds(show)

        return [params]

    def _get_episode_search_strings(self, ep_obj):

        # DailyTvTorrents currently doesn't support searching for a specifc episode
        return self._get_season_search_strings(ep_obj.show, ep_obj.season)

    def _doSearch(self, search_params, show=None):

        feed_params = {}

        # The show's name is used to form the path, but not sent in the querystring
        if search_params:
            if search_params['show_name']:
                show_name = search_params.pop('show_name')
            feed_params.update(search_params)

        if not show_name:
            show_name = self._get_show_name_for_feeds(show)

        searchURL = self.url + 'show/' + show_name

        if feed_params:
            searchURL += "?" + urllib.urlencode(feed_params)

        logger.log(u"Search string: " + searchURL, logger.DEBUG)

        data = self.getURL(searchURL)

        if not data:
            return []

        try:
            parsedXML = parseString(data)
            items = parsedXML.getElementsByTagName('item')
        except Exception, e:
            logger.log(u"Error trying to load DailyTvTorrents RSS feed: " + ex(e), logger.ERROR)
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

    def _get_title_and_url(self, item):

        title = get_xml_text(item.getElementsByTagName('title')[0])

        url = item.getElementsByTagName('enclosure')[0].getAttribute('url')

        return (title, url)


class DailyTvTorrentsCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll DailyTvTorrents every 30 minutes max
        self.minTime = 30

    def _getRSSData(self):

        url = self.provider.url + 'allshows'

        params = self.provider.get_rss_feed_parameters(None, None)

        if params:
            url += "?" + urllib.urlencode(params)

        logger.log(u"DailyTvTorrents cache update URL: " + url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data

    def _parseItem(self, item):

        (title, url) = self.provider._get_title_and_url(item)

        if not title or not url:
            logger.log(u"The XML returned from the DailyTvTorrents RSS feed is incomplete, this result is unusable", logger.ERROR)
            return

        logger.log(u"Adding item from RSS to cache: " + title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = DailyTvTorrentsProvider()
