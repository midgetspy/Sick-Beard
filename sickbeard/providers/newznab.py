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
import datetime
import re

import xml.etree.cElementTree as etree

import sickbeard
import generic

from sickbeard import classes, sceneHelpers

from sickbeard import exceptions
from sickbeard.common import *
from sickbeard import logger
from sickbeard import tvcache

from lib.tvnamer.utils import FileParser
from lib.tvnamer import tvnamer_exceptions

class NewznabProvider(generic.NZBProvider):
	
	def __init__(self, name, url, key=''):
		
		generic.NZBProvider.__init__(self, name)
		
		self.cache = NewznabCache(self)
		
		self.url = url
		self.key = key
		
		self.enabled = True
		
		self.default = False

	def configStr(self):
		return self.name + '|' + self.url + '|' + self.key + '|' + str(int(self.enabled)) 

	def imageName(self):
		return 'newznab.gif'

	def isEnabled(self):
		return self.enabled

	def findEpisode (self, episode, manualSearch=False):
	
		nzbResults = generic.NZBProvider.findEpisode(self, episode, manualSearch)
	
		# if we got some results then use them no matter what.
		# OR
		# return anyway unless we're doing a backlog/missing or manual search
		if nzbResults or not manualSearch:
			return nzbResults
	
		itemList = []
		results = []
	
		itemList += self._doSearch(episode.show, episode.season, episode.episode)
	
		for item in itemList:
			
			title = item.findtext('title')
			url = item.findtext('link')
			
			quality = Quality.nameQuality(title)
			
			if not episode.show.wantEpisode(episode.season, episode.episode, quality, manualSearch):
				logger.log("Ignoring result "+title+" because we don't want an episode that is "+Quality.qualityStrings[quality], logger.DEBUG)
				continue
			
			logger.log("Found result " + title + " at " + url, logger.DEBUG)
			
			result = self.getResult([episode])
			result.url = url
			result.name = title
			result.quality = quality
			
			results.append(result)
			
		return results


	def findSeasonResults(self, show, season):
		
		results = {}
	
		itemList = self._doSearch(show, season)
	
		for item in itemList:
	
			title = item.findtext('title')
			url = item.findtext('link')
			
			quality = Quality.nameQuality(title)
			
			# parse the file name
			try:
				myParser = FileParser(title)
				epInfo = myParser.parse()
			except tvnamer_exceptions.InvalidFilename:
				logger.log("Unable to parse the name "+title+" into a valid episode", logger.WARNING)
				continue
			
			if (epInfo.seasonnumber != None and epInfo.seasonnumber != season) or (epInfo.seasonnumber == None and season != 1):
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
		

	def _doSearch(self, show, season=None, episode=None, search=None):
	
		params = {"t": "tvsearch",
				  "maxage": sickbeard.USENET_RETENTION,
				  "limit": 100,
				  "cat": '5030,5040'}

		if show:
			params['rid'] = show.tvrid
			if season != None:
				params['season'] = season
		elif search:
			params['q'] = search
		else:
			return []

		if self.key:
			params['apikey'] = self.key
		
		if episode:
			params['ep'] = episode

		searchURL = self.url + 'api?' + urllib.urlencode(params)
	
		logger.log("Search url: " + searchURL, logger.DEBUG)
	
		data = self.getURL(searchURL)
	
		if data == None:
			return []
	
		try:
			responseSoup = etree.ElementTree(etree.XML(data))
			items = responseSoup.getiterator('item')
		except Exception, e:
			logger.log("Error trying to load "+self.name+" RSS feed: "+str(e), logger.ERROR)
			logger.log("RSS data: "+data, logger.DEBUG)
			return []
			
		if responseSoup.getroot().tag == 'error':
			code = responseSoup.getroot().get('code')
			if code == '100':
				raise exceptions.AuthException("Your API key for "+self.name+" is incorrect, check your config.")
			elif code == '101':
				raise exceptions.AuthException("Your account on "+self.name+" has been suspended, contact the administrator.")
			elif code == '102':
				raise exceptions.AuthException("Your account isn't allowed to use the API on "+self.name+", contact the administrator")
			else:
				logger.log("Unknown error given from "+self.name+": "+responseSoup.getroot().get('description'), logger.ERROR)
				return []
				
		if responseSoup.getroot().tag != 'rss':
			logger.log("Resulting XML from "+self.name+" isn't RSS, not parsing it", logger.ERROR)
			return []

		results = []
		
		for curItem in items:
			title = curItem.findtext('title')
			url = curItem.findtext('link')
	
			if not title or not url:
				logger.log("The XML returned from the "+self.name+" RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
				continue
	
			url = url.replace('&amp;','&')
	
			results.append(curItem)
		
		return results

	def findPropers(self, date=None):
	
		return []
	
		results = []
		
		for curResult in self._doSearch(None, search="proper repack"):

			match = re.search('(\w{3}, \d{1,2} \w{3} \d{4} \d\d:\d\d:\d\d) [\+\-]\d{4}', curResult.findtext('pubDate'))
			if not match:
				continue

			resultDate = datetime.datetime.strptime(match.group(1), "%a, %d %b %Y %H:%M:%S")
			
			if date == None or resultDate > date:
				results.append(classes.Proper(curResult.findtext('title'), curResult.findtext('link'), resultDate))
		
		return results

class NewznabCache(tvcache.TVCache):
	
	def __init__(self, provider):

		# only poll newznab providers every 15 minutes max
		self.minTime = 15
		
		tvcache.TVCache.__init__(self, provider)
	
	def _getRSSData(self):
		
		params = {"t": "tvsearch",
				  "age": sickbeard.USENET_RETENTION,
				  "cat": '5040,5030'}

		if self.provider.key:
			params['apikey'] = self.provider.key

		url = self.provider.url + 'api?' + urllib.urlencode(params)
		
		logger.log(self.provider.name + " cache update URL: "+ url, logger.DEBUG)
		
		data = self.provider.getURL(url)
		
		return data
	
	def _checkAuth(self, data):

		try:
			responseSoup = etree.ElementTree(etree.XML(data))
		except Exception, e:
			return True
			
		if responseSoup.getroot().tag == 'error':
			code = responseSoup.getroot().get('code')
			if code == '100':
				raise exceptions.AuthException("Your API key for "+self.provider.name+" is incorrect, check your config.")
			elif code == '101':
				raise exceptions.AuthException("Your account on "+self.provider.name+" has been suspended, contact the administrator.")
			elif code == '102':
				raise exceptions.AuthException("Your account isn't allowed to use the API on "+self.provider.name+", contact the administrator")
			else:
				logger.log("Unknown error given from "+self.provider.name+": "+responseSoup.getroot().get('description'), logger.ERROR)
				return False
		
		return True
