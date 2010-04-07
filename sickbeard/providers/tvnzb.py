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
import sqlite3
import time
import datetime

from lib.tvnamer.utils import FileParser
from lib.tvnamer import tvnamer_exceptions

import xml.etree.cElementTree as etree

import sickbeard
from sickbeard import helpers, classes
from sickbeard import db
from sickbeard import tvcache
from sickbeard import exceptions

from sickbeard.common import *
from sickbeard import logger

providerType = "nzb"
providerName = "TVNZB"

def isActive():
	return sickbeard.TVNZB and sickbeard.USE_NZB

def getTVNZBURL (url):

	result = None

	try:
		f = urllib2.urlopen(url)
		result = "".join(f.readlines())
	except (urllib.ContentTooShortError, IOError), e:
		logger.log("Error loading TVNZB URL: " + str(sys.exc_info()) + " - " + str(e), logger.ERROR)
		return None

	return result

						
def downloadNZB (nzb):

	logger.log("Downloading an NZB from NZBs.org at " + nzb.url)

	data = getTVNZBURL(nzb.url)
	
	if data == None:
		return False
	
	fileName = os.path.join(sickbeard.NZB_DIR, nzb.extraInfo[0] + ".nzb")
	
	logger.log("Saving to " + fileName, logger.DEBUG)
	
	fileOut = open(fileName, "w")
	fileOut.write(data)
	fileOut.close()

	return True
	
def findEpisode (episode, forceQuality=None):

	if episode.status == DISCBACKLOG:
		logger.log("TVNZB doesn't support disc backlog. Use Newzbin or download it manually from TVNZB")
		return []

	logger.log("Searching TVNZB for " + episode.prettyName(True))

	if forceQuality != None:
		epQuality = forceQuality
	elif episode.show.quality == BEST:
		epQuality = ANY
	else:
		epQuality = episode.show.quality
	
	myCache = TVNZBCache()
	
	myCache.updateCache()
	
	cacheResults = myCache.searchCache(episode.show, episode.season, episode.episode, epQuality)
	logger.log("Cache results: "+str(cacheResults), logger.DEBUG)

	nzbResults = []

	for curResult in cacheResults:
		
		title = curResult["name"]
		url = curResult["url"]
	
		logger.log("Found result " + title + " at " + url)

		result = classes.NZBSearchResult(episode)
		result.provider = 'tvnzb'
		result.url = url 
		result.extraInfo = [title]
		result.quality = epQuality
		
		nzbResults.append(result)

	return nzbResults
		
def findPropers(date=None):

	results = TVNZBCache().listPropers(date)
	
	return [classes.Proper(x['name'], x['url'], datetime.datetime.fromtimestamp(x['time'])) for x in results]
	


class TVNZBCache(tvcache.TVCache):
	
	def __init__(self):

		# only poll TVNZB every 10 minutes at the most
		self.minTime = 10
		
		tvcache.TVCache.__init__(self, "tvnzb")
	
	def updateCache(self):

		if not self.shouldUpdate():
			return
			
		# get all records since the last timestamp
		url = "http://www.tvnzb.com/tvnzb_new.rss"
		
		logger.log("TVNZB cache update URL: "+ url, logger.DEBUG)
		
		data = getTVNZBURL(url)
		
		# as long as the http request worked we count this as an update
		if data:
			self.setLastUpdate()
		
		# now that we've loaded the current RSS feed lets delete the old cache
		logger.log("Clearing cache and updating with new information")
		self._clearCache()
		
		try:
			responseSoup = etree.ElementTree(element = etree.XML(data))
		except (SyntaxError, TypeError), e:
			logger.log("Invalid XML returned by TVNZB: " + str(sys.exc_info()) + " - " + str(e), logger.ERROR)
			return

		items = responseSoup.getiterator('item')
			
		for item in items:

			if item.findtext('title') == None or item.findtext('link') == None:
				logger.log("The XML returned from the TVNZB RSS feed is incomplete, this result is unusable: "+str(item), logger.ERROR)
				continue

			title = item.findtext('title')
			desc = item.findtext('description')
			url = item.findtext('link')

			logger.log("Adding item from RSS to cache: "+title, logger.DEBUG)			

			season = int(item.findtext('season'))
			episode = int(item.findtext('episode'))

			self._addCacheEntry(title, url, season, [episode], extraNames=[desc])
				
