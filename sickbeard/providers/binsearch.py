# Author: Brenden Pereira Carvalho <BrendenCarvalho@hotmail.com>
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

import sickbeard

from sickbeard import exceptions, logger

from sickbeard import tvcache

import generic

class BinSearchProvider(generic.NZBProvider):

        def __init__(self):

                generic.NZBProvider.__init__(self, "BinSearch")

                self.cache = BinSearchCache(self)

                self.url = 'http://rss.binsearch.net/'

        def isEnabled(self):
                return sickbeard.BINSEARCH

        def imageName(self):
            return 'binsearch.png'

        def _checkAuth(self):
                if sickbeard.BINSEARCH_MAX in (None, "") or sickbeard.BINSEARCH_ALT in (None, ""):
                        raise exceptions.AuthException("binsearch parameters details are empty, check your config")


class BinSearchCache(tvcache.TVCache):

        def __init__(self, provider):

                tvcache.TVCache.__init__(self, provider)

                # only poll binsearch every 30 minutes max
                self.minTime = 30

        def _getRSSData(self):

                url = self.provider.url + 'rss.php?'
                urlArgs = {'max': sickbeard.BINSEARCH_MAX,'g': sickbeard.BINSEARCH_ALT}

                url += urllib.urlencode(urlArgs)

                logger.log(u"binsearch cache update URL: "+ url, logger.DEBUG)

                data = self.provider.getURL(url)

                return data

        def _checkAuth(self, data):
                return data != 'Invalid Link'

provider = BinSearchProvider()
