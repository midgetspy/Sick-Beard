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
from sickbeard.exceptions import ex

class NZBiProvider(generic.NZBProvider):

	def __init__(self):

		generic.NZBProvider.__init__(self, "nzbindex.nl")

		self.supportsBacklog = True

		self.url = 'http://www.nzbindex.nl'
		self.searchString = ''

	def isEnabled(self):
		return sickbeard.NZBI

	def _get_season_search_strings(self, show, season):
		return ['^'+x for x in show_name_helpers.makeSceneSeasonSearchString(show, season)]

	def _get_episode_search_strings(self, ep_obj):
		return ['^'+x for x in show_name_helpers.makeSceneSearchString(ep_obj)]

	def _doSearch(self, curString, show=None):

		curString = curString.replace('.', ' ')
		curString = curString.replace('^', '')
		showName = curString
		self.searchString = showName.replace(" ",".")
		curString = curString + " -sub"
		logger.log(u"Search string: " + curString, logger.DEBUG)
		#http://www.nzbindex.nl/rss/?q=person+of+interest+s01e02&sort=agedesc&max=25
		params = { "q": curString.encode('utf-8'),
				   "sort": "agedesc",
				   "minsize": "200",
				   "max": 250}

		searchURL = self.url + "/rss/?" + urllib.urlencode(params)

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
			logger.log(u"Error trying to load NZBindex.nl RSS feed: "+ex(e), logger.ERROR)
			return []

		results = []

		for curItem in items:
			(title, url) = self._get_title_and_url(curItem)

			if not title or not url:
				logger.log(u"The XML returned from the NZBindex.nl RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
				continue
			if not title == 'Not_Valid':
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
	def _get_title_and_url(self, item):
		showName = self.searchString
		title = helpers.get_xml_text(item.getElementsByTagName('title')[0])
		try:
			if title.count(showName) == 1:
				titleStart = title.index(showName)
				titleEnd = title.index(" ",titleStart)
				title = title[titleStart:titleEnd]
			elif title.count(showName) > 1:
				titleStart = title.rindex(showName)
				titleEnd = title.index(" ",titleStart)
				title = title[titleStart:titleEnd]
			else:
				title = "Not_Valid"
		except ValueError:
			title = "Not_Valid"
		try:
			url = item.getElementsByTagName('enclosure')[0].getAttribute('url')
			if url:
				url = url.replace('&amp;','&')
		except IndexError:
				url = None

		return (title, url)

provider = NZBiProvider()