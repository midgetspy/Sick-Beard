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



import time
import urllib
import datetime

import xml.etree.cElementTree as etree

import sickbeard
import generic

from sickbeard import classes, logger, sceneHelpers
from sickbeard import tvcache
from sickbeard.common import *

from lib.tvnamer.utils import FileParser
from lib.tvnamer import tvnamer_exceptions

class NZBMatrixProvider(generic.NZBProvider):
	
	def __init__(self):
		
		generic.NZBProvider.__init__(self, "NZBMatrix")
		
		self.cache = NZBMatrixCache(self)
		
		self.url = 'http://www.nzbmatrix.com/'

	def isEnabled(self):
		return sickbeard.NZBS

	
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
				logger.log("Unable to parse the filename "+title+" into a valid episode", logger.ERROR)
				continue
			
			quality = Quality.nameQuality(title)
			
			if not episode.show.wantEpisode(episode.season, episode.episode, quality, manualSearch):
				logger.log("Ignoring result "+title+" because we don't want an episode that is "+Quality.qualityStrings[quality], logger.DEBUG)
				continue
			
			logger.log("Found result " + title + " at " + url, logger.DEBUG)
			
			result = self.getResult([episode])
			result.provider = self.getID()
			result.url = url
			result.name = title
			result.quality = quality
			
			results.append(result)
			
		return results
	
	
	def findSeasonResults(self, show, season):
		
		itemList = []
		results = {}
	
		for curString in sceneHelpers.makeSceneSeasonSearchString(show, season, "nzbmatrix"):
			itemList += self._doSearch(curString)
	
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
			result.provider = self.getID()
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
	
	
	def _doSearch(self, curString, quotes=False):
	
		term = curString.replace("."," ").encode('utf-8')
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
	
		logger.log("Search string: " + searchURL, logger.DEBUG)
	
		logger.log("Sleeping 10 seconds to respect NZBMatrix's rules")
		time.sleep(10)
	
		f = urllib.urlopen(searchURL)
		searchResult = "".join(f.readlines())
		f.close()
		
		if not searchResult:
			return []
	
		try:
			responseSoup = etree.ElementTree(etree.XML(searchResult))
			items = responseSoup.getiterator('item')
		except Exception, e:
			logger.log("Error trying to load NZBMatrix RSS feed: "+str(e), logger.ERROR)
			return []
			
		results = []
		
		for curItem in items:
			title = curItem.findtext('title')
			url = curItem.findtext('link')
	
			if not title or not url:
				logger.log("The XML returned from the NZBMatrix RSS feed is incomplete, this result is unusable", logger.ERROR)
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
				logger.log("Unable to figure out the date for entry "+title+", skipping it")
				continue
			else:
				resultDate = datetime.datetime.strptime(dateStr, "%Y-%m-%d %H:%M:%S")
	
			if date == None or resultDate > date:
				results.append(classes.Proper(title, url, resultDate))
	
		return results


class NZBMatrixCache(tvcache.TVCache):
	
	def __init__(self, provider):

		# only poll NZBMatrix every 25 minutes max
		self.minTime = 25
		
		tvcache.TVCache.__init__(self, provider)
	
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
		
		logger.log("NZBMatrix cache update URL: "+ url, logger.DEBUG)
		
		data = self.provider.getURL(url)
		
		return data
	

provider = NZBMatrixProvider()