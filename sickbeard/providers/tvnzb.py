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
import sickbeard.classes
from sickbeard import helpers
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

		result = sickbeard.classes.NZBSearchResult(episode)
		result.provider = 'tvnzb'
		result.url = url 
		result.extraInfo = [title]
		result.quality = epQuality
		
		nzbResults.append(result)

	return nzbResults
		

class TVNZBDBConnection(db.DBConnection):

	def __init__(self):
		db.DBConnection.__init__(self, "cache.db")

		# Create the table if it's not already there
		try:
			sql = "CREATE TABLE tvnzb (name TEXT, season NUMERIC, episode NUMERIC, tvdbid NUMERIC, url TEXT, time NUMERIC, quality TEXT);"
			self.connection.execute(sql)
			self.connection.commit()
		except sqlite3.OperationalError, e:
			if str(e) != "table tvnzb already exists":
				raise


class TVNZBCache(tvcache.TVCache):
	
	def __init__(self):

		# only poll TVNZB every 10 minutes
		self.minTime = 10
		
		tvcache.TVCache.__init__(self, "tvnzb")
	
	def _getDB(self):
		return TVNZBDBConnection()
	
	def _addCacheEntry(self, name, season, episode, url):
	
		myDB = self._getDB()

		tvdbid = 0

		# for each show in our list
		for curShow in sickbeard.showList:
	
			# get the scene name masks
			sceneNames = set(helpers.makeSceneShowSearchStrings(curShow))
	
			# for each scene name mask
			for curSceneName in sceneNames:
	
				# if it matches
				if name.lower().startswith(curSceneName.lower()):
					logger.log("Successful match! Result "+name+" matched to show "+curShow.name, logger.DEBUG)
					
					# set the tvdbid in the db to the show's tvdbid
					tvdbid = curShow.tvdbid
					
					# since we found it, break out
					break
			
			# if we found something in the inner for loop break out of this one
			if tvdbid != 0:
				break

		# get the current timestamp
		curTimestamp = int(time.mktime(datetime.datetime.today().timetuple()))
		
		if any(x in name.lower() for x in ("720p", "1080p", "x264")):
			quality = HD
		elif any(x in name.lower() for x in ("xvid", "divx")):
			quality = SD
		else:
			logger.log("Unable to figure out the quality of "+name+", assuming SD", logger.DEBUG)
			quality = SD
		
		myDB.action("INSERT INTO tvnzb (name, season, episode, tvdbid, url, time, quality) VALUES (?,?,?,?,?,?,?)",
					[name, season, episode, tvdbid, url, curTimestamp, quality])

	def updateCache(self):

		myDB = self._getDB()

		# get the timestamp of the last update
		sqlResults = myDB.select("SELECT * FROM "+self.providerName+" ORDER BY time DESC LIMIT 1")
		if len(sqlResults) == 0:
			lastTimestamp = 0
		else:
			lastTimestamp = int(sqlResults[0]["time"])		

		# if we've updated recently then skip the update
		if datetime.datetime.today() - datetime.datetime.fromtimestamp(lastTimestamp) < datetime.timedelta(minutes=self.minTime):
			logger.log("Last update was too soon, using old cache", logger.DEBUG)
			return
				
		# get all records since the last timestamp
		url = "http://www.tvnzb.com/tvnzb_new.rss"
		
		logger.log("TVNZB cache update URL: "+ url, logger.DEBUG)
		
		data = getTVNZBURL(url)
		
		# now that we've loaded the current RSS feed lets delete the old cache
		logger.log("Clearing cache and updating with new information")
		self._clearCache()
		
		try:
			responseSoup = etree.ElementTree(element = etree.XML(data))
		except (SyntaxError), e:
			logger.log("Invalid XML returned by TVNZB: " + str(sys.exc_info()) + " - " + str(e), logger.ERROR)
			return

		items = responseSoup.getiterator('item')
			
		for item in items:

			if item.findtext('title') == None or item.findtext('link') == None:
				logger.log("The XML returned from the TVNZB RSS feed is incomplete, this result is unusable: "+str(item), logger.ERROR)
				continue

			title = item.findtext('title')
			url = item.findtext('link')

			logger.log("Adding item from RSS to cache: "+title, logger.DEBUG)			

			season = int(item.findtext('season'))
			episode = int(item.findtext('episode'))

			self._addCacheEntry(title, season, episode, url)
