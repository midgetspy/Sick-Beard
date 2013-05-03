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
		# use the newznab constructor, the parameters used here are only default values because at startup the config file isn't read
		newznab.NewznabProvider.__init__(self, "kerews", "http://kere.ws/",  None)
		self.catIDs="2000,8000"
		#self.enabled = 1

		self.cache = KereWSCache(self)

	def isEnabled(self):
		return sickbeard.KEREWS

	def _doSearch(self, search_params, show=None, max_age=0):

		params = {"t": "tvsearch",
				"maxage": sickbeard.USENET_RETENTION,
				"limit": 100,
				"cat": sickbeard.KEREWS_CATIDS}

		if search_params:
			params.update(search_params)

		if sickbeard.KEREWS_APIKEY:
			params['apikey'] = sickbeard.KEREWS_APIKEY

		searchURL = sickbeard.KEREWS_URL + 'api?' + urllib.urlencode(params)

		logparams = params
		logparams['apikey'] = "XXXXXXXXXXXXXX"
		logURL = sickbeard.KEREWS_URL + 'api?' + urllib.urlencode(logparams)

		logger.log(u"Search url: " + logURL, logger.DEBUG)

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

		params = {"t": "tvsearch",
				"age": sickbeard.USENET_RETENTION,
				"cat": sickbeard.KEREWS_CATIDS}

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
