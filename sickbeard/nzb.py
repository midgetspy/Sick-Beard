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
