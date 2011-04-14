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

from sickbeard import classes
from sickbeard.helpers import sanitizeSceneName

from sickbeard import exceptions
from sickbeard import logger
from sickbeard import tvcache

class NewznabProvider(generic.NZBProvider):

	def __init__(self, name, url, key=''):

		generic.NZBProvider.__init__(self, name)

		self.cache = NewznabCache(self)

		self.url = url
		self.key = key

		self.enabled = True
		self.supportsBacklog = True
		self.combine_results = True

		self.default = False

	def configStr(self):
		return self.name + '|' + self.url + '|' + self.key + '|' + str(int(self.enabled))

	def imageName(self):
		return 'newznab.gif'

	def isEnabled(self):
		return self.enabled

	def _get_id_from_url(self, url):
		"""
		Split the URL up into the pieces that matter.
		
		Returns: a tuple containing the first part of the URL, the ID, and the rest of the URL.

		Eg. http://www.newznab.com/getnzb/203ba7dc120049dff03cd94d468a1948.nzb&i=123&r=ecd38ab63c46d626416e8241afcc58a2
		
		Returns: ('http://www.newznab.com/getnzb', '203ba7dc120049dff03cd94d468a1948', '&i=123&r=ecd38ab63c46d626416e8241afcc58a2')
		"""
		match = re.match("(.*getnzb)/(.*?)\.nzb(.*)", url)
		if not match:
			logger.log(u"url didn't match: "+str(url), logger.WARNING)
			return None
		
		return (match.group(1), match.group(2), match.group(3))
			
	def amalgamate_results(self, results):
		"""
		Newznab allows us to retrieve multiple NZBs at once by specifying comma separated IDs and then &zip=1.
		This function takes a list of SearchResult instances and makes a single NZBSearchResult out of them with
		the multi-snatch URL in it.
		
		results: A list of SearchResults
		
		Returns: A single NZBSearchResult with a single multi-snatch URL, all relevant episodes, and a concatenated name.
		"""
	
		if not results:
			return None

		# retrieve the relevant info from our results		
		id_list = []
		ep_list = []
		name_list = []
		for cur_result in results:
			start, cur_id, end = self._get_id_from_url(cur_result.url)
			id_list.append(cur_id)
			ep_list += cur_result.episodes
			name_list.append(cur_result.name)

		# make the multi-snatch URL		
		final_url = start + '?id=' + ','.join(id_list) + end + '&zip=1'
		final_name = ', '.join(name_list)
		
		# set the relevant fields on the amalgamated result. note no quality since it's not necessary or sensical		
		final_result = classes.NZBSearchResult(ep_list)
		final_result.provider = self
		final_result.url = final_url
		final_result.name = final_name
		
		return final_result

	def downloadResults(self, nzb_list):
		"""
		Downloads a list of NZBs as a single request and saves it as a zip file.
		
		nzb_list: A list of NZBSearchResult objects to download.
		
		Returns: bool representing success
		"""
		
		amalgamated_result = self.amalgamate_results(nzb_list)
		
		return self.downloadResult(amalgamated_result, zip=True)

	def _get_season_search_strings(self, show, season=None):

		params = {}

		if not show:
			return params
		
		# search directly by tvrage id
		if show.tvrid:
			params['rid'] = show.tvrid
		# if we can't then fall back on a very basic name search
		else:
			params['q'] = sanitizeSceneName(show.name)

		if season != None:
			# air-by-date means &season=2010&q=2010.03, no other way to do it atm
			if show.air_by_date:
				params['season'] = season.split('-')[0]
				if 'q' in params:
					params['q'] += '.' + season.replace('-', '.')
				else:
					params['q'] = season.replace('-', '.')
			else:
				params['season'] = season

		return [params]

	def _get_episode_search_strings(self, ep_obj):
		
		params = {}

		if not ep_obj:
			return params
		
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

		return [params]


	def _doGeneralSearch(self, search_string):
		return self._doSearch({'q': search_string})

	#def _doSearch(self, show, season=None, episode=None, search=None):
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
			responseSoup = etree.ElementTree(etree.XML(data))
			items = responseSoup.getiterator('item')
		except Exception, e:
			logger.log(u"Error trying to load "+self.name+" RSS feed: "+str(e).decode('utf-8'), logger.ERROR)
			logger.log(u"RSS data: "+data, logger.DEBUG)
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
				logger.log(u"Unknown error given from "+self.name+": "+responseSoup.getroot().get('description'), logger.ERROR)
				return []

		if responseSoup.getroot().tag != 'rss':
			logger.log(u"Resulting XML from "+self.name+" isn't RSS, not parsing it", logger.ERROR)
			return []

		results = []

		for curItem in items:
			title = curItem.findtext('title')
			url = curItem.findtext('link')

			if not title or not url:
				logger.log(u"The XML returned from the "+self.name+" RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
				continue

			url = url.replace('&amp;','&')

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

		try:
			responseSoup = etree.ElementTree(etree.XML(data))
		except Exception:
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
				logger.log(u"Unknown error given from "+self.provider.name+": "+responseSoup.getroot().get('description'), logger.ERROR)
				return False

		return True
