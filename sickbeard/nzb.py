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

from sickbeard import sab, contactXBMC

from providers import newzbin
from providers import tvbinz

def _downloadNZB(nzb):

	if nzb.provider == NEWZBIN:
		return newzbin.downloadNZB(nzb)
	elif nzb.provider == TVBINZ:
		return tvbinz.downloadNZB(nzb)
	else:
		Logger().log("Invalid provider - this is a coding error, this should never happen.", ERROR)
		return False

def snatchNZB(nzb):

	if sickbeard.NZB_METHOD == "blackhole":
		result = _downloadNZB(nzb)
	elif sickbeard.NZB_METHOD == "sabnzbd":
		result = sab.sendNZB(nzb)
	else:
		Logger().log("Unknown NZB action specified in config: " + sickbeard.NZB_METHOD, ERROR)
		result = False
	
	if result == False:
		return

	if sickbeard.XBMC_NOTIFY_ONDOWNLOAD == True:
		contactXBMC.notifyXBMC(nzb.episode.prettyName(), "Started download")
	
	with nzb.episode.lock:
		if nzb.predownloaded == False:
			print "changing status from " + str(nzb.episode.status) + " to " + str(SNATCHED)
			nzb.episode.status = SNATCHED
		elif nzb.predownloaded == True:
			print "changing status from " + str(nzb.episode.status) + " to " + str(PREDOWNLOADED)
			nzb.episode.status = PREDOWNLOADED
		nzb.episode.saveToDB()


def _doSearch(episode, provider):

	foundEps = provider.findNZB(episode)
	
	# if we couldn't find any HD eps and we're allowing predownloading, retry for SD
	if len(foundEps) == 0 and episode.show.quality == HD and episode.show.predownload == True and episode.status != PREDOWNLOADED:
		foundEps = provider.findNZB(episode, SD)
		for curEp in foundEps:
			curEp.predownloaded = True

	return foundEps

def findNZB(episode):

	Logger().log("Searching for " + episode.prettyName())

	foundEps = []

	for curProvider in (newzbin, tvbinz):
		
		if not curProvider.isActive():
			continue
		
		foundEps = _doSearch(episode, curProvider)
		if len(foundEps) > 0:
			break
	
	return foundEps
