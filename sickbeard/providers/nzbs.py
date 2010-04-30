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
import urllib2
import os.path
import sys
import datetime
import time

import xml.etree.cElementTree as etree

import sickbeard

from sickbeard import helpers, classes

from sickbeard import exceptions
from sickbeard.common import *
from sickbeard import logger
from sickbeard import tvcache

providerType = "nzb"
providerName = "NZBs"

def isActive():
	return sickbeard.NZBS and sickbeard.USE_NZB

def getNZBsURL (url):

	result = None

	try:
		f = urllib2.urlopen(url)
		result = "".join(f.readlines())
	except (urllib.ContentTooShortError, IOError), e:
		logger.log("Error loading NZBs.org URL: " + str(sys.exc_info()) + " - " + str(e), logger.ERROR)
		return None

	return result

						
def downloadNZB (nzb):

	logger.log("Downloading an NZB from NZBs.org at " + nzb.url)

	data = getNZBsURL(nzb.url)
	
	if data == None:
		return False
	
	fileName = os.path.join(sickbeard.NZB_DIR, nzb.extraInfo[0] + ".nzb")
	
	logger.log("Saving to " + fileName, logger.DEBUG)
	
	fileOut = open(fileName, "w")
	fileOut.write(data)
	fileOut.close()

	return True
	
	
def findEpisode (episode, forceQuality=None, manualSearch=False):

	if episode.status == DISCBACKLOG:
		logger.log("NZBs.org doesn't support disc backlog. Use newzbin or download it manually from NZBs.org")
		return []

	if sickbeard.NZBS_UID in (None, "") or sickbeard.NZBS_HASH in (None, ""):
		raise exceptions.AuthException("NZBs.org authentication details are empty, check your config")

	logger.log("Searching NZBs.org for " + episode.prettyName(True))

	if forceQuality != None:
		epQuality = forceQuality
	elif episode.show.quality == BEST:
		epQuality = ANY
	else:
		epQuality = episode.show.quality
	
	if epQuality == SD:
		quality = {"catid": 1}
	elif epQuality == HD:
		quality = {"catid": 14}
	else:
		quality = {"type": 1}
		
		
	myCache = NZBsCache()
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
	if nzbResults or not (episode.status == BACKLOG or manualSearch):
		return nzbResults

	sceneSearchStrings = set(helpers.makeSceneSearchString(episode))
	
	itemList = []
	results = []

	for curString in sceneSearchStrings:

		itemList += _doSearch("^"+curString, quality)
		
		if len(itemList) > 0:
			break

	for item in itemList:
		
		title = item.findtext('title')
		url = item.findtext('link')
		
		logger.log("Found result " + title + " at " + url, logger.DEBUG)
		
		result = classes.NZBSearchResult(episode)
		result.provider = providerName.lower()
		result.url = url 
		result.extraInfo = [title]
		result.quality = epQuality
		
		results.append(result)
		
	return results
		

def _doSearch(curString, quality):

	params = {"action": "search", "q": curString.encode('utf-8'), "dl": 1, "i": sickbeard.NZBS_UID, "h": sickbeard.NZBS_HASH, "age": sickbeard.USENET_RETENTION}
	params.update(quality)
	
	searchURL = "http://www.nzbs.org/rss.php?" + urllib.urlencode(params)

	logger.log("Search string: " + searchURL, logger.DEBUG)

	data = getNZBsURL(searchURL)

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

		if "subpack" in title.lower():
			logger.log("This result appears to be a subtitle pack, ignoring: "+title, logger.ERROR)
			continue
		
		if "&i=" not in url and "&h=" not in url:
			raise exceptions.AuthException("The NZBs.org result URL has no auth info which means your UID/hash are incorrect, check your config")
		
		results.append(curItem)
	
	return results

def findPropers(date=None):

	results = []
	
	for curString in (".PROPER.", ".REPACK."):
	
		for curResult in _doSearch(curString, {"type": 1}):

			resultDate = datetime.datetime.strptime(curResult.findtext('pubDate'), "%a, %d %b %Y %H:%M:%S +0000")
			
			if date == None or resultDate > date:
				results.append(classes.Proper(curResult.findtext('title'), curResult.findtext('link'), resultDate))
	
	return results

class NZBsCache(tvcache.TVCache):
	
	def __init__(self):

		# only poll NZBMatrix every 10 minutes max
		self.minTime = 25
		
		tvcache.TVCache.__init__(self, providerName.lower())
	
	def updateCache(self):

		if not self.shouldUpdate():
			return
		
		url = 'http://www.nzbs.org/rss.php?'
		urlArgs = {'type': 1,
				   'dl': 1,
				   'num': 100,
				   'i': sickbeard.NZBS_UID,
				   'h': sickbeard.NZBS_HASH,
				   'age': sickbeard.USENET_RETENTION}

		url += urllib.urlencode(urlArgs)
		
		logger.log("NZBs cache update URL: "+ url, logger.DEBUG)
		
		data = getNZBsURL(url)
		
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
			logger.log("Error trying to load TVBinz RSS feed: "+str(e), logger.ERROR)
			return []
			
		for item in items:

			title = item.findtext('title')
			url = item.findtext('link')

			if not title or not url:
				logger.log("The XML returned from the NZBs.org RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
				continue
			
			if "subpack" in title.lower():
				logger.log("This result appears to be a subtitle pack, ignoring: "+title, logger.ERROR)
				continue
			
			if "&i=" not in url and "&h=" not in url:
				raise exceptions.AuthException("The NZBs.org result URL has no auth info which means your UID/hash are incorrect, check your config")

			url = url.replace('&amp;','&')

			logger.log("Adding item from RSS to cache: "+title, logger.DEBUG)			

			self._addCacheEntry(title, url)

