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

from __future__ import with_statement

import urllib
import urllib2
import os.path
import sys
import sqlite3
import time
import datetime

import xml.etree.cElementTree as etree

import sickbeard
from sickbeard import helpers, classes
from sickbeard import db
from sickbeard import tvcache
from sickbeard import exceptions

from sickbeard.common import *
from sickbeard import logger

providerType = "nzb"
providerName = "TVBinz"

def isActive():
	return sickbeard.TVBINZ and sickbeard.USE_NZB

def getTVBinzURL (url):

	searchHeaders = {"Cookie": "uid=" + sickbeard.TVBINZ_UID + ";hash=" + sickbeard.TVBINZ_HASH + ";auth=" + sickbeard.TVBINZ_AUTH,
					 'Accept-encoding': 'gzip',
					 'User-Agent': classes.SickBeardURLopener().version}
	req = urllib2.Request(url=url, headers=searchHeaders)
	
	try:
		f = urllib2.urlopen(req)
	except (urllib.ContentTooShortError, IOError), e:
		logger.log("Error loading TVBinz URL: " + str(sys.exc_info()) + " - " + str(e))
		return None

	result = helpers.getGZippedURL(f)

	return result

						
def downloadNZB (nzb):

	logger.log("Downloading an NZB from tvbinz at " + nzb.url)

	data = getTVBinzURL(nzb.url)
	
	if data == None:
		return False
	
	fileName = os.path.join(sickbeard.NZB_DIR, nzb.name + ".nzb")
	
	logger.log("Saving to " + fileName, logger.DEBUG)
	
	fileOut = open(fileName, "w")
	fileOut.write(data)
	fileOut.close()

	return True
	
	
def searchRSS():
	myCache = TVBinzCache()
	myCache.updateCache()
	foundResults = myCache.findNeededEpisodes()
	
	# append auth
	urlParams = {'i': sickbeard.TVBINZ_SABUID, 'h': sickbeard.TVBINZ_HASH}

	for curEp in foundResults:
		for curResult in foundResults[curEp]:
			curResult.url += "&" + urllib.urlencode(urlParams)			

	return foundResults
	
def findEpisode (episode, manualSearch=False):

	if sickbeard.TVBINZ_UID in (None, "") or sickbeard.TVBINZ_HASH in (None, "") or sickbeard.TVBINZ_AUTH in (None, ""):
		raise exceptions.AuthException("TVBinz authentication details are empty, check your config")
	
	logger.log("Searching tvbinz for " + episode.prettyName(True))

	myCache = TVBinzCache()
	myCache.updateCache()
	nzbResults = myCache.searchCache(episode, manualSearch)
	logger.log("Cache results: "+str(nzbResults), logger.DEBUG)

	# append auth
	urlParams = {'i': sickbeard.TVBINZ_SABUID, 'h': sickbeard.TVBINZ_HASH}
	for curResult in nzbResults:
		curResult.url += "&" + urllib.urlencode(urlParams) 

	return nzbResults
		

def findSeasonResults(show, season):
	
	return {}		

def findPropers(date=None):

	results = TVBinzCache().listPropers(date)
	
	return [classes.Proper(x['name'], x['url'], datetime.datetime.fromtimestamp(x['time'])) for x in results]
	

class TVBinzCache(tvcache.TVCache):
	
	def __init__(self):

		# only poll TVBinz every 10 minutes max
		self.minTime = 10
		
		tvcache.TVCache.__init__(self, "tvbinz")
	
	def updateCache(self):

		if not self.shouldUpdate():
			return
			
		# get all records since the last timestamp
		url = "https://tvbinz.net/rss.php?"
		
		urlArgs = {'normalize': 1012, 'n': 100, 'maxage': 400, 'seriesinfo': 1, 'nodupes': 1, 'sets': 'none'}

		url += urllib.urlencode(urlArgs)
		
		logger.log("TVBinz cache update URL: "+ url, logger.DEBUG)
		
		data = getTVBinzURL(url)
		
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

			if item.findtext('title') != None and item.findtext('title') == "You must be logged in to view this feed":
				raise exceptions.AuthException("TVBinz authentication details are incorrect, check your config")

			if item.findtext('title') == None or item.findtext('link') == None:
				logger.log("The XML returned from the TVBinz RSS feed is incomplete, this result is unusable: "+str(item), logger.ERROR)
				continue

			title = item.findtext('title')
			url = item.findtext('link').replace('&amp;', '&')

			sInfo = item.find('{http://tvbinz.net/rss/tvb/}seriesInfo')
			if sInfo == None:
				logger.log("No series info, this is some kind of non-standard release, ignoring it", logger.DEBUG)
				continue

			logger.log("Adding item from RSS to cache: "+title, logger.DEBUG)			

			quality = Quality.nameQuality(title)
			
			season = int(sInfo.findtext('{http://tvbinz.net/rss/tvb/}seasonNum'))

			if sInfo.findtext('{http://tvbinz.net/rss/tvb/}tvrID') == None:
				tvrid = 0
			else:
				tvrid = int(sInfo.findtext('{http://tvbinz.net/rss/tvb/}tvrID'))
			
			# since TVBinz normalizes the scene names it's more reliable to parse the episodes out myself
			# than to rely on it, because it doesn't support multi-episode numbers in the feed
			self._addCacheEntry(title, url, season, tvrage_id=tvrid, quality=quality)
