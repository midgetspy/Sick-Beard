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
from sickbeard.name_parser.parser import NameParser, InvalidNameException, ParseResult
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
            self.complete_result.parse_result = ParseResult(name_to_parse)
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
            _tmp_adb_season, _tmp_adb_episode = self._convertADB(cur_show, self.complete_result.parse_result.air_date)
            if _tmp_adb_season != None and _tmp_adb_episode != None:
                self.complete_result.season = _tmp_adb_season
                self.complete_result.episodes = _tmp_adb_episode
            else:
                self._log("Could not convert ADB to season and episode numbers from " + self.name_to_parse, logger.WARNING)
        else:
            self._log("Assuming tvdb numbers", logger.DEBUG)
            self.complete_result.season = self.raw_parse_result.season_number
            self.complete_result.episodes = self.raw_parse_result.episode_numbers
        
        if not cur_show:
            self._log("No show couldn't be matched. assuming tvdb numbers", logger.DEBUG)
            # we will use the stuff from the parser
            self.complete_result.season = self.raw_parse_result.season_number
            self.complete_result.episodes = self.raw_parse_result.episode_numbers

        #self.complete_result.quality = common.Quality.nameQuality(self.name_to_parse, bool(cur_show and cur_show.is_anime))
        self.complete_result.quality = common.Quality.nameQuality(self.name_to_parse)
        return self.complete_result

    def _convertADB(self, show, adb_part):
        self._log("Getting season and episodes for ADB episode: " + str(adb_part), logger.DEBUG)
        if not show:
            return (None, None)

        myDB = db.DBConnection()
        sql_results = myDB.select("SELECT season, episode FROM tv_episodes WHERE showid = ? AND airdate = ?", [show.tvdbid, adb_part.toordinal()])
        if len(sql_results) == 1:
            return (int(sql_results[0]["season"]), [int(sql_results[0]["episode"])])

        if self.tvdbActiveLookUp:
            try:
                # There's gotta be a better way of doing this but we don't wanna
                # change the cache value elsewhere
                ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

                if show.lang:
                    ltvdb_api_parms['language'] = self.lang

                t = tvdb_api.Tvdb(**ltvdb_api_parms)

                epObj = t[show.tvdbid].airedOn(adb_part)[0]
                season = int(epObj["seasonnumber"])
                episodes = [int(epObj["episodenumber"])]
            except tvdb_exceptions.tvdb_episodenotfound:
                self._log(u"Unable to find episode with date " + str(episodes[0]) + " for show " + self.name_to_parse + ", skipping", logger.WARNING)
                return (None, None)
            except tvdb_exceptions.tvdb_error, e:
                self._log(u"Unable to contact TVDB: " + ex(e), logger.WARNING)
                return (None, None)
            else:
                return (season, episodes)
        else:
            self._log(u"Tried to look up the date for the episode " + self.name_to_parse + " but the database didn't give proper results, skipping it", logger.DEBUG)
            return(None, None)

    def parse_wrapper(self, show=None, toParse='', showList=[], tvdbActiveLookUp=False):
        """Returns a parse result or a InvalidNameException
           to get the tvdbid the tvdbapi might be used if tvdbActiveLookUp is True
        """
        # TODO: refactor ABD into its own mode ... if done remove simple check in parse()
        if len(showList) == 0:
            showList = sickbeard.showList
        try:
            myParser = NameParser()
            parse_result = myParser.parse(toParse)
        except InvalidNameException:
            raise InvalidNameException(u"Unable to parse: " + toParse)
        else:
            show = self.get_show_by_name(parse_result.series_name, showList, toParse, tvdbActiveLookUp)
        return (parse_result, show)

    def scene2tvdb(self, show, scene_name, season, episodes, absolute_numbers):
        # TODO: check if adb and make scene2tvdb useable with correct numbers
        out_season = None
        out_episodes = []
        out_absolute_numbers = []

        # is the scene name a special season ?
        # TODO: define if we get scene seasons or tvdb seasons ... for now they are mostly the same ... and i will use them as scene seasons
        #_possible_seasons = sickbeard.scene_exceptions.get_scene_exception_by_name(scene_name)
        # filter possible_seasons
        possible_seasons = []
        #for cur_scene_tvdb_id, cur_scene_season in _possible_seasons:
        #    if cur_scene_tvdb_id and str(cur_scene_tvdb_id) != str(show.tvdbid):
        #        self._log("dfuq when i tried to figure out the season from the name i got a different tvdbid then we got before !! stoping right now! before: " + str(show.tvdbid) + " now: " + str(cur_scene_tvdb_id), logger.ERROR)
        #        raise MultipleSceneShowResults("different tvdbid then we got before")
            # don't add season -1 since this is a generic name and not a real season... or if we get None
            # if this was the only result possible_seasons will stay empty and the next parts will look in the general matter
        #    if cur_scene_season == -1 or cur_scene_season == None:
        #        continue
        #    possible_seasons.append(cur_scene_season)
        #if not possible_seasons: # no special season name was used or we could not find it
        self._log("possible seasons for '" + scene_name + "' (" + str(show.tvdbid) + ") are " + str(possible_seasons), logger.DEBUG)

        # lets just get a db connection we will need it anyway
        myDB = db.DBConnection()
        # should we use absolute_numbers -> season, episodes -> normal show
        self._log(u"Trying to scene convert the season and episode (if needed) for '" + show.name + "' - " + str(season) + "x" + str(episodes), logger.DEBUG)
        out_absolute_numbers = None
        if possible_seasons:
            #check if we have a scene_absolute_number in the possible seasons
            for cur_possible_season in possible_seasons:
                # and for all episode
                for cur_episode in episodes:
                    namesSQlResult = myDB.select("SELECT season, episode, name FROM tv_episodes WHERE showid = ? and scene_season = ? and scene_episode = ?", [show.tvdbid, cur_possible_season, cur_episode])
                    if len(namesSQlResult) > 1:
                        self._log("(" + show.name + ") Multiple episodes for season episode number combination. this should not be check xem configuration", logger.ERROR)
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
                    self._log("(" + show.name + ") Multiple episodes for season episode number combination. this might happend because we are missing a scene name for this season. xem lacking behind ?", logger.ERROR)
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
            self.complete_result.scene = False # we don't consider this a scene fix

        # okay that was easy we found the correct season and episode numbers
        return (out_season, out_episodes, out_absolute_numbers)

    def get_show_by_name(self, name, showList, fileName, useTvdb=False):
        if not name:
            self._log(u"Not trying to get the tvdbid. No name given", logger.DEBUG)
            return None

        self._log(u"Trying to get the tvdbid for " + name, logger.DEBUG)

        name_orig = name
        name = helpers.sanitizeSceneName(name)
        
        cacheDB = db.DBConnection('cache.db')
        cacheDB.action("DELETE FROM scene_names WHERE tvdb_id = ?", [0])

        self._log(u"Checking the cache to see if we allready know the tvdb_id of " + name, logger.DEBUG)
        tvdb_id = sickbeard.name_cache.retrieveNameFromCache(name)
        if tvdb_id is None:
            from_cache = False
            self._log(u"No cache results returned, continuing on with the search", logger.DEBUG)
        else:
            logger.log(u"Cache lookup found "+repr(tvdb_id)+", using that", logger.DEBUG)
            from_cache = True
        
        #checking scene exception list
        if tvdb_id is None:
            if name in sickbeard.scene_exceptions.exception_tvdb:
                self._log(u"Found " + name + " in the exception list", logger.DEBUG)
                tvdb_id = sickbeard.scene_exceptions.exception_tvdb[name]
            else:
                self._log(u"Did NOT find " + name + " in the exception list", logger.DEBUG)
        
        # if the cache failed, try looking up the show name in the database
        if tvdb_id is None:
            logger.log(u"Trying to look up the show in the show database", logger.DEBUG)
            showResult = helpers.searchDBForShow(name_orig)
            if showResult:
                logger.log(name+" was found to be show "+showResult[1]+" ("+str(showResult[0])+") in our DB.", logger.DEBUG)
                tvdb_id = showResult[0]

        # if the DB lookup fails then do a comprehensive regex search
        if tvdb_id is None:
            logger.log(u"Couldn't figure out a show name straight from the DB, trying a regex search instead", logger.DEBUG)
            for curShow in sickbeard.showList:
                if sickbeard.show_name_helpers.isGoodResult(fileName, curShow):
                    logger.log(u"Successfully matched "+fileName+" to "+curShow.name+" with regex", logger.DEBUG)
                    tvdb_id = curShow.tvdbid
                    break
                
        if tvdb_id is None and useTvdb:
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
                tvdb_id = int(showObj["id"])
                #if show:
                #    return show
        
        # if tvdb_id was anything but None (0 or a number) then
        if not from_cache:
            if tvdb_id > 0:
                sickbeard.name_cache.addNameToCache(name, tvdb_id)
            
        # if we came out with tvdb_id = None it means we couldn't figure it out at all, just use 0 for that
        if tvdb_id is None:
            tvdb_id = 0
        
        if tvdb_id:
            showObj = helpers.findCertainShow(sickbeard.showList, tvdb_id)
            if showObj:
                return showObj
            
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