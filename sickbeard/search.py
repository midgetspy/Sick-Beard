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



import sickbeard

from common import *

from sickbeard import logger
from sickbeard import sab
from sickbeard import history

from sickbeard import notifiers 
from sickbeard import exceptions

from providers import newzbin
from providers import tvbinz
from providers import nzbs
from providers import nzbmatrix
from providers import eztv

def _downloadResult(result):

	if result.provider == NEWZBIN:
		return newzbin.downloadNZB(result)
	elif result.provider == TVBINZ:
		return tvbinz.downloadNZB(result)
	elif result.provider == NZBS:
		return nzbs.downloadNZB(result)
	elif result.provider == EZTV:
		return eztv.downloadTorrent(result)
	elif result.provider == NZBMATRIX:
		return nzbmatrix.downloadNZB(result)
	else:
		logger.log("Invalid provider - this is a coding error, this should never happen.", logger.ERROR)
		return False

def snatchEpisode(result):

	if result.resultType == "nzb":
		if sickbeard.NZB_METHOD == "blackhole":
			dlResult = _downloadResult(result)
		elif sickbeard.NZB_METHOD == "sabnzbd":
			dlResult = sab.sendNZB(result)
		else:
			logger.log("Unknown NZB action specified in config: " + sickbeard.NZB_METHOD, logger.ERROR)
			dlResult = False
	elif result.resultType == "torrent":
		dlResult = _downloadResult(result)
	else:
		logger.log("Unknown result type, unable to download it", logger.ERROR)
		dlResult = False
	
	if dlResult == False:
		return

	# log the snatch
	history.logSnatch(result)

	notifiers.notify(NOTIFY_SNATCH, result.episode.prettyName())
	
	with result.episode.lock:
		if result.predownloaded == False:
			logger.log("changing status from " + str(result.episode.status) + " to " + str(SNATCHED), logger.DEBUG)
			result.episode.status = SNATCHED
		elif result.predownloaded == True:
			logger.log("changing status from " + str(result.episode.status) + " to " + str(PREDOWNLOADED), logger.DEBUG)
			result.episode.status = PREDOWNLOADED
		result.episode.saveToDB()

	sickbeard.updateMissingList()
	sickbeard.updateAiringList()
	sickbeard.updateComingList()

def _doSearch(episode, provider):

	# if we already got the SD then only try HD on BEST episodes
	if episode.show.quality == BEST and episode.status == PREDOWNLOADED:
		foundEps = provider.findEpisode(episode, HD)
	else:
		foundEps = provider.findEpisode(episode)

	
	# if we found something and we're on BEST, retry to see if we can guarantee HD.
	if len(foundEps) > 0 and episode.show.quality == BEST and episode.status != PREDOWNLOADED:
			moreFoundEps = provider.findEpisode(episode, HD)
			
			# if we couldn't find a definitive HD version then mark the original ones as predownloaded
			if len(moreFoundEps) == 0:
				for curResult in foundEps:
					curResult.predownloaded = True
			else:
				return moreFoundEps

	return foundEps

def findEpisode(episode):

	logger.log("Searching for " + episode.prettyName())

	foundEps = []

	didSearch = False

	for curProvider in (newzbin, tvbinz, nzbs, nzbmatrix, eztv):
		
		if not curProvider.isActive():
			continue
		
		try:
			foundEps = _doSearch(episode, curProvider)
		except exceptions.AuthException as e:
			logger.log("Authentication error: "+str(e), logger.ERROR)
			continue
		
		didSearch = True
		
		if len(foundEps) > 0:
			break
	
	if not didSearch:
		logger.log("No providers were used for the search - check your settings and ensure that either NZB/Torrents is selected and at least one NZB provider is being used.", logger.ERROR)
	
	return foundEps
