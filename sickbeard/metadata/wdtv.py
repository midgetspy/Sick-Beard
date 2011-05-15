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
import re

import generic

from sickbeard import logger, helpers

from sickbeard import encodingKludge as ek

class WDTVMetadata(generic.GenericMetadata):
    """
    Metadata generation class for WDTV

    The following file structure is used:
    
    show_root/folder.jpg                                     (poster)
    show_root/Season 01/folder.jpg                           (episode thumb)
    show_root/Season 01/show - 1x01 - episode.jpg            (existing video)
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
        
        self.name = 'WDTV'

        self.eg_show_metadata = "<i>not supported</i>"
        self.eg_episode_metadata = "<i>not supported</i>"
        self.eg_fanart = "<i>not supported</i>"
        self.eg_poster = "folder.jpg"
        self.eg_episode_thumbnails = "Season##\\<i>filename</i>.jpg"
        self.eg_season_thumbnails = "Season##\\folder.jpg"
    
    # all of the following are not supported, so do nothing
    def create_show_metadata(self, show_obj):
        pass
    
    def create_episode_metadata(self, ep_obj):
        pass
    
    def create_fanart(self, show_obj):
        pass
    
    def get_episode_thumb_path(self, ep_obj):
        """
        Returns the path where the episode thumbnail should be stored. Defaults to
        the same path as the episode file but with a .cover.jpg extension.
        
        ep_obj: a TVEpisode instance for which to create the thumbnail
        """
        if ek.ek(os.path.isfile, ep_obj.location):
            tbn_filename = helpers.replaceExtension(ep_obj.location, 'jpg')
        else:
            return None

        return tbn_filename
    
    def get_season_thumb_path(self, show_obj, season):
        """
        Season thumbs for MediaBrowser go in Show Dir/Season X/folder.jpg
        
        If no season folder exists, None is returned
        """
        
        dir_list = [x for x in ek.ek(os.listdir, show_obj.location) if ek.ek(os.path.isdir, ek.ek(os.path.join, show_obj.location, x))]
        
        season_dir_regex = '^Season\s+(\d+)$'
        
        season_dir = None
        
        for cur_dir in dir_list:
            if season == 0 and cur_dir == 'Specials':
                season_dir = cur_dir
                break
            
            match = re.match(season_dir_regex, cur_dir, re.I)
            if not match:
                continue
        
            cur_season = int(match.group(1))
            
            if cur_season == season:
                season_dir = cur_dir
                break

        if not season_dir:
            logger.log(u"Unable to find a season dir for season "+str(season), logger.DEBUG)
            return None

        logger.log(u"Using "+str(season_dir)+"/folder.jpg as season dir for season "+str(season), logger.DEBUG)

        return ek.ek(os.path.join, show_obj.location, season_dir, 'folder.jpg')

    def retrieveShowMetadata(self, dir):
        return (None, None)

# present a standard "interface"
metadata_class = WDTVMetadata

