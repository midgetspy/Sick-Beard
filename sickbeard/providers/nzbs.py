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

from lib.BeautifulSoup import BeautifulStoneSoup

import sickbeard
import sickbeard.classes
import sickbeard.helpers

from sickbeard.common import *
from sickbeard.logging import *

providerType = "nzb"
providerName = "NZBs.org"

def isActive():
	return sickbeard.NZBS and sickbeard.USE_NZB

def getNZBsURL (url):

	result = None

	try:
		f = urllib2.urlopen(url)
		result = "".join(f.readlines())
	except (urllib.ContentTooShortError, IOError) as e:
		Logger().log("Error loading NZBs.org URL: " + sys.exc_info() + " - " + str(e), ERROR)
		return None

	return result

						
def downloadNZB (nzb):

	Logger().log("Downloading an NZB from NZBs.org at " + nzb.url)

	data = getNZBsURL(nzb.url)
	
	if data == None:
		return False
	
	fileName = os.path.join(sickbeard.NZB_DIR, nzb.extraInfo[0] + ".nzb")
	
	Logger().log("Saving to " + fileName, DEBUG)
	
	fileOut = open(fileName, "w")
	fileOut.write(data)
	fileOut.close()

	return True
	
	
def findEpisode (episode, forceQuality=None):

	if episode.status == DISCBACKLOG:
		Logger().log("NZBs.org doesn't support disc backlog. Use newzbin or download it manually from NZBs.org")
		return []

	Logger().log("Searching NZBs.org for " + episode.prettyName())

	if forceQuality != None:
		epQuality = forceQuality
	else:
		epQuality = episode.show.quality
	
	if epQuality == SD:
		quality = {"catid": 1}
	elif epQuality == HD:
		quality = {"catid": 14}
	else:
		quality = {}
		
	sceneSearchStrings = sickbeard.helpers.makeSceneSearchString(episode)
	
	for curString in sceneSearchStrings:
		params = {"action": "search", "q": "^"+curString, "dl": 1, "i": sickbeard.NZBS_UID, "h": sickbeard.NZBS_HASH, "age": sickbeard.USENET_RETENTION}
		params.update(quality)
		
		searchURL = "http://www.nzbs.org/rss.php?" + urllib.urlencode(params)
	
		Logger().log("Search string: " + searchURL, DEBUG)
	
		data = getNZBsURL(searchURL)

		if data == None:
			return []

		results = []
		
		try:
			responseSoup = BeautifulStoneSoup(data, convertEntities=BeautifulStoneSoup.XML_ENTITIES)
			items = responseSoup.findAll('item')
		except Exception as e:
			Logger().log("Error trying to load NZBs.org RSS feed: "+str(e), ERROR)
			return []
			
		
		if len(items) > 0:
			break

	for item in items:
		
		if item.title == None or item.link == None:
			Logger().log("The XML returned from the NZBs.org RSS feed is incomplete, this result is unusable: "+data, ERROR)
			continue
		
		title = item.title.string
		url = item.link.string
		
		Logger().log("Found result " + title + " at " + url, DEBUG)
		
		result = sickbeard.classes.NZBSearchResult(episode)
		result.provider = sickbeard.common.NZBS
		result.url = url 
		result.extraInfo = [title]
		result.quality = epQuality
		
		results.append(result)
		
	return results
