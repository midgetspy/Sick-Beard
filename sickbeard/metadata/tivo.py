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
from lib.tvdb_api import tvdb_api, tvdb_exceptions

from sickbeard import encodingKludge as ek

class TIVOMetadata(generic.GenericMetadata):
    """
    Metadata generation class for TIVO

    The following file structure is used:

    show_root/Season 01/show - 1x01 - episode.avi.txt       (* existing episode)
    show_root/Season 01/.meta/show - 1x01 - episode.avi.txt (episode metadata)
    """
    
    def __init__(self,
                 show_metadata=False,
                 episode_metadata=False,
                 poster=False,
                 fanart=False,
                 episode_thumbnails=False,
                 season_thumbnails=False):

        generic.GenericMetadata.__init__(self,
                                         show_metadata,
                                         episode_metadata,
                                         poster,
                                         fanart,
                                         episode_thumbnails,
                                         season_thumbnails)
        
        self.name = 'TIVO'

        self.eg_show_metadata = "<i>not supported</i>"
        self.eg_episode_metadata = "Season##\\.meta\\<i>filename</i>.txt"
        self.eg_fanart = "<i>not supported</i>"
        self.eg_poster = "<i>not supported</i>"
        self.eg_episode_thumbnails = "<i>not supported</i>"
        self.eg_season_thumbnails = "<i>not supported</i>"
    
    # all of the following are not supported, so do nothing
    def create_show_metadata(self, show_obj):
        pass
    
    def create_episode_metadata(self, ep_obj):
        pass
    
    def create_fanart(self, show_obj):
        pass
    
    def get_episode_thumb_path(self, ep_obj):
        pass
    
    def get_season_thumb_path(self, show_obj, season):
        pass

    def retrieveShowMetadata(self, dir):
        return (None, None)

# present a standard "interface"
metadata_class = TIVOMetadata

