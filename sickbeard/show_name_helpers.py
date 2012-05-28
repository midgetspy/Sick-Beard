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

from sickbeard.common import countryList
from sickbeard.helpers import sanitizeSceneName
from sickbeard.scene_exceptions import get_scene_exceptions
from sickbeard import logger
from sickbeard import db
from sickbeard.blackandwhitelist import *

from sickbeard.completparser import CompleteParser

import re
import datetime
import common

from name_parser.parser import NameParser, InvalidNameException

resultFilters = ["sub(pack|s|bed)", "nlsub(bed|s)?", "swesub(bed)?",
                 "(dir|sample|nfo)fix", "sample", "(dvd)?extras", 
                 "dub(bed)?"]

def filterBadReleases(name):
    """
    Filters out non-english and just all-around stupid releases by comparing them
    to the resultFilters contents.
    
    name: the release name to check
    
    Returns: True if the release name is OK, False if it's bad.
    """
    """
    try:
        parse_result = parse_result_wrapper(None,name)
    except InvalidNameException:
        logger.log(u"Unable to parse the filename "+name+" into a valid episode", logger.WARNING)
        return False
    """
    cp = CompleteParser()
    cpr = cp.parse(name)
    parse_result = cpr.parse_result
    
    # use the extra info and the scene group to filter against
    check_string = ''
    if parse_result.extra_info:
        check_string = parse_result.extra_info
    if parse_result.release_group:
        if check_string:
            check_string = check_string + '-' + parse_result.release_group
        else:
            check_string = parse_result.release_group 

    # if there's no info after the season info then assume it's fine
    if not check_string:
        return True

    # if any of the bad strings are in the name then say no
    for x in resultFilters + sickbeard.IGNORE_WORDS.split(','):
        if re.search('(^|[\W_])'+x+'($|[\W_])', check_string, re.I):
            logger.log(u"Invalid scene release: "+name+" contains "+x+", ignoring it", logger.DEBUG)
            return False

    return True

def sceneToNormalShowNames(name):
    """
    Takes a show name from a scene dirname and converts it to a more "human-readable" format.
    
    name: The show name to convert
    
    Returns: a list of all the possible "normal" names
    """

    if not name:
        return []

    name_list = [name]
    
    # use both and and &
    new_name = re.sub('(?i)([\. ])and([\. ])', '\\1&\\2', name, re.I)
    if new_name not in name_list:
        name_list.append(new_name)

    results = []

    for cur_name in name_list:
        # add brackets around the year
        results.append(re.sub('(\D)(\d{4})$', '\\1(\\2)', cur_name))
    
        # add brackets around the country
        country_match_str = '|'.join(common.countryList.values())
        results.append(re.sub('(?i)([. _-])('+country_match_str+')$', '\\1(\\2)', cur_name))

    results += name_list

    return list(set(results))

def makeSceneShowSearchStrings(show, season=-1):

    showNames = allPossibleShowNames(show, season=season)

    # scenify the names
    return map(sanitizeSceneName, showNames)


