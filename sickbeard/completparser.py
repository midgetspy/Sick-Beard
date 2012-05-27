# Author: Dennis Lutter <lad1337@gmail.com>
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

import threading
import re

import sickbeard
from sickbeard.exceptions import MultipleShowObjectsException, EpisodeNotFoundByAbsoluteNumerException, ex
from sickbeard import logger, classes, exceptions, helpers
from sickbeard.name_parser.parser import NameParser, InvalidNameException
from sickbeard import common

from sickbeard import db
from sickbeard import encodingKludge as ek

from lib.tvdb_api import tvdb_api, tvdb_exceptions


class CompleteParser(object):

    def __init__(self, show=None, showList=None, tvdbActiveLookUp=False):
        self.name_to_parse = ""
        self.raw_parse_result = None
        self.complete_result = CompleteResult()
        self.succesful_regex_mode = None
        self.show = show
        if showList != None:
            self.showList = showList
        else:
            self.showList = sickbeard.showList
        self.tvdbActiveLookUp = tvdbActiveLookUp

    def parse(self, name_to_parse):
        self.complete_result.lock.acquire()

        self.name_to_parse = name_to_parse
        # lets parse the name
        try:
            self.raw_parse_result, cur_show = self.parse_wrapper(self.show, self.name_to_parse, self.showList, self.tvdbActiveLookUp)
        except InvalidNameException:
            logger.log("Could not parse " + ek.ek(str, name_to_parse), logger.DEBUG)
            return self.complete_result

        # setup values of the
        self.complete_result.parse_result = self.raw_parse_result
        if self.show and cur_show:
            if self.show.tvdbid != cur_show.tvdbid:
                logger.log("I expected an episode of the show " + str(self.show.name) + " but the parser thinks its the show " + str(cur_show) + ". I will continue thinking its " + str(self.show), logger.WARNING)
                cur_show = self.show
        self.complete_result.show = cur_show

        # TODO: find a place for "if there's no season then we can hopefully just use 1 automatically"
        # fix scene numbers now !
        if cur_show and self.raw_parse_result.release_group:
            # this does also take care of absolute number to sxxexx conversion
            logger.log("This looks like a scene release converting numbers", logger.DEBUG)
            self.complete_result.season, self.complete_result.episodes, self.complete_result.ab_episode_numbers = \
                self.scene2tvdb(cur_show, self.raw_parse_result.series_name, self.raw_parse_result.season_number, self.raw_parse_result.episode_numbers, self.raw_parse_result.ab_episode_numbers)
            self.complete_result.scene = True
        elif cur_show:
            logger.log("This does not look like a scene release. assuming tvdb numbers", logger.DEBUG)
            if cur_show.is_anime:
                logger.log("Getting season and episodes from absolute numbers", logger.DEBUG)
                try:
                    (actual_season, actual_episodes) = helpers.get_all_episodes_from_absolute_number(cur_show, None, self.parse_result.ab_episode_numbers)
                except exceptions.EpisodeNotFoundByAbsoluteNumerException:
                    logger.log(str(cur_show.tvdbid) + ": TVDB object absolute number " + str(self.parse_result.ab_episode_numbers) + " is incomplete, cant determin season and episode numbers")
                else:
                    self.complete_result.season = actual_season
                    self.complete_result.episodes = actual_episodes
            elif cur_show.air_by_date:
                logger.log("Getting season and episodes for ADB show", logger.DEBUG)
                self.complete_result.season, self.complete_result.episodes = self._convertADB(self.parse_result.air_date)
        else: # parse_wrapper could not find a show :(
            logger.log("No show could be matched. assuming tvdb numbers", logger.DEBUG)
            # we will use the stuff from the parser
            self.complete_result.season = self.raw_parse_result.season_number
            self.complete_result.episodes = self.raw_parse_result.episode_numbers

        _quality_as_anime = False
        if cur_show and cur_show.is_anime:
            _quality_as_anime = True
        self.complete_result.quality = common.Quality.nameQuality(self.name_to_parse, _quality_as_anime)

        self.complete_result.lock.release()
        return self.complete_result

    def _convertADB(self, adb_part):
        logger.log("Getting season and episodes for ADB episode: " + str(adb_part), logger.DEBUG)
        if self.tvdbActiveLookUp:
            try:
                # There's gotta be a better way of doing this but we don't wanna
                # change the cache value elsewhere
                ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

                if self.lang:
                    ltvdb_api_parms['language'] = self.lang

                t = tvdb_api.Tvdb(**ltvdb_api_parms)

                epObj = t[self.tvdbid].airedOn(adb_part)[0]
                season = int(epObj["seasonnumber"])
                episodes = [int(epObj["episodenumber"])]
            except tvdb_exceptions.tvdb_episodenotfound:
                logger.log(u"Unable to find episode with date " + str(episodes[0]) + " for show " + self.name + ", skipping", logger.WARNING)
                return (None, None)
            except tvdb_exceptions.tvdb_error, e:
                logger.log(u"Unable to contact TVDB: " + ex(e), logger.WARNING)
                return (None, None)
            else:
                return (season, episodes)
        else: #TODO: implement a local lookup
            return (None, None)

    def parse_wrapper(self, show=None, toParse='', showList=[], tvdbActiveLookUp=False):
        """Retruns a parse result or a InvalidNameException
            it will try to take the correct regex for the show if given
            if not given it will try Anime first then Normal
            if name is parsed as anime it will lookup the tvdbid and check if we have it as an anime
            only if both is true we will consider it an anime
            to get the tvdbid the tvdbapi might be used if tvdbActiveLookUp is True
        """
        # TODO: refactor ABD into its own mode
        if len(showList) == 0:
            showList = sickbeard.showList

        if show and show.is_anime:
            modeList = [NameParser.ANIME_REGEX, NameParser.NORMAL_REGEX]
        elif show and not show.is_anime:
            modeList = [NameParser.NORMAL_REGEX]
        else: # just try both ... time consuming
            modeList = [NameParser.ANIME_REGEX, NameParser.NORMAL_REGEX]

        for mode in modeList:
            try:
                myParser = NameParser(regexMode=mode)
                parse_result = myParser.parse(toParse)
            except InvalidNameException:
                pass
            else:
                show = helpers.get_show_by_name(parse_result.series_name, showList, tvdbActiveLookUp)
                if mode == NameParser.ANIME_REGEX:
                    if show and show.is_anime:
                        break
                elif mode == NameParser.NORMAL_REGEX:
                    if (show and not show.is_anime) or not show:
                        break
        else:
            raise InvalidNameException("Unable to parse " + toParse)

        return (parse_result, show)

    def scene2tvdb(self, show, scene_name, season, episodes, absolute_numbers):
        # TODO: check if adb and make scene2tvdb useabel with correct numbers
        out_season = None
        out_episodes = []
        out_absolute_numbers = []

        # is the scene name a special season ?
        # TODO: define if we get scene seasons or tvdb seasons ... for now they are mostly the same ... and i will tried them as scene seasons
        _possible_seasons = sickbeard.scene_exceptions.get_scene_exception_by_name_multiple(scene_name)
        # filter possible_seasons
        possible_seasons = []
        for cur_scene_tvdb_id, cur_scene_season in _possible_seasons:
            if cur_scene_tvdb_id != show.tvdbid:
                logger.log("dfuq when i tried to figure out the season from the name i got a different tvdbid then we got before !! stoping right now!", logger.ERROR)
                raise
            possible_seasons.append(cur_scene_season)
        #if not possible_seasons: # no special season name was used or we could not find it
        #    possible_seasons = show.getAllSeasonNumbers() # lets look at every season
        logger.log("possible seasons for " + scene_name + "(" + str(show.tvdbid) + ") are " + str(possible_seasons), logger.DEBUG)

        # lets just get a db connection we will need it anyway
        myDB = db.DBConnection()
        # should we use absolute_numbers -> anime or season, episodes -> normal show
        if show.is_anime:
            logger.log(u"" + show.name + " is an anime i will scene convert the absolute numbers " + str(absolute_numbers), logger.DEBUG)
            if possible_seasons:
                #check if we have a scene_absolute_number in the possible seasons
                for cur_possible_season in possible_seasons:
                    # and for all absolute numbers
                    for cur_ab_number in absolute_numbers:
                        namesSQlResult = myDB.select("SELECT season, episode, absolute_number, name FROM tv_episodes WHERE showid = ? and scene_season = ? and scene_absolute_number = ?", [show.tvdbid, cur_possible_season, cur_ab_number])
                        if len(namesSQlResult) > 1:
                            logger.log("Multiple scene absolute number for season. this should not be check xem configuration", logger.ERROR)
                            raise
                        elif len(namesSQlResult) == 0:
                            break # break out of current absolute_numbers -> next season
                        # if we are here we found ONE episode for this season absolute number
                        logger.log("I found matching episode " + ek.ek(str, namesSQlResult[0]['name']), logger.DEBUG)
                        out_episodes.append(int(namesSQlResult[0]['episode']))
                        out_absolute_numbers.append(int(namesSQlResult[0]['absolute_number']))
                        out_season = int(namesSQlResult[0]['season']) # note this will always use the last season we got ... this will be a problem on double episodes that break the season barrier
                    if out_season: # if we found a episode in the cur_possible_season we dont need / want to look at the other possibilites
                        break
            else: # no possible seasons from the scene names lets look at this more generic
                for cur_ab_number in absolute_numbers:
                    namesSQlResult = myDB.select("SELECT season, episode, absolute_number, name FROM tv_episodes WHERE showid = ? and scene_absolute_number = ?", [show.tvdbid, cur_ab_number])
                    if len(namesSQlResult) > 1:
                        logger.log("Multiple scene absolute number. this might happend because we are missing a scene name for this season. xem lacking behind ?", logger.ERROR)
                        raise
                    elif len(namesSQlResult) == 0:
                        continue
                    # if we are here we found ONE episode for this season absolute number
                    logger.log("I found matching episode " + ek.ek(str, namesSQlResult[0]['name']), logger.DEBUG)
                    out_episodes.append(int(namesSQlResult[0]['episode']))
                    out_absolute_numbers.append(int(namesSQlResult[0]['absolute_number']))
                    out_season = int(namesSQlResult[0]['season']) # note this will always use the last season we got ... this will be a problem on double episodes that break the season barrier
            if not out_season: # we did not find anything in the loops ? damit there is no episode
                logger.log("No episode found for these scene numbers. xem lacking behind ?", logger.ERROR)
                raise
            # okay that was easy we found the correct season and episode numbers
            return (out_season, out_episodes, out_absolute_numbers)
        else:
            logger.log(u"" + show.name + " is a normal show i will scene convert the season and episodes " + str(season) + "x" + str(episodes), logger.DEBUG)
            out_absolute_numbers = None
            if possible_seasons:
                #check if we have a scene_absolute_number in the possible seasons
                for cur_possible_season in possible_seasons:
                    # and for all episode
                    for cur_episode in episodes:
                        namesSQlResult = myDB.select("SELECT season, episode, name FROM tv_episodes WHERE showid = ? and scene_season = ? and scene_episode = ?", [show.tvdbid, cur_possible_season, cur_episode])
                        if len(namesSQlResult) > 1:
                            logger.log("Multiple scene sxxexx numbers. this should not be check xem configuration", logger.ERROR)
                            raise
                        elif len(namesSQlResult) == 0:
                            break # break out of current absolute_numbers -> next season
                        # if we are here we found ONE episode for this season absolute number
                        logger.log("I found matching episode " + ek.ek(str, namesSQlResult[0]['name']), logger.DEBUG)
                        out_episodes.append(int(namesSQlResult[0]['episode']))
                        out_season = int(namesSQlResult[0]['season']) # note this will always use the last season we got ... this will be a problem on double episodes that break the season barrier
                    if out_season: # if we found a episode in the cur_possible_season we dont need / want to look at the other possibilites
                        break
            else: # no possible seasons from the scene names lets look at this more generic
                for cur_episode in episodes:
                    namesSQlResult = myDB.select("SELECT season, episode, name FROM tv_episodes WHERE showid = ? and scene_absolute_number = ?", [show.tvdbid, cur_episode])
                    if len(namesSQlResult) > 1:
                        logger.log("Multiple scene absolute number. this might happend because we are missing a scene name for this season. xem lacking behind ?", logger.ERROR)
                        raise
                    elif len(namesSQlResult) == 0:
                        continue
                    # if we are here we found ONE episode for this season absolute number
                    logger.log("I found matching episode " + ek.ek(str, namesSQlResult[0]['name']), logger.DEBUG)
                    out_episodes.append(int(namesSQlResult[0]['episode']))
                    out_season = int(namesSQlResult[0]['season']) # note this will always use the last season we got ... this will be a problem on double episodes that break the season barrier

            if not out_season: # we did not find anything in the loops ? damit there is no episode
                logger.log("No episode found for these scene numbers. assuming these are valid tvdb numbers", logger.DEBUG)
                out_season = season
                out_episodes = episodes
                out_absolute_numbers = absolute_numbers

            # okay that was easy we found the correct season and episode numbers
            return (out_season, out_episodes, out_absolute_numbers)

    def get_show_by_name(self, name, showList, useTvdb=False):
        logger.log(u"Trying to get the tvdbid for " + name, logger.DEBUG)

        name = helpers.full_sanitizeSceneName(name)

        cacheResult = sickbeard.name_cache.retrieveNameFromCache(name)
        if cacheResult:
            return helpers.findCertainShow(sickbeard.showList, cacheResult)

        if name in sickbeard.scene_exceptions.exception_tvdb:
            logger.log(u"Found " + name + " in the exception_tvdb", logger.DEBUG)
            return helpers.findCertainShow(showList, sickbeard.scene_exceptions.exception_tvdb[name])
        else:
            logger.log(u"NOT Found " + name + " in the exception_tvdb", logger.DEBUG)

        if useTvdb:
            try:
                t = tvdb_api.Tvdb(custom_ui=classes.ShowListUI, **sickbeard.TVDB_API_PARMS)
                showObj = t[name]
            except (tvdb_exceptions.tvdb_exception):
                # if none found, search on all languages
                try:
                    # There's gotta be a better way of doing this but we don't wanna
                    # change the language value elsewhere
                    ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

                    ltvdb_api_parms['search_all_languages'] = True
                    t = tvdb_api.Tvdb(custom_ui=classes.ShowListUI, **ltvdb_api_parms)
                    showObj = t[name]
                except (tvdb_exceptions.tvdb_exception, IOError):
                    pass

                return None
            except (IOError):
                return None
            else:
                show = helpers.findCertainShow(sickbeard.showList, int(showObj["id"]))
                if show:
                    return show

        return None


class CompleteResult(object):

    def __init__(self, show=None, season=None, episodes=[], absolute_numbers=[], quality=None, raw_parse_result=None, scene=False):
        self.show = show
        self.season = season
        self.episodes = episodes
        self.absolute_numbers = absolute_numbers
        self.quality = quality
        if self.quality == None:
            self.quality = common.Quality.UNKNOWN
        self.parse_result = raw_parse_result
        self.scene = scene # was a scene conversion done ?
        self._is_proper = False
        self.lock = threading.Lock()

    def _getTVDBID(self):
        if self.show:
            return self.show.tvdbid
        return 0

    def _isProper(self):
        return re.search('(^|[\. _-])(proper|repack)([\. _-]|$)', self.parse_result.extra_info, re.I) != None

    def _getReleaseGroup(self):
        return self.parse_result.release_group

    def _getSeriesName(self):
        return self.parse_result.series_name

    def __nonzero__(self):
        return bool(self.show and self.parse_result)

    tvdbid = property(_getTVDBID)
    is_proper = property(_isProper)
    release_group = property(_getReleaseGroup)
    series_name = property(_getSeriesName)
