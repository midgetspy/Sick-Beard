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
        
        self._ep_nfo_extension = "txt"
        
        self.generate_ep_metadata = True
        
        self.name = 'TIVO'

        self.eg_show_metadata = "<i>not supported</i>"
        self.eg_episode_metadata = "Season##\\.meta\\<i>filename</i>.txt"
        self.eg_fanart = "<i>not supported</i>"
        self.eg_poster = "<i>not supported</i>"
        self.eg_episode_thumbnails = "<i>not supported</i>"
        self.eg_season_thumbnails = "<i>not supported</i>"
    
    # Override with empty methods for unsupported features.
    def create_show_metadata(self, show_obj):
        pass
    
    def create_fanart(self, show_obj):
        pass
    
    def get_episode_thumb_path(self, ep_obj):
        pass
    
    def get_season_thumb_path(self, show_obj, season):
        pass

    def retrieveShowMetadata(self, dir):
        return (None, None)
        
    # Override and implement features for Tivo.
    def get_episode_file_path(self, ep_obj):
        """
        Returns a full show dir/.meta/episode.txt path for Tivo
        episode metadata files
        
        ep_obj: a TVEpisode object to get the path for
        """
        logger.log("TIVO get_episode_file_path called");
        
        if ek.ek(os.path.isfile, ep_obj.location):
            metadata_file_name = helpers.replaceExtension(ek.ek(os.path.basename, ep_obj.location), self._ep_nfo_extension)
            metadata_dir_name = ek.ek(os.path.join, ek.ek(os.path.dirname, ep_obj.location), '.meta')
            metadata_file_path = ek.ek(os.path.join, metadata_dir_name, metadata_file_name)
        else:
            logger.log(u"Episode location doesn't exist: "+str(ep_obj.location), logger.DEBUG)
            return ''
            

        logger.log("TIVO metadata_file_path '" + metadata_file_path + "'");
        
        return metadata_file_path

    def _ep_data(self, ep_obj):
        """
        TODO: implement
        
        Creates a key value structure for a Tivo episode metadata file and
        returns the resulting data object.
        
        show_obj: a TVEpisode instance to create the metadata file for
        """
        logger.log("TIVO _ep_data called");
        
        data = "Tivo test data"
        
        return data

    def write_ep_file(self, ep_obj):
        """
        TODO: implement
        
        Generates and writes ep_obj's metadata under the given path with the
        given filename root. Uses the episode's name with the extension in
        _ep_nfo_extension.
        
        ep_obj: TVEpisode object for which to create the metadata
        
        file_name_path: The file name to use for this metadata. Note that the extension
                will be automatically added based on _ep_nfo_extension. This should
                include an absolute path.
        """
        logger.log("TIVO write_ep_file called");
        
        data = self._ep_data(ep_obj)
        
        if not data:
            return False
        
        nfo_file_path = self.get_episode_file_path(ep_obj)
        nfo_file_dir = ek.ek(os.path.dirname, nfo_file_path)
        
        logger.log("TIVO nfo_file_path: '" + nfo_file_path +"'");
        logger.log("TIVO nfo_file_dir:  '" + nfo_file_dir +"'");
        logger.log("TIVO With data: " + data);
        
        return None

# present a standard "interface"
metadata_class = TIVOMetadata

