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
import sqlite3
import time
import urllib
import datetime

import xml.etree.cElementTree as etree

import sickbeard

from sickbeard import exceptions, helpers, classes
from sickbeard import db, tvcache
from sickbeard.common import *
from sickbeard import logger

providerType = "nzb"
providerName = "NZBMatrix"

def isActive():
	return sickbeard.NZBMATRIX and sickbeard.USE_NZB

def downloadNZB (nzb):

	logger.log("Downloading an NZB from NZBMatrix at " + nzb.url)

	fileName = os.path.join(sickbeard.NZB_DIR, nzb.extraInfo[0] + ".nzb.gz")
	
	logger.log("Saving to " + fileName, logger.DEBUG)

	urllib.urlretrieve(nzb.url, fileName)

	return True
	
	
def findEpisode (episode, forceQuality=None, manualSearch=False):

	if episode.status == DISCBACKLOG:
		logger.log("NZBMatrix doesn't support disc backlog. Use newzbin or download it manually from NZBMatrix")
		return []

	logger.log("Searching NZBMatrix for " + episode.prettyName(True))

	if forceQuality != None:
		epQuality = forceQuality
	elif episode.show.quality == BEST:
		epQuality = ANY
	else:
		epQuality = episode.show.quality
	
	if epQuality == SD:
		quality = {"catid": 6}
	elif epQuality == HD:
		quality = {"catid": 41}
	else:
		quality = {"catid": "tv-all"}
	
	myCache = NZBMatrixCache()
	
	myCache.updateCache()
	
	cacheResults = myCache.searchCache(episode.show, episode.season, episode.episode, epQuality)
	logger.log("Cache results: "+str(cacheResults), logger.DEBUG)

	nzbResults = []

	for curResult in cacheResults:
		
		title = curResult["name"]
		url = curResult["url"]
	
		logger.log("Found result " + title + " at " + url)

		result = classes.NZBSearchResult(episode)
		result.provider = providerName.lower()
		result.url = url 
		result.extraInfo = [title]
		result.quality = epQuality
		
		nzbResults.append(result)

	# if we got some results then use them no matter what.
	# OR
	# return anyway unless we're doing a backlog or manual search
	if nzbResults or not (episode.status in (BACKLOG, MISSED) or manualSearch):
		return nzbResults
	
	sceneSearchStrings = set(sickbeard.helpers.makeSceneSearchString(episode))
	
	results = []

	for curString in sceneSearchStrings:

		for resultDict in _doSearch(curString, quality):

			if epQuality == HD and ("720p" not in resultDict["NZBNAME"] or "itouch" in resultDict["NZBNAME"].lower()):
				logger.log("Ignoring result "+resultDict["NZBNAME"]+" because it doesn't contain 720p in the name", logger.DEBUG)
				continue

			result = classes.NZBSearchResult(episode)
			result.provider = providerName.lower()
			result.url = resultDict["SBURL"]
			result.extraInfo = [resultDict["NZBNAME"]]
			result.quality = epQuality
		
			results.append(result)
					
	return results


def _doSearch(curString, quality):
	params = {"search": curString.replace("."," ").encode('utf-8'), "age": sickbeard.USENET_RETENTION, "username": sickbeard.NZBMATRIX_USERNAME, "apikey": sickbeard.NZBMATRIX_APIKEY}
	params.update(quality)
	
	searchURL = "https://nzbmatrix.com/api-nzb-search.php?" + urllib.urlencode(params)

	logger.log("Search string: " + searchURL, logger.DEBUG)

	logger.log("Sleeping 10 seconds to respect NZBMatrix's API rules")
	time.sleep(10)
	f = urllib.urlopen(searchURL)
	searchResult = "".join(f.readlines())
	f.close()
	
	if searchResult.startswith("error:"):
		err = searchResult.split(":")[1]
		if err == "nothing_found":
			return []
		elif err == "invalid_login" or err == "invalid_api":
			raise exceptions.AuthException("NZBMatrix username or API key is incorrect")
		logger.log("An error was encountered during the search: "+err, logger.ERROR)

	results = []
	
	for curResult in searchResult.split("|"):
		resultDict = {}
		lines = curResult.split("\n")
		for info in lines:
			curInfo = info.strip(";").partition(":")
			if len(curInfo) != 3:
				continue
			resultDict[curInfo[0]] = curInfo[2]

		if len(resultDict) == 0:
			continue

		if "NZBID" not in resultDict:
			continue

		resultDict["SBURL"] = "http://nzbmatrix.com/api-nzb-download.php?id="+resultDict["NZBID"]+"&username="+sickbeard.NZBMATRIX_USERNAME+"&apikey="+sickbeard.NZBMATRIX_APIKEY

		results.append(resultDict)

	return results

def findPropers(date=None):
	
	results = []
	
	for curString in ("PROPER", "REPACK"):
	
		for curQuality in (6,41):
		
			for curResult in _doSearch(curString, {"catid": curQuality}):

				resultDate = datetime.datetime.strptime(curResult["INDEX_DATE"], "%Y-%m-%d %H:%M:%S")
				
				if date == None or resultDate > date:
					results.append(classes.Proper(curResult["NZBNAME"], curResult["SBURL"], resultDate))
	
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
				   'subcat': '6,5,41',
				   'english': 1}

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

