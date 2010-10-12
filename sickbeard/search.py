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

from __future__ import with_statement

import traceback

from lib.tvnamer.utils import FileParser
from lib.tvnamer import tvnamer_exceptions

import sickbeard

from common import *

from sickbeard import logger, db, sceneHelpers, exceptions, helpers
from sickbeard import sab
from sickbeard import history
from sickbeard import notifiers
from sickbeard import nzbSplitter 

from sickbeard.providers import *
from sickbeard import providers

def _downloadResult(result):

	resProvider = result.provider

	newResult = False

	if resProvider == None:
		logger.log("Invalid provider name - this is a coding error, report it please", logger.ERROR)
		return False

	if result.resultType == "nzb":
		newResult = resProvider.downloadResult(result)
	elif result.resultType == "nzbdata":
		fileName = os.path.join(sickbeard.NZB_DIR, result.name + ".nzb")
		
		logger.log("Saving NZB to " + fileName)
		
		newResult = True

		try:
			fileOut = open(fileName, "w")
			fileOut.write(result.extraInfo[0])
			fileOut.close()
		except IOError, e:
			logger.log("Error trying to save NZB to black hole: "+str(e), logger.ERROR)
			newResult = False
		
	elif resProvider.providerType == "torrent":
		newResult = resProvider.downloadResult(result)
	else:
		logger.log("Invalid provider type - this is a coding error, report it please", logger.ERROR)
		return False

	return newResult

def snatchEpisode(result, endStatus=SNATCHED):

	if result.resultType in ("nzb", "nzbdata"):
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

	history.logSnatch(result)

	# don't notify when we re-download an episode
	for curEpObj in result.episodes:
		with curEpObj.lock:
			curEpObj.status = Quality.compositeStatus(endStatus, result.quality)
			curEpObj.saveToDB()

		if curEpObj.status not in Quality.DOWNLOADED:
			notifiers.notify(NOTIFY_SNATCH, curEpObj.prettyName(True))
	

	sickbeard.updateAiringList()
	sickbeard.updateComingList()

def searchForNeededEpisodes():
	
	logger.log("Searching all providers for any needed episodes")

	foundResults = {}

	didSearch = False

	# ask all providers for any episodes it finds
	for curProvider in providers.sortedProviderList():
		
		if not curProvider.isActive():
			continue
		
		curFoundResults = {}
		
		try:
			curFoundResults = curProvider.searchRSS()
		except exceptions.AuthException, e:
			logger.log("Authentication error: "+str(e), logger.ERROR)
			continue
		except Exception, e:
			logger.log("Error while searching "+curProvider.name+", skipping: "+str(e), logger.ERROR)
			logger.log(traceback.format_exc(), logger.DEBUG)
			continue

		didSearch = True
		
		# pick a single result for each episode, respecting existing results
		for curEp in curFoundResults:
			
			if curEp.show.paused:
				logger.log("Show "+curEp.show.name+" is paused, ignoring all RSS items for "+curEp.prettyName(True), logger.DEBUG)
				continue
			
			# find the best result for the current episode
			bestResult = None
			for curResult in curFoundResults[curEp]:
				if not bestResult or bestResult.quality < curResult.quality:
					bestResult = curResult
			
			bestResult = pickBestResult(curFoundResults[curEp])
			
			# if it's already in the list (from another provider) and the newly found quality is no better then skip it
			if curEp in foundResults and bestResult.quality <= foundResults[curEp].quality:
				continue

			foundResults[curEp] = bestResult

	if not didSearch:
		logger.log("No providers were used for the search - check your settings and ensure that either NZB/Torrents is selected and at least one NZB provider is being used.", logger.ERROR)

	return foundResults.values()


