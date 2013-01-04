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

import sickbeard
import generic

from sickbeard import logger
from sickbeard import tvcache


class WombleProvider(generic.NZBProvider):

    def __init__(self):
        generic.NZBProvider.__init__(self, "Womble's Index")
        self.cache = WombleCache(self)
        self.url = 'http://nzb.isasecret.com/'

    def isEnabled(self):
        return sickbeard.WOMBLE


class WombleCache(tvcache.TVCache):

    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        # only poll Womble's Index every 15 minutes max
        self.minTime = 15

    def _getRSSData(self):
        url = self.provider.url + 'rss/?sec=TV-x264&fr=false'
        logger.log(u"Womble's Index cache update URL: " + url, logger.DEBUG)
        data = self.provider.getURL(url)
        return data

    def _checkAuth(self, data):
        return data != 'Invalid Link'

provider = WombleProvider()
