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

import sickbeard

from sickbeard import helpers, logger, exceptions
from sickbeard import encodingKludge as ek

from sickbeard.metadata.generic import GenericMetadata

from lib.hachoir_parser import createParser
from lib.hachoir_metadata import extractMetadata

class ImageCache:
    
    def __init__(self):
        pass
    
    def _cache_dir(self):
        """
        Builds up the full path to the image cache directory
        """
        return ek.ek(os.path.abspath, ek.ek(os.path.join, sickbeard.CACHE_DIR, 'images'))

    def poster_path(self, tvdb_id):
        """
        Builds up the path to a poster cache for a given tvdb id

        returns: a full path to the cached poster file for the given tvdb id 
        
        tvdb_id: ID of the show to use in the file name
        """
        poster_file_name = str(tvdb_id) + '.poster.jpg'
        return ek.ek(os.path.join, self._cache_dir(), poster_file_name)
    
    def banner_path(self, tvdb_id):
        """
        Builds up the path to a banner cache for a given tvdb id

        returns: a full path to the cached banner file for the given tvdb id 
        
        tvdb_id: ID of the show to use in the file name
        """
        banner_file_name = str(tvdb_id) + '.banner.jpg'
        return ek.ek(os.path.join, self._cache_dir(), banner_file_name)

    def has_poster(self, tvdb_id):
        """
        Returns true if a cached poster exists for the given tvdb id
        """
        poster_path = self.poster_path(tvdb_id)
        logger.log(u"Checking if file "+str(poster_path)+" exists", logger.DEBUG)
        return ek.ek(os.path.isfile, poster_path)

    def has_banner(self, tvdb_id):
        """
        Returns true if a cached banner exists for the given tvdb id
        """
        banner_path = self.banner_path(tvdb_id)
        logger.log(u"Checking if file "+str(banner_path)+" exists", logger.DEBUG)
        return ek.ek(os.path.isfile, banner_path)

    BANNER = 1
    POSTER = 2
    
    def which_type(self, path):
        """
        Analyzes the image provided and attempts to determine whether it is a poster or banner.
        
        returns: BANNER, POSTER if it concluded one or the other, or None if the image was neither (or didn't exist)
        
        path: full path to the image
        """

        if not ek.ek(os.path.isfile, path):
            logger.log(u"Couldn't check the type of "+str(path)+" cause it doesn't exist", logger.WARNING)
            return None

        # use hachoir to parse the image for us
        img_parser = createParser(path)
        img_metadata = extractMetadata(img_parser)

        if not img_metadata:
            logger.log(u"Unable to get metadata from "+str(path)+", not using your existing image", logger.DEBUG)
            return None
        
        img_ratio = float(img_metadata.get('width'))/float(img_metadata.get('height'))

        img_parser.stream._input.close()

        # most posters are around 0.68 width/height ratio (eg. 680/1000)
        if 0.55 < img_ratio < 0.8:
            return self.POSTER
        
        # most banners are around 5.4 width/height ratio (eg. 758/140)
        elif 5 < img_ratio < 6:
            return self.BANNER
        else:
            logger.log(u"Image has size ratio of "+str(img_ratio)+", unknown type", logger.WARNING)
            return None
    
    def _cache_image_from_file(self, image_path, img_type, tvdb_id):
        """
        Takes the image provided and copies it to the cache folder
        
        returns: bool representing success
        
        image_path: path to the image we're caching
        img_type: BANNER or POSTER
        tvdb_id: id of the show this image belongs to
        """

        # generate the path based on the type & tvdb_id
        if img_type == self.POSTER:
            dest_path = self.poster_path(tvdb_id)
        elif img_type == self.BANNER:
            dest_path = self.banner_path(tvdb_id)
        else:
            logger.log(u"Invalid cache image type: "+str(img_type), logger.ERROR)
            return False

        # make sure the cache folder exists before we try copying to it
        if not ek.ek(os.path.isdir, self._cache_dir()):
            logger.log(u"Image cache dir didn't exist, creating it at "+str(self._cache_dir()))
            ek.ek(os.makedirs, self._cache_dir())

        logger.log(u"Copying from "+image_path+" to "+dest_path)
        helpers.copyFile(image_path, dest_path)
        
        return True

    def _cache_image_from_tvdb(self, show_obj, img_type):
        """
        Retrieves an image of the type specified from TVDB and saves it to the cache folder
        
        returns: bool representing success
        
        show_obj: TVShow object that we want to cache an image for
        img_type: BANNER or POSTER
        """

        # generate the path based on the type & tvdb_id
        if img_type == self.POSTER:
            img_type_name = 'poster'
            dest_path = self.poster_path(show_obj.tvdbid)
        elif img_type == self.BANNER:
            img_type_name = 'banner'
            dest_path = self.banner_path(show_obj.tvdbid)
        else:
            logger.log(u"Invalid cache image type: "+str(img_type), logger.ERROR)
            return False

        # retrieve the image from TVDB using the generic metadata class
        #TODO: refactor
        metadata_generator = GenericMetadata()
        img_data = metadata_generator._retrieve_show_image(img_type_name, show_obj)
        result = metadata_generator._write_image(img_data, dest_path)

        return result
    
    def fill_cache(self, show_obj):
        """
        Caches all images for the given show. Copies them from the show dir if possible, or
        downloads them from TVDB if they aren't in the show dir.
        
        show_obj: TVShow object to cache images for
        """

        logger.log(u"Checking if we need any cache images for show "+str(show_obj.tvdbid), logger.DEBUG)

        # check if the images are already cached or not
        need_images = {self.POSTER: not self.has_poster(show_obj.tvdbid),
                       self.BANNER: not self.has_banner(show_obj.tvdbid),
                       }
        
        if not need_images[self.POSTER] and not need_images[self.BANNER]:
            logger.log(u"No new cache images needed, not retrieving new ones")
            return
        
        # check the show dir for images and use them
        try:
            for cur_provider in sickbeard.metadata_provider_dict.values():
                logger.log(u"Checking if we can use the show image from the "+cur_provider.name+" metadata", logger.DEBUG)
                if ek.ek(os.path.isfile, cur_provider.get_poster_path(show_obj)):
                    cur_file_name = os.path.abspath(cur_provider.get_poster_path(show_obj))
                    cur_file_type = self.which_type(cur_file_name)
                    
                    if cur_file_type == None:
                        logger.log(u"Unable to retrieve image type, not using the image from "+str(cur_file_name), logger.WARNING)
                        continue

                    logger.log(u"Checking if image "+cur_file_name+" (type "+str(cur_file_type)+" needs metadata: "+str(need_images[cur_file_type]), logger.DEBUG)
                    
                    if cur_file_type in need_images and need_images[cur_file_type]:
                        logger.log(u"Found an image in the show dir that doesn't exist in the cache, caching it: "+cur_file_name+", type "+str(cur_file_type), logger.DEBUG)
                        self._cache_image_from_file(cur_file_name, cur_file_type, show_obj.tvdbid)
                        need_images[cur_file_type] = False
        except exceptions.ShowDirNotFoundException:
            logger.log(u"Unable to search for images in show dir because it doesn't exist", logger.WARNING)
                    
        # download from TVDB for missing ones
        for cur_image_type in [self.POSTER, self.BANNER]:
            logger.log(u"Seeing if we still need an image of type "+str(cur_image_type)+": "+str(need_images[cur_image_type]), logger.DEBUG)
            if cur_image_type in need_images and need_images[cur_image_type]:
                self._cache_image_from_tvdb(show_obj, cur_image_type)
        

        logger.log(u"Done cache check")
