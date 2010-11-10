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

import re
import time
import urllib
import datetime

import xml.etree.cElementTree as etree

import sickbeard
import generic

from sickbeard import classes, logger, sceneHelpers, db
from sickbeard import tvcache
from sickbeard.common import *

from lib.tvnamer.utils import FileParser
from lib.tvnamer import tvnamer_exceptions

class NZBMatrixProvider(generic.NZBProvider):

	def __init__(self):

		generic.NZBProvider.__init__(self, "NZBMatrix")

		self.supportsBacklog = True

		self.cache = NZBMatrixCache(self)

		self.url = 'http://www.nzbmatrix.com/'

	def isEnabled(self):
		return sickbeard.NZBMATRIX

	def findSeasonResults(self, show, season):
		
		results = {}
		
		if show.is_air_by_date:
			logger.log(u"NZBMatrix doesn't support air-by-date backlog because of a bug in their RSS search. Pressure them to fix it!", logger.WARNING)
			return results
		
		results = generic.NZBProvider.findSeasonResults(self, show, season)
		
		return results


	def findEpisode (self, episode, manualSearch=False):

		nzbResults = generic.NZBProvider.findEpisode(self, episode, manualSearch)

		# if we got some results then use them no matter what.
		# OR
		# return anyway unless we're doing a manual search
		if nzbResults or not manualSearch:
			return nzbResults

		sceneSearchStrings = set(sceneHelpers.makeSceneSearchString(episode))

		results = []

		# search for all show names and episode numbers like ("a","b","c") in a single search
		nzbMatrixSearchString = '("' + '","'.join(sceneSearchStrings) + '")'
		itemList = self._doSearch(nzbMatrixSearchString)

		for item in itemList:

			title = item.findtext('title')
			url = item.findtext('link').replace('&amp;','&')

			# parse the file name
			try:
				myParser = FileParser(title)
				epInfo = myParser.parse()
			except tvnamer_exceptions.InvalidFilename:
				logger.log(u"Unable to parse the name "+title+" into a valid episode", logger.WARNING)
				continue

			quality = self.getQuality(item)

			season = epInfo.seasonnumber if epInfo.seasonnumber != None else 1

			if not episode.show.wantEpisode(season, episode.episode, quality, manualSearch):
				logger.log(u"Ignoring result "+title+" because we don't want an episode that is "+Quality.qualityStrings[quality], logger.DEBUG)
				continue

			logger.log(u"Found result " + title + " at " + url, logger.DEBUG)

			result = self.getResult([episode])
			result.url = url
			result.name = title
			result.quality = quality

			results.append(result)

		return results


	def _get_season_search_strings(self, show, season):
		return sceneHelpers.makeSceneSeasonSearchString(show, season, "nzbmatrix")

	def _doSearch(self, curString, quotes=False):

		term =  re.sub('[\.\-]', ' ', curString).encode('utf-8')
		if quotes:
			term = "\""+term+"\""

		params = {"term": term,
				  "age": sickbeard.USENET_RETENTION,
				  "page": "download",
				  "username": sickbeard.NZBMATRIX_USERNAME,
				  "apikey": sickbeard.NZBMATRIX_APIKEY,
				  "subcat": "6,41",
				  "english": 1}

		searchURL = "http://rss.nzbmatrix.com/rss.php?" + urllib.urlencode(params)

		logger.log(u"Search string: " + searchURL, logger.DEBUG)

		logger.log(u"Sleeping 10 seconds to respect NZBMatrix's rules")
		time.sleep(10)

		searchResult = self.getURL(searchURL)

		if not searchResult:
			return []

		try:
			responseSoup = etree.ElementTree(etree.XML(searchResult))
			items = responseSoup.getiterator('item')
		except Exception, e:
			logger.log(u"Error trying to load NZBMatrix RSS feed: "+str(e).decode('utf-8'), logger.ERROR)
			return []

		results = []

		for curItem in items:
			title = curItem.findtext('title')
			url = curItem.findtext('link')

			if title == 'Error: No Results Found For Your Search':
				continue

			if not title or not url:
				logger.log(u"The XML returned from the NZBMatrix RSS feed is incomplete, this result is unusable", logger.ERROR)
				continue

			results.append(curItem)

		return results


	def findPropers(self, date=None):

		results = []

		for curResult in self._doSearch("(PROPER,REPACK)"):

			title = curResult.findtext('title')
			url = curResult.findtext('link').replace('&amp;','&')

			descriptionStr = curResult.findtext('description')
			dateStr = re.search('<b>Added:</b> (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)', descriptionStr).group(1)
			if not dateStr:
				logger.log(u"Unable to figure out the date for entry "+title+", skipping it")
				continue
			else:
				resultDate = datetime.datetime.strptime(dateStr, "%Y-%m-%d %H:%M:%S")

			if date == None or resultDate > date:
				results.append(classes.Proper(title, url, resultDate))

		return results


class NZBMatrixCache(tvcache.TVCache):

	def __init__(self, provider):

		tvcache.TVCache.__init__(self, provider)

		# only poll NZBMatrix every 25 minutes max
		self.minTime = 25


	def _getRSSData(self):
		# get all records since the last timestamp
		url = "http://rss.nzbmatrix.com/rss.php?"

		urlArgs = {'page': 'download',
				   'username': sickbeard.NZBMATRIX_USERNAME,
				   'apikey': sickbeard.NZBMATRIX_APIKEY,
				   'english': 1,
				   'scenename': 1,
				   'subcat': '6,41'}

		url += urllib.urlencode(urlArgs)

		logger.log(u"NZBMatrix cache update URL: "+ url, logger.DEBUG)

		data = self.provider.getURL(url)

		return data


provider = NZBMatrixProvider()