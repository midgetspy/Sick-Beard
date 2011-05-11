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

import os

import generic

from sickbeard import encodingKludge as ek

class PS3Metadata(generic.GenericMetadata):
    """
    Metadata generation class for Sony PS3.

    The following file structure is used:
    
    show_root/cover.jpg                                      (poster)
    show_root/Season 01/show - 1x01 - episode.avi            (existing video)
    show_root/Season 01/show - 1x01 - episode.avi.cover.jpg  (episode thumb)
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
        
        self.poster_name = 'cover.jpg'
        self.name = 'Sony PS3'

        self.eg_show_metadata = "<i>not supported</i>"
        self.eg_episode_metadata = "<i>not supported</i>"
        self.eg_fanart = "<i>not supported</i>"
        self.eg_poster = "cover.jpg"
        self.eg_episode_thumbnails = "Season##\\<i>filename</i>.ext.cover.jpg"
        self.eg_season_thumbnails = "<i>not supported</i>"
    
    # all of the following are not supported, so do nothing
    def create_show_metadata(self, show_obj):
        pass
    
    def create_episode_metadata(self, ep_obj):
        pass
    
    def create_fanart(self, show_obj):
        pass
    
    def create_season_thumbs(self, show_obj):
        pass
    
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

    def retrieveShowMetadata(self, dir):
        return (None, None)

# present a standard "interface"
metadata_class = PS3Metadata

