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

from sickbeard import helpers, logger, exceptions, tvcache


class TorrentLeechProvider(generic.TorrentProvider):

    def __init__(self):
        generic.TorrentProvider.__init__(self, "TorrentLeech")

        self.supportsBacklog = False
        self.cache = TorrentLeechCache(self)
        self.url = 'http://www.torrentleech.org/'

    def isEnabled(self):
        return sickbeard.TORRENTLEECH

    def imageName(self):
        return 'torrentleech.png'


class TorrentLeechCache(tvcache.TVCache):

    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)

        # only poll every 15 minutes
        self.minTime = 15

    def _getRSSData(self):

        if not sickbeard.TORRENTLEECH_KEY:
            raise exceptions.AuthException("TorrentLeech requires an API key to work correctly")

        url = 'http://rss.torrentleech.org/' + sickbeard.TORRENTLEECH_KEY
        logger.log(u"TorrentLeech cache update URL: " + url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data

    def _parseItem(self, item):
        description = helpers.get_xml_text(item.getElementsByTagName('description')[0])

        if "Your RSS key is invalid" in description:
            raise exceptions.AuthException("TorrentLeech key invalid")

        (title, url) = self.provider._get_title_and_url(item)

        # torrentleech converts dots to spaces, undo this
        title = title.replace(' ', '.')

        if not title or not url:
            logger.log(u"The XML returned from the TorrentLeech RSS feed is incomplete, this result is unusable", logger.ERROR)
            return

        logger.log(u"Adding item from RSS to cache: " + title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = TorrentLeechProvider()
