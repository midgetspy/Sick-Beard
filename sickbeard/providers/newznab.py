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
import os

from xml.dom.minidom import parseString

import sickbeard
import generic

from sickbeard import classes
from sickbeard.helpers import sanitizeSceneName
from sickbeard import scene_exceptions
from sickbeard import encodingKludge as ek

from sickbeard import exceptions
from sickbeard import logger
from sickbeard import tvcache
from sickbeard.exceptions import ex

class NewznabProvider(generic.NZBProvider):

	def __init__(self, name, url, key=''):

		generic.NZBProvider.__init__(self, name)

		self.cache = NewznabCache(self)

		self.url = url
		self.key = key
		
		# if a provider doesn't need an api key then this can be false
		self.needs_auth = True

		self.enabled = True
		self.supportsBacklog = True

		self.default = False

	def configStr(self):
		return self.name + '|' + self.url + '|' + self.key + '|' + str(int(self.enabled))

	def imageName(self):
		if ek.ek(os.path.isfile, ek.ek(os.path.join, sickbeard.PROG_DIR, 'data', 'images', 'providers', self.getID()+'.gif')):
			return self.getID()+'.gif'
		return 'newznab.gif'

	def isEnabled(self):
		return self.enabled

	def _get_season_search_strings(self, show, season=None):

		if not show:
			return [{}]
		
		to_return = []

		# add new query strings for exceptions
		name_exceptions = scene_exceptions.get_scene_exceptions(show.tvdbid) + [show.name]
		for cur_exception in name_exceptions:
		
			cur_params = {}
	
			# search directly by tvrage id
			if show.tvrid:
				cur_params['rid'] = show.tvrid
			# if we can't then fall back on a very basic name search
			else:
				cur_params['q'] = sanitizeSceneName(cur_exception)
	
			if season != None:
				# air-by-date means &season=2010&q=2010.03, no other way to do it atm
				if show.air_by_date:
					cur_params['season'] = season.split('-')[0]
					if 'q' in cur_params:
						cur_params['q'] += '.' + season.replace('-', '.')
					else:
						cur_params['q'] = season.replace('-', '.')
				else:
					cur_params['season'] = season

			# hack to only add a single result if it's a rageid search
			if not ('rid' in cur_params and to_return):
				to_return.append(cur_params) 

		return to_return

	def _get_episode_search_strings(self, ep_obj):
		
		params = {}

		if not ep_obj:
			return [params]
		
		# search directly by tvrage id
		if ep_obj.show.tvrid:
			params['rid'] = ep_obj.show.tvrid
		# if we can't then fall back on a very basic name search
		else:
			params['q'] = sanitizeSceneName(ep_obj.show.name)

		if ep_obj.show.air_by_date:
			date_str = str(ep_obj.airdate)
			
			params['season'] = date_str.partition('-')[0]
			params['ep'] = date_str.partition('-')[2].replace('-','/')
		else:
			params['season'] = ep_obj.season
			params['ep'] = ep_obj.episode

		to_return = [params]

		# only do exceptions if we are searching by name
		if 'q' in params:

			# add new query strings for exceptions
			name_exceptions = scene_exceptions.get_scene_exceptions(ep_obj.show.tvdbid)
			for cur_exception in name_exceptions:
				
				# don't add duplicates 
				if cur_exception == ep_obj.show.name:
					continue

				cur_return = params.copy()
				cur_return['q'] = sanitizeSceneName(cur_exception)
				to_return.append(cur_return)

		return to_return

	def _doGeneralSearch(self, search_string):
		return self._doSearch({'q': search_string})

	def _checkAuthFromData(self, data):

		try:
			parsedXML = parseString(data)
		except Exception:
			return False

		if parsedXML.documentElement.tagName == 'error':
			code = parsedXML.documentElement.getAttribute('code')
			if code == '100':
				raise exceptions.AuthException("Your API key for "+self.name+" is incorrect, check your config.")
			elif code == '101':
				raise exceptions.AuthException("Your account on "+self.name+" has been suspended, contact the administrator.")
			elif code == '102':
				raise exceptions.AuthException("Your account isn't allowed to use the API on "+self.name+", contact the administrator")
			else:
				logger.log(u"Unknown error given from "+self.name+": "+parsedXML.documentElement.getAttribute('description'), logger.ERROR)
				return False

		return True

	def _doSearch(self, search_params, show=None):

		params = {"t": "tvsearch",
				  "maxage": sickbeard.USENET_RETENTION,
				  "limit": 100,
				  "cat": '5030,5040'}

		if search_params:
			params.update(search_params)

		if self.key:
			params['apikey'] = self.key

		searchURL = self.url + 'api?' + urllib.urlencode(params)

		logger.log(u"Search url: " + searchURL, logger.DEBUG)

		data = self.getURL(searchURL)
		
		if not data:
			return []

		# hack this in until it's fixed server side
		if not data.startswith('<?xml'):
			data = '<?xml version="1.0" encoding="ISO-8859-1" ?>' + data

		try:
			parsedXML = parseString(data)
			items = parsedXML.getElementsByTagName('item')
		except Exception, e:
			logger.log(u"Error trying to load "+self.name+" RSS feed: "+ex(e), logger.ERROR)
			logger.log(u"RSS data: "+data, logger.DEBUG)
			return []

		if not self._checkAuthFromData(data):
			return []

		if parsedXML.documentElement.tagName != 'rss':
			logger.log(u"Resulting XML from "+self.name+" isn't RSS, not parsing it", logger.ERROR)
			return []

		results = []

		for curItem in items:
			(title, url) = self._get_title_and_url(curItem)

			if not title or not url:
				logger.log(u"The XML returned from the "+self.name+" RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
				continue

			results.append(curItem)

		return results

	def findPropers(self, date=None):

		return []

		results = []

		for curResult in self._doGeneralSearch("proper repack"):

			match = re.search('(\w{3}, \d{1,2} \w{3} \d{4} \d\d:\d\d:\d\d) [\+\-]\d{4}', curResult.findtext('pubDate'))
			if not match:
				continue

			resultDate = datetime.datetime.strptime(match.group(1), "%a, %d %b %Y %H:%M:%S")

			if date == None or resultDate > date:
				results.append(classes.Proper(curResult.findtext('title'), curResult.findtext('link'), resultDate))

		return results

class NewznabCache(tvcache.TVCache):

	def __init__(self, provider):

		tvcache.TVCache.__init__(self, provider)

		# only poll newznab providers every 15 minutes max
		self.minTime = 15

	def _getRSSData(self):

		params = {"t": "tvsearch",
				  "age": sickbeard.USENET_RETENTION,
				  "cat": '5040,5030'}

		if self.provider.key:
			params['apikey'] = self.provider.key

		url = self.provider.url + 'api?' + urllib.urlencode(params)

		logger.log(self.provider.name + " cache update URL: "+ url, logger.DEBUG)

		data = self.provider.getURL(url)

		# hack this in until it's fixed server side
		if data and not data.startswith('<?xml'):
			data = '<?xml version="1.0" encoding="ISO-8859-1" ?>' + data

		return data

	def _checkAuth(self, data):

		return self.provider._checkAuthFromData(data)
