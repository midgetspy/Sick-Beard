# -*- coding: utf8 -*-
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

import traceback
import threading
import re
from types import FunctionType, MethodType

import sickbeard
from sickbeard.exceptions import MultipleShowObjectsException, EpisodeNotFoundByAbsoluteNumerException, ex
from sickbeard import logger, classes, exceptions, helpers
from sickbeard.name_parser.parser import NameParser, InvalidNameException
from sickbeard import common

from sickbeard import db
from sickbeard import encodingKludge as ek

from lib.tvdb_api import tvdb_api, tvdb_exceptions


class CompleteParser(object):

    def __init__(self, show=None, showList=None, tvdbActiveLookUp=False, log=None):
        # first init log
        if type(log) in (FunctionType, MethodType):# if we get a function or a method use that.
            self._log = log

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
        self._parse_mode = None

    def _log(self, toLog, logLevel=logger.MESSAGE):
        logger.log(toLog, logLevel)

    def parse(self, name_to_parse):
        # a wrapper to definitely unlock the complete_result ... but still re raise any errors
        self.complete_result.lock.acquire()
        try:
            result = self._parse(name_to_parse)
        except Exception, e:
            self.complete_result.lock.release()
            self._log(u"Error during parsing. Error will raise again. traceback:", logger.ERROR)
            self._log(traceback.format_exc(), logger.ERROR)
            raise e
        else:
            self.complete_result.lock.release()
            return result

    def _parse(self, name_to_parse):
        self.name_to_parse = name_to_parse
        try:
            self._log(u"Parser for '" + ek.ek(str, self.name_to_parse) + "' locked. Starting to parse now", logger.DEBUG)
        except (UnicodeEncodeError, UnicodeDecodeError), e:
            self._log("Could not encode name i was going to parse. This might lead to later issues when we need to access the file system. error message: " + ex(e), logger.WARNING)
            self._log("Current encoding used by sickbeard is '" + str(sickbeard.SYS_ENCODING) + "'", logger.WARNING)
            self._log(traceback.format_exc(), logger.DEBUG)
            self._log(u"Parser for '" + self.name_to_parse + "' locked. Starting to parse now", logger.DEBUG)

        # lets parse the name
        try:
            self.raw_parse_result, cur_show = self.parse_wrapper(self.show, self.name_to_parse, self.showList, self.tvdbActiveLookUp)
        except InvalidNameException:
            self._log(u"Could not parse: " + self.name_to_parse, logger.DEBUG)
            return self.complete_result

        try:
            self._log(u"Parsed :" + self.name_to_parse + " into: " + unicode(self.raw_parse_result), logger.DEBUG)
        except (UnicodeEncodeError, UnicodeDecodeError), e:
            self._log("Could not encode parse result. This might lead to later issues. error message: " + ex(e), logger.WARNING)
            self._log(u"Parsing done for " + self.name_to_parse, logger.DEBUG)

        # setup values of the
        self.complete_result.parse_result = self.raw_parse_result
        if self.show and cur_show:
            if self.show.tvdbid != cur_show.tvdbid:
                self._log(u"I expected an episode of the show " + self.show.name + " but the parser thinks its the show " + cur_show.name + ". I will continue thinking its " + self.show.name, logger.WARNING)
                cur_show = self.show
        self.complete_result.show = cur_show

        # TODO: move this into the parse_wrapper()
        # check if we parsed an air by date show as air by date
        if cur_show and cur_show.air_by_date and not self.raw_parse_result.air_by_date:
            return self.complete_result

        # TODO: find a place for "if there's no season then we can hopefully just use 1 automatically"
        # fixing scene numbers now !
        # removed "and self.raw_parse_result.release_group" check ... less save but maybe save enough
        if cur_show and not cur_show.air_by_date:
            # this does also take care of absolute number to sxxexx conversion
            self._log("This looks like a scene release converting numbers", logger.DEBUG)
            self.complete_result.season, self.complete_result.episodes, self.complete_result.ab_episode_numbers = \
                self.scene2tvdb(cur_show, self.raw_parse_result.series_name, self.raw_parse_result.season_number, self.raw_parse_result.episode_numbers, self.raw_parse_result.ab_episode_numbers)
        elif cur_show and cur_show.air_by_date:
            _tmp_adb_season, _tmp_adb_episode = self._convertADB(self.parse_result.air_date)
            if _tmp_adb_season != None and _tmp_adb_episode != None:
                self.complete_result.season = _tmp_adb_season
                self.complete_result.episodes = _tmp_adb_episode
            else:
                pass
        else:
            self._log("Assuming tvdb numbers", logger.DEBUG)
            self.complete_result.season = self.raw_parse_result.season_number
            self.complete_result.episodes = self.raw_parse_result.episode_numbers

        if cur_show and cur_show.is_anime and not self.complete_result.scene: # only need to to do another conversion if the scene2tvdb didn work
            _ab_conversion = False
            if self.raw_parse_result.is_anime:
                self._log("Getting season and episodes from absolute numbers", logger.DEBUG)
                try:
                    _actual_season, _actual_episodes = helpers.get_all_episodes_from_absolute_number(cur_show, None, self.raw_parse_result.ab_episode_numbers)
                except exceptions.EpisodeNotFoundByAbsoluteNumerException:
                    self._log(str(cur_show.tvdbid) + ": TVDB object absolute number " + str(self.raw_parse_result.ab_episode_numbers) + " is incomplete, cant determin season and episode numbers")
                else:
                    self.complete_result.season = _actual_season
                    self.complete_result.episodes = _actual_episodes
                    _ab_conversion = True

            if not _ab_conversion and self.raw_parse_result.sxxexx:
                self._log("Absolute number conversion failed. but we have season and episode numbers. There will be no scene conversion for this!", logger.DEBUG)
                # this show is an anime but scene conversion did not work and we dont have any absolute numbers but we do have sxxexx numbers
                self.complete_result.season = self.raw_parse_result.season_number
                self.complete_result.episodes = self.raw_parse_result.episode_numbers

        if not cur_show:
            self._log("No show couldn't be matched. assuming tvdb numbers", logger.DEBUG)
            # we will use the stuff from the parser
            self.complete_result.season = self.raw_parse_result.season_number
            self.complete_result.episodes = self.raw_parse_result.episode_numbers

        self.complete_result.quality = common.Quality.nameQuality(self.name_to_parse, bool(cur_show and cur_show.is_anime))
        return self.complete_result

    def _convertADB(self, adb_part):
        self._log("Getting season and episodes for ADB episode: " + str(adb_part), logger.DEBUG)
        if not self.show:
            return (None, None)

        myDB = db.DBConnection()
        sql_results = myDB.select("SELECT season, episode FROM tv_episodes WHERE showid = ? AND airdate = ?", [self.show.tvdbid, adb_part.toordinal()])
        if len(sql_results) == 1:
            return (int(sql_results[0]["season"]), [int(sql_results[0]["episode"])])

        self._log(u"Tried to look up the date for the episode " + self.name_to_parse + " but the database didn't give proper results, skipping it", logger.WARNING)
        if self.tvdbActiveLookUp:
            try:
                # There's gotta be a better way of doing this but we don't wanna
                # change the cache value elsewhere
                ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

                if self.lang:
                    ltvdb_api_parms['language'] = self.lang

                t = tvdb_api.Tvdb(**ltvdb_api_parms)

                epObj = t[self.show.tvdbid].airedOn(adb_part)[0]
                season = int(epObj["seasonnumber"])
                episodes = [int(epObj["episodenumber"])]
            except tvdb_exceptions.tvdb_episodenotfound:
                self._log(u"Unable to find episode with date " + str(episodes[0]) + " for show " + self.name + ", skipping", logger.WARNING)
                return (None, None)
            except tvdb_exceptions.tvdb_error, e:
                self._log(u"Unable to contact TVDB: " + ex(e), logger.WARNING)
                return (None, None)
            else:
                return (season, episodes)
        else:
            return(None, None)

    def parse_wrapper(self, show=None, toParse='', showList=[], tvdbActiveLookUp=False):
        """Retruns a parse result or a InvalidNameException
            it will try to take the correct regex for the show if given
            if not given it will try Anime first then Normal
            if name is parsed as anime it will lookup the tvdbid and check if we have it as an anime
            only if both is true we will consider it an anime
            to get the tvdbid the tvdbapi might be used if tvdbActiveLookUp is True
        """
        # TODO: refactor ABD into its own mode ... if done remove simple check in parse()
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
                self._log(u"Could not parse '" + toParse + "' in regex mode: " + str(0), logger.DEBUG)
            else:
                show = self.get_show_by_name(parse_result.series_name, showList, tvdbActiveLookUp)
                if show and show.is_anime:
                    if mode == NameParser.ANIME_REGEX or mode == NameParser.NORMAL_REGEX:
                        break
                else:
                    if mode == NameParser.NORMAL_REGEX:
                        break
        else:
            raise InvalidNameException(u"Unable to parse " + toParse)

        self._parse_mode = mode
        return (parse_result, show)

    def scene2tvdb(self, show, scene_name, season, episodes, absolute_numbers):
        # TODO: check if adb and make scene2tvdb useable with correct numbers
        out_season = None
        out_episodes = []
        out_absolute_numbers = []

        # is the scene name a special season ?
        # TODO: define if we get scene seasons or tvdb seasons ... for now they are mostly the same ... and i will use them as scene seasons
        _possible_seasons = sickbeard.scene_exceptions.get_scene_exception_by_name_multiple(scene_name)
        # filter possible_seasons
        possible_seasons = []
        for cur_scene_tvdb_id, cur_scene_season in _possible_seasons:
            if cur_scene_tvdb_id and cur_scene_tvdb_id != show.tvdbid:
                self._log("dfuq when i tried to figure out the season from the name i got a different tvdbid then we got before !! stoping right now! before: " + str(show.tvdbid) + " now:" + str(cur_scene_tvdb_id), logger.ERROR)
                raise MultipleSceneShowResults("different tvdbid then we got before")
            # don't add season -1 since this is a generic name and not a real season... or if we get None
            # if this was the only result possible_seasons will stay empty and the next parts will look in the general matter
            if cur_scene_season == -1 or cur_scene_season == None:
                continue
            possible_seasons.append(cur_scene_season)
        #if not possible_seasons: # no special season name was used or we could not find it
        self._log("possible seasons for '" + scene_name + "' (" + str(show.tvdbid) + ") are " + str(possible_seasons), logger.DEBUG)

        # lets just get a db connection we will need it anyway
        myDB = db.DBConnection()
        # should we use absolute_numbers -> anime or season, episodes -> normal show
        if show.is_anime:
            self._log(u"'" + show.name + "' is an anime i will scene convert the absolute numbers " + str(absolute_numbers), logger.DEBUG)
            if possible_seasons:
                #check if we have a scene_absolute_number in the possible seasons
                for cur_possible_season in possible_seasons:
                    # and for all absolute numbers
                    for cur_ab_number in absolute_numbers:
                        namesSQlResult = myDB.select("SELECT season, episode, absolute_number, name FROM tv_episodes WHERE showid = ? and scene_season = ? and scene_absolute_number = ?", [show.tvdbid, cur_possible_season, cur_ab_number])
                        if len(namesSQlResult) > 1:
                            self._log("Multiple episodes for a absolute number and season. this should not be check xem configuration", logger.ERROR)
                            self.complete_result.scene = False
                            raise MultipleSceneEpisodeResults("Multiple episodes for a absolute number and season")
                        elif len(namesSQlResult) == 0:
                            break # break out of current absolute_numbers -> next season ... this is not a good sign
                        # if we are here we found ONE episode for this season absolute number
                        self._log(u"I found matching episode: " + namesSQlResult[0]['name'], logger.DEBUG)
                        out_episodes.append(int(namesSQlResult[0]['episode']))
                        out_absolute_numbers.append(int(namesSQlResult[0]['absolute_number']))
                        out_season = int(namesSQlResult[0]['season']) # note this will always use the last season we got ... this will be a problem on double episodes that break the season barrier
                    if out_season: # if we found a episode in the cur_possible_season we dont need / want to look at the other season possibilities
                        self.complete_result.scene = True
                        break
            else: # no possible seasons from the scene names lets look at this more generic
                for cur_ab_number in absolute_numbers:
                    namesSQlResult = myDB.select("SELECT season, episode, absolute_number, name FROM tv_episodes WHERE showid = ? and scene_absolute_number = ?", [show.tvdbid, cur_ab_number])
                    if len(namesSQlResult) > 1:
                        self._log("Multiple episodes for a absolute number. this might happend because we are missing a scene name for this season. xem lacking behind ?", logger.ERROR)
                        self.complete_result.scene = False
                        raise MultipleSceneEpisodeResults("Multiple episodes for a absolute number")
                    elif len(namesSQlResult) == 0:
                        continue
                    # if we are here we found ONE episode for this season absolute number
                    self._log(u"I found matching episode: " + namesSQlResult[0]['name'], logger.DEBUG)
                    out_episodes.append(int(namesSQlResult[0]['episode']))
                    out_absolute_numbers.append(int(namesSQlResult[0]['absolute_number']))
                    out_season = int(namesSQlResult[0]['season']) # note this will always use the last season we got ... this will be a problem on double episodes that break the season barrier
                    self.complete_result.scene = True
            if not out_season: # we did not find anything in the loops ? damit there is no episode
                self._log("No episode found for these scene numbers. asuming tvdb numbers", logger.DEBUG)
                # we still have to convert the absolute number to sxxexx ... but that is done not here
                self.complete_result.scene = False # should be false
        else:
            self._log(u"'" + show.name + "' is a normal show i will scene convert the season and episodes " + str(season) + "x" + str(episodes), logger.DEBUG)
            out_absolute_numbers = None
            if possible_seasons:
                #check if we have a scene_absolute_number in the possible seasons
                for cur_possible_season in possible_seasons:
                    # and for all episode
                    for cur_episode in episodes:
                        namesSQlResult = myDB.select("SELECT season, episode, name FROM tv_episodes WHERE showid = ? and scene_season = ? and scene_episode = ?", [show.tvdbid, cur_possible_season, cur_episode])
                        if len(namesSQlResult) > 1:
                            self._log("Multiple episodes for season episode number combination. this should not be check xem configuration", logger.ERROR)
                            raise MultipleSceneEpisodeResults("Multiple episodes for season episode number combination")
                        elif len(namesSQlResult) == 0:
                            break # break out of current episode -> next season ... this is not a good sign
                        # if we are here we found ONE episode for this season absolute number
                        self._log(u"I found matching episode: " + namesSQlResult[0]['name'], logger.DEBUG)
                        out_episodes.append(int(namesSQlResult[0]['episode']))
                        out_season = int(namesSQlResult[0]['season']) # note this will always use the last season we got ... this will be a problem on double episodes that break the season barrier
                    if out_season: # if we found a episode in the cur_possible_season we dont need / want to look at the other posibilites
                        self.complete_result.scene = False
                        break
            else: # no possible seasons from the scene names lets look at this more generic
                for cur_episode in episodes:
                    namesSQlResult = myDB.select("SELECT season, episode, name FROM tv_episodes WHERE showid = ? and scene_episode = ? and scene_season = ?", [show.tvdbid, cur_episode, season])
                    if len(namesSQlResult) > 1:
                        self._log("Multiple episodes for season episode number combination. this might happend because we are missing a scene name for this season. xem lacking behind ?", logger.ERROR)
                        raise MultipleSceneEpisodeResults("Multiple episodes for season episode number combination")
                    elif len(namesSQlResult) == 0:
                        continue
                    # if we are here we found ONE episode for this season absolute number
                    self._log(u"I found matching episode: " + namesSQlResult[0]['name'], logger.DEBUG)
                    out_episodes.append(int(namesSQlResult[0]['episode']))
                    out_season = int(namesSQlResult[0]['season']) # note this will always use the last season we got ... this will be a problem on double episodes that break the season barrier
                    self.complete_result.scene = True
            # this is only done for normal shows
            if not out_season: # we did not find anything in the loops ? darn there is no episode
                self._log("No episode found for these scene numbers. assuming these are valid tvdb numbers", logger.DEBUG)
                out_season = season
                out_episodes = episodes
                out_absolute_numbers = absolute_numbers
                self.complete_result.scene = False # we still don't consider this a scene fix

        # okay that was easy we found the correct season and episode numbers
        return (out_season, out_episodes, out_absolute_numbers)

    def get_show_by_name(self, name, showList, useTvdb=False):
        if not name:
            self._log(u"Not trying to get the tvdbid. No name given", logger.DEBUG)
            return None

        self._log(u"Trying to get the tvdbid for " + name, logger.DEBUG)

        name = helpers.full_sanitizeSceneName(name)

        cacheResult = sickbeard.name_cache.retrieveNameFromCache(name)
        if cacheResult:
            return helpers.findCertainShow(sickbeard.showList, cacheResult)

        if name in sickbeard.scene_exceptions.exception_tvdb:
            self._log(u"Found " + name + " in the exception list", logger.DEBUG)
            return helpers.findCertainShow(showList, sickbeard.scene_exceptions.exception_tvdb[name])
        else:
            self._log(u"Did NOT find " + name + " in the exception list", logger.DEBUG)

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

    def __init__(self, show=None, season=None, episodes=[], absolute_numbers=[], quality=common.Quality.UNKNOWN, raw_parse_result=None, scene=False):
        self.show = show
        self.season = season
        self.episodes = episodes
        self.absolute_numbers = absolute_numbers
        self.quality = quality
        self.parse_result = raw_parse_result
        self.scene = scene # was a scene conversion done ?
        self._is_proper = False
        self.lock = threading.Lock()

    def _getTVDBID(self):
        if self.show:
            return self.show.tvdbid
        return 0

    def _isProper(self):
        return bool(self.parse_result and self.parse_result.extra_info and re.search('(^|[\. _-])(proper|repack)([\. _-]|$)', self.parse_result.extra_info, re.I) != None)

    def _getReleaseGroup(self):
        return self.parse_result.release_group

    def _getSeriesName(self):
        return self.parse_result.series_name

    def _sxxexx(self):
        return bool(self.season != None and self.episodes)

    def __nonzero__(self):
        return bool(self.show and self.parse_result and self.season != None and self.episodes)

    tvdbid = property(_getTVDBID)
    is_proper = property(_isProper)
    release_group = property(_getReleaseGroup)
    series_name = property(_getSeriesName)
    sxxexx = property(_sxxexx)


class MultipleSceneShowResults(Exception):
    pass


class MultipleSceneEpisodeResults(Exception):
    pass
