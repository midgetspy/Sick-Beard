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

import os

import sickbeard
from sickbeard import encodingKludge as ek
from sickbeard import tv
from sickbeard import common
from sickbeard import logger
from sickbeard.name_parser.parser import NameParser, InvalidNameException

from common import Quality, DOWNLOADED

dir_presets = ('Season %0S',
               '%RN',
               )

name_presets = ('%SN - %Sx%0E - %EN',
                '%S.N.S%0SE%0E.%E.N',
                '%Sx%0E - %EN',
                'S%0SE%0E - %EN')

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
    if multi == None:
        multi = sickbeard.NAMING_MULTI_EP

    # if either of these are false then we need to force season folders
    to_return = not validate_name(pattern, None, file_only=True) or not validate_name(pattern, multi, file_only=True)
    
    return to_return

def check_valid_naming(pattern=None, multi=None):
    """
    Checks if the name is can be parsed back to its original form for both single and multi episodes.
    
    Returns true if the naming is valid, false if not.
    """
    if pattern == None:
        pattern = sickbeard.NAMING_PATTERN
    if multi == None:
        multi = sickbeard.NAMING_MULTI_EP

    return validate_name(pattern, None) and validate_name(pattern, multi)


def validate_name(pattern, multi=None, file_only=False):
    ep = _generate_sample_ep(multi)

    parser = NameParser(True)

    new_name = ep.formatted_filename(pattern, multi) + '.ext'
    new_path = ep.formatted_dir(pattern, multi)
    if not file_only:
        new_name = ek.ek(os.path.join, new_path, new_name)

    try:
        result = parser.parse(new_name)
    except InvalidNameException:
        return False
    
    logger.log(new_name + " vs " + str(result), logger.DEBUG)

    if result.season_number != ep.season:
        return False
    if result.episode_numbers != [x.episode for x in [ep] + ep.relatedEps]:
        return False

    return True

def _generate_sample_ep(multi=None):
    # make a fake episode object
    ep = TVEpisode(2,3,"Ep Name")
    ep._status = Quality.compositeStatus(DOWNLOADED, Quality.HDTV)

    if multi != None:
        ep._name = "Ep Name (1)"
        secondEp = TVEpisode(2,4,"Ep Name (2)")
        secondEp._status = Quality.compositeStatus(DOWNLOADED, Quality.HDTV)
        ep.relatedEps.append(secondEp)
        ep._release_name = 'Show.Name.S02E03E04.HDTV.XviD-RLSGROUP'
        secondEp._release_name = ep._release_name

    return ep

def test_name(pattern, multi=None):

    ep = _generate_sample_ep(multi)

    return {'name': ep.formatted_filename(pattern, multi), 'dir': ep.formatted_dir(pattern, multi)}
