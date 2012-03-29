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



import datetime
import re
import time
import urllib

from xml.dom.minidom import parseString

import sickbeard
import generic

from sickbeard import classes, show_name_helpers, helpers

from sickbeard import exceptions, logger
from sickbeard import tvcache
from sickbeard.exceptions import ex

class NZBsProvider(generic.NZBProvider):

	def __init__(self):

		generic.NZBProvider.__init__(self, "NZBs.org Old")

		self.supportsBacklog = True

		self.cache = NZBsCache(self)

		self.url = 'https://secure.nzbs.org/'

	def isEnabled(self):
		return sickbeard.NZBS

	def _checkAuth(self):
		if sickbeard.NZBS_UID in (None, "") or sickbeard.NZBS_HASH in (None, ""):
			raise exceptions.AuthException("NZBs.org authentication details are empty, check your config")

	def _get_season_search_strings(self, show, season):
		return ['^'+x for x in show_name_helpers.makeSceneSeasonSearchString(show, season)]

	def _get_episode_search_strings(self, ep_obj):
		return ['^'+x for x in show_name_helpers.makeSceneSearchString(ep_obj)]

	def _doSearch(self, curString, show=None):

		curString = curString.replace('.', ' ')

		params = {"action": "search",
				  "q": curString.encode('utf-8'),
				  "dl": 1,
				  "i": sickbeard.NZBS_UID,
				  "h": sickbeard.NZBS_HASH,
				  "age": sickbeard.USENET_RETENTION,
				  "num": 100,
				  "type": 1}

		searchURL = self.url + "rss.php?" + urllib.urlencode(params)

		logger.log(u"Search string: " + searchURL, logger.DEBUG)

		data = self.getURL(searchURL)

		# Pause to avoid 503's
		time.sleep(5)

		if data == None:
			return []

		try:
			parsedXML = parseString(data)
			items = parsedXML.getElementsByTagName('item')
		except Exception, e:
			logger.log(u"Error trying to load NZBs.org RSS feed: "+ex(e), logger.ERROR)
			return []

		results = []

		for curItem in items:
			(title, url) = self._get_title_and_url(curItem)

			if not title or not url:
				logger.log(u"The XML returned from the NZBs.org RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
				continue

			if "&i=" not in url and "&h=" not in url:
				raise exceptions.AuthException("The NZBs.org result URL has no auth info which means your UID/hash are incorrect, check your config")

			results.append(curItem)

		return results

	def findPropers(self, date=None):

		results = []

		for curString in (".PROPER.", ".REPACK."):

			for curResult in self._doSearch(curString):

				(title, url) = self._get_title_and_url(curResult)

				pubDate_node = curResult.getElementsByTagName('pubDate')[0]
				pubDate = helpers.get_xml_text(pubDate_node)

				match = re.search('(\w{3}, \d{1,2} \w{3} \d{4} \d\d:\d\d:\d\d) [\+\-]\d{4}', pubDate)
				if not match:
					continue

				resultDate = datetime.datetime.strptime(match.group(1), "%a, %d %b %Y %H:%M:%S")

				if date == None or resultDate > date:
					results.append(classes.Proper(title, url, resultDate))

		return results

class NZBsCache(tvcache.TVCache):

	def __init__(self, provider):

		tvcache.TVCache.__init__(self, provider)

		# only poll NZBs.org every 15 minutes max
		self.minTime = 15

	def _getRSSData(self):
		url = self.provider.url + 'rss.php?'
		urlArgs = {'type': 1,
				   'dl': 1,
				   'num': 100,
				   'i': sickbeard.NZBS_UID,
				   'h': sickbeard.NZBS_HASH,
				   'age': sickbeard.USENET_RETENTION}

		url += urllib.urlencode(urlArgs)

		logger.log(u"NZBs cache update URL: "+ url, logger.DEBUG)

		data = self.provider.getURL(url)

		return data

	def _checkItemAuth(self, title, url):
		if "&i=" not in url and "&h=" not in url:
			raise exceptions.AuthException("The NZBs.org result URL has no auth info which means your UID/hash are incorrect, check your config")

provider = NZBsProvider()