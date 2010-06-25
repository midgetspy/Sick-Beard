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
import sys


import sickbeard
import generic

from sickbeard import helpers, classes, exceptions, logger
from sickbeard import tvcache

from sickbeard.common import *

class TVBinzProvider(generic.NZBProvider):
	
	def __init__(self):
		
		generic.NZBProvider.__init__(self, "TVBinz")
		
		self.cache = TVBinzCache(self)
		
		self.url = 'http://www.tvbinz.net/'

	def isEnabled(self):
		return sickbeard.TVBINZ

	def _checkAuth(self):
		if sickbeard.TVBINZ_UID in (None, "") or sickbeard.TVBINZ_HASH in (None, "") or sickbeard.TVBINZ_AUTH in (None, ""):
			raise exceptions.AuthException("TVBinz authentication details are empty, check your config")

	def getURL (self, url):
	
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


def findEpisode (episode, manualSearch=False):

	nzbResults = generic.NZBProvider.findEpisode(self, episode, manualSearch)

	# append auth
	urlParams = {'i': sickbeard.TVBINZ_SABUID, 'h': sickbeard.TVBINZ_HASH}
	for curResult in nzbResults:
		curResult.url += "&" + urllib.urlencode(urlParams) 

	return nzbResults
		


class TVBinzCache(tvcache.TVCache):
	
	def __init__(self, provider):

		# only poll TVBinz every 10 minutes max
		self.minTime = 10
		
		tvcache.TVCache.__init__(self, provider)
	
	def getRSSData(self):
		# get all records since the last timestamp
		url = self.url + "rss.php?"
		
		urlArgs = {'normalize': 1012,
				   'n': 100,
				   'maxage': sickbeard.USENET_RETENTION,
				   'seriesinfo': 1,
				   'nodupes': 1,
				   'sets': 'none'}

		url += urllib.urlencode(urlArgs)
		
		logger.log("TVBinz cache update URL: "+ url, logger.DEBUG)
		
		data = self.provider.getURL(url)
		
		return data
	
	def _parseItem(self, item):

		if item.findtext('title') != None and item.findtext('title') == "You must be logged in to view this feed":
			raise exceptions.AuthException("TVBinz authentication details are incorrect, check your config")

		if item.findtext('title') == None or item.findtext('link') == None:
			logger.log("The XML returned from the TVBinz RSS feed is incomplete, this result is unusable: "+str(item), logger.ERROR)
			return

		title = item.findtext('title')
		url = item.findtext('link').replace('&amp;', '&')

		sInfo = item.find('{http://tvbinz.net/rss/tvb/}seriesInfo')
		if sInfo == None:
			logger.log("No series info, this is some kind of non-standard release, ignoring it", logger.DEBUG)
			return

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

provider = TVBinzProvider()