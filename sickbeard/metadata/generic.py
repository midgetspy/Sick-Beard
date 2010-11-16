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

import urllib

import sickbeard

from sickbeard.common import *
from sickbeard import logger, exceptions, helpers
from sickbeard import encodingKludge as ek
from sickbeard.metadata import helpers as metadata_helpers

from lib.tvdb_api import tvdb_api, tvdb_exceptions


from sickbeard import logger
from sickbeard import encodingKludge as ek

class GenericMetadata():
    """
    Base class for all metadata providers. Default behavior is meant to mostly
    follow XBMC metadata standards. Has support for:
    
    - show poster
    - show fanart
    - show metadata file
    - episode thumbnail
    - episode metadata file
    - season thumbnails
    """
    
    def __init__(self):
        self._show_file_name = "tvshow.nfo"
        self._ep_nfo_extension = "nfo"
        
        self.poster_name = "folder.jpg"
        self.fanart_name = "fanart.jpg"

        self.generate_show_metadata = True
        self.generate_ep_metadata = True
        
        self.name = 'Generic'
    
    def get_show_file_path(self, show_obj):
        return ek.ek(os.path.join, show_obj.location, self._show_file_name)

    def get_episode_file_path(self, ep_obj):
        return helpers.replaceExtension(ep_obj.location, self._ep_nfo_extension)

    def get_poster_path(self, show_obj):
        return ek.ek(os.path.join, show_obj.location, self.poster_name)
            
    def get_fanart_path(self, show_obj):
        return ek.ek(os.path.join, show_obj.location, self.fanart_name)
            
    def get_episode_thumb_path(self, ep_obj):
        """
        Returns the path where the episode thumbnail should be stored. Defaults to
        the same path as the episode file but with a .tbn extension.
        
        ep_obj: a TVEpisode instance for which to create the thumbnail
        """
        if ek.ek(os.path.isfile, ep_obj.location):
            tbn_filename = helpers.replaceExtension(ep_obj.location, 'tbn')
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
        
        return ek.ek(os.path.join, show_obj.location, season_thumb_file_path+'.tbn')
    
    def _show_data(self, show_obj):
        """
        This should be overridden by the implementing class. It should
        provide the content of the show metadata file.
        """
        return None
    
    def _ep_data(self, ep_obj):
        """
        This should be overridden by the implementing class. It should
        provide the content of the episode metadata file.
        """
        return None
    
    def write_show_file(self, show_obj):
        """
        Generates and writes show_obj's metadata under the given path to the
        filename given by get_show_file_path()
        
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
        
        nfo_file_path = self.get_show_file_path(show_obj)

        logger.log(u"Writing show nfo file to "+nfo_file_path)
        
        nfo_file = ek.ek(open, nfo_file_path, 'w')

        data.write(nfo_file, encoding="utf-8")
        nfo_file.close()
        
        return True

    def write_ep_file(self, ep_obj):
        """
        Generates and writes ep_obj's metadata under the given path with the
        given filename root. Uses the episode's name with the extension in
        _ep_nfo_extension.
        
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
        
        nfo_file_path = self.get_episode_file_path(ep_obj)
        
        logger.log(u"Writing episode nfo file to "+nfo_file_path)
        
        nfo_file = ek.ek(open, nfo_file_path, 'w')

        data.write(nfo_file, encoding="utf-8")
        nfo_file.close()
        
        return True

    def _get_episode_thumb_url(self, ep_obj):
        """
        Returns the URL to use for downloading an episode's thumbnail. Uses
        theTVDB.com data.
        
        ep_obj: a TVEpisode object for which to grab the thumb URL
        """
        all_eps = [ep_obj] + ep_obj.relatedEps
    
        # get a TVDB object
        try:
            t = tvdb_api.Tvdb(actors=True, **sickbeard.TVDB_API_PARMS)
            tvdb_show_obj = t[ep_obj.show.tvdbid]
        except tvdb_exceptions.tvdb_shownotfound, e:
            raise exceptions.ShowNotFoundException(str(e))
        except tvdb_exceptions.tvdb_error, e:
            logger.log(u"Unable to connect to TVDB while creating meta files - skipping - "+str(e).decode('utf-8'), logger.ERROR)
            return None
    
        # try all included episodes in case some have thumbs and others don't
        for cur_ep in all_eps:
            try:
                myEp = tvdb_show_obj[cur_ep.season][cur_ep.episode]
            except (tvdb_exceptions.tvdb_episodenotfound, tvdb_exceptions.tvdb_seasonnotfound):
                logger.log(u"Unable to find episode " + str(cur_ep.season) + "x" + str(cur_ep.episode) + " on tvdb... has it been removed? Should I delete from db?")
                continue
    
            thumb_url = myEp["filename"]
            
            if thumb_url:
                return thumb_url

        return None
    
    def save_thumbnail(self, ep_obj):
        """
        Retrieves a thumbnail and saves it to the correct spot. This method should not need to
        be overridden by implementing classes, changing get_episode_thumb_path and
        _get_episode_thumb_url should suffice.
        
        ep_obj: a TVEpisode object for which to generate a thumbnail
        """
    
        file_path = self.get_episode_thumb_path(ep_obj)
        
        if not file_path:
            logger.log(u"Unable to find a file path to use for this thumbnail, not generating it", logger.DEBUG)
            return False
    
        thumb_url = self._get_episode_thumb_url(ep_obj)
    
        # if we can't find one then give up
        if not thumb_url:
            logger.log("No thumb is available for this episode, not creating a thumb", logger.DEBUG)
            return False

        thumb_data = metadata_helpers.getShowImage(thumb_url)
        
        result = self._write_image(thumb_data, file_path)

        if not result:
            return False

        for cur_ep in [ep_obj] + ep_obj.relatedEps:
            cur_ep.hastbn = True
    
        return True
    
    def save_fanart(self, show_obj, which=None):
        """
        Downloads a fanart image and saves it to the filename specified by fanart_name
        inside the show's root folder.
        
        show_obj: a TVShow object for which to download fanart 
        """

        # use the default fanart name
        fanart_path = self.get_fanart_path(show_obj)
        
        fanart_data = self._retrieve_show_image('fanart', show_obj, which)

        if not fanart_data:
            logger.log(u"No fanart image was retrieved, unable to write fanart", logger.DEBUG)
            return False

        return self._write_image(fanart_data, fanart_path)


    def save_poster(self, show_obj, which=None):
        """
        Downloads a poster image and saves it to the filename specified by poster_name
        inside the show's root folder.
        
        show_obj: a TVShow object for which to download a poster 
        """

        # use the default poster name
        poster_path = self.get_poster_path(show_obj)
        
        poster_data = self._retrieve_show_image('poster', show_obj, which)

        if not poster_data:
            logger.log(u"No poster image was retrieved, unable to write poster", logger.DEBUG)
            return False

        return self._write_image(poster_data, poster_path)


    def _write_image(self, image_data, image_path):
        """
        Saves the data in image_data to the location image_path. Returns True/False
        to represent success or failure.
        
        image_data: binary image data to write to file
        image_path: file location to save the image to
        """
        
        # don't bother overwriting it
        if ek.ek(os.path.isfile, image_path):
            logger.log(u"Image already exists, not downloading", logger.DEBUG)
            return False
        
        if not image_data:
            logger.log(u"Unable to retrieve image, skipping", logger.WARNING)
            return False

        try:
            outFile = ek.ek(open, image_path, 'wb')
            outFile.write(image_data)
            outFile.close()
        except IOError, e:
            logger.log(u"Unable to write image to "+image_path+" - are you sure the show folder is writable? "+str(e).decode('utf-8'), logger.ERROR)
            return False
    
        return True
    
    def _retrieve_show_image(self, image_type, show_obj, which=None):
        """
        Gets an image URL from theTVDB.com, downloads it and returns the data.
        
        image_type: type of image to retrieve (currently supported: poster, fanart)
        show_obj: a TVShow object to use when searching for the image
        which: optional, a specific numbered poster to look for
        
        Returns: the binary image data if available, or else None
        """

        try:
            t = tvdb_api.Tvdb(banners=True, **sickbeard.TVDB_API_PARMS)
            tvdb_show_obj = t[show_obj.tvdbid]
        except (tvdb_exceptions.tvdb_error, IOError), e:
            logger.log(u"Unable to look up show on TVDB, not downloading images: "+str(e).decode('utf-8'), logger.ERROR)
            return None
    
        if image_type not in ('fanart', 'poster'):
            logger.log(u"Invalid image type "+str(image_type)+", couldn't find it in the TVDB object", logger.ERROR)
            return None
    
        image_url = tvdb_show_obj[image_type]
    
        image_data = metadata_helpers.getShowImage(image_url, which)

        return image_data
    
    def _season_thumb_dict(self, show_obj):
        """
        Should return a dict like:
        
        result = {<season number>: 
                    {1: '<url 1>', 2: <url 2>, ...},}
        """

        # This holds our resulting dictionary of season art
        result = {}
    
        try:
            t = tvdb_api.Tvdb(banners=True, **sickbeard.TVDB_API_PARMS)
            tvdb_show_obj = t[show_obj.tvdbid]
        except (tvdb_exceptions.tvdb_error, IOError), e:
            logger.log(u"Unable to look up show on TVDB, not downloading images: "+str(e).decode('utf-8'), logger.ERROR)
            return result
    
        #  How many seasons?
        num_seasons = len(tvdb_show_obj)
    
        # if we have no season banners then just finish
        if 'season' not in tvdb_show_obj['_banners'] or 'season' not in tvdb_show_obj['_banners']['season']:
            return result
    
        # Give us just the normal poster-style season graphics
        seasonsArtObj = tvdb_show_obj['_banners']['season']['season']
    
        # Returns a nested dictionary of season art with the season
        # number as primary key. It's really overkill but gives the option
        # to present to user via ui to pick down the road.
        for cur_season in range(num_seasons):

            result[cur_season] = {}
            
            # find the correct season in the tvdb object and just copy the dict into our result dict
            for seasonArtID in seasonsArtObj.keys():
                if int(seasonsArtObj[seasonArtID]['season']) == cur_season and seasonsArtObj[seasonArtID]['language'] == 'en':
                    result[cur_season][seasonArtID] = seasonsArtObj[seasonArtID]['_bannerpath']
            
            if len(result[cur_season]) == 0:
                continue

        return result
    
    
    def save_season_thumbs(self, show_obj):
        """
        Saves all season thumbnails to disk for the given show.
        
        show_obj: a TVShow object for which to save the season thumbs
        
        Cycles through all seasons and saves the season thumbs if possible. This
        method should not need to be overridden by implementing classes, changing
        _season_thumb_dict and get_season_thumb_path should be good enough.
        """
    
        season_dict = self._season_thumb_dict(show_obj)
    
        # Returns a nested dictionary of season art with the season
        # number as primary key. It's really overkill but gives the option
        # to present to user via ui to pick down the road.
        for cur_season in season_dict:

            cur_season_art = season_dict[cur_season]
            
            if len(cur_season_art) == 0:
                continue
    
            # Just grab whatever's there for now
            art_id, season_url = cur_season_art.popitem()

            season_thumb_file_path = self.get_season_thumb_path(show_obj, cur_season)
            
            if not season_thumb_file_path:
                logger.log(u"Path for season "+str(cur_season)+" came back blank, skipping this season", logger.DEBUG)
                continue
    
            seasonData = metadata_helpers.getShowImage(season_url)
            
            if not seasonData:
                logger.log(u"No season thumb data available, skipping this season", logger.DEBUG)
                continue
            
            self._write_image(seasonData, season_thumb_file_path)
    
        return True

