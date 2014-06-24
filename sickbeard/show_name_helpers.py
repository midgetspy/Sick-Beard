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

import re
import datetime

from name_parser.parser import NameParser, InvalidNameException

resultFilters = ["sub(bed|ed|pack|s)", "(dk|fin|heb|kor|nl|nor|nordic|pl|swe)sub(bed|ed|s)?",
                 "(dir|sample|sub|nfo|proof)fix(es)?", "sample", "(dvd)?extras",
                 "dub(bed)?"]


def filterBadReleases(name):
    """
    Filters out non-english and just all-around stupid releases by comparing them
    to the resultFilters contents.

    name: the release name to check

    Returns: True if the release name is OK, False if it's bad.
    """

    try:
        fp = NameParser()
        parse_result = fp.parse(name)
    except InvalidNameException:
        logger.log(u"Unable to parse the filename " + name + " into a valid episode", logger.WARNING)
        return False

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
    for ignore_word in resultFilters + sickbeard.IGNORE_WORDS.split(','):
        ignore_word = ignore_word.strip()
        if ignore_word:
            if re.search('(^|[\W_])' + ignore_word + '($|[\W_])', check_string, re.I):
                logger.log(u"Invalid scene release: " + name + " contains " + ignore_word + ", ignoring it", logger.DEBUG)
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
        country_match_str = '|'.join(countryList.values())
        results.append(re.sub('(?i)([. _-])(' + country_match_str + ')$', '\\1(\\2)', cur_name))

    results += name_list

    return list(set(results))


def makeSceneShowSearchStrings(show):

    showNames = allPossibleShowNames(show)

    # scenify the names
    return map(sanitizeSceneName, showNames)


def makeSceneSeasonSearchString(show, segment, extraSearchType=None):

    myDB = db.DBConnection()

    if show.air_by_date:
        numseasons = 0

        # the search string for air by date shows is just
        seasonStrings = [segment]

    else:
        numseasonsSQlResult = myDB.select("SELECT COUNT(DISTINCT season) as numseasons FROM tv_episodes WHERE showid = ? and season != 0", [show.tvdbid])
        numseasons = int(numseasonsSQlResult[0][0])

        seasonStrings = ["S%02d" % segment]

    showNames = set(makeSceneShowSearchStrings(show))

    toReturn = []

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
                    toReturn.append(curShow + "." + cur_season)

    return toReturn


def makeSceneSearchString(episode):

    myDB = db.DBConnection()
    numseasonsSQlResult = myDB.select("SELECT COUNT(DISTINCT season) as numseasons FROM tv_episodes WHERE showid = ? and season != 0", [episode.show.tvdbid])
    numseasons = int(numseasonsSQlResult[0][0])
    numepisodesSQlResult = myDB.select("SELECT COUNT(episode) as numepisodes FROM tv_episodes WHERE showid = ? and season != 0", [episode.show.tvdbid])
    numepisodes = int(numepisodesSQlResult[0][0])

    # see if we should use dates instead of episodes
    if episode.show.air_by_date and episode.airdate != datetime.date.fromordinal(1):
        epStrings = [str(episode.airdate)]
    else:
        epStrings = ["S%02iE%02i" % (int(episode.season), int(episode.episode)),
                    "%ix%02i" % (int(episode.season), int(episode.episode))]

    # for single-season shows just search for the show name -- if total ep count (exclude s0) is less than 11
    # due to the amount of qualities and releases, it is easy to go over the 50 result limit on rss feeds otherwise
    if numseasons == 1 and numepisodes < 11:
        epStrings = ['']

    showNames = set(makeSceneShowSearchStrings(episode.show))

    toReturn = []

    for curShow in showNames:
        for curEpString in epStrings:
            toReturn.append(curShow + '.' + curEpString)

    return toReturn


def isGoodResult(name, show, log=True):
    """
    Use an automatically-created regex to make sure the result actually is the show it claims to be
    """

    all_show_names = allPossibleShowNames(show)
    showNames = map(sanitizeSceneName, all_show_names) + all_show_names

    for curName in set(showNames):
        escaped_name = re.sub('\\\\[\\s.-]', '\W+', re.escape(curName))
        if show.startyear:
            escaped_name += "(?:\W+" + str(show.startyear) + ")?"
        curRegex = '^' + escaped_name + '\W+(?:(?:S\d[\dE._ -])|(?:\d\d?x)|(?:\d{4}\W\d\d\W\d\d)|(?:(?:part|pt)[\._ -]?(\d|[ivx]))|Season\W+\d+\W+|E\d+\W+)'
        if log:
            logger.log(u"Checking if show " + name + " matches " + curRegex, logger.DEBUG)

        match = re.search(curRegex, name, re.I)

        if match:
            logger.log(u"Matched " + curRegex + " to " + name, logger.DEBUG)
            return True

    if log:
        logger.log(u"Provider gave result " + name + " but that doesn't seem like a valid result for " + show.name + " so I'm ignoring it")
    return False


def allPossibleShowNames(show):
    """
    Figures out every possible variation of the name for a particular show. Includes TVDB name, TVRage name,
    country codes on the end, eg. "Show Name (AU)", and any scene exception names.

    show: a TVShow object that we should get the names of

    Returns: a list of all the possible show names
    """

    showNames = [show.name]
    showNames += [name for name in get_scene_exceptions(show.tvdbid)]

    # if we have a tvrage name then use it
    if show.tvrname != "" and show.tvrname != None:
        showNames.append(show.tvrname)

    newShowNames = []

    country_list = countryList
    country_list.update(dict(zip(countryList.values(), countryList.keys())))

    # if we have "Show Name Australia" or "Show Name (Australia)" this will add "Show Name (AU)" for
    # any countries defined in common.countryList
    # (and vice versa)
    for curName in set(showNames):
        if not curName:
            continue
        for curCountry in country_list:
            if curName.endswith(' ' + curCountry):
                newShowNames.append(curName.replace(' ' + curCountry, ' (' + country_list[curCountry] + ')'))
            elif curName.endswith(' (' + curCountry + ')'):
                newShowNames.append(curName.replace(' (' + curCountry + ')', ' (' + country_list[curCountry] + ')'))

    showNames += newShowNames

    return showNames
