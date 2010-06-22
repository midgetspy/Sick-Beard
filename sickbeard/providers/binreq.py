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



import urllib

import sickbeard
import generic

from sickbeard import logger

from sickbeard.common import *
from sickbeard import tvcache

class BinReqProvider(generic.NZBProvider):
	
	def __init__(self):
		
		generic.NZBProvider.__init__(self, "BinReq")
		
		self.cache = BinReqCache(self)

	def isEnabled(self):
		return sickbeard.BINREQ


class BinReqCache(tvcache.TVCache):
	
	def __init__(self, provider):

		# only poll Bin-Req every 15 minutes max
		self.minTime = 15
		
		tvcache.TVCache.__init__(self, provider)

	def _getRSSData(self):
		url = 'http://www.bin-req.net/rss.php?'
		urlArgs = {'id': 3}

		url += urllib.urlencode(urlArgs)
		
		logger.log("Bin-Req cache update URL: "+ url, logger.DEBUG)
		
		data = self.provider.getURL(url)
		
		return data
	
	def _checkAuth(self, data):
		return data != 'Invalid Link'

	def _translateLinkURL(self, url):
		return url.replace('&amp;','&').replace('view.php', 'download.php')


provider = BinReqProvider()