def pickBestResult(results):

	logger.log("Picking the best result out of "+str([x.name for x in results]), logger.DEBUG)

	# find the best result for the current episode
	bestResult = None
	for curResult in results:
		if not bestResult or bestResult.quality < curResult.quality and curResult.quality != Quality.UNKNOWN:
			bestResult = curResult
		elif bestResult.quality == curResult.quality:
			if "proper" in curResult.name.lower() or "repack" in curResult.name.lower():
				bestResult = curResult
			elif "internal" in bestResult.name.lower() and "internal" not in curResult.name.lower():
				bestResult = curResult
	
	if bestResult:
		logger.log("Picked "+bestResult.name+" as the best", logger.DEBUG)
	else:
		logger.log("No result picked.", logger.DEBUG)
	
	return bestResult


def findEpisode(episode, manualSearch=False):

	logger.log("Searching for " + episode.prettyName(True))

	foundResults = []

	didSearch = False

	for curProvider in providers.sortedProviderList():
		
		if not curProvider.isActive():
			continue
		
		try:
			curFoundResults = curProvider.findEpisode(episode, manualSearch=manualSearch)
		except exceptions.AuthException, e:
			logger.log("Authentication error: "+str(e), logger.ERROR)
			continue
		except Exception, e:
			logger.log("Error while searching "+curProvider.name+", skipping: "+str(e), logger.ERROR)
			logger.log(traceback.format_exc(), logger.DEBUG)
			continue
		
		didSearch = True
		
		# skip non-tv crap
		curFoundResults = filter(lambda x: sceneHelpers.filterBadReleases(x.name) and isGoodResult(x, episode.show), curFoundResults)

		foundResults += curFoundResults
		
	if not didSearch:
		logger.log("No providers were used for the search - check your settings and ensure that either NZB/Torrents is selected and at least one NZB provider is being used.", logger.ERROR)

	bestResult = pickBestResult(foundResults)

	return bestResult

