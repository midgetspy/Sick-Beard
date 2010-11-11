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

from sickbeard.common import *
from sickbeard import logger
from sickbeard import db

import re
import datetime

from lib.tvnamer.utils import FileParser
from lib.tvnamer import tvnamer_exceptions

resultFilters = ("subpack", "nlsub", "swesub", "subbed", "subs",
                 "dirfix", "samplefix", "nfofix", "dvdextras",
                 "sample", "extras", "special", "dubbed", "german",
                "french", "core2hd")

def filterBadReleases(name):

    try:
        fp = FileParser(name)
        epInfo = fp.parse()
    except tvnamer_exceptions.InvalidFilename:
        logger.log(u"Unable to parse the filename "+name+" into a valid episode", logger.WARNING)
        return False

    # if there's no info after the season info then assume it's fine
    if not epInfo.episodename:
        return True

    # if any of the bad strings are in the name then say no
    for x in resultFilters:
        if re.search('(^|[\W_])'+x+'($|[\W_])', epInfo.episodename, re.I):
            logger.log(u"Invalid scene release: "+name+" contains "+x+", ignoring it", logger.DEBUG)
            return False

    return True

def sanitizeSceneName (name):
    for x in ",:()'!":
        name = name.replace(x, "")

    name = name.replace("- ", ".").replace(" ", ".").replace("&", "and")
    name = re.sub("\.\.*", ".", name)

    if name.endswith('.'):
        name = name[:-1]

    return name

def sceneToNormalShowNames(name):

    return [name, name.replace(".and.", ".&.")]

def makeSceneShowSearchStrings(show):

    showNames = allPossibleShowNames(show)

    # scenify the names
    return map(sanitizeSceneName, showNames)


def makeSceneSeasonSearchString (show, segment, extraSearchType=None):

    myDB = db.DBConnection()

    if show.is_air_by_date:
        numseasons = 0
        
        # the search string for air by date shows is just 
        seasonStrings = [segment]
    
    else:
        numseasonsSQlResult = myDB.select("SELECT COUNT(DISTINCT season) as numseasons FROM tv_episodes WHERE showid = ? and season != 0", [show.tvdbid])
        numseasons = numseasonsSQlResult[0][0]

        seasonStrings = ["S%02d" % segment]
        # since nzbmatrix allows more than one search per request we search SxEE results too
        if extraSearchType == "nzbmatrix":
            seasonStrings.append("%ix" % segment)

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
        
        # nzbmatrix is special, we build a search string just for them
        elif extraSearchType == "nzbmatrix":
            if numseasons == 1:
                toReturn.append('+"'+curShow+'"')
            else:
                term_list = [x+'*' for x in seasonStrings]
                if show.is_air_by_date:
                    term_list = ['"'+x+'"' for x in term_list]

                toReturn.append('+"'+curShow+'" +('+','.join(term_list)+')')

    return toReturn


def makeSceneSearchString (episode):

    # see if we should use dates instead of episodes
    if episode.show.is_air_by_date and episode.airdate != datetime.date.fromordinal(1):
        epStrings = [str(episode.airdate)]
    else:
        epStrings = ["S%02iE%02i" % (int(episode.season), int(episode.episode)),
                    "%ix%02i" % (int(episode.season), int(episode.episode))]

    showNames = set(makeSceneShowSearchStrings(episode.show))

    toReturn = []

    for curShow in showNames:
        for curEpString in epStrings:
            toReturn.append(curShow + '.' + curEpString)

    return toReturn

def allPossibleShowNames(show):

    showNames = [show.name]

    if int(show.tvdbid) in sceneExceptions:
        showNames += sceneExceptions[int(show.tvdbid)]

    # if we have a tvrage name then use it
    if show.tvrname != "" and show.tvrname != None:
        showNames.append(show.tvrname)

    newShowNames = []

    # if we have "Show Name Australia" or "Show Name (Australia)" this will add "Show Name (AU)" for
    # any countries defined in common.countryList
    for curName in showNames:
        for curCountry in countryList:
            if curName.endswith(' '+curCountry):
                logger.log(u"Show names ends with "+curCountry+", so trying to add ("+countryList[curCountry]+") to it as well", logger.DEBUG)
                newShowNames.append(curName.replace(' '+curCountry, ' ('+countryList[curCountry]+')'))
            elif curName.endswith(' ('+curCountry+')'):
                logger.log(u"Show names ends with "+curCountry+", so trying to add ("+countryList[curCountry]+") to it as well", logger.DEBUG)
                newShowNames.append(curName.replace(' ('+curCountry+')', ' ('+countryList[curCountry]+')'))

    showNames += newShowNames

    return showNames

def isGoodResult(name, show, log=True):
    """
    Use an automatically-created regex to make sure the result actually is the show it claims to be
    """

    showNames = map(sanitizeSceneName, allPossibleShowNames(show))

    for curName in set(showNames):
        curRegex = '^' + re.sub('[\.\-]', '\W+', curName) + '\W+(?:(?:S\d\d)|(?:\d\d?x)|(?:\d{4}\W\d\d\W\d\d)|(?:(?:part|pt)[\._ -]?(\d|[ivx]))|Season\W+\d+\W+|E\d+\W+)'
        if log:
            logger.log(u"Checking if show "+name+" matches " + curRegex, logger.DEBUG)

        match = re.search(curRegex, name, re.I)

        if match:
            return True

    if log:
        logger.log(u"Provider gave result "+name+" but that doesn't seem like a valid result for "+show.name+" so I'm ignoring it")
    return False
