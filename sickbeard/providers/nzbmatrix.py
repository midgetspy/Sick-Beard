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
import datetime

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
		quality = {"catid": "tv-all"}
		
	sceneSearchStrings = set(sickbeard.helpers.makeSceneSearchString(episode))
	
	results = []

	for curString in sceneSearchStrings:

		for resultDict in _doSearch(curString, quality):

			if epQuality == HD and "720p" not in resultDict["NZBNAME"]:
				logger.log("Ignoring result "+resultDict["NZBNAME"]+" because it doesn't contain 720p in the name", logger.DEBUG)
				continue

			result = sickbeard.classes.NZBSearchResult(episode)
			result.provider = providerName.lower()
			result.url = resultDict["SBURL"]
			result.extraInfo = [resultDict["NZBNAME"]]
			result.quality = epQuality
		
			results.append(result)
					
	return results

def _doSearch(curString, quality):
	params = {"search": curString.replace("."," ").encode('utf-8'), "age": sickbeard.USENET_RETENTION, "username": sickbeard.NZBMATRIX_USERNAME, "apikey": sickbeard.NZBMATRIX_APIKEY}
	params.update(quality)
	
	searchURL = "https://nzbmatrix.com/api-nzb-search.php?" + urllib.urlencode(params)

	logger.log("Search string: " + searchURL, logger.DEBUG)

	logger.log("Sleeping 10 seconds to respect NZBMatrix's API rules")
	time.sleep(10)
	f = urllib.urlopen(searchURL)
	searchResult = "".join(f.readlines())
	f.close()
	
	if searchResult.startswith("error:"):
		err = searchResult.split(":")[1]
		if err == "nothing_found":
			return []
		elif err == "invalid_login" or err == "invalid_api":
			raise exceptions.AuthException("NZBMatrix username or API key is incorrect")
		logger.log("An error was encountered during the search: "+err, logger.ERROR)

	results = []
	
	for curResult in searchResult.split("|"):
		resultDict = {}
		lines = curResult.split("\n")
		for info in lines:
			curInfo = info.strip(";").partition(":")
			if len(curInfo) != 3:
				continue
			resultDict[curInfo[0]] = curInfo[2]

		if len(resultDict) == 0:
			continue

		if "NZBID" not in resultDict:
			continue

		resultDict["SBURL"] = "http://nzbmatrix.com/api-nzb-download.php?id="+resultDict["NZBID"]+"&username="+sickbeard.NZBMATRIX_USERNAME+"&apikey="+sickbeard.NZBMATRIX_APIKEY

		results.append(resultDict)

	return results

def findPropers(date=None):
	
	results = []
	
	for curString in ("PROPER", "REPACK"):
	
		for curQuality in (6,41):
		
			for curResult in _doSearch(curString, {"catid": curQuality}):

				resultDate = datetime.datetime.strptime(curResult["INDEX_DATE"], "%Y-%m-%d %H:%M:%S")
				
				if date == None or resultDate > date:
					results.append(classes.Proper(curResult["NZBNAME"], curResult["SBURL"], resultDate))
	
	return results
