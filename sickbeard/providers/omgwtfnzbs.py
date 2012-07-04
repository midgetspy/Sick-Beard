# Author: James Cox <james@imaj.es>
# Based on nzbsrus.py by Nic Wolfe <nic@wolfeden.ca>
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

import sickbeard

from sickbeard import exceptions, logger

from sickbeard import tvcache

import generic

class OMGWTFNZBSProvider(generic.NZBProvider):

	def __init__(self):

		generic.NZBProvider.__init__(self, "omgwtfnzbs")

		self.cache = OmgWtfNzbsCache(self)

		self.url = 'http://rss.omgwtfnzbs.com/'

	def isEnabled(self):
		return sickbeard.OMGWTFNZBS

	def _checkAuth(self):
		if sickbeard.OMGWTFNZBS_UID in (None, "") or sickbeard.OMGWTFNZBS_HASH in (None, ""):
			raise exceptions.AuthException("omgwtfnzbs authentication details are empty, check your config")


class OmgWtfNzbsCache(tvcache.TVCache):

	def __init__(self, provider):

		tvcache.TVCache.__init__(self, provider)

		# only poll omgwtfnzbs every 15 minutes max
		self.minTime = 15


	def _getRSSData(self):

		url = self.provider.url + 'rss-search.php?'
		urlArgs = {'catid': '19,20',
				   'user': sickbeard.OMGWTFNZBS_UID,
				   'api': sickbeard.OMGWTFNZBS_HASH}

		url += urllib.urlencode(urlArgs)

		logger.log(u"omgwtfnzbs cache update URL: "+ url, logger.DEBUG)

		data = self.provider.getURL(url)

		return data

	def _checkAuth(self, data):
		return data != 'Invalid Link'

provider = OMGWTFNZBSProvider()
