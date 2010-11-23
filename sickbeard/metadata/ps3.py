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

import sickbeard

import generic

from sickbeard.common import *
from sickbeard import logger, exceptions, helpers
from sickbeard import encodingKludge as ek
from lib.tvdb_api import tvdb_api, tvdb_exceptions

class PS3Metadata(generic.GenericMetadata):
    """
    Metadata generation class for Sony PS3.
    
    The following file structure is used:
    
    show_root/cover.jpg                                      (poster)
    show_root/fanart.jpg                                     (fanart)
    show_root/Season 01/season.jpg                           (season thumb)
    show_root/Season 01/show - 1x01 - episode.avi            (* example of existing ep
                                                                of course)
    show_root/Season 01/show - 1x01 - episode.avi.cover.jpg   (episode thumb)
    """
    
    def __init__(self):
        generic.GenericMetadata.__init__(self)

        self.name = 'PS3'

    def get_episode_thumb_path(self, ep_obj):
        """
        Returns the path where the episode thumbnail should be stored. Defaults to
        the same path as the episode file but with a .cover.jpg extension.
        
        ep_obj: a TVEpisode instance for which to create the thumbnail
        """
        if ek.ek(os.path.isfile, ep_obj.location):
            tbn_filename = ep_obj.location + '.cover.jpg'
        else:
            return None
        
        return tbn_filename
    
    def get_season_thumb_path(self, show_obj, season):
        """
        Returns the full path to the file for a given season thumb.
        
        show_obj: a TVShow instance for which to generate the path
        season: a season number to be used for the path. Note that sesaon 0
                means specials.
        """

        # Our specials thumbnail is, well, special
        if season == 0:
            season_thumb_file_path = 'season-specials'
        else:
            season_thumb_file_path = 'season' + str(season).zfill(2)
        
        return ek.ek(os.path.join, show_obj.location, season_thumb_file_path+'.jpg')
    
# present a standard "interface"
metadata_class = PS3Metadata

