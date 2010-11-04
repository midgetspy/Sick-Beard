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

from sickbeard import exceptions, logger

from sickbeard.common import *
from sickbeard import tvcache

import generic

class NZBsRUSProvider(generic.NZBProvider):
	
	def __init__(self):
		
		generic.NZBProvider.__init__(self, "NZBs'R'US")
		
		self.cache = NZBsRUSCache(self)
		
		self.url = 'http://www.nzbsrus.com/'

	def isEnabled(self):
		return sickbeard.NZBSRUS

	def _checkAuth(self):
		if sickbeard.NZBSRUS_UID in (None, "") or sickbeard.NZBSRUS_HASH in (None, ""):
			raise exceptions.AuthException("NZBs'R'US authentication details are empty, check your config")	
		

class NZBsRUSCache(tvcache.TVCache):
	
	def __init__(self, provider):

		tvcache.TVCache.__init__(self, provider)

		# only poll NZBs'R'US every 15 minutes max
		self.minTime = 15
		
	
	def _getRSSData(self):

		url = self.provider.url + 'rssfeed.php?'
		urlArgs = {'cat': '91,75',
				   'i': sickbeard.NZBSRUS_UID,
				   'h': sickbeard.NZBSRUS_HASH}

		url += urllib.urlencode(urlArgs)
		
		logger.log(u"NZBs'R'US cache update URL: "+ url, logger.DEBUG)
		
		data = self.provider.getURL(url)
		
		return data
	
	def _checkAuth(self, data):
		return data != 'Invalid Link'

provider = NZBsRUSProvider()