def makeSceneSeasonSearchString (show, segment, extraSearchType=None, scene=False):

    myDB = db.DBConnection()

    if show.air_by_date:
        numseasons = 0
        
        # the search string for air by date shows is just 
        seasonStrings = [segment]
    elif show.is_anime:
        """this part is from darkcube"""
        numseasons = 0
        if not scene:
            episodeNumbersSQLResult = myDB.select("SELECT absolute_number, status FROM tv_episodes WHERE showid = ? and season = ?", [show.tvdbid, segment])
        else:
            episodeNumbersSQLResult = myDB.select("SELECT scene_absolute_number, status FROM tv_episodes WHERE showid = ? and scene_season = ?", [show.tvdbid, segment])
        
        # get show qualities
        anyQualities, bestQualities = common.Quality.splitQuality(show.quality)
        
        # compile a list of all the episode numbers we need in this 'season'
        seasonStrings = []
        for episodeNumberResult in episodeNumbersSQLResult:
            
            # get quality of the episode
            curCompositeStatus = int(episodeNumberResult["status"])
            curStatus, curQuality = common.Quality.splitCompositeStatus(curCompositeStatus)
            
            if bestQualities:
                highestBestQuality = max(bestQualities)
            else:
                highestBestQuality = 0
        
            # if we need a better one then add it to the list of episodes to fetch
            if (curStatus in (common.DOWNLOADED, common.SNATCHED) and curQuality < highestBestQuality) or curStatus == common.WANTED:
                if not scene:
                    if isinstance(episodeNumberResult["absolute_number"], int):
                        ab_number = int(episodeNumberResult["absolute_number"])
                else:
                    if isinstance(episodeNumberResult["scene_absolute_number"], int):
                        ab_number = int(episodeNumberResult["scene_absolute_number"])
                if ab_number > 0:
                    seasonStrings.append("%d" % ab_number)

    else:
        numseasonsSQlResult = myDB.select("SELECT COUNT(DISTINCT season) as numseasons FROM tv_episodes WHERE showid = ? and season != 0", [show.tvdbid])
        numseasons = int(numseasonsSQlResult[0][0])

        seasonStrings = ["S%02d" % segment]
        # since nzbmatrix allows more than one search per request we search SxEE results too
        if extraSearchType == "nzbmatrix":
            seasonStrings.append("%ix" % segment)

    bwl = BlackAndWhiteList(show.tvdbid)
    showNames = set(makeSceneShowSearchStrings(show, segment))

    toReturn = []
    term_list = []

    # search each show name
    for curShow in showNames:
        # most providers all work the same way
        if not extraSearchType:
            # if there's only one season then we can just use the show name straight up
            if numseasons == 1:
                toReturn.append(curShow)
            # for providers that don't allow multiple searches in one request we only search for Sxx style stuff
            else:
                for cur_season in seasonStrings:
                    if len(bwl.whiteList) > 0:
                        for keyword in bwl.whiteList:
                            toReturn.append(keyword + '.' + curShow+ "." + cur_season)
                    else:
                        toReturn.append(curShow + "." + cur_season)
        
        # nzbmatrix is special, we build a search string just for them
        elif extraSearchType == "nzbmatrix":
            if numseasons == 1:
                toReturn.append('"'+curShow+'"')
            elif numseasons == 0:
                if show.is_anime:
                    term_list = ['(+"'+curShow+'"+"'+x+'")' for x in seasonStrings]
                    toReturn.append('.'.join(term_list))
                else:
                    toReturn.append('"'+curShow+' '+str(segment).replace('-',' ')+'"')
            else:
                term_list = [x+'*' for x in seasonStrings]
                if show.air_by_date:
                    term_list = ['"'+x+'"' for x in term_list]

                toReturn.append('+"'+curShow+'" +('+','.join(term_list)+')')
    
    if extraSearchType == "nzbmatrix":     
        toReturn = ['+('+','.join(toReturn)+')']
        if term_list:
            toReturn.append('+('+','.join(term_list)+')')
    return toReturn


def makeSceneSearchString (episode):

    myDB = db.DBConnection()
    numseasonsSQlResult = myDB.select("SELECT COUNT(DISTINCT season) as numseasons FROM tv_episodes WHERE showid = ? and season != 0", [episode.show.tvdbid])
    numseasons = int(numseasonsSQlResult[0][0])
    
    # see if we should use dates instead of episodes
    if episode.show.air_by_date and episode.airdate != datetime.date.fromordinal(1):
        epStrings = [str(episode.airdate)]
    elif episode.show.is_anime:
        epStrings = ["%i" % int(episode.scene_absolute_number)]
    else:
        epStrings = ["S%02iE%02i" % (int(episode.scene_season), int(episode.scene_episode)),
                    "%ix%02i" % (int(episode.scene_season), int(episode.scene_episode))]

    # for single-season shows just search for the show name
    if numseasons == 1 and not episode.show.is_anime:
        epStrings = ['']

    bwl = BlackAndWhiteList(episode.show.tvdbid)
    showNames = set(makeSceneShowSearchStrings(episode.show, episode.scene_season))

    toReturn = []
    for curShow in showNames:
        for curEpString in epStrings:
            if len(bwl.whiteList) > 0:
                for keyword in bwl.whiteList:
                    toReturn.append(keyword + '.' + curShow + '.' + curEpString)
            else:
                toReturn.append(curShow + '.' + curEpString)

    return toReturn

