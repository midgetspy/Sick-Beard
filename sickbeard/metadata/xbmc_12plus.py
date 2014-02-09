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

import generic
import xbmc
import os

from sickbeard import encodingKludge as ek


class XBMC_12PLUS(xbmc.XBMCMetadata):
    """
    Metadata generation class for XBMC 12+.

    The following file structure is used:

    show_root/tvshow.nfo                    (show metadata)
    show_root/poster.jpg                    (poster)
    show_root/fanart.jpg                    (fanart)
    show_root/season##-poster.jpg           (season thumb)
    show_root/Season ##/filename.ext        (*)
    show_root/Season ##/filename.nfo        (episode metadata)
    show_root/Season ##/filename-thumb.jpg  (episode thumb)
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

        self.banner_name = "banner.jpg"
        self.poster_name = "poster.jpg"

        self.name = 'XBMC 12+'

        self.eg_show_metadata = "tvshow.nfo"
        self.eg_episode_metadata = "Season##\\<i>filename</i>.nfo"
        self.eg_fanart = "fanart.jpg"
        self.eg_poster = "poster.jpg (banner.jpg)"
        self.eg_episode_thumbnails = "Season##\\<i>filename</i>-thumb.jpg"
        self.eg_season_thumbnails = "season##-poster.jpg"

    def get_id(self):
        return 'xbmc_12plus'

    def get_episode_thumb_path(self, ep_obj):
        """
        Returns the path where the episode thumbnail should be stored.
        ep_obj: a TVEpisode instance for which to create the thumbnail
        """
        if ek.ek(os.path.isfile, ep_obj.location):

            tbn_filename = ep_obj.location.rpartition(".")

            if tbn_filename[0] == "":
                tbn_filename = ep_obj.location + "-thumb.jpg"
            else:
                tbn_filename = tbn_filename[0] + "-thumb.jpg"
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

        return ek.ek(os.path.join, show_obj.location, season_thumb_file_path + '-poster.jpg')


# present a standard "interface" from the module
metadata_class = XBMC_12PLUS
