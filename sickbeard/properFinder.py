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

import datetime
import operator

import sickbeard

from sickbeard import db
from sickbeard import exceptions
from sickbeard.exceptions import ex
from sickbeard import helpers, logger, show_name_helpers
from sickbeard import providers
from sickbeard import search
from sickbeard import history

from sickbeard.common import DOWNLOADED, SNATCHED, SNATCHED_PROPER, Quality

from lib.tvdb_api import tvdb_api, tvdb_exceptions

from name_parser.parser import NameParser, InvalidNameException


class ProperFinder():

    def __init__(self):
        self.updateInterval = datetime.timedelta(hours=1)

    def run(self):

        if not sickbeard.DOWNLOAD_PROPERS:
            return

        # look for propers every night at 1 AM
        updateTime = datetime.time(hour=1)
        hourDiff = datetime.datetime.today().time().hour - updateTime.hour

        # if it's less than an interval after the update time then do an update
        if hourDiff >= 0 and hourDiff < self.updateInterval.seconds / 3600:
            logger.log(u"Beginning the search for new propers")
        else:
            return

        propers = self._getProperList()

        self._downloadPropers(propers)

    def _getProperList(self):

        propers = {}

        # for each provider get a list of the propers
        for curProvider in providers.sortedProviderList():

            if not curProvider.isActive():
                continue

            search_date = datetime.datetime.today() - datetime.timedelta(days=2)

            logger.log(u"Searching for any new PROPER releases from " + curProvider.name)
            try:
                curPropers = curProvider.findPropers(search_date)
            except exceptions.AuthException, e:
                logger.log(u"Authentication error: " + ex(e), logger.ERROR)
                continue

            # if they haven't been added by a different provider than add the proper to the list
            for x in curPropers:
                name = self._genericName(x.name)

                if not name in propers:
                    logger.log(u"Found new proper: " + x.name, logger.DEBUG)
                    x.provider = curProvider
                    propers[name] = x

        # take the list of unique propers and get it sorted by
        sortedPropers = sorted(propers.values(), key=operator.attrgetter('date'), reverse=True)
        finalPropers = []

        for curProper in sortedPropers:

            # parse the file name
            try:
                myParser = NameParser(False)
                parse_result = myParser.parse(curProper.name)
            except InvalidNameException:
                logger.log(u"Unable to parse the filename " + curProper.name + " into a valid episode", logger.DEBUG)
                continue

            if not parse_result.episode_numbers:
                logger.log(u"Ignoring " + curProper.name + " because it's for a full season rather than specific episode", logger.DEBUG)
                continue

            # populate our Proper instance
            if parse_result.air_by_date:
                curProper.season = -1
                curProper.episode = parse_result.air_date
            else:
                curProper.season = parse_result.season_number if parse_result.season_number != None else 1
                curProper.episode = parse_result.episode_numbers[0]
            curProper.quality = Quality.nameQuality(curProper.name)

            # for each show in our list
            for curShow in sickbeard.showList:

                if not parse_result.series_name:
                    continue

                genericName = self._genericName(parse_result.series_name)

                # get the scene name masks
                sceneNames = set(show_name_helpers.makeSceneShowSearchStrings(curShow))

                # for each scene name mask
                for curSceneName in sceneNames:

                    # if it matches
                    if genericName == self._genericName(curSceneName):
                        logger.log(u"Successful match! Result " + parse_result.series_name + " matched to show " + curShow.name, logger.DEBUG)

                        # set the tvdbid in the db to the show's tvdbid
                        curProper.tvdbid = curShow.tvdbid

                        # since we found it, break out
                        break

                # if we found something in the inner for loop break out of this one
                if curProper.tvdbid != -1:
                    break

            if curProper.tvdbid == -1:
                continue

            if not show_name_helpers.filterBadReleases(curProper.name):
                logger.log(u"Proper " + curProper.name + " isn't a valid scene release that we want, ignoring it", logger.DEBUG)
                continue

            show = helpers.findCertainShow(sickbeard.showList, curProper.tvdbid)
            if not show:
                logger.log(u"Unable to find the show with tvdbid " + str(curProper.tvdbid), logger.ERROR)
                continue

            if show.rls_ignore_words and search.filter_release_name(curProper.name, show.rls_ignore_words):
                logger.log(u"Ignoring " + curProper.name + " based on ignored words filter: " + show.rls_ignore_words, logger.MESSAGE)
                continue

            if show.rls_require_words and not search.filter_release_name(curProper.name, show.rls_require_words):
                logger.log(u"Ignoring " + curProper.name + " based on required words filter: " + show.rls_require_words, logger.MESSAGE)
                continue

            # if we have an air-by-date show then get the real season/episode numbers
            if curProper.season == -1 and curProper.tvdbid:

                tvdb_lang = show.lang
                # There's gotta be a better way of doing this but we don't wanna
                # change the language value elsewhere
                ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

                if tvdb_lang and not tvdb_lang == 'en':
                    ltvdb_api_parms['language'] = tvdb_lang

                try:
                    t = tvdb_api.Tvdb(**ltvdb_api_parms)
                    epObj = t[curProper.tvdbid].airedOn(curProper.episode)[0]
                    curProper.season = int(epObj["seasonnumber"])
                    curProper.episodes = [int(epObj["episodenumber"])]
                except tvdb_exceptions.tvdb_episodenotfound:
                    logger.log(u"Unable to find episode with date " + str(curProper.episode) + " for show " + parse_result.series_name + ", skipping", logger.WARNING)
                    continue

            # check if we actually want this proper (if it's the right quality)
            sqlResults = db.DBConnection().select("SELECT status FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?", [curProper.tvdbid, curProper.season, curProper.episode])
            if not sqlResults:
                continue
            oldStatus, oldQuality = Quality.splitCompositeStatus(int(sqlResults[0]["status"]))

            # only keep the proper if we have already retrieved the same quality ep (don't get better/worse ones)
            if oldStatus not in (DOWNLOADED, SNATCHED) or oldQuality != curProper.quality:
                continue

            # if the show is in our list and there hasn't been a proper already added for that particular episode then add it to our list of propers
            if curProper.tvdbid != -1 and (curProper.tvdbid, curProper.season, curProper.episode) not in map(operator.attrgetter('tvdbid', 'season', 'episode'), finalPropers):
                logger.log(u"Found a proper that we need: " + str(curProper.name))
                finalPropers.append(curProper)

        return finalPropers

    def _downloadPropers(self, properList):

        for curProper in properList:

            historyLimit = datetime.datetime.today() - datetime.timedelta(days=30)

            # make sure the episode has been downloaded before
            myDB = db.DBConnection()
            historyResults = myDB.select(
                "SELECT resource FROM history "
                "WHERE showid = ? AND season = ? AND episode = ? AND quality = ? AND date >= ? "
                "AND action IN (" + ",".join([str(x) for x in Quality.SNATCHED]) + ")",
                        [curProper.tvdbid, curProper.season, curProper.episode, curProper.quality, historyLimit.strftime(history.dateFormat)])

            # if we didn't download this episode in the first place we don't know what quality to use for the proper so we can't do it
            if len(historyResults) == 0:
                logger.log(u"Unable to find an original history entry for proper " + curProper.name + " so I'm not downloading it.")
                continue

            else:

                # make sure that none of the existing history downloads are the same proper we're trying to download
                isSame = False
                for curResult in historyResults:
                    # if the result exists in history already we need to skip it
                    if self._genericName(curResult["resource"]) == self._genericName(curProper.name):
                        isSame = True
                        break
                if isSame:
                    logger.log(u"This proper is already in history, skipping it", logger.DEBUG)
                    continue

                # get the episode object
                showObj = helpers.findCertainShow(sickbeard.showList, curProper.tvdbid)
                if showObj == None:
                    logger.log(u"Unable to find the show with tvdbid " + str(curProper.tvdbid) + " so unable to download the proper", logger.ERROR)
                    continue
                epObj = showObj.getEpisode(curProper.season, curProper.episode)

                # make the result object
                result = curProper.provider.getResult([epObj])
                result.url = curProper.url
                result.name = curProper.name
                result.quality = curProper.quality

                # snatch it
                search.snatchEpisode(result, SNATCHED_PROPER)

    def _genericName(self, name):
        return name.replace(".", " ").replace("-", " ").replace("_", " ").lower()
