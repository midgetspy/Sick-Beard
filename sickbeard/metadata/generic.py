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

import os.path

import xml.etree.cElementTree as etree

from sickbeard import helpers, logger
from sickbeard import encodingKludge as ek

class GenericMetadata():
    
    def __init__(self):
        self._show_file_name = "tvshow.nfo"
        self._ep_nfo_extension = "nfo"

        self.generate_show_metadata = True
        self.generate_ep_metadata = True
        
        self.name = 'Generic'
    
    def show_file_name(self):
        return self._show_file_name
    
    def _show_data(self, show_obj):
        return None
    
    def _ep_data(self, ep_obj):
        return None
    
    def write_show_file(self, show_obj, path):
        """
        Generates and writes show_obj's metadata under the given path.
        
        show_obj: TVShow object for which to create the metadata
        
        path: An absolute or relative path where we should put the file. Note that
                the file name will be the default show_file_name.
        
        Note that this method expects that _show_data will return an ElementTree
        object. If your _show_data returns data in another format you'll need to
        override this method.
        """
        
        data = self._show_data(show_obj)
        
        if not data:
            return False
        
        nfo_file_path = ek.ek(os.path.join, path, self.show_file_name())

        logger.log(u"Writing show nfo file to "+nfo_file_path)
        
        nfo_file = open(nfo_file_path, 'w')

        data.write(nfo_file, encoding="utf-8")
        nfo_file.close()
        
        return True

    def write_ep_file(self, ep_obj, file_name_path):
        """
        Generates and writes ep_obj's metadata under the given path with the
        given filename root.
        
        ep_obj: TVEpisode object for which to create the metadata
        
        file_name_path: The file name to use for this metadata. Note that the extension
                will be automatically added based on _ep_nfo_extension. This should
                include an absolute path.
        
        Note that this method expects that _ep_data will return an ElementTree
        object. If your _ep_data returns data in another format you'll need to
        override this method.
        """
        
        data = self._ep_data(ep_obj)
        
        if not data:
            return False
        
        nfo_file_path = helpers.replaceExtension(file_name_path, self._ep_nfo_extension)
        
        logger.log(u"Writing episode nfo file to "+nfo_file_path)
        
        nfo_file = open(nfo_file_path, 'w')

        data.write(nfo_file, encoding="utf-8")
        nfo_file.close()
        
        return True
        