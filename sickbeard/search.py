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

import os
import traceback

import sickbeard

from common import SNATCHED, Quality, SEASON_RESULT, MULTI_EP_RESULT

from sickbeard import logger, db, show_name_helpers, exceptions, helpers
from sickbeard import sab
from sickbeard import nzbget
from sickbeard import history
from sickbeard import notifiers
from sickbeard import nzbSplitter
from sickbeard import ui
from sickbeard import encodingKludge as ek
from sickbeard.exceptions import ex
from sickbeard import providers

def _downloadResult(result):
    """
    Downloads a result to the appropriate black hole folder.
    
    Returns a bool representing success.
    
    result: SearchResult instance to download.
    """

    resProvider = result.provider

    newResult = False

    if resProvider == None:
        logger.log(u"Invalid provider name - this is a coding error, report it please", logger.ERROR)
        return False

    # nzbs with an URL can just be downloaded from the provider
    if result.resultType == "nzb":
        newResult = resProvider.downloadResult(result)

    # if it's an nzb data result 
    elif result.resultType == "nzbdata":
        
        # get the final file path to the nzb
        fileName = ek.ek(os.path.join, sickbeard.NZB_DIR, result.name + ".nzb")

        logger.log(u"Saving NZB to " + fileName)

        newResult = True

        # save the data to disk
        try:
            fileOut = open(fileName, "w")
            fileOut.write(result.extraInfo[0])
            fileOut.close()
            helpers.chmodAsParent(fileName)
        except IOError, e:
            logger.log(u"Error trying to save NZB to black hole: "+ex(e), logger.ERROR)
            newResult = False

    elif resProvider.providerType == "torrent":
        newResult = resProvider.downloadResult(result)

    else:
        logger.log(u"Invalid provider type - this is a coding error, report it please", logger.ERROR)
        return False

    if newResult:
        ui.notifications.message('Episode snatched','<b>%s</b> snatched from <b>%s</b>' % (result.name, resProvider.name))

    return newResult

def snatchEpisode(result, endStatus=SNATCHED):
    """
    Contains the internal logic necessary to actually "snatch" a result that
    has been found.
    
    Returns a bool representing success.
    
    result: SearchResult instance to be snatched.
    endStatus: the episode status that should be used for the episode object once it's snatched.
    """

    # NZBs can be sent straight to SAB or saved to disk
    if result.resultType in ("nzb", "nzbdata"):
        if sickbeard.NZB_METHOD == "blackhole":
            dlResult = _downloadResult(result)
        elif sickbeard.NZB_METHOD == "sabnzbd":
            dlResult = sab.sendNZB(result)
        elif sickbeard.NZB_METHOD == "nzbget":
            dlResult = nzbget.sendNZB(result)
        else:
            logger.log(u"Unknown NZB action specified in config: " + sickbeard.NZB_METHOD, logger.ERROR)
            dlResult = False

    # torrents are always saved to disk
    elif result.resultType == "torrent":
        dlResult = _downloadResult(result)
    else:
        logger.log(u"Unknown result type, unable to download it", logger.ERROR)
        dlResult = False

    if dlResult == False:
        return False

    history.logSnatch(result)

    # don't notify when we re-download an episode
    for curEpObj in result.episodes:
        with curEpObj.lock:
            curEpObj.status = Quality.compositeStatus(endStatus, result.quality)
            curEpObj.saveToDB()

        if curEpObj.status not in Quality.DOWNLOADED:
            notifiers.notify_snatch(curEpObj.prettyName(True))

    return True

