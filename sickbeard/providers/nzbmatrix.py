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
from sickbeard import logger

providerType = "nzb"
providerName = "NZBMatrix"

def isActive():
	return sickbeard.NZBMATRIX and sickbeard.USE_NZB

def downloadNZB (nzb):

	logger.log("Downloading an NZB from NZBMatrix at " + nzb.url)

	fileName = os.path.join(sickbeard.NZB_DIR, nzb.extraInfo[0] + ".nzb")
	
	logger.log("Saving to " + fileName, logger.DEBUG)

	urllib.urlretrieve(nzb.url, fileName)

	return True
	
	
def findEpisode (episode, forceQuality=None):

	if episode.status == DISCBACKLOG:
		logger.log("NZBMatrix doesn't support disc backlog. Use newzbin or download it manually from NZBMatrix")
		return []

	logger.log("Searching NZBMatrix for " + episode.prettyName(True))

	if forceQuality != None:
		epQuality = forceQuality
	elif episode.show.quality == BEST:
		epQuality = ANY
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
		params = {"search": curString.replace("."," ").encode('utf-8'), "age": sickbeard.USENET_RETENTION, "username": sickbeard.NZBMATRIX_USERNAME, "apikey": sickbeard.NZBMATRIX_APIKEY}
		params.update(quality)
		
		searchURL = "https://nzbmatrix.com/api-nzb-search.php?" + urllib.urlencode(params)
	
		logger.log("Search string: " + searchURL, logger.DEBUG)

		f = urllib.urlopen(searchURL)
		searchResult = "".join(f.readlines())
		f.close()
		
		if searchResult.startswith("error:"):
			err = searchResult.split(":")[1]
			if err == "nothing_found":
				continue
			elif err == "invalid_login" or err == "invalid_api":
				raise exceptions.AuthException("NZBMatrix username or API key is incorrect")
			logger.log("An error was encountered during the search: "+err, logger.ERROR)
		
		
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
				logger.log("Ignoring result "+resultDict["NZBNAME"]+" because it doesn't contain 720p in the name", logger.DEBUG)
				continue

			result = sickbeard.classes.NZBSearchResult(episode)
			result.provider = 'nzbmatrix' 
			result.url = "http://nzbmatrix.com/api-nzb-download.php?id="+resultDict["NZBID"]+"&username="+sickbeard.NZBMATRIX_USERNAME+"&apikey="+sickbeard.NZBMATRIX_APIKEY
			result.extraInfo = [resultDict["NZBNAME"]]
			result.quality = epQuality
			
			results.append(result)
					
	return results
