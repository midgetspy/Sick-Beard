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



import os.path
import re
import time
import urllib
import datetime

import xml.etree.cElementTree as etree

import sickbeard

from sickbeard import exceptions, classes, sceneHelpers
from sickbeard import db, tvcache
from sickbeard.common import *
from sickbeard import logger

from lib.tvnamer.utils import FileParser
from lib.tvnamer import tvnamer_exceptions

urllib._urlopen = classes.SickBeardURLOpener()

providerType = "nzb"
providerName = "NZBMatrix"
delimiter = " "

def isActive():
	return sickbeard.NZBMATRIX and sickbeard.USE_NZB

def downloadNZB (nzb):

	logger.log("Downloading an NZB from NZBMatrix at " + nzb.url)

	fileName = os.path.join(sickbeard.NZB_DIR, nzb.name + ".nzb")
	
	logger.log("Saving to " + fileName, logger.DEBUG)

	logger.log("Sleeping 10 seconds before downloading to respect NZBMatrix's rules")
	time.sleep(10)
	urllib.urlretrieve(nzb.url, fileName)

	return True
	
def searchRSS():
	myCache = NZBMatrixCache()
	myCache.updateCache()
	return myCache.findNeededEpisodes()

	
def findEpisode (episode, manualSearch=False):

	logger.log("Searching NZBMatrix for " + episode.prettyName(True))

	myCache = NZBMatrixCache()
	myCache.updateCache()
	nzbResults = myCache.searchCache(episode)
	logger.log("Cache results: "+str(nzbResults), logger.DEBUG)

	# if we got some results then use them no matter what.
	# OR
	# return anyway unless we're doing a manual search
	if nzbResults or not manualSearch:
		return nzbResults
	
	sceneSearchStrings = set(sceneHelpers.makeSceneSearchString(episode))
	
	results = []
	itemList = []

	for curString in sceneSearchStrings:
		itemList += _doSearch(curString, quotes=True)
		
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
		
		
		if epInfo.seasonnumber != episode.season and len(epInfo.episodeNumbers) == 0 and epInfo.episodeNumbers[0] == episode.episode:
			logger.log("The result "+title+" doesn't seem to be a valid episode for this episode, ignoring")
			continue

		quality = Quality.nameQuality(title)
		
		if not episode.show.wantEpisode(episode.season, episode.episode, quality, manualSearch):
			logger.log("Ignoring result "+title+" because we don't want an episode that is "+Quality.qualityStrings[quality], logger.DEBUG)
			continue
		
		logger.log("Found result " + title + " at " + url, logger.DEBUG)
		
		result = classes.NZBSearchResult([episode])
		result.provider = providerName.lower()
		result.url = url
		result.name = title
		result.quality = quality
		
		results.append(result)
		
	return results


def findSeasonResults(show, season):
	
	itemList = []
	results = {}

	for curString in sceneHelpers.makeSceneSeasonSearchString(show, season, "nzbmatrix"):
		itemList += _doSearch(curString)

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
		
		result = classes.NZBSearchResult(epObj)
		result.provider = providerName.lower()
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


def _doSearch(curString, quotes=False):

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
	
	searchURL = "http://services.nzbmatrix.com/rss.php?" + urllib.urlencode(params)

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
			logger.log("The XML returned from the NZBMatrix RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
			continue

		results.append(curItem)
	
	return results


def findPropers(date=None):
	
	results = []
	
	for curResult in _doSearch("(PROPER,REPACK)"):

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
	
	def __init__(self):

		# only poll NZBMatrix every 10 minutes max
		self.minTime = 25
		
		tvcache.TVCache.__init__(self, providerName.lower())
	
	def updateCache(self):

		if not self.shouldUpdate():
			return
		
		# get all records since the last timestamp
		url = "http://services.nzbmatrix.com/rss.php?"

		urlArgs = {'page': 'download',
				   'username': sickbeard.NZBMATRIX_USERNAME,
				   'apikey': sickbeard.NZBMATRIX_APIKEY,
				   'english': 1,
				   'scenename': 1,
				   'subcat': '6,41'}

		url += urllib.urlencode(urlArgs)
		
		logger.log("NZBMatrix cache update URL: "+ url, logger.DEBUG)
		
		try:
			f = urllib.urlopen(url)
			data = "".join(f.readlines())
			f.close()
		except IOError, e:
			logger.log("Unable to load RSS feed from NZBMatrix, skipping: "+str(e), logger.ERROR)
			return []
		
		# as long as the http request worked we count this as an update
		if data:
			self.setLastUpdate()
		
		# now that we've loaded the current RSS feed lets delete the old cache
		logger.log("Clearing cache and updating with new information")
		self._clearCache()
		
		try:
			responseSoup = etree.ElementTree(etree.XML(data))
			items = responseSoup.getiterator('item')
		except Exception, e:
			logger.log("Error trying to load NZBMatrix RSS feed: "+str(e), logger.ERROR)
			return []
			
		for item in items:

			if item.findtext('title') == None or item.findtext('link') == None:
				logger.log("The XML returned from the NZBMatrix RSS feed is incomplete, this result is unusable: "+str(item), logger.ERROR)
				continue

			title = item.findtext('title')
			url = item.findtext('link').replace('&amp;', '&')

			logger.log("Adding item from RSS to cache: "+title, logger.DEBUG)			

			self._addCacheEntry(title, url)
