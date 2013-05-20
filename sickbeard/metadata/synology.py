# Author: Frans Kool <big_cabbage@hotmail.com>
# Created for Synology NAS, based on mediabrowser
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
import os
import re

import sickbeard

import generic

from sickbeard.common import XML_NSMAP
from sickbeard import logger, exceptions, helpers
from sickbeard import encodingKludge as ek
from lib.tvdb_api import tvdb_api, tvdb_exceptions
from sickbeard.exceptions import ex

import xml.etree.cElementTree as etree

class SynologyMetadata(generic.GenericMetadata):
    """
    Metadata generation class for Synology. All xml formatting and
    file naming information was contributed by users in the following
    ticket's comments:
    
    http://code.google.com/p/sickbeard/issues/detail?id=311
    
    The following file structure is used:
    
    show_root/series.xml                           (show metadata)
    show_root/folder.jpg                           (poster)
    show_root/backdrop.jpg                         (fanart)
    show_root/Season 01/folder.jpg                 (season thumb)
    show_root/Season 01/show - 1x01 - episode.avi  (* example of existing ep of course)
    show_root/Season 01/show - 1x01 - episode.xml  (episode metadata)
    show_root/Season 01/show - 1x01 - episode.jpg  (episode thumb)
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
        
        self.fanart_name = "backdrop.jpg"
        self._show_file_name = 'series.xml'
        self._ep_nfo_extension = 'xml'

        self.name = 'Synology'

        self.eg_show_metadata = "series.xml"
        self.eg_episode_metadata = "Season##\\<i>filename</i>.xml"
        self.eg_fanart = "backdrop.jpg"
        self.eg_poster = "folder.jpg"
        self.eg_episode_thumbnails = "Season##\\<i>filename</i>.jpg"
        self.eg_season_thumbnails = "Season##\\folder.jpg"
    
    def get_episode_file_path(self, ep_obj):
        """
        Returns a full show dir/episode.xml path for Synology
        episode metadata files
        
        ep_obj: a TVEpisode object to get the path for
        """

        if ek.ek(os.path.isfile, ep_obj.location):
            xml_file_name = helpers.replaceExtension(ek.ek(os.path.basename, ep_obj.location), self._ep_nfo_extension)
            metadata_dir_name = ek.ek(os.path.join, ek.ek(os.path.dirname, ep_obj.location), '')
            xml_file_path = ek.ek(os.path.join, metadata_dir_name, xml_file_name)
        else:
            logger.log(u"Episode location doesn't exist: "+str(ep_obj.location), logger.DEBUG)
            return ''
        
        return xml_file_path

    def get_episode_thumb_path(self, ep_obj):
        """
        Returns a full show dir/episode.jpg path for Synology
        episode thumbs.
        
        ep_obj: a TVEpisode object to get the path from
        """

        if ek.ek(os.path.isfile, ep_obj.location):
            tbn_file_name = helpers.replaceExtension(ek.ek(os.path.basename, ep_obj.location), 'jpg')
            metadata_dir_name = ek.ek(os.path.join, ek.ek(os.path.dirname, ep_obj.location), '')
            tbn_file_path = ek.ek(os.path.join, metadata_dir_name, tbn_file_name)
        else:
            return None
        
        return tbn_file_path
    
    def get_season_thumb_path(self, show_obj, season):
        """
        Season thumbs for Synology go in Show Dir/Season X/folder.jpg
        
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

    def _show_data(self, show_obj):
        """
        Creates an elementTree XML structure for a Synology-style series.xml
        returns the resulting data object.
        
        show_obj: a TVShow instance to create the NFO for
        """

        tvdb_lang = show_obj.lang
        # There's gotta be a better way of doing this but we don't wanna
        # change the language value elsewhere
        ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

        if tvdb_lang and not tvdb_lang == 'en':
            ltvdb_api_parms['language'] = tvdb_lang

        t = tvdb_api.Tvdb(actors=True, **ltvdb_api_parms)
    
        tv_node = etree.Element("Series")
        for ns in XML_NSMAP.keys():
            tv_node.set(ns, XML_NSMAP[ns])
    
        try:
            myShow = t[int(show_obj.tvdbid)]
        except tvdb_exceptions.tvdb_shownotfound:
            logger.log("Unable to find show with id " + str(show_obj.tvdbid) + " on tvdb, skipping it", logger.ERROR)
            raise
    
        except tvdb_exceptions.tvdb_error:
            logger.log("TVDB is down, can't use its data to make the NFO", logger.ERROR)
            raise
    
        # check for title and id
        try:
            if myShow["seriesname"] == None or myShow["seriesname"] == "" or myShow["id"] == None or myShow["id"] == "":
                logger.log("Incomplete info for show with id " + str(show_obj.tvdbid) + " on tvdb, skipping it", logger.ERROR)
                return False
        except tvdb_exceptions.tvdb_attributenotfound:
            logger.log("Incomplete info for show with id " + str(show_obj.tvdbid) + " on tvdb, skipping it", logger.ERROR)
    
            return False
        
        tvdbid = etree.SubElement(tv_node, "id")
        if myShow["id"] != None:
            tvdbid.text = myShow["id"]
    
        Actors = etree.SubElement(tv_node, "Actors")
        if myShow["actors"] != None:
            Actors.text = myShow["actors"]
    
        ContentRating = etree.SubElement(tv_node, "ContentRating")
        if myShow["contentrating"] != None:
            ContentRating.text = myShow["contentrating"]
    
        premiered = etree.SubElement(tv_node, "FirstAired")
        if myShow["firstaired"] != None:
            premiered.text = myShow["firstaired"]
    
        genre = etree.SubElement(tv_node, "genre")
        if myShow["genre"] != None:
            genre.text = myShow["genre"]  
    
        IMDBId = etree.SubElement(tv_node, "IMDBId")
        if myShow["imdb_id"] != None:
            IMDBId.text = myShow["imdb_id"]
    
        IMDB_ID = etree.SubElement(tv_node, "IMDB_ID")
        if myShow["imdb_id"] != None:
            IMDB_ID.text = myShow["imdb_id"]        
    
        Overview = etree.SubElement(tv_node, "Overview")
        if myShow["overview"] != None:
            Overview.text = myShow["overview"]
            
        Network = etree.SubElement(tv_node, "Network")
        if myShow["network"] != None:
            Network.text = myShow["network"]
            
        Runtime = etree.SubElement(tv_node, "Runtime")
        if myShow["runtime"] != None:
            Runtime.text = myShow["runtime"]
    
            
        Rating = etree.SubElement(tv_node, "Rating")
        if myShow["rating"] != None:
            Rating.text = myShow["rating"]
    
        SeriesID = etree.SubElement(tv_node, "SeriesID")
        if myShow["seriesid"] != None:
            SeriesID.text = myShow["seriesid"]
    
        SeriesName = etree.SubElement(tv_node, "SeriesName")
        if myShow["seriesname"] != None:
            SeriesName.text = myShow["seriesname"]        
            
        rating = etree.SubElement(tv_node, "Status")
        if myShow["status"] != None:
            rating.text = myShow["status"]
      
        helpers.indentXML(tv_node)

        data = etree.ElementTree(tv_node)

        return data


    def _ep_data(self, ep_obj):
        """
        Creates an elementTree XML structure for a Synology style episode.xml
        and returns the resulting data object.
        
        show_obj: a TVShow instance to create the NFO for
        """
        
        eps_to_write = [ep_obj] + ep_obj.relatedEps
        
        tvdb_lang = ep_obj.show.lang
    
        try:
            # There's gotta be a better way of doing this but we don't wanna
            # change the language value elsewhere
            ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

            if tvdb_lang and not tvdb_lang == 'en':
                ltvdb_api_parms['language'] = tvdb_lang

            t = tvdb_api.Tvdb(actors=True, **ltvdb_api_parms)
            myShow = t[ep_obj.show.tvdbid]
        except tvdb_exceptions.tvdb_shownotfound, e:
            raise exceptions.ShowNotFoundException(e.message)
        except tvdb_exceptions.tvdb_error, e:
            logger.log("Unable to connect to TVDB while creating meta files - skipping - "+ex(e), logger.ERROR)
            return False

        rootNode = etree.Element("Item")

        # Set our namespace correctly
        for ns in XML_NSMAP.keys():
            rootNode.set(ns, XML_NSMAP[ns])
        
        # write an Synology XML containing info for all matching episodes
        for curEpToWrite in eps_to_write:
        
            try:
                myEp = myShow[curEpToWrite.season][curEpToWrite.episode]
            except (tvdb_exceptions.tvdb_episodenotfound, tvdb_exceptions.tvdb_seasonnotfound):
                logger.log("Unable to find episode " + str(curEpToWrite.season) + "x" + str(curEpToWrite.episode) + " on tvdb... has it been removed? Should I delete from db?")
                return None
            
            if myEp["firstaired"] == None and ep_obj.season == 0:
                myEp["firstaired"] = str(datetime.date.fromordinal(1))
            
            if myEp["episodename"] == None or myEp["firstaired"] == None:
                return None
                
            if len(eps_to_write) > 1:
                episode = etree.SubElement(rootNode, "Item")
            else:
                episode = rootNode

            ID = etree.SubElement(episode, "ID")
            ID.text = str(curEpToWrite.episode)

            #To do get right EpisodeID
            episodeID = etree.SubElement(episode, "EpisodeID")
            episodeID.text = str(curEpToWrite.tvdbid)

            title = etree.SubElement(episode, "EpisodeName")
            if curEpToWrite.name != None:
                title.text = curEpToWrite.name
                
            episodenum = etree.SubElement(episode, "EpisodeNumber")
            episodenum.text = str(curEpToWrite.episode)
            
            FirstAired = etree.SubElement(episode, "FirstAired")
            if curEpToWrite.airdate != datetime.date.fromordinal(1):
                FirstAired.text = str(curEpToWrite.airdate)
            else:
                FirstAired.text = ''

            Overview = etree.SubElement(episode, "Overview")
            if curEpToWrite.description != None:
                Overview.text = curEpToWrite.description

            DVD_chapter = etree.SubElement(episode, "DVD_chapter")
            DVD_chapter.text = ''

            DVD_discid = etree.SubElement(episode, "DVD_discid")
            DVD_discid.text = ''

            DVD_episodenumber = etree.SubElement(episode, "DVD_episodenumber")
            DVD_episodenumber.text = ''

            DVD_season = etree.SubElement(episode, "DVD_season")
            DVD_season.text = ''

            director = etree.SubElement(episode, "Director")
            director_text = myEp['director']
            if director_text != None:
                director.text = director_text

            gueststar = etree.SubElement(episode, "GuestStars")
            gueststar_text = myEp['gueststars']
            if gueststar_text != None:
                gueststar.text = gueststar_text

            IMDB_ID = etree.SubElement(episode, "IMDB_ID")
            IMDB_ID.text = myEp['imdb_id']

            Language = etree.SubElement(episode, "Language")
            Language.text = myEp['language']

            ProductionCode = etree.SubElement(episode, "ProductionCode")
            ProductionCode.text = myEp['productioncode']

            Rating = etree.SubElement(episode, "Rating")
            rating_text = myEp['rating']
            if rating_text != None:
                Rating.text = rating_text

            Writer = etree.SubElement(episode, "Writer")
            Writer_text = myEp['writer']
            if Writer_text != None:
                Writer.text = Writer_text
                
            SeasonNumber = etree.SubElement(episode, "SeasonNumber")
            SeasonNumber.text = str(curEpToWrite.season)

            absolute_number = etree.SubElement(episode, "absolute_number")
            absolute_number.text = myEp['absolute_number']

            seasonid = etree.SubElement(episode, "seasonid")
            seasonid.text = myEp['seasonid']
            
            seriesid = etree.SubElement(episode, "seriesid")
            seriesid.text = str(curEpToWrite.show.tvdbid)
  
            thumb = etree.SubElement(episode, "filename")
            
            # just write this to the NFO regardless of whether it actually exists or not
            # note: renaming files after nfo generation will break this, tough luck
            thumb_text = self.get_episode_thumb_path(ep_obj)
            if thumb_text:
                thumb.text = thumb_text

            # Make it purdy
            helpers.indentXML(rootNode)
            data = etree.ElementTree(rootNode)

        return data
    
    def retrieveShowMetadata(self, dir):
        return (None, None)

# present a standard "interface"
metadata_class = SynologyMetadata
