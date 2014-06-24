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
import datetime
import os
import traceback
import re

import sickbeard

from common import SNATCHED, WANTED, Quality, SEASON_RESULT, MULTI_EP_RESULT

from sickbeard import logger, db, show_name_helpers, exceptions, helpers
from sickbeard import sab
from sickbeard import nzbget
from sickbeard import history
from sickbeard import notifiers
from sickbeard import nzbSplitter
from sickbeard import ui
from sickbeard import encodingKludge as ek
from sickbeard import providers

from sickbeard.exceptions import ex
from sickbeard.providers.generic import GenericProvider


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
            with ek.ek(open, fileName, 'w') as fileOut:
                fileOut.write(result.extraInfo[0])

            helpers.chmodAsParent(fileName)

        except EnvironmentError, e:
            logger.log(u"Error trying to save NZB to black hole: " + ex(e), logger.ERROR)
            newResult = False

    elif resProvider.providerType == "torrent":
        newResult = resProvider.downloadResult(result)

    else:
        logger.log(u"Invalid provider type - this is a coding error, report it please", logger.ERROR)
        return False

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

    ui.notifications.message('Episode snatched', result.name)

    history.logSnatch(result)

    # don't notify when we re-download an episode
    for curEpObj in result.episodes:
        with curEpObj.lock:
            curEpObj.status = Quality.compositeStatus(endStatus, result.quality)
            curEpObj.saveToDB()

        if curEpObj.status not in Quality.DOWNLOADED:
            notifiers.notify_snatch(curEpObj.prettyName())

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
            logger.log(u"Authentication error: " + ex(e), logger.ERROR)
            continue
        except Exception, e:
            logger.log(u"Error while searching " + curProvider.name + ", skipping: " + ex(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
            continue

        didSearch = True

        # pick a single result for each episode, respecting existing results
        for curEp in curFoundResults:

            if curEp.show.paused:
                logger.log(u"Show " + curEp.show.name + " is paused, ignoring all RSS items for " + curEp.prettyName(), logger.DEBUG)
                continue

            # find the best result for the current episode
            bestResult = None
            for curResult in curFoundResults[curEp]:
                if not bestResult or bestResult.quality < curResult.quality:
                    bestResult = curResult

            bestResult = pickBestResult(curFoundResults[curEp], curEp.show)

            # if all results were rejected move on to the next episode
            if not bestResult:
                logger.log(u"All found results for " + curEp.prettyName() + " were rejected.", logger.DEBUG)
                continue

            # if it's already in the list (from another provider) and the newly found quality is no better then skip it
            if curEp in foundResults and bestResult.quality <= foundResults[curEp].quality:
                continue

            foundResults[curEp] = bestResult

    if not didSearch:
        logger.log(u"No NZB/Torrent providers found or enabled in the sickbeard config. Please check your settings.", logger.ERROR)

    return foundResults.values()


def filter_release_name(name, filter_words):
    """
    Filters out results based on filter_words

    name: name to check
    filter_words : Words to filter on, separated by comma

    Returns: False if the release name is OK, True if it contains one of the filter_words
    """
    if filter_words:
        for test_word in filter_words.split(','):
            test_word = test_word.strip()

            if test_word:
                if re.search('(^|[\W_])' + test_word + '($|[\W_])', name, re.I):
                    logger.log(u"" + name + " contains word: " + test_word, logger.DEBUG)
                    return True

    return False


def pickBestResult(results, show, quality_list=None):

    logger.log(u"Picking the best result out of " + str([x.name for x in results]), logger.DEBUG)

    # find the best result for the current episode
    bestResult = None
    for cur_result in results:
        logger.log(u"Quality of " + cur_result.name + " is " + Quality.qualityStrings[cur_result.quality])

        if quality_list and cur_result.quality not in quality_list:
            logger.log(cur_result.name + " is a quality we know we don't want, rejecting it", logger.DEBUG)
            continue

        if show.rls_ignore_words and filter_release_name(cur_result.name, show.rls_ignore_words):
            logger.log(u"Ignoring " + cur_result.name + " based on ignored words filter: " + show.rls_ignore_words, logger.MESSAGE)
            continue

        if show.rls_require_words and not filter_release_name(cur_result.name, show.rls_require_words):
            logger.log(u"Ignoring " + cur_result.name + " based on required words filter: " + show.rls_require_words, logger.MESSAGE)
            continue

        if not bestResult or bestResult.quality < cur_result.quality and cur_result.quality != Quality.UNKNOWN:
            bestResult = cur_result

        elif bestResult.quality == cur_result.quality:
            if "proper" in cur_result.name.lower() or "repack" in cur_result.name.lower():
                bestResult = cur_result
            elif "internal" in bestResult.name.lower() and "internal" not in cur_result.name.lower():
                bestResult = cur_result

    if bestResult:
        logger.log(u"Picked " + bestResult.name + " as the best", logger.MESSAGE)
    else:
        logger.log(u"No result picked.", logger.DEBUG)

    return bestResult


def isFinalResult(result):
    """
    Checks if the given result is good enough quality that we can stop searching for other ones.

    If the result is the highest quality in both the any/best quality lists then this function
    returns True, if not then it's False

    """

    logger.log(u"Checking if we should keep searching after we've found " + result.name, logger.DEBUG)

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

    logger.log(u"Searching for " + episode.prettyName())

    foundResults = []

    didSearch = False

    for curProvider in providers.sortedProviderList():

        if not curProvider.isActive():
            continue

        try:
            curFoundResults = curProvider.findEpisode(episode, manualSearch=manualSearch)
        except exceptions.AuthException, e:
            logger.log(u"Authentication error: " + ex(e), logger.ERROR)
            continue
        except Exception, e:
            logger.log(u"Error while searching " + curProvider.name + ", skipping: " + ex(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
            continue

        didSearch = True

        # skip non-tv crap
        curFoundResults = filter(lambda x: show_name_helpers.filterBadReleases(x.name) and show_name_helpers.isGoodResult(x.name, episode.show), curFoundResults)

        # loop all results and see if any of them are good enough that we can stop searching
        done_searching = False
        for cur_result in curFoundResults:
            done_searching = isFinalResult(cur_result)
            logger.log(u"Should we stop searching after finding " + cur_result.name + ": " + str(done_searching), logger.DEBUG)
            if done_searching:
                break

        foundResults += curFoundResults

        # if we did find a result that's good enough to stop then don't continue
        if done_searching:
            break

    if not didSearch:
        logger.log(u"No NZB/Torrent providers found or enabled in the sickbeard config. Please check your settings.", logger.ERROR)

    bestResult = pickBestResult(foundResults, episode.show)

    return bestResult


def findSeason(show, season):

    logger.log(u"Searching for stuff we need from " + show.name + " season " + str(season))

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
                curResults[curEp] = filter(lambda x: show_name_helpers.filterBadReleases(x.name) and show_name_helpers.isGoodResult(x.name, show), curResults[curEp])

                if curEp in foundResults:
                    foundResults[curEp] += curResults[curEp]
                else:
                    foundResults[curEp] = curResults[curEp]

        except exceptions.AuthException, e:
            logger.log(u"Authentication error: " + ex(e), logger.ERROR)
            continue
        except Exception, e:
            logger.log(u"Error while searching " + curProvider.name + ", skipping: " + ex(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
            continue

        didSearch = True

    if not didSearch:
        logger.log(u"No NZB/Torrent providers found or enabled in the sickbeard config. Please check your settings.", logger.ERROR)

    finalResults = []

    anyQualities, bestQualities = Quality.splitQuality(show.quality)

    # pick the best season NZB
    BestSeasonResult = None
    if SEASON_RESULT in foundResults:
        BestSeasonResult = pickBestResult(foundResults[SEASON_RESULT], show, anyQualities + bestQualities)

    highest_wanted_quality_overall = 0
    for cur_season in foundResults:
        for cur_result in foundResults[cur_season]:
            if cur_result.quality != Quality.UNKNOWN and cur_result.quality in anyQualities + bestQualities and cur_result.quality > highest_wanted_quality_overall:
                highest_wanted_quality_overall = cur_result.quality

    logger.log(u"The highest wanted quality of any match is " + Quality.qualityStrings[highest_wanted_quality_overall], logger.DEBUG)

    # check if complete season pack can be used
    if BestSeasonResult:

        # get the quality of the season nzb
        seasonQual = BestSeasonResult.quality
        logger.log(u"The quality of the season result is " + Quality.qualityStrings[seasonQual], logger.DEBUG)

        # get all episodes in season from db
        myDB = db.DBConnection()
        sql_result = myDB.select("SELECT episode, airdate FROM tv_episodes WHERE showid = ? AND season = ? ORDER BY episode DESC;", [show.tvdbid, season])

        if sql_result:
            last_airdate = datetime.date.fromordinal(sql_result[0]['airdate'])
            all_episodes = sorted([int(x['episode']) for x in sql_result])

        else:
            last_airdate = datetime.date.fromordinal(1)
            all_episodes = []

        logger.log(u"Episode list: " + str(all_episodes), logger.DEBUG)

        today = datetime.date.today()

        # only use complete season packs if season ended
        # only use complete season as fallback if season ended > 7 days

        season_ended = False
        use_season_fallback = False

        if last_airdate == datetime.date.fromordinal(1) or last_airdate > today:
            logger.log(u"Ignoring " + BestSeasonResult.name + ", airdate of last episode in season: " + str(last_airdate) + " is never or > today", logger.DEBUG)

        elif last_airdate + datetime.timedelta(days=7) <= today:
            season_ended = True
            use_season_fallback = True

        elif last_airdate < today:
            season_ended = True
            logger.log(u"Ignoring " + BestSeasonResult.name + " as fallback, airdate of last episode in season: " + str(last_airdate) + " is < 7 days", logger.DEBUG)

        # check if all or some episodes of the season are wanted
        want_all_eps = True
        want_some_eps = False

        for cur_ep_num in all_episodes:
            if not show.wantEpisode(season, cur_ep_num, seasonQual):
                want_all_eps = False
            else:
                want_some_eps = True

        # if every episode is needed in the season and there's nothing better then just download this and be done with it
        if season_ended and want_all_eps and BestSeasonResult.quality == highest_wanted_quality_overall:
            logger.log(u"Every episode in this season is needed, downloading the whole season " + BestSeasonResult.name)
            epObjs = []
            for cur_ep_num in all_episodes:
                epObjs.append(show.getEpisode(season, cur_ep_num))
            BestSeasonResult.episodes = epObjs
            return [BestSeasonResult]

        elif not want_some_eps:
            logger.log(u"No episodes from this season are wanted at this quality, ignoring the result of " + BestSeasonResult.name, logger.DEBUG)

        else:

            # if not all episodes are wanted try splitting up the complete season pack
            if BestSeasonResult.provider.providerType == GenericProvider.NZB:
                logger.log(u"Try breaking apart the NZB and adding the individual ones to our results", logger.DEBUG)

                # break it apart and add them as the lowest priority results
                individualResults = nzbSplitter.splitResult(BestSeasonResult)

                individualResults = filter(lambda x: show_name_helpers.filterBadReleases(x.name) and show_name_helpers.isGoodResult(x.name, show), individualResults)

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

                # if not all episodes are wanted, splitting up the complete season pack for torrents is not possible
                # all we can do is leech the entire torrent, user will have to select which episodes not do download in his torrent client

                if use_season_fallback:
                    # Creating a multi-ep result from a torrent Season result
                    logger.log(u"Adding multi-ep result for full-season torrent. Set the episodes you don't want to 'don't download' in your torrent client if desired!")
                    epObjs = []

                    for cur_ep_num in all_episodes:
                        # only add wanted episodes for comparing/filter later with single results
                        if show.wantEpisode(season, cur_ep_num, BestSeasonResult.quality):
                            epObjs.append(show.getEpisode(season, cur_ep_num))

                    BestSeasonResult.episodes = epObjs

                    if MULTI_EP_RESULT in foundResults:
                        foundResults[MULTI_EP_RESULT].append(BestSeasonResult)
                    else:
                        foundResults[MULTI_EP_RESULT] = [BestSeasonResult]

    # go through multi-ep results and see if we really want them or not, get rid of the rest
    multiResults = {}
    if MULTI_EP_RESULT in foundResults:
        for multiResult in foundResults[MULTI_EP_RESULT]:

            logger.log(u"Check multi-episode result against single episode results" + multiResult.name, logger.DEBUG)

            # see how many of the eps that this result covers aren't covered by single results
            in_single_results = []
            not_in_single_results = []
            for epObj in multiResult.episodes:
                epNum = epObj.episode
                # if we have results for the episode
                if epNum in foundResults and len(foundResults[epNum]) > 0:
                    in_single_results.append(epNum)
                else:
                    not_in_single_results.append(epNum)

            logger.log(u"Multi-episode check result, episodes not in single results: " + str(not_in_single_results) + ", episodes in single results: " + str(in_single_results), logger.DEBUG)

            if not not_in_single_results:
                logger.log(u"All of these episodes were covered by single episode results, ignoring this multi-episode result", logger.DEBUG)
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

            logger.log(u"Multi-ep check result is multiNeededEps: " + str(multiNeededEps) + ", multiNotNeededEps: " + str(multiNotNeededEps), logger.DEBUG)

            if not multiNeededEps:
                logger.log(u"All of these episodes were covered by another multi-episode nzbs, ignoring this multi-ep result", logger.DEBUG)
                continue

            # if we're keeping this multi-result then remember it
            for epObj in multiResult.episodes:
                multiResults[epObj.episode] = multiResult

            # don't bother with the single result if we're going to get it with a multi result
            for epObj in multiResult.episodes:
                epNum = epObj.episode
                if epNum in foundResults:
                    logger.log(u"A needed multi-episode result overlaps with a single-episode result for ep #" + str(epNum) + ", removing the single-episode results from the list", logger.DEBUG)
                    del foundResults[epNum]

    finalResults += set(multiResults.values())

    # of all the single ep results narrow it down to the best one for each episode
    for curEp in foundResults:
        if curEp in (MULTI_EP_RESULT, SEASON_RESULT):
            continue

        if len(foundResults[curEp]) == 0:
            continue

        finalResults.append(pickBestResult(foundResults[curEp], show))

    return finalResults
