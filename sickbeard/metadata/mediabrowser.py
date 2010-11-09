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
from sickbeard import encodingKludge as ek
from lib.tvdb_api import tvdb_api, tvdb_exceptions

import xml.etree.cElementTree as etree

class MediaBrowserMetadata(generic.GenericMetadata):
    
    def __init__(self):
        generic.GenericMetadata.__init__(self)
        
        self._ep_nfo_extension = "nfo"

        self.name = 'MediaBrowser'
    
    def _show_data(self, show_obj):
        """
        Creates an elementTree XML structure for a MediaBrowser-style
        returns the resulting data object.
        
        show_obj: a TVShow instance to create the NFO for
        """

        t = tvdb_api.Tvdb(actors=True, **sickbeard.TVDB_API_PARMS)
        
        tv_node = etree.Element("Series")
        for ns in XML_NSMAP.keys():
            tv_node.set(ns, XML_NSMAP[ns])
    
        try:
            myShow = t[int(show_obj.tvdbid)]
        except tvdb_exceptions.tvdb_shownotfound:
            logger.log("Unable to find show with id " + str(show_obj.tvdbid) + " on tvdb, skipping it", logger.ERROR)
            raise
    
        except tvdb_exceptions.tvdb_error:
            logger.log("TVDB is down, can't use its data to add this show", logger.ERROR)
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
        
        # Create metadata directory
        metadata_dir = ek.ek(os.path.join, ek.ek(os.path.dirname, file_name_path), 'metadata')
        if not os.path.exists(metadata_dir):
            ek.ek(os.makedirs, metadata_dir)

        # get the ep file name
        ep_file_name = helpers.replaceExtension(ek.ek(os.path.basename, file_name_path), self._ep_nfo_extension)
        
        # get the full path to the eventual metadata file
        metadata_file_path = ek.ek(os.path.join, ep_file_name)

        logger.log(u"Writing episode xml file to "+metadata_file_path)
        
        metadata_file = open(metadata_file_path, 'w')

        data.write(metadata_file, encoding="utf-8")
        metadata_file.close()
        
        return True

    def _ep_data(self, ep_obj):
        
        eps_to_write = [ep_obj] + ep_obj.relatedEps
        
        shouldSave = False
        try:
            t = tvdb_api.Tvdb(actors=True, **sickbeard.TVDB_API_PARMS)
            myShow = t[self.show.tvdbid]
        except tvdb_exceptions.tvdb_shownotfound, e:
            raise exceptions.ShowNotFoundException(str(e))
        except tvdb_exceptions.tvdb_error, e:
            logger.log("Unable to connect to TVDB while creating meta files - skipping - "+str(e), logger.ERROR)
            return False

        rootNode = etree.Element("Item")

        # Set our namespace correctly
        for ns in XML_NSMAP.keys():
            rootNode.set(ns, XML_NSMAP[ns])
        
        # write an MediaBrowser XML containing info for all matching episodes
        for curEpToWrite in eps_to_write:
        
            try:
                myEp = myShow[curEpToWrite.season][curEpToWrite.episode]
            except (tvdb_exceptions.tvdb_episodenotfound, tvdb_exceptions.tvdb_seasonnotfound):
                logger.log("Unable to find episode " + str(curEpToWrite.season) + "x" + str(curEpToWrite.episode) + " on tvdb... has it been removed? Should I delete from db?")
                return None
            
            if myEp["firstaired"] == None and self.season == 0:
                myEp["firstaired"] = str(datetime.date.fromordinal(1))
            
            if myEp["episodename"] == None or myEp["firstaired"] == None:
                return None
                
            if not needsMediaBrowserXML:
                logger.log("Skipping metadata generation for myself ("+str(self.season)+"x"+str(self.episode)+")", logger.DEBUG)
                continue
            else:
                logger.log("Creating metadata for myself ("+str(self.season)+"x"+str(self.episode)+")", logger.DEBUG)
            
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

            # Make it purdy
            helpers.indentXML(rootNode)
            data = etree.ElementTree(rootNode)

        return data