def isGoodResult(name, show, log=True, season=-1):
    """
    Use an automatically-created regex to make sure the result actually is the show it claims to be
    """

    all_show_names = allPossibleShowNames(show, season=season)
    showNames = map(sanitizeSceneName, all_show_names) + all_show_names

    for curName in set(showNames):
        if not show.is_anime:
            escaped_name = re.sub('\\\\[\\s.-]', '\W+', re.escape(curName))
            if show.startyear:
                escaped_name += "(?:\W+"+str(show.startyear)+")?"
            curRegex = '^' + escaped_name + '\W+(?:(?:S\d[\dE._ -])|(?:\d\d?x)|(?:\d{4}\W\d\d\W\d\d)|(?:(?:part|pt)[\._ -]?(\d|[ivx]))|Season\W+\d+\W+|E\d+\W+)'
        else:
            escaped_name = re.sub('\\\\[\\s.-]', '[\W_]+', re.escape(curName))
            # FIXME: find a "automatically-created" regex for anime releases # test at http://regexr.com?2uon3
            curRegex = '^((\[.*?\])|(\d+[\.-]))*[ _\.]*' + escaped_name + '(([ ._-]+\d+)|([ ._-]+s\d{2})).*'

        if log:
            logger.log(u"Checking if show "+name+" matches " + curRegex, logger.DEBUG)

        match = re.search(curRegex, name, re.I)

        if match:
            logger.log(u"Matched "+curRegex+" to "+name, logger.DEBUG)
            return True

    if log:
        logger.log(u"Provider gave result " + name + " but that doesn't seem like a valid result for " + show.name + " " + str(season) + "so I'm ignoring it")
    return False

def allPossibleShowNames(show, season=-1):
    """
    Figures out every possible variation of the name for a particular show. Includes TVDB name, TVRage name,
    country codes on the end, eg. "Show Name (AU)", and any scene exception names.
    
    show: a TVShow object that we should get the names of
    
    Returns: a list of all the possible show names
    """

    showNames = get_scene_exceptions(show.tvdbid, season=season)
    if not showNames: # if we dont have any season specific exceptions fallback to generic exceptions
        season = -1
        showNames = get_scene_exceptions(show.tvdbid, season=season)

    if season in [-1, 1]:
        showNames.append(show.name)
    # if we have a tvrage name then use it
    if show.tvrname != "" and show.tvrname != None and season in [-1, 1]:
        showNames.append(show.tvrname)

    newShowNames = []

    country_list = countryList
    country_list.update(dict(zip(countryList.values(), countryList.keys())))

    # if we have "Show Name Australia" or "Show Name (Australia)" this will add "Show Name (AU)" for
    # any countries defined in common.countryList
    # (and vice versa)
    # only for none anime
    if not show.is_anime:
        for curName in set(showNames):
            if not curName:
                continue
            for curCountry in country_list:
                if curName.endswith(' '+curCountry):
                    newShowNames.append(curName.replace(' '+curCountry, ' ('+country_list[curCountry]+')'))
                elif curName.endswith(' ('+curCountry+')'):
                    newShowNames.append(curName.replace(' ('+curCountry+')', ' ('+country_list[curCountry]+')'))
        showNames += newShowNames

    return showNames

