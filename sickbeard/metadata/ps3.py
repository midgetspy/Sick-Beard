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
    show_root/cover.jpg                                      (show poster)
    show_root/Season 01/show - 1x01 - episode.avi            (* example of existing ep of course)
    show_root/Season 01/show - 1x01 - episode.avi.cover.jpg  (episode thumb)
    """
    
    def __init__(self,
                 show_metadata=False,
                 show_fanart=False,
                 show_poster=False,
                 show_banner=False,
                 season_all_fanart=False,
                 season_all_poster=False,
                 season_all_banner=False,
                 season_fanarts=False,
                 season_posters=False,
                 season_banners=False,
                 episode_metadata=False,
                 episode_thumbnails=False):

        generic.GenericMetadata.__init__(self,
                                         show_metadata,
                                         show_fanart,
                                         show_poster,
                                         show_banner,
                                         season_all_fanart,
                                         season_all_poster,
                                         season_all_banner,
                                         season_fanarts,
                                         season_posters,
                                         season_banners,
                                         episode_metadata,
                                         episode_thumbnails)
        

        self.name = 'Sony PS3'

        self.show_poster_name = 'cover.jpg'

        self.eg_show_metadata = "<i>not supported</i>"
        self.eg_show_fanart = "<i>not supported</i>"
        self.eg_show_poster = "cover.jpg"
        self.eg_show_banner = "<i>not supported</i>"

        self.eg_season_all_fanart = "<i>not supported</i>"
        self.eg_season_all_poster = "<i>not supported</i>"
        self.eg_season_all_banner = "<i>not supported</i>"
        self.eg_season_fanarts = "<i>not supported</i>"
        self.eg_season_posters = "<i>not supported</i>" 
        self.eg_season_banners = "<i>not supported</i>"

        self.eg_episode_metadata = "<i>not supported</i>"
        self.eg_episode_thumbnails = "Season##\\<i>filename</i>.ext.cover.jpg"

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

    # all of the following are not supported, so do nothing
    def create_show_metadata(self, show_obj):
        pass

    def create_show_fanart(self, show_obj): 
        pass

    def create_show_poster(self, show_obj):
        if self.show_poster and show_obj and not self._has_show_poster(show_obj):
            logger.log("Metadata provider "+self.name+" creating show poster for "+show_obj.name, logger.DEBUG)
            poster_path = self.get_show_poster_path(show_obj)
            if sickbeard.USE_BANNER:
                img_type = 'banner'
            else:
                img_type = 'poster'
            return self.save_show_fpb(show_obj, img_type, poster_path)
        return False

    def create_show_banner(self, show_obj): 
        pass

    def create_season_all_fanart(self, show_obj): 
        pass

    def create_season_all_poster(self, show_obj): 
        pass

    def create_season_all_banner(self, show_obj): 
        pass

    def create_season_fanart(self, show_obj): 
        pass

    def create_season_poster(self, show_obj):
        pass

    def create_season_banner(self, show_obj): 
        pass

    def create_episode_metadata(self, ep_obj):
        pass

    def retrieveShowMetadata(self, dir):
        return (None, None)

# present a standard "interface"
metadata_class = PS3Metadata

