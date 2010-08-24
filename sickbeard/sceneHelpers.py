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
from sickbeard import logger, db

import re
import datetime

from lib.tvnamer.utils import FileParser 
from lib.tvnamer import tvnamer_exceptions

resultFilters = ("subpack", "nlsub", "swesub", "subbed", "subs",
                 "dirfix", "samplefix", "nfofix", "dvdextras",
                 "sample", "extras", "special", "dubbed", "german")

def filterBadReleases(name):

    try:
        fp = FileParser(name)
        epInfo = fp.parse()
    except tvnamer_exceptions.InvalidFilename:
        logger.log("Unable to parse the filename "+name+" into a valid episode", logger.WARNING)
        return False
    
    # if there's no info after the season info then assume it's fine
    if not epInfo.episodename:
        return True
    
    # if any of the bad strings are in the name then say no
    for x in resultFilters:
        if re.search('(^|[\W_])'+x+'($|[\W_])', epInfo.episodename, re.I):
            logger.log("Invalid scene release: "+name+" contains "+x+", ignoring it", logger.DEBUG)
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


def makeSceneSeasonSearchString (show, season, extraSearchType=None):

    seasonStrings = ["S%02d" % season, "%ix" % season]

    showNames = set(makeSceneShowSearchStrings(show))

    toReturn = []

    for curShow in showNames:
        if not extraSearchType:
            toReturn.append(curShow + "." + seasonStrings[0])
        elif extraSearchType == "nzbmatrix":
            seasonString = ','.join([x+'*' for x in seasonStrings])
            toReturn.append('+"'+curShow+'" +('+seasonString+')')

    return toReturn


def makeSceneSearchString (episode):

    myDB = db.DBConnection()
    numseasonsSQlResult = myDB.select("SELECT COUNT(DISTINCT season) as numseasons FROM tv_episodes WHERE showid = ? and season != 0", [episode.show.tvdbid])
    numseasons = numseasonsSQlResult[0][0]

    # see if we should use dates instead of episodes
    if episode.show.air_by_date or (episode.show.genre and "Talk Show" in episode.show.genre and episode.airdate != datetime.date.fromordinal(1)):
        epStrings = [str(episode.airdate).replace('-', '.')]
    elif numseasons == 1:
        logger.log("Looks like this show only has 1 season and could be a mini-series, searching for it using 'Part' as the episode identifier", logger.DEBUG)
        epStrings = ["S%02iE%02i" % (int(episode.season), int(episode.episode)),
                    "%ix%02i" % (int(episode.season), int(episode.episode)),
                    "Part %i" % (int(episode.episode)), 
                    "Part%i" % (int(episode.episode)),
                    "Pt %i" % (int(episode.episode)),
                    "Pt%i" % (int(episode.episode))]
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
                logger.log("Show names ends with "+curCountry+", so trying to add ("+countryList[curCountry]+") to it as well", logger.DEBUG)
                newShowNames.append(curName.replace(' '+curCountry, ' ('+countryList[curCountry]+')'))
            elif curName.endswith(' ('+curCountry+')'):
                logger.log("Show names ends with "+curCountry+", so trying to add ("+countryList[curCountry]+") to it as well", logger.DEBUG)
                newShowNames.append(curName.replace(' ('+curCountry+')', ' ('+countryList[curCountry]+')'))

    showNames += newShowNames

    return showNames

