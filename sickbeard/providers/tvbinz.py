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

def isActive():
	return sickbeard.TVBINZ

def getTVBinzURL (url):

	searchHeaders = {"Cookie": "uid=" + sickbeard.TVBINZ_UID + ";hash=" + sickbeard.TVBINZ_HASH, 'Accept-encoding': 'gzip'}
	req = urllib2.Request(url=url, headers=searchHeaders)
	
	try:
		f = urllib2.urlopen(req)
	except (urllib.ContentTooShortError, IOError) as e:
		Logger().log("Error loading TVBinz URL: " + sys.exc_info() + " - " + str(e))
		return None

	result = sickbeard.helpers.getGZippedURL(f)

	return result

						
def downloadNZB (nzb):

	Logger().log("Downloading an NZB from tvbinz at " + nzb.url)

	data = getTVBinzURL(nzb.url)
	
	if data == None:
		return False
	
	fileName = os.path.join(sickbeard.NZB_DIR, nzb.extraInfo[0] + ".nzb")
	
	Logger().log("Saving to " + fileName, DEBUG)
	
	fileOut = open(fileName, "w")
	fileOut.write(data)
	fileOut.close()

	return True
	
	
def findNZB (episode, forceQuality=None):

	if episode.status == DISCBACKLOG:
		Logger().log("TVbinz doesn't support disc backlog. Use newzbin or download it manually from TVbinz")
		return []

	Logger().log("Searching tvbinz for " + episode.prettyName())

	if forceQuality != None:
		epQuality = forceQuality
	else:
		epQuality = episode.show.quality
	
	if epQuality == SD:
		quality = {"priority": "sd", "wait": "9999999999999"}
	elif epQuality == HD:
		quality = {"priority": "hd", "wait": "9999999999999"}
	else:
		quality = {}
		
	sceneSearchStrings = sickbeard.helpers.makeSceneSearchString(episode)
	
	for curString in sceneSearchStrings:
		params = {"search": curString, "nodupes": "1", "normalize": "1"}
		params.update(quality)
		
		searchURL = "https://tvbinz.net/rss.php?" + urllib.urlencode(params)
	
		Logger().log("Search string: " + searchURL, DEBUG)
	
		data = getTVBinzURL(searchURL)
		
		if data == None:
			return []
	
		results = []
		
		responseSoup = BeautifulStoneSoup(data)
		items = responseSoup.findAll('item')
		
		if len(items) > 0:
			break

	for item in items:
		
		if item.title == None or item.link == None:
			Logger().log("The XML returned from the TVBinz RSS feed is incomplete, this result is unusable: "+data, ERROR)
			continue
		
		title = item.title.string
		url = item.link.string.replace("&amp;", "&")
		urlParams = {'i': sickbeard.TVBINZ_UID, 'h': sickbeard.TVBINZ_HASH}
		
		Logger().log("Found result " + title + " at " + url)

		result = sickbeard.classes.NZBSearchResult(episode)
		result.provider = sickbeard.common.TVBINZ
		result.url = url + "&" + urllib.urlencode(urlParams) 
		result.extraInfo = [title]
		
		results.append(result)
		
	return results
