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
import time

import xml.etree.cElementTree as etree

import sickbeard
import generic

from sickbeard import classes, sceneHelpers

from sickbeard import exceptions
from sickbeard.common import *
from sickbeard import logger
from sickbeard import tvcache

from lib.tvnamer.utils import FileParser
from lib.tvnamer import tvnamer_exceptions

class NZBsProvider(generic.NZBProvider):
	
	def __init__(self):
		
		generic.NZBProvider.__init__(self, "NZBs.org")
		
		self.cache = NZBsCache(self)
		
		self.url = 'http://www.nzbs.org/'

	def isEnabled(self):
		return sickbeard.NZBS

	def _checkAuth(self):
		if sickbeard.NZBS_UID in (None, "") or sickbeard.NZBS_HASH in (None, ""):
			raise exceptions.AuthException("NZBs.org authentication details are empty, check your config")

	def findEpisode (self, episode, manualSearch=False):
	
		nzbResults = generic.NZBProvider.findEpisode(self, episode, manualSearch)
	
		# if we got some results then use them no matter what.
		# OR
		# return anyway unless we're doing a backlog/missing or manual search
		if nzbResults or not manualSearch:
			return nzbResults
	
		sceneSearchStrings = set(sceneHelpers.makeSceneSearchString(episode))
		
		itemList = []
		results = []
	
		for curString in sceneSearchStrings:
			itemList += self._doSearch("^"+curString)
	
		for item in itemList:
			
			title = item.findtext('title')
			url = item.findtext('link')
			
			quality = Quality.nameQuality(title)
			
			if not episode.show.wantEpisode(episode.season, episode.episode, quality, manualSearch):
				logger.log("Ignoring result "+title+" because we don't want an episode that is "+Quality.qualityStrings[quality], logger.DEBUG)
				continue
			
			logger.log("Found result " + title + " at " + url, logger.DEBUG)
			
			result = self.getResult([episode])
			result.url = url
			result.name = title
			result.quality = quality
			
			results.append(result)
			
		return results


	def findSeasonResults(self, show, season):
		
		itemList = []
		results = {}
	
		for curString in sceneHelpers.makeSceneSeasonSearchString(show, season):
			itemList += self._doSearch("^"+curString)
	
		for item in itemList:
	
			title = item.findtext('title')
			url = item.findtext('link')
			
			quality = Quality.nameQuality(title)
			
			# parse the file name
			try:
				myParser = FileParser(title)
				epInfo = myParser.parse()
			except tvnamer_exceptions.InvalidFilename:
				logger.log("Unable to parse the filename "+title+" into a valid episode", logger.ERROR)
				continue
			
			if epInfo.seasonnumber != season:
				logger.log("The result "+title+" doesn't seem to be a valid episode for season "+str(season)+", ignoring")
				continue
			
			# make sure we want the episode
			wantEp = True
			for epNo in epInfo.episodenumbers:
				if not show.wantEpisode(season, epNo, quality):
					logger.log("Ignoring result "+title+" because we don't want an episode that is "+Quality.qualityStrings[quality], logger.DEBUG)
					wantEp = False
					break
			if not wantEp:
				continue
			
			logger.log("Found result " + title + " at " + url, logger.DEBUG)
			
			# make a result object
			epObj = []
			for curEp in epInfo.episodenumbers:
				epObj.append(show.getEpisode(season, curEp))
			
			result = self.getResult(epObj)
			result.url = url
			result.name = title
			result.quality = quality
		
			if len(epObj) == 1:
				epNum = epObj[0].episode
			elif len(epObj) > 1:
				epNum = MULTI_EP_RESULT
				logger.log("Separating multi-episode result to check for later - result contains episodes: "+str(epInfo.episodenumbers), logger.DEBUG)
			elif len(epObj) == 0:
				epNum = SEASON_RESULT
				result.extraInfo = [show]
				logger.log("Separating full season result to check for later", logger.DEBUG)
		
			if epNum in results:
				results[epNum].append(result)
			else:
				results[epNum] = [result]
	
			
		return results
		

	def _doSearch(self, curString):
	
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
	
		logger.log("Search string: " + searchURL, logger.DEBUG)
	
		data = self.getURL(searchURL)
	
		# Pause to avoid 503's
		time.sleep(5)
	
		if data == None:
			return []
	
		try:
			responseSoup = etree.ElementTree(etree.XML(data))
			items = responseSoup.getiterator('item')
		except Exception, e:
			logger.log("Error trying to load NZBs.org RSS feed: "+str(e), logger.ERROR)
			return []
			
		results = []
		
		for curItem in items:
			title = curItem.findtext('title')
			url = curItem.findtext('link')
	
			if not title or not url:
				logger.log("The XML returned from the NZBs.org RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
				continue
	
			url = url.replace('&amp;','&')
	
			if "&i=" not in url and "&h=" not in url:
				raise exceptions.AuthException("The NZBs.org result URL has no auth info which means your UID/hash are incorrect, check your config")
			
			results.append(curItem)
		
		return results

	def findPropers(self, date=None):
	
		results = []
		
		for curString in (".PROPER.", ".REPACK."):
		
			for curResult in self._doSearch(curString):
	
				match = re.search('(\w{3}, \d{1,2} \w{3} \d{4} \d\d:\d\d:\d\d) [\+\-]\d{4}', curResult.findtext('pubDate'))
				if not match:
					continue

				resultDate = datetime.datetime.strptime(match.group(1), "%a, %d %b %Y %H:%M:%S")
				
				if date == None or resultDate > date:
					results.append(classes.Proper(curResult.findtext('title'), curResult.findtext('link'), resultDate))
		
		return results

class NZBsCache(tvcache.TVCache):
	
	def __init__(self, provider):

		# only poll NZBs.org every 15 minutes max
		self.minTime = 15
		
		tvcache.TVCache.__init__(self, provider)
	
	def _getRSSData(self):
		url = self.provider.url + 'rss.php?'
		urlArgs = {'type': 1,
				   'dl': 1,
				   'num': 100,
				   'i': sickbeard.NZBS_UID,
				   'h': sickbeard.NZBS_HASH,
				   'age': sickbeard.USENET_RETENTION}

		url += urllib.urlencode(urlArgs)
		
		logger.log("NZBs cache update URL: "+ url, logger.DEBUG)
		
		data = self.provider.getURL(url)
		
		return data
	
	def _checkItemAuth(self, title, url):
		if "&i=" not in url and "&h=" not in url:
			raise exceptions.AuthException("The NZBs.org result URL has no auth info which means your UID/hash are incorrect, check your config")
	
provider = NZBsProvider()