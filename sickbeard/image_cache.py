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
import sys

sys.path.append(os.path.abspath('lib'))

import sickbeard

from sickbeard import helpers, logger
from sickbeard import encodingKludge as ek
from sickbeard.metadata.generic import GenericMetadata

from lib.hachoir_parser import createParser
from lib.hachoir_metadata import extractMetadata

class ImageCache:
    
    def __init__(self):
        pass
    
    def _cache_dir(self):
        return ek.ek(os.path.abspath, ek.ek(os.path.join, sickbeard.CACHE_DIR, 'images'))

    def poster_path(self, tvdb_id):
        poster_file_name = str(tvdb_id) + '.poster.jpg'
        return ek.ek(os.path.join, self._cache_dir(), poster_file_name)
    
    def banner_path(self, tvdb_id):
        banner_file_name = str(tvdb_id) + '.banner.jpg'
        return ek.ek(os.path.join, self._cache_dir(), banner_file_name)

    def has_poster(self, tvdb_id):
        return ek.ek(os.path.isfile, self.poster_path(tvdb_id))

    def has_banner(self, tvdb_id):
        return ek.ek(os.path.isfile, self.banner_path(tvdb_id))

    BANNER = 1
    POSTER = 2
    
    def which_type(self, path):
        if not ek.ek(os.path.isfile, path):
            return None
        img_parser = createParser(path)
        img_metadata = extractMetadata(img_parser)
        img_ratio = float(img_metadata.get('width'))/float(img_metadata.get('height'))
        
        if 0.55 < img_ratio < 0.8:
            return self.POSTER
        elif 5 < img_ratio < 6:
            return self.BANNER
        else:
            logger.log(u"Image has size ratio of "+str(img_ratio)+", unknown type", logger.WARNING)
            return None
    
    def _cache_image_from_file(self, image_path, img_type, tvdb_id):
        if img_type == self.POSTER:
            dest_path = self.poster_path(tvdb_id)
        elif img_type == self.BANNER:
            dest_path = self.banner_path(tvdb_id)
        else:
            logger.log(u"Invalid cache image type: "+str(img_type), logger.ERROR)
            return False

        if not ek.ek(os.path.isdir, self._cache_dir()):
            logger.log(u"Image cache dir didn't exist, creating it at "+str(self._cache_dir()))
            ek.ek(os.makedirs, self._cache_dir())

        logger.log(u"Copying from "+image_path+" to "+dest_path)
        helpers.copyFile(image_path, dest_path)
        
        return True

    def _cache_image_from_tvdb(self, show_obj, img_type):
        if img_type == self.POSTER:
            img_type_name = 'poster'
            dest_path = self.poster_path(show_obj.tvdbid)
        elif img_type == self.BANNER:
            img_type_name = 'banner'
            dest_path = self.banner_path(show_obj.tvdbid)
        else:
            logger.log(u"Invalid cache image type: "+str(img_type), logger.ERROR)
            return False

        #TODO: refactor
        metadata_generator = GenericMetadata()
        img_data = metadata_generator._retrieve_show_image(img_type_name, show_obj)
        result = metadata_generator._write_image(img_data, dest_path)

        return result
    
    def fill_cache(self, show_obj):

        logger.log(u"Checking if we need any cache images for show "+str(show_obj.tvdbid), logger.DEBUG)
        
        # check if the images are already cached or not
        need_images = {self.POSTER: not self.has_poster(show_obj.tvdbid),
                       self.BANNER: not self.has_banner(show_obj.tvdbid),
                       }

        if not need_images[self.POSTER] and not need_images[self.BANNER]:
            return
        
        # check the show dir for images and use them
        for cur_provider in sickbeard.metadata_provider_dict.values():
            if ek.ek(os.path.isfile, cur_provider.get_poster_path(show_obj)):
                cur_file_name = os.path.abspath(cur_provider.get_poster_path(show_obj))
                cur_file_type = self.which_type(cur_file_name)
                
                logger.log(u"Checking if image "+cur_file_name+" (type "+str(cur_file_type)+" needs metadata: "+str(need_images[cur_file_type]), logger.DEBUG)
                
                if cur_file_type in need_images and need_images[cur_file_type]:
                    logger.log(u"Found an image in the show dir that doesn't exist in the cache, caching it: "+str(cur_file_name)+", type "+str(cur_file_type), logger.DEBUG)
                    self._cache_image_from_file(cur_file_name, cur_file_type, show_obj.tvdbid)
                    need_images[cur_file_type] = False
                    
        # download from TVDB for missing ones
        for cur_image_type in [self.POSTER, self.BANNER]:
            logger.log(u"Seeing if we still need an image of type "+str(cur_image_type)+": "+str(need_images[cur_image_type]), logger.DEBUG)
            if cur_image_type in need_images and need_images[cur_image_type]:
                self._cache_image_from_tvdb(show_obj, cur_image_type)
        
