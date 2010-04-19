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

	searchHeaders = {"Cookie": "uid=" + sickbeard.TVBINZ_UID + ";hash=" + sickbeard.TVBINZ_HASH + ";auth=" + sickbeard.TVBINZ_AUTH, 'Accept-encoding': 'gzip'}
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
	
	fileName = os.path.join(sickbeard.NZB_DIR, nzb.extraInfo[0] + ".nzb")
	
	logger.log("Saving to " + fileName, logger.DEBUG)
	
	fileOut = open(fileName, "w")
	fileOut.write(data)
	fileOut.close()

	return True
	
	
def findEpisode (episode, forceQuality=None):

	if episode.status == DISCBACKLOG:
		logger.log("TVbinz doesn't support disc backlog. Use Newzbin or download it manually from TVbinz")
		return []

	if sickbeard.TVBINZ_UID in (None, "") or sickbeard.TVBINZ_HASH in (None, "") or sickbeard.TVBINZ_AUTH in (None, ""):
		raise exceptions.AuthException("TVBinz authentication details are empty, check your config")
	
	logger.log("Searching tvbinz for " + episode.prettyName(True))

	if forceQuality != None:
		epQuality = forceQuality
	elif episode.show.quality == BEST:
		epQuality = ANY
	else:
		epQuality = episode.show.quality
	
	myCache = TVBinzCache()
	
	myCache.updateCache()
	
	cacheResults = myCache.searchCache(episode.show, episode.season, episode.episode, epQuality)
	logger.log("Cache results: "+str(cacheResults), logger.DEBUG)

	nzbResults = []

	for curResult in cacheResults:
		
		title = curResult["name"]
		url = curResult["url"]
		urlParams = {'i': sickbeard.TVBINZ_SABUID, 'h': sickbeard.TVBINZ_HASH}
	
		logger.log("Found result " + title + " at " + url)

		result = classes.NZBSearchResult(episode)
		result.provider = 'tvbinz'
		result.url = url + "&" + urllib.urlencode(urlParams) 
		result.extraInfo = [title]
		result.quality = epQuality
		
		nzbResults.append(result)

	return nzbResults
		

def findPropers(date=None):

	results = TVBinzCache().listPropers(date)
	
	return [classes.Proper(x['name'], x['url'], datetime.datetime.fromtimestamp(x['time'])) for x in results]
	

class TVBinzDBConnection(db.DBConnection):

	def __init__(self):
		db.DBConnection.__init__(self, "cache.db")

		# Create the table if it's not already there
		try:
			sql = "CREATE TABLE tvbinz (name TEXT, season NUMERIC, episode NUMERIC, tvrid NUMERIC, tvdbid NUMERIC, url TEXT, time NUMERIC, quality TEXT);"
			self.connection.execute(sql)
			self.connection.commit()
		except sqlite3.OperationalError, e:
			if str(e) != "table tvbinz already exists":
				raise


class TVBinzCache(tvcache.TVCache):
	
	def __init__(self):

		# only poll TVBinz every 10 minutes max
		self.minTime = 10
		
		tvcache.TVCache.__init__(self, "tvbinz")
	
	def _getDB(self):
		return TVBinzDBConnection()
	
	def _addCacheEntry(self, name, season, episode, tvrid, url, quality):
	
		myDB = self._getDB()

		tvdbid = 0

		tvrShow = helpers.findCertainTVRageShow(sickbeard.showList, tvrid)

		if tvrShow == None:

			logger.log("No show in our list that already matches the TVRage ID, trying to match names", logger.DEBUG)

			# for each show in our list
			for curShow in sickbeard.showList:
		
				# get the scene name masks\
				sceneNames = set(helpers.makeSceneShowSearchStrings(curShow))

				# for each scene name mask
				for curSceneName in sceneNames:

					# if it matches
					if name.startswith(curSceneName):
						logger.log("Successful match! Result "+name+" matched to show "+curShow.name, logger.DEBUG)
						
						# set the tvrid of the show to tvrid
						with curShow.lock:
							curShow.tvrid = tvrid
							curShow.saveToDB()
						
						# set the tvdbid in the db to the show's tvdbid
						tvdbid = curShow.tvdbid
						
						# since we found it, break out
						break
				
				# if we found something in the inner for loop break out of tchis one
				if tvdbid != 0:
					break

			if tvdbid == 0:
				logger.log("Unable to find a match for this show in the cache", logger.DEBUG)
		
		else:
			tvdbid = tvrShow.tvdbid

		# get the current timestamp
		curTimestamp = int(time.mktime(datetime.datetime.today().timetuple()))
		
		myDB.action("INSERT INTO tvbinz (name, season, episode, tvrid, tvdbid, url, time, quality) VALUES (?,?,?,?,?,?,?,?)",
					[name, season, episode, tvrid, tvdbid, url, curTimestamp, quality])

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
		url = "https://tvbinz.net/rss.php?"
		
		urlArgs = {'normalize': 1012, 'n': 100, 'maxage': 400, 'seriesinfo': 1, 'nodupes': 1, 'sets': 'none'}

		url += urllib.urlencode(urlArgs)
		
		logger.log("TVBinz cache update URL: "+ url, logger.DEBUG)
		
		data = getTVBinzURL(url)
		
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

			quality = sInfo.findtext('{http://tvbinz.net/rss/tvb/}quality')
			if quality == "HD":
				quality = HD
			else:
				quality = SD
			
			season = int(sInfo.findtext('{http://tvbinz.net/rss/tvb/}seasonNum'))
			epNum = sInfo.findtext('{http://tvbinz.net/rss/tvb/}episodeNum')
			if epNum == '':
				epNum = 0
			episode = int(epNum)

			if sInfo.findtext('{http://tvbinz.net/rss/tvb/}tvrID') == None:
				tvrid = 0
			else:
				tvrid = int(sInfo.findtext('{http://tvbinz.net/rss/tvb/}tvrID'))
			
			self._addCacheEntry(title, season, episode, tvrid, url, quality)

