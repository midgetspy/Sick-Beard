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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import elementtree.ElementTree as etree

import sickbeard
import generic

from sickbeard.exceptions import ex, AuthException
from sickbeard import helpers
from sickbeard import logger
from sickbeard import tvcache


class TvTorrentsProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "TvTorrents")

        self.supportsBacklog = False

        self.cache = TvTorrentsCache(self)

        self.url = 'http://www.tvtorrents.com/'

    def isEnabled(self):
        return sickbeard.TVTORRENTS

    def imageName(self):
        return 'tvtorrents.png'

    def _checkAuth(self):

        if not sickbeard.TVTORRENTS_DIGEST or not sickbeard.TVTORRENTS_HASH:
            raise AuthException("Your authentication credentials for " + self.name + " are missing, check your config.")

        return True

    def _checkAuthFromData(self, parsedXML):

        if parsedXML is None:
            return self._checkAuth()

        description_text = helpers.get_xml_text(parsedXML.find('.//channel/description'))

        if "User can't be found" in description_text or "Invalid Hash" in description_text:
            logger.log(u"Incorrect authentication credentials for " + self.name + " : " + str(description_text), logger.DEBUG)
            raise AuthException(u"Your authentication credentials for " + self.name + " are incorrect, check your config")

        return True


class TvTorrentsCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll TvTorrents every 15 minutes max
        self.minTime = 15

    def _getRSSData(self):

        # These will be ignored on the serverside.
        ignore_regex = "all.month|month.of|season[\s\d]*complete"

        rss_url = self.provider.url + 'RssServlet?digest=' + sickbeard.TVTORRENTS_DIGEST + '&hash=' + sickbeard.TVTORRENTS_HASH + '&fname=true&exclude=(' + ignore_regex + ')'
        logger.log(self.provider.name + u" cache update URL: " + rss_url, logger.DEBUG)

        data = self.provider.getURL(rss_url)

        if not data:
            logger.log(u"No data returned from " + rss_url, logger.ERROR)
            return None

        return data

    def _checkAuth(self, parsedXML):
            return self.provider._checkAuthFromData(parsedXML)

provider = TvTorrentsProvider()
