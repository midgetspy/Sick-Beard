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
providerName = "NZBsRUS"

urllib._urlopener = classes.SickBeardURLopener()

def isActive():
	return sickbeard.NZBSRUS and sickbeard.USE_NZB

def getNZBsURL (url):

	result = None

	try:
		f = urllib.urlopen(url)
		result = "".join(f.readlines())
	except (urllib.ContentTooShortError, IOError), e:
		logger.log("Error loading NZBs'R'US URL: " + str(sys.exc_info()) + " - " + str(e), logger.ERROR)
		return None

	return result

						
def downloadNZB (nzb):

	logger.log("Downloading an NZB from NZBs'R'US at " + nzb.url)

	data = getNZBsURL(nzb.url)
	
	if data == None:
		return False
	
	fileName = os.path.join(sickbeard.NZB_DIR, nzb.name + ".nzb")
	
	logger.log("Saving to " + fileName, logger.DEBUG)
	
	fileOut = open(fileName, "w")
	fileOut.write(data)
	fileOut.close()

	return True
	
	
def searchRSS():
	myCache = NZBsRUSCache()
	myCache.updateCache()
	return myCache.findNeededEpisodes()
	
def findEpisode (episode, manualSearch=False):

	if sickbeard.NZBSRUS_UID in (None, "") or sickbeard.NZBSRUS_HASH in (None, ""):
		raise exceptions.AuthException("NZBs'R'US authentication details are empty, check your config")

	logger.log("Searching NZBs'R'US for " + episode.prettyName(True))

	myCache = NZBsRUSCache()
	myCache.updateCache()
	
	nzbResults = myCache.searchCache(episode, manualSearch)
	logger.log("Cache results: "+str(nzbResults), logger.DEBUG)

	return nzbResults
		

def findSeasonResults(show, season):
	
	return {}		

def findPropers(date=None):

	results = NZBsRUSCache().listPropers(date)
	
	return [classes.Proper(x['name'], x['url'], datetime.datetime.fromtimestamp(x['time'])) for x in results]

class NZBsRUSCache(tvcache.TVCache):
	
	def __init__(self):

		tvcache.TVCache.__init__(self, providerName.lower())

		# only poll NZBs'R'US every 15 minutes max
		self.minTime = 15
		
	
	def updateCache(self):

		if not self.shouldUpdate():
			return
		
		url = 'http://www.nzbsrus.com/rssfeed.php?'
		urlArgs = {'cat': '91,75',
				   'i': sickbeard.NZBSRUS_UID,
				   'h': sickbeard.NZBSRUS_HASH}

		url += urllib.urlencode(urlArgs)
		
		logger.log("NZBs'R'US cache update URL: "+ url, logger.DEBUG)
		
		data = getNZBsURL(url)
		
		# as long as the http request worked we count this as an update
		if data:
			self.setLastUpdate()
		
		# now that we've loaded the current RSS feed lets delete the old cache
		logger.log("Clearing cache and updating with new information")
		self._clearCache()
		
		if data == 'Invalid Link':
			raise exceptions.AuthException("Your UID/hash for NZBs'R'US is incorrect.")
		
		try:
			responseSoup = etree.ElementTree(etree.XML(data))
			items = responseSoup.getiterator('item')
		except Exception, e:
			logger.log("Error trying to load NZBs'R'US RSS feed: "+str(e), logger.ERROR)
			return []
			
		for item in items:

			title = item.findtext('title')
			url = item.findtext('link')

			if not title or not url:
				logger.log("The XML returned from the NZBs'R'US RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
				continue
			
			url = url.replace('&amp;','&')

			logger.log("Adding item from RSS to cache: "+title, logger.DEBUG)			

			self._addCacheEntry(title, url)

