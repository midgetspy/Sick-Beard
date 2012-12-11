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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import os

import sickbeard
from sickbeard import encodingKludge as ek
from sickbeard import tv
from sickbeard import common
from sickbeard import logger
from sickbeard.name_parser.parser import NameParser, InvalidNameException

from common import Quality, DOWNLOADED

name_presets = ('%SN - %Sx%0E - %EN',
                '%S.N.S%0SE%0E.%E.N',
                '%Sx%0E - %EN',
                'S%0SE%0E - %EN',
                'Season %0S/%S.N.S%0SE%0E.%Q.N-%RG'
                )

name_abd_presets = ('%SN - %A-D - %EN',
                    '%S.N.%A.D.%E.N.%Q.N',
                    '%Y/%0M/%S.N.%A.D.%E.N-%RG'
                    )

class TVShow():
    def __init__(self):
        self.name = "Show Name"
        self.genre = "Comedy"
        self.air_by_date = 0

class TVEpisode(tv.TVEpisode):
    def __init__(self, season, episode, name):
        self.relatedEps = []
        self._name = name
        self._season = season
        self._episode = episode
        self._airdate = datetime.date(2010, 3, 9)
        self.show = TVShow()
        self._status = Quality.compositeStatus(common.DOWNLOADED, common.Quality.SDTV)
        self._release_name = 'Show.Name.S02E03.HDTV.XviD-RLSGROUP'

def check_force_season_folders(pattern=None, multi=None):
    """
    Checks if the name can still be parsed if you strip off the folders to determine if we need to force season folders
    to be enabled or not.
    
    Returns true if season folders need to be forced on or false otherwise.
    """
    if pattern == None:
        pattern = sickbeard.NAMING_PATTERN
    
    errors = validate_name(pattern, None, file_only=True, warn=False)
    
    if multi != None:
        errors += validate_name(pattern, multi, file_only=True, warn=False)

    return errors

def check_valid_naming(pattern=None, multi=None):
    """
    Checks if the name is can be parsed back to its original form for both single and multi episodes.
    
    Returns a list which will be empty if the name was valid or contain error strings if not.
    """
    if pattern == None:
        pattern = sickbeard.NAMING_PATTERN
        
    logger.log(u"Checking whether the pattern "+pattern+" is valid for a single episode", logger.DEBUG)
    errors = validate_name(pattern, None)

    if multi != None:
        logger.log(u"Checking whether the pattern "+pattern+" is valid for a multi episode", logger.DEBUG)
        errors += validate_name(pattern, multi)

    logger.log(u"Checking whether the pattern "+pattern+" can be mistaken for a multi episode when the ep name begins with a number", logger.DEBUG)
    errors += validate_name(pattern, None, ep_name_number=True)

    return list(set(errors))

def check_valid_abd_naming(pattern=None):
    """
    Checks if the name is can be parsed back to its original form for an air-by-date format.
    
    Returns true if the naming is valid, false if not.
    """
    if pattern == None:
        pattern = sickbeard.NAMING_PATTERN
        
    logger.log(u"Checking whether the pattern "+pattern+" is valid for an air-by-date episode", logger.DEBUG)
    return validate_name(pattern, abd=True)


def validate_name(pattern, multi=None, file_only=False, abd=False, warn=True, ep_name_number=False):
    ep = _generate_sample_ep(multi, abd, ep_name_number)

    parser = NameParser(True)

    new_name = ep.formatted_filename(pattern, multi) + '.ext'
    new_path = ep.formatted_dir(pattern, multi)
    if not file_only:
        new_name = ek.ek(os.path.join, new_path, new_name)

    if warn:
        warn_level = logger.WARNING
    else:
        warn_level = logger.DEBUG

    if not new_name:
        logger.log(u"Pattern "+pattern+" is not a valid pattern", warn_level)
        return ["Pattern is invalid"]

    logger.log(u"Trying to parse "+new_name, logger.DEBUG)

    try:
        result = parser.parse(new_name)
    except InvalidNameException:
        logger.log(u"The pattern "+pattern+" generated an unrecognizable name: "+new_name, warn_level)
        return ["Pattern results in invalid name"]
    
    logger.log("The name "+new_name + " parsed into " + str(result), logger.DEBUG)

    if abd:
        if result.air_date != ep.airdate:
            logger.log(u"The pattern "+pattern+" resulted in "+new_name+" which was recognized as having date "+str(result.air_date)+" but should have had date "+str(ep.airdate), warn_level)
            return ["The air date parses incorrectly"]
    else:
        if result.season_number != ep.season:
            logger.log(u"The pattern "+pattern+" resulted in "+new_name+" which was recognized as being season "+str(result.season_number)+" but should have been season "+str(ep.season), warn_level)
            return ["The season number was not recognized correctly"]

        if set(result.episode_numbers) ^ set([x.episode for x in [ep] + ep.relatedEps]):
            logger.log(u"The pattern "+pattern+" resulted in "+new_name+" which was recognized as being episodes "+repr([str(x) for x in result.episode_numbers])+" but should have been episodes "+repr([str(x.episode) for x in [ep] + ep.relatedEps]), warn_level)
            if result.episode_numbers and ep_name_number:
                return ["If the episode name began with a number it would be mistaken for a multi-episode"]
            else:
                return ["The episode number was not recognized correctly"]

    return []

def _generate_sample_ep(multi=None, abd=False, ep_name_number=False):
    ep_name = "Ep Name"
    if ep_name_number:
        ep_name = "10 is part of the " + ep_name

    # make a fake episode object
    ep = TVEpisode(2,3,ep_name)
    ep._status = Quality.compositeStatus(DOWNLOADED, Quality.HDTV)
    ep._airdate = datetime.date(2011, 3, 9)
    if abd:
        ep._release_name = 'Show.Name.2011.03.09.HDTV.XviD-RLSGROUP'
    else:
        ep._release_name = 'Show.Name.S02E03.HDTV.XviD-RLSGROUP'

    if multi != None:
        ep._name = ep_name+" (1)"
        ep._release_name = 'Show.Name.S02E03E04E05.HDTV.XviD-RLSGROUP'

        secondEp = TVEpisode(2,4,ep_name+" (2)")
        secondEp._status = Quality.compositeStatus(DOWNLOADED, Quality.HDTV)
        secondEp._release_name = ep._release_name

        thirdEp = TVEpisode(2,5,ep_name+" (3)")
        thirdEp._status = Quality.compositeStatus(DOWNLOADED, Quality.HDTV)
        thirdEp._release_name = ep._release_name

        ep.relatedEps.append(secondEp)
        ep.relatedEps.append(thirdEp)

    return ep

def test_name(pattern, multi=None, abd=False):

    ep = _generate_sample_ep(multi, abd)

    return {'name': ep.formatted_filename(pattern, multi), 'dir': ep.formatted_dir(pattern, multi)}