def searchForNeededEpisodes():

    logger.log(u"Searching all providers for any needed episodes")

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
            logger.log(u"Authentication error: "+ex(e), logger.ERROR)
            continue
        except Exception, e:
            logger.log(u"Error while searching "+curProvider.name+", skipping: "+ex(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
            continue

        didSearch = True

        # pick a single result for each episode, respecting existing results
        for curEp in curFoundResults:

            if curEp.show.paused:
                logger.log(u"Show "+curEp.show.name+" is paused, ignoring all RSS items for "+curEp.prettyName(True), logger.DEBUG)
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
        logger.log(u"No NZB/Torrent providers found or enabled in the sickbeard config. Please check your settings.", logger.ERROR)

    return foundResults.values()


def pickBestResult(results, quality_list=None):

    logger.log(u"Picking the best result out of "+str([x.name for x in results]), logger.DEBUG)

    # find the best result for the current episode
    bestResult = None
    for cur_result in results:
        logger.log("Quality of "+cur_result.name+" is "+Quality.qualityStrings[cur_result.quality])
        
        if quality_list and cur_result.quality not in quality_list:
            logger.log(cur_result.name+" is a quality we know we don't want, rejecting it", logger.DEBUG)
            continue
        
        if not bestResult or bestResult.quality < cur_result.quality and cur_result.quality != Quality.UNKNOWN:
            bestResult = cur_result
        elif bestResult.quality == cur_result.quality:
            if "proper" in cur_result.name.lower() or "repack" in cur_result.name.lower():
                bestResult = cur_result
            elif "internal" in bestResult.name.lower() and "internal" not in cur_result.name.lower():
                bestResult = cur_result

    if bestResult:
        logger.log(u"Picked "+bestResult.name+" as the best", logger.DEBUG)
    else:
        logger.log(u"No result picked.", logger.DEBUG)

    return bestResult

def isFinalResult(result):
    """
    Checks if the given result is good enough quality that we can stop searching for other ones.
    
    If the result is the highest quality in both the any/best quality lists then this function
    returns True, if not then it's False

    """
    
    logger.log(u"Checking if we should keep searching after we've found "+result.name, logger.DEBUG)
    
    show_obj = result.episodes[0].show
    
    any_qualities, best_qualities = Quality.splitQuality(show_obj.quality)
    
    # if there is a redownload that's higher than this then we definitely need to keep looking
    if best_qualities and result.quality < max(best_qualities):
        return False

    # if there's no redownload that's higher (above) and this is the highest initial download then we're good
    elif any_qualities and result.quality == max(any_qualities):
        return True
    
    elif best_qualities and result.quality == max(best_qualities):
        
        # if this is the best redownload but we have a higher initial download then keep looking
        if any_qualities and result.quality < max(any_qualities):
            return False
        
        # if this is the best redownload and we don't have a higher initial download then we're done
        else:
            return True

    # if we got here than it's either not on the lists, they're empty, or it's lower than the highest required
    else:
        return False


def findEpisode(episode, manualSearch=False):

    logger.log(u"Searching for " + episode.prettyName(True))

    foundResults = []

    didSearch = False

    for curProvider in providers.sortedProviderList():

        if not curProvider.isActive():
            continue

        try:
            curFoundResults = curProvider.findEpisode(episode, manualSearch=manualSearch)
        except exceptions.AuthException, e:
            logger.log(u"Authentication error: "+ex(e), logger.ERROR)
            continue
        except Exception, e:
            logger.log(u"Error while searching "+curProvider.name+", skipping: "+ex(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
            continue

        didSearch = True

        # skip non-tv crap
        curFoundResults = filter(lambda x: show_name_helpers.filterBadReleases(x.name) and show_name_helpers.isGoodResult(x.name, episode.show), curFoundResults)

        # loop all results and see if any of them are good enough that we can stop searching
        done_searching = False
        for cur_result in curFoundResults:
            done_searching = isFinalResult(cur_result)
            logger.log(u"Should we stop searching after finding "+cur_result.name+": "+str(done_searching), logger.DEBUG)
            if done_searching:
                break
        
        foundResults += curFoundResults

        # if we did find a result that's good enough to stop then don't continue
        if done_searching:
            break

    if not didSearch:
        logger.log(u"No NZB/Torrent providers found or enabled in the sickbeard config. Please check your settings.", logger.ERROR)

    bestResult = pickBestResult(foundResults)

    return bestResult

def findSeason(show, season):

    logger.log(u"Searching for stuff we need from "+show.name+" season "+str(season))

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
                curResults[curEp] = filter(lambda x:  show_name_helpers.filterBadReleases(x.name) and show_name_helpers.isGoodResult(x.name, show), curResults[curEp])

                if curEp in foundResults:
                    foundResults[curEp] += curResults[curEp]
                else:
                    foundResults[curEp] = curResults[curEp]

        except exceptions.AuthException, e:
            logger.log(u"Authentication error: "+ex(e), logger.ERROR)
            continue
        except Exception, e:
            logger.log(u"Error while searching "+curProvider.name+", skipping: "+ex(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
            continue

        didSearch = True

    if not didSearch:
        logger.log(u"No NZB/Torrent providers found or enabled in the sickbeard config. Please check your settings.", logger.ERROR)

    finalResults = []

    anyQualities, bestQualities = Quality.splitQuality(show.quality)

    # pick the best season NZB
    bestSeasonNZB = None
    if SEASON_RESULT in foundResults:
        bestSeasonNZB = pickBestResult(foundResults[SEASON_RESULT], anyQualities+bestQualities)

    highest_quality_overall = 0
    for cur_season in foundResults:
        for cur_result in foundResults[cur_season]:
            if cur_result.quality != Quality.UNKNOWN and cur_result.quality > highest_quality_overall:
                highest_quality_overall = cur_result.quality
    logger.log(u"The highest quality of any match is "+Quality.qualityStrings[highest_quality_overall], logger.DEBUG)

    # see if every episode is wanted
    if bestSeasonNZB:

        # get the quality of the season nzb
        seasonQual = Quality.nameQuality(bestSeasonNZB.name)
        seasonQual = bestSeasonNZB.quality
        logger.log(u"The quality of the season NZB is "+Quality.qualityStrings[seasonQual], logger.DEBUG)

        myDB = db.DBConnection()
        allEps = [int(x["episode"]) for x in myDB.select("SELECT episode FROM tv_episodes WHERE showid = ? AND season = ?", [show.tvdbid, season])]
        logger.log(u"Episode list: "+str(allEps), logger.DEBUG)

        allWanted = True
        anyWanted = False
        for curEpNum in allEps:
            if not show.wantEpisode(season, curEpNum, seasonQual):
                allWanted = False
            else:
                anyWanted = True

        # if we need every ep in the season and there's nothing better then just download this and be done with it
        if allWanted and bestSeasonNZB.quality == highest_quality_overall:
            logger.log(u"Every ep in this season is needed, downloading the whole NZB "+bestSeasonNZB.name)
            epObjs = []
            for curEpNum in allEps:
                epObjs.append(show.getEpisode(season, curEpNum))
            bestSeasonNZB.episodes = epObjs
            return [bestSeasonNZB]

        elif not anyWanted:
            logger.log(u"No eps from this season are wanted at this quality, ignoring the result of "+bestSeasonNZB.name, logger.DEBUG)

        else:
            
            # Check if the provider of this NZB is BTN, if so it's not a NZB but a torrent so all we can do is leach the entire torrent, user will have to select which eps not do download in his torrent client
            if not 'BTN' in bestSeasonNZB.provider.name:
                logger.log(u"Breaking apart the NZB and adding the individual ones to our results", logger.DEBUG)
                
                # if not, break it apart and add them as the lowest priority results
                individualResults = nzbSplitter.splitResult(bestSeasonNZB)

                individualResults = filter(lambda x:  show_name_helpers.filterBadReleases(x.name) and show_name_helpers.isGoodResult(x.name, show), individualResults)

                for curResult in individualResults:
                    if len(curResult.episodes) == 1:
                        epNum = curResult.episodes[0].episode
                    elif len(curResult.episodes) > 1:
                        epNum = MULTI_EP_RESULT

                    if epNum in foundResults:
                        foundResults[epNum].append(curResult)
                    else:
                        foundResults[epNum] = [curResult]
            else:
                # Season result from BTN must be a full-season torrent, creating multi-ep result for it.
                logger.log(u"Adding multi-ep result for full-season torrent. Set the episodes you don't want to 'don't download' in your torrent client if desired!")
                epObjs = []
                for curEpNum in allEps:
                    epObjs.append(show.getEpisode(season, curEpNum))
                bestSeasonNZB.episodes = epObjs

                epNum = MULTI_EP_RESULT
                if epNum in foundResults:
                    foundResults[epNum].append(bestSeasonNZB)
                else:
                    foundResults[epNum] = [bestSeasonNZB]

    # go through multi-ep results and see if we really want them or not, get rid of the rest
    multiResults = {}
    if MULTI_EP_RESULT in foundResults:
        for multiResult in foundResults[MULTI_EP_RESULT]:

            logger.log(u"Seeing if we want to bother with multi-episode result "+multiResult.name, logger.DEBUG)

            # see how many of the eps that this result covers aren't covered by single results
            neededEps = []
            notNeededEps = []
            for epObj in multiResult.episodes:
                epNum = epObj.episode
                # if we have results for the episode
                if epNum in foundResults and len(foundResults[epNum]) > 0:
                    # but the multi-ep is worse quality, we don't want it
                    # TODO: wtf is this False for
                    #if False and multiResult.quality <= pickBestResult(foundResults[epNum]):
                    #    notNeededEps.append(epNum)
                    #else:
                    neededEps.append(epNum)
                else:
                    neededEps.append(epNum)

            logger.log(u"Single-ep check result is neededEps: "+str(neededEps)+", notNeededEps: "+str(notNeededEps), logger.DEBUG)

            if not neededEps:
                logger.log(u"All of these episodes were covered by single nzbs, ignoring this multi-ep result", logger.DEBUG)
                continue

            # check if these eps are already covered by another multi-result
            multiNeededEps = []
            multiNotNeededEps = []
            for epObj in multiResult.episodes:
                epNum = epObj.episode
                if epNum in multiResults:
                    multiNotNeededEps.append(epNum)
                else:
                    multiNeededEps.append(epNum)

            logger.log(u"Multi-ep check result is multiNeededEps: "+str(multiNeededEps)+", multiNotNeededEps: "+str(multiNotNeededEps), logger.DEBUG)

            if not neededEps:
                logger.log(u"All of these episodes were covered by another multi-episode nzbs, ignoring this multi-ep result", logger.DEBUG)
                continue

            # if we're keeping this multi-result then remember it
            for epObj in multiResult.episodes:
                multiResults[epObj.episode] = multiResult

            # don't bother with the single result if we're going to get it with a multi result
            for epObj in multiResult.episodes:
                epNum = epObj.episode
                if epNum in foundResults:
                    logger.log(u"A needed multi-episode result overlaps with a single-episode result for ep #"+str(epNum)+", removing the single-episode results from the list", logger.DEBUG)
                    del foundResults[epNum]

    finalResults += set(multiResults.values())

    # of all the single ep results narrow it down to the best one for each episode
    for curEp in foundResults:
        if curEp in (MULTI_EP_RESULT, SEASON_RESULT):
            continue

        if len(foundResults[curEp]) == 0:
            continue

        finalResults.append(pickBestResult(foundResults[curEp]))

    return finalResults
