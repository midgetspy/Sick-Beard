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
import datetime
import re
import os

from xml.dom.minidom import parseString

import sickbeard
import generic
import newznab

from sickbeard import classes
from sickbeard.helpers import sanitizeSceneName
from sickbeard import scene_exceptions
from sickbeard import encodingKludge as ek

from sickbeard import exceptions
from sickbeard import logger
from sickbeard import tvcache
from sickbeard.exceptions import ex

class KereWSProvider(newznab.NewznabProvider):

	def __init__(self):
		# use the newznab constructor, URL and APIKEY will be replaced below in the code
		newznab.NewznabProvider.__init__(self, "kerews", None, None)

		self.cache = KereWSCache(self)

	def configStr(self):
		configStr = self.name + '|' + sickbeard.KEREWS_URL + '|' + sickbeard.KEREWS_APIKEY + '|' + str(int(self.enabled))
		#logger.log(u"Returning ConfigString for kere.ws: " , logger.DEBUG)
		return configStr

	def isEnabled(self):
		return sickbeard.KEREWS

	def _doSearch(self, search_params, show=None):

		# cat 2010,2020,2030,2040 -> TV/Serien-XviD, TV/Serien-DVD, TV/Serien-720p, TV/Serien-1080p
                params = {"t": "tvsearch",
                                  "maxage": sickbeard.USENET_RETENTION,
                                  "limit": 100,
                                  "cat": '2010,2020,2030,2040'}

		# cat 5030 -> TV/SD, 5040 -> TV/HD
		# params = {"t": "tvsearch",
		#		  "maxage": sickbeard.USENET_RETENTION,
		#		  "limit": 100,
		#		  "cat": '5030,5040'}

		# hack this in for now
		if self.getID() == 'nzbs_org':
			params['cat'] += ',5070,5090'

		if search_params:
			params.update(search_params)

		if sickbeard.KEREWS_APIKEY:
			params['apikey'] = sickbeard.KEREWS_APIKEY

		searchURL = sickbeard.KEREWS_URL + 'api?' + urllib.urlencode(params)

		logger.log(u"Search url: " + searchURL, logger.DEBUG)

		data = self.getURL(searchURL)
		
		if not data:
			return []

		# hack this in until it's fixed server side
		if not data.startswith('<?xml'):
			data = '<?xml version="1.0" encoding="ISO-8859-1" ?>' + data

		try:
			parsedXML = parseString(data)
			items = parsedXML.getElementsByTagName('item')
		except Exception, e:
			logger.log(u"Error trying to load "+self.name+" RSS feed: "+ex(e), logger.ERROR)
			logger.log(u"RSS data: "+data, logger.DEBUG)
			return []

		if not self._checkAuthFromData(data):
			return []

		if parsedXML.documentElement.tagName != 'rss':
			logger.log(u"Resulting XML from "+self.name+" isn't RSS, not parsing it", logger.ERROR)
			return []

		results = []

		for curItem in items:
			(title, url) = self._get_title_and_url(curItem)

			if not title or not url:
				logger.log(u"The XML returned from the "+self.name+" RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
				continue

			results.append(curItem)

		return results

class KereWSCache(newznab.NewznabCache):

	def _getRSSData(self):

		# cat 2010,2020,2030,2040 -> TV/Serien-XviD, TV/Serien-DVD, TV/Serien-720p, TV/Serien-1080p
		params = {"t": "tvsearch",
				"age": sickbeard.USENET_RETENTION,
				"cat": '2010,2020,2030,2040'}

		# cat 5030 -> TV/SD, 5040 -> TV/HD
		#params = {"t": "tvsearch",
		#                  "age": sickbeard.USENET_RETENTION,
		#                  "cat": '5040,5030'}

		# hack this in for now
		if self.provider.getID() == 'nzbs_org':
			params['cat'] += ',5070,5090'

		if sickbeard.KEREWS_APIKEY:
			params['apikey'] = sickbeard.KEREWS_APIKEY

		url = sickbeard.KEREWS_URL + 'api?' + urllib.urlencode(params)

		logger.log(self.provider.name + " cache update URL: "+ url, logger.DEBUG)

		data = self.provider.getURL(url)

		# hack this in until it's fixed server side
		if data and not data.startswith('<?xml'):
			data = '<?xml version="1.0" encoding="ISO-8859-1" ?>' + data

		return data

provider = KereWSProvider()