def findSeason(show, season):
	
	logger.log("Searching for stuff we need from "+show.name+" season "+str(season))
	
	foundResults = {}
	
	didSearch = False
	
	for curProvider in providers.sortedProviderList():
		
		if not curProvider.isActive():
			continue
		
		try:
			curResults = curProvider.findSeasonResults(show, season)

			# make a list of all the results for this provider
			for curEp in curResults:
				
				# skip non-tv crap
				curResults[curEp] = filter(lambda x:  sceneHelpers.filterBadReleases(x.name) and isGoodResult(x, show), curResults[curEp])

				if curEp in foundResults:
					foundResults[curEp] += curResults[curEp]
				else:
					foundResults[curEp] = curResults[curEp]
		
		except exceptions.AuthException, e:
			logger.log("Authentication error: "+str(e), logger.ERROR)
			continue
		except Exception, e:
			logger.log("Error while searching "+curProvider.name+", skipping: "+str(e), logger.ERROR)
			logger.log(traceback.format_exc(), logger.DEBUG)
			continue
		
		didSearch = True
		
	if not didSearch:
		logger.log("No providers were used for the search - check your settings and ensure that either NZB/Torrents is selected and at least one NZB provider is being used.", logger.ERROR)
	
	finalResults = []

	# pick the best season NZB
	bestSeasonNZB = None
	if SEASON_RESULT in foundResults:
		bestSeasonNZB = pickBestResult(foundResults[SEASON_RESULT])
	
	# see if every episode is wanted
	if bestSeasonNZB:
		
		# get the quality of the season nzb
		seasonQual = Quality.nameQuality(bestSeasonNZB.name)
		logger.log("The quality of the season NZB is "+Quality.qualityStrings[seasonQual], logger.DEBUG)
		
		myDB = db.DBConnection()
		allEps = [int(x["episode"]) for x in myDB.select("SELECT episode FROM tv_episodes WHERE showid = ? AND season = ?", [show.tvdbid, season])]
		logger.log("Episode list: "+str(allEps), logger.DEBUG)
		
		allWanted = True
		anyWanted = False
		for curEpNum in allEps:
			if not show.wantEpisode(season, curEpNum, seasonQual):
				allWanted = False
			else:
				anyWanted = True

		# if we need every ep in the season then just download this and be done with it
		if allWanted:
			logger.log("Every ep in this season is needed, downloading the whole NZB "+bestSeasonNZB.name)
			epObjs = []
			for curEpNum in allEps:
				epObjs.append(show.getEpisode(season, curEpNum))
			bestSeasonNZB.episodes = epObjs
			return [bestSeasonNZB]

		elif not anyWanted:
			logger.log("No eps from this season are wanted at this quality, ignoring the result of "+bestSeasonNZB.name, logger.DEBUG)
			
		else:

			logger.log("Breaking apart the NZB and adding the individual ones to our results", logger.DEBUG)

			# if not, break it apart and add them as the lowest priority results
			individualResults = nzbSplitter.splitResult(bestSeasonNZB)

			individualResults = filter(lambda x:  sceneHelpers.filterBadReleases(x.name) and isGoodResult(x, show), individualResults)

			for curResult in individualResults:
				if len(curResult.episodes) == 1:
					epNum = curResult.episodes[0].episode
				elif len(curResult.episodes) > 1:
					epNum = MULTI_EP_RESULT
				
				if epNum in foundResults:
					foundResults[epNum].append(curResult)
				else:
					foundResults[epNum] = [curResult] 


	# go through multi-ep results and see if we really want them or not, get rid of the rest
	if MULTI_EP_RESULT in foundResults:
		for multiResult in foundResults[MULTI_EP_RESULT]:
			
			logger.log("Seeing if we want to bother with multi-episode result "+multiResult.name, logger.DEBUG)
			
			# see how many of the eps that this result covers aren't covered by single results
			neededEps = []
			notNeededEps = []
			for epObj in multiResult.episodes:
				epNum = epObj.episode
				# if we have results for the episode
				if epNum in foundResults and len(foundResults[epNum]) > 0:
					# but the multi-ep is worse quality, we don't want it
					if False and multiResult.quality <= pickBestResult(foundResults[epNum]):
						notNeededEps.append(epNum)
					else:
						neededEps.append(epNum)
				else:
					neededEps.append(epNum)
	
			logger.log("Result is neededEps: "+str(neededEps)+", notNeededEps: "+str(notNeededEps), logger.DEBUG)

			if not neededEps:
				logger.log("All of these episodes were covered by single nzbs, ignoring this multi-ep result", logger.DEBUG)
				continue
			
			# don't bother with the single result if we're going to get it with a multi result
			for epObj in multiResult.episodes:
				epNum = epObj.episode
				if epNum in foundResults:
					logger.log("A needed multi-episode result overlaps with episode "+str(epNum)+", removing its results from the list", logger.DEBUG)
					del foundResults[epNum]
			
			finalResults.append(multiResult)
	
	# of all the single ep results narrow it down to the best one for each episode
	for curEp in foundResults:
		if curEp in (MULTI_EP_RESULT, SEASON_RESULT):
			continue
		
		if len(foundResults[curEp]) == 0:
			continue
		
		finalResults.append(pickBestResult(foundResults[curEp]))
	
	return finalResults


def isGoodResult(result, show):
	"""
	Use an automatically-created regex to make sure the result actually is the show it claims to be
	"""
	
	showNames = map(sceneHelpers.sanitizeSceneName, sceneHelpers.allPossibleShowNames(show))
	
	for curName in set(showNames):
		curRegex = '^' + re.sub('[\.\-]', '\W+', curName) + '\W+(?:(?:S\d\d)|(?:\d\d?x)|(?:\d{4}\W\d\d\W\d\d)|(?:(?:part|pt)[\._ -]?(\d|[ivx])))'
		logger.log("Checking if show "+result.name+" matches " + curRegex, logger.DEBUG)
		
		match = re.search(curRegex, result.name, re.I)
		
		if match:
			return True
	
	logger.log("Provider gave result "+result.name+" but that doesn't seem like a valid result for "+show.name+" so I'm ignoring it")
	return False
