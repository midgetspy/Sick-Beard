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



import os.path
import re
import sys
import time
import urllib

import sickbeard

from sickbeard import exceptions, helpers, classes
from sickbeard.common import *
from sickbeard.logging import *

providerType = "nzb"
providerName = "NZBMatrix"

def isActive():
	return sickbeard.NZBMATRIX and sickbeard.USE_NZB

def downloadNZB (nzb):

	Logger().log("Downloading an NZB from NZBMatrix at " + nzb.url)

	fileName = os.path.join(sickbeard.NZB_DIR, nzb.extraInfo[0] + ".nzb")
	
	Logger().log("Saving to " + fileName, DEBUG)

	urllib.urlretrieve(nzb.url, fileName)

	return True
	
	
def findEpisode (episode, forceQuality=None):

	if episode.status == DISCBACKLOG:
		Logger().log("NZBMatrix doesn't support disc backlog. Use newzbin or download it manually from NZBMatrix")
		return []

	Logger().log("Searching NZBMatrix for " + episode.prettyName())

	if forceQuality != None:
		epQuality = forceQuality
	elif episode.show.quality == BEST:
		epQuality = HD
	else:
		epQuality = episode.show.quality
	
	if epQuality == SD:
		quality = {"catid": 6}
	elif epQuality == HD:
		quality = {"catid": 41}
	else:
		quality = {}
		
	sceneSearchStrings = sickbeard.helpers.makeSceneSearchString(episode)
	
	results = []

	for curString in sceneSearchStrings:
		params = {"search": curString.replace("."," "), "age": sickbeard.USENET_RETENTION, "username": sickbeard.NZBMATRIX_USERNAME, "apikey": sickbeard.NZBMATRIX_APIKEY}
		params.update(quality)
		
		searchURL = "http://nzbmatrix.com/api-nzb-search.php?" + urllib.urlencode(params)
	
		Logger().log("Search string: " + searchURL, DEBUG)

		f = urllib.urlopen(searchURL)
		searchResult = "".join(f.readlines())
		f.close()
		
		if searchResult.startswith("error:"):
			err = searchResult.split(":")[1]
			Logger().log("An error was encountered during the search: "+err, ERROR)
			if err == "nothing_found":
				continue
			elif err == "invalid_login" or err == "invalid_api":
				raise exceptions.AuthException("NZBMatrix username or API key is incorrect")
		
		
		for curResult in searchResult.split("|"):
			resultDict = {}
			lines = curResult.split("\n")
			for info in lines:
				curInfo = info.strip(";").split(":")
				if len(curInfo) != 2:
					continue
				resultDict[curInfo[0]] = curInfo[1]

			if len(resultDict) == 0:
				continue

			if epQuality == HD and "720p" not in resultDict["NZBNAME"]:
				Logger().log("Ignoring result "+resultDict["NZBNAME"]+" because it doesn't contain 720p in the name", DEBUG)
				continue

			result = sickbeard.classes.NZBSearchResult(episode)
			result.provider = NZBMATRIX 
			result.url = "http://nzbmatrix.com/api-nzb-download.php?id="+resultDict["NZBID"]+"&username="+sickbeard.NZBMATRIX_USERNAME+"&apikey="+sickbeard.NZBMATRIX_APIKEY
			result.extraInfo = [resultDict["NZBNAME"]]
			result.quality = epQuality
			
			results.append(result)
					
	return results
