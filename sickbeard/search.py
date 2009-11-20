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
from logging import *

import sab, contactXBMC, history

from providers import newzbin
from providers import tvbinz
from providers import nzbs
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
	else:
		Logger().log("Invalid provider - this is a coding error, this should never happen.", ERROR)
		return False

def snatchEpisode(result):

	if result.resultType == "nzb":
		if sickbeard.NZB_METHOD == "blackhole":
			dlResult = _downloadResult(result)
		elif sickbeard.NZB_METHOD == "sabnzbd":
			dlResult = sab.sendNZB(result)
		else:
			Logger().log("Unknown NZB action specified in config: " + sickbeard.NZB_METHOD, ERROR)
			dlResult = False
	elif result.resultType == "torrent":
		dlResult = _downloadResult(result)
	else:
		Logger().log("Unknown result type, unable to download it", ERROR)
		dlResult = False
	
	if dlResult == False:
		return

	# log the snatch
	history.logSnatch(result)

	if sickbeard.XBMC_NOTIFY_ONDOWNLOAD == True:
		contactXBMC.notifyXBMC(result.episode.prettyName(), "Started download")
	
	with result.episode.lock:
		if result.predownloaded == False:
			Logger().log("changing status from " + str(result.episode.status) + " to " + str(SNATCHED), DEBUG)
			result.episode.status = SNATCHED
		elif result.predownloaded == True:
			Logger().log("changing status from " + str(result.episode.status) + " to " + str(PREDOWNLOADED), DEBUG)
			result.episode.status = PREDOWNLOADED
		result.episode.saveToDB()


def _doSearch(episode, provider):

	foundEps = provider.findEpisode(episode)
	
	# if we couldn't find any HD eps and we're allowing predownloading, retry for SD
	if len(foundEps) == 0 and episode.show.quality == HD and episode.show.predownload == True and episode.status != PREDOWNLOADED:
		foundEps = provider.findEpisode(episode, SD)
		for curEp in foundEps:
			curEp.predownloaded = True

	return foundEps

def findEpisode(episode):

	Logger().log("Searching for " + episode.prettyName())

	foundEps = []

	for curProvider in (newzbin, tvbinz, nzbs, eztv):
		
		if not curProvider.isActive():
			continue
		
		foundEps = _doSearch(episode, curProvider)
		if len(foundEps) > 0:
			break
	
	return foundEps
