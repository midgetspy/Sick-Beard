# Author: triion <triion@gmail.com>
# Based on mediabrowser.py by Nic Wolfe <nic@wolfeden.ca>
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

class Mede8erMetadata(generic.GenericMetadata):
    """
    Metadata generation class for Mede8er.
    
    The following file structure is used:
    
    show_root/Series.xml                           (show metadata)
    show_root/folder.jpg                           (poster)
    show_root/fanart.jpg                           (fanart)
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
        
        self.fanart_name = "fanart.jpg"
        self._show_file_name = 'Series.xml'
        self._ep_nfo_extension = 'xml'

        self.name = 'Mede8er'

        self.eg_show_metadata = "Series.xml"
        self.eg_episode_metadata = "Season##\\<i>filename</i>.xml"
        self.eg_fanart = "fanart.jpg"
        self.eg_poster = "folder.jpg"
        self.eg_episode_thumbnails = "Season##\\<i>filename</i>.jpg"
        self.eg_season_thumbnails = "Season##\\folder.jpg"
    
    def get_episode_file_path(self, ep_obj):
        """
        Returns a full show dir/episode.xml path for Mede8er
        episode metadata files
        
        ep_obj: a TVEpisode object to get the path for
        """

        if ek.ek(os.path.isfile, ep_obj.location):
            xml_file_name = helpers.replaceExtension(ek.ek(os.path.basename, ep_obj.location), self._ep_nfo_extension)
            metadata_dir_name = ek.ek(os.path.join, ek.ek(os.path.dirname, ep_obj.location), '')
            xml_file_path = ek.ek(os.path.join, metadata_dir_name, xml_file_name)
        else:
            logger.log(u"Mede8er: Episode location doesn't exist: "+str(ep_obj.location), logger.DEBUG)
            return ''
        
        return xml_file_path

    def get_episode_thumb_path(self, ep_obj):
        """
        Returns a full show dir/episode.jpg path for Mede8er
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
        Season thumbs for Mede8er go in Show Dir/Season X/folder.jpg
        
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
            logger.log(u"Mede8er: Unable to find a season dir for season "+str(season), logger.DEBUG)
            return None

        logger.log(u"Mede8er: Using "+str(season_dir)+"/folder.jpg as season dir for season "+str(season), logger.DEBUG)

        return ek.ek(os.path.join, show_obj.location, season_dir, 'folder.jpg')

    def _show_data(self, show_obj):
        """
        Creates an elementTree XML structure for a Mede8er-style Series.xml
        returns the resulting data object.
        
        show_obj: a TVShow instance to create the XML-NFO for
        """
        
        logger.log("Mede8er: Starting Mede8er _show_data method", logger.MESSAGE)

        tvdb_lang = show_obj.lang
        # There's gotta be a better way of doing this but we don't wanna
        # change the language value elsewhere
        ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

        if tvdb_lang and not tvdb_lang == 'en':
            ltvdb_api_parms['language'] = tvdb_lang

        t = tvdb_api.Tvdb(actors=True, **ltvdb_api_parms)
    
        rootNode = etree.Element("details")
        tv_node = etree.SubElement(rootNode, "movie")
        #tv_node = etree.Element("movie")
        tv_node.attrib["isExtra"] = "false"
        tv_node.attrib["isSet"] = "false"
        tv_node.attrib["isTV"] = "true"

        for ns in XML_NSMAP.keys():
            tv_node.set(ns, XML_NSMAP[ns])
    
        try:
            myShow = t[int(show_obj.tvdbid)]
        except tvdb_exceptions.tvdb_shownotfound:
            logger.log("Mede8er: Unable to find show with id " + str(show_obj.tvdbid) + " on tvdb, skipping it", logger.ERROR)
            raise
    
        except tvdb_exceptions.tvdb_error:
            logger.log("Mede8er: TVDB is down, can't use its data to make the XML-NFO", logger.ERROR)
            raise
    
        # check for title and id
        try:
            if myShow["seriesname"] == None or myShow["seriesname"] == "" or myShow["id"] == None or myShow["id"] == "":
                logger.log("Mede8er: Incomplete info for show with id " + str(show_obj.tvdbid) + " on tvdb, skipping it", logger.ERROR)
                return False
        except tvdb_exceptions.tvdb_attributenotfound:
            logger.log("Mede8er: Incomplete info for show with id " + str(show_obj.tvdbid) + " on tvdb, skipping it", logger.ERROR)
    
            return False
        
        title = etree.SubElement(tv_node, "title")
        if myShow["seriesname"] != None:
            title.text = myShow["seriesname"]    

        tvdbid = etree.SubElement(tv_node, "tvdbid")
        if myShow["id"] != None:
            tvdbid.text = myShow["id"]

        seriesID = etree.SubElement(tv_node, "seriesID")
        if myShow["seriesid"] != None:
            seriesID.text = myShow["seriesid"]

        imdbid = etree.SubElement(tv_node, "imdbid")
        if myShow["imdb_id"] != None:
            imdbid.text = myShow["imdb_id"]

        zap2id = etree.SubElement(tv_node, "zap2itid")
        if myShow["zap2it_id"] != None:
            zap2id.text = myShow["zap2it_id"]

        premiered = etree.SubElement(tv_node, "releasedate")
        if myShow["firstaired"] != None:
            premiered.text = myShow["firstaired"]

        rating = etree.SubElement(tv_node, "rating")
        if myShow["rating"] != None:
            rating.text = myShow["rating"]

        ratingcount = etree.SubElement(tv_node, "ratingcount")
        if myShow["ratingcount"] != None:
            ratingcount.text = myShow["ratingcount"]        
    
        network = etree.SubElement(tv_node, "network")
        if myShow["network"] != None:
            network.text = myShow["network"]

        Runtime = etree.SubElement(tv_node, "runtime")
        if myShow["runtime"] != None:
            Runtime.text = myShow["runtime"]
            
        genre = etree.SubElement(tv_node, "genre")
        if myShow["genre"] != None:
            genre.text = myShow["genre"]  

        #tmpNode = etree.SubElement(tv_node, "myShow")
        #tmpNode.text = str(vars(myShow))
        #logger.log("Printing myShow info: " +  str(vars(myShow)), logger.MESSAGE)
    
        #Actors = etree.SubElement(tv_node, "Actors")
        #if myShow["actors"] != None:
        #    Actors.text = myShow["actors"]
    
        rating = etree.SubElement(tv_node, "certification")
        if myShow["contentrating"] != None:
            rating.text = myShow["contentrating"]
    
        Overview = etree.SubElement(tv_node, "plot")
        if myShow["overview"] != None:
            Overview.text = myShow["overview"]        

        cast = etree.SubElement(tv_node, "cast")
        for actor in myShow['_actors']:
            cast_actor = etree.SubElement(cast, "actor")
            cast_actor.text = actor['name']

        rating = etree.SubElement(tv_node, "Status")
        if myShow["status"] != None:
            rating.text = myShow["status"]

        cover = etree.SubElement(tv_node, "cover")
        poster = etree.SubElement(cover, "name")
        if myShow["poster"] != None:
            poster.text = myShow["poster"]

        backdrop = etree.SubElement(tv_node, "backdrop")
        fanart = etree.SubElement(backdrop, "name")
        if myShow["fanart"] != None:
            fanart.text = myShow["fanart"]
      
        helpers.indentXML(tv_node)

        data = etree.ElementTree(tv_node)

        return data


    def _ep_data(self, ep_obj):
        """
        Creates an elementTree XML structure for a Mede8er style episode.xml
        and returns the resulting data object.
        
        show_obj: a TVShow instance to create the NFO for
        """
        
        logger.log("Mede8er: Starting Mede8er _ep_data method", logger.MESSAGE)

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
            logger.log("Mede8er: Unable to connect to TVDB while creating meta files - skipping - "+ex(e), logger.ERROR)
            return False

        rootNode = etree.Element("movie")

        # Set our namespace correctly
        for ns in XML_NSMAP.keys():
            rootNode.set(ns, XML_NSMAP[ns])
        
        # write an Mede8er XML containing info for all matching episodes
        for curEpToWrite in eps_to_write:
        
            try:
                myEp = myShow[curEpToWrite.season][curEpToWrite.episode]
            except (tvdb_exceptions.tvdb_episodenotfound, tvdb_exceptions.tvdb_seasonnotfound):
                logger.log("Mede8er: Unable to find episode " + str(curEpToWrite.season) + "x" + str(curEpToWrite.episode) + " on tvdb... has it been removed? Should I delete from db?")
                return None
            
            if myEp["firstaired"] == None and ep_obj.season == 0:
                myEp["firstaired"] = str(datetime.date.fromordinal(1))
            
            if myEp["episodename"] == None or myEp["firstaired"] == None:
                return None
                
            if len(eps_to_write) > 1:
                episode = etree.SubElement(rootNode, "Item")
            else:
                episode = rootNode

            #tmpNode = etree.SubElement(episode, "myEp_Season_Show")
            #tmpNode.text = str(vars(myEp.season.show))
            #logger.log("Printing myEp.season info: " +  str(vars(myEp.season.show)), logger.MESSAGE)

            #tmpNode = etree.SubElement(episode, "myCurEp_show")
            #tmpNode.text = str(vars(curEpToWrite.show))
            #logger.log("Printing myCurEp info: " +  str(vars(curEpToWrite.show)), logger.MESSAGE)

            episodeID = etree.SubElement(episode, "tvdbid")
            episodeID.text = str(curEpToWrite.tvdbid)
            
            IMDB_ID = etree.SubElement(episode, "imdbid")
            IMDB_ID.text = myEp.season.show['imdb_id']
            
            title = etree.SubElement(episode, "title")
            if curEpToWrite.show.name != None:
                title.text = curEpToWrite.show.name

            seriesid = etree.SubElement(episode, "seriesid")
            seriesid.text = str(curEpToWrite.show.tvdbid)

            SeasonNumber = etree.SubElement(episode, "season")
            SeasonNumber.text = str(curEpToWrite.season)

            seasonid = etree.SubElement(episode, "seasonid")
            seasonid.text = myEp['seasonid']

            episodenum = etree.SubElement(episode, "EpisodeNumber")
            episodenum.text = str(curEpToWrite.episode)
            
            absolute_number = etree.SubElement(episode, "absolute_number")
            absolute_number.text = myEp['absolute_number']
            
            episodename = etree.SubElement(episode, "episodename")
            if curEpToWrite.name != None:
                episodename.text = curEpToWrite.name
                       
            FirstAired = etree.SubElement(episode, "episodereleasedate")
            if curEpToWrite.airdate != datetime.date.fromordinal(1):
                FirstAired.text = str(curEpToWrite.airdate)
            else:
                FirstAired.text = ''

            startyear = etree.SubElement(episode, "year")
            if curEpToWrite.show.startyear != None:
                startyear.text = str(curEpToWrite.show.startyear)

            EpPlot = etree.SubElement(episode, "episodeplot")
            if curEpToWrite.description != None:
                EpPlot.text = curEpToWrite.description

            plot = etree.SubElement(episode, "plot")
            if curEpToWrite.description != None:
                plot.text = myEp.season.show["overview"]

            genre = etree.SubElement(episode, "genre")
            if myEp.season.show["genre"] != None:
                genre.text = myEp.season.show["genre"]

            rating = etree.SubElement(episode, "certification")
            if myEp.season.show["contentrating"] != None:
                rating.text = myEp.season.show["contentrating"]

            runtime = etree.SubElement(episode, "runtime")
            if myEp.season.show["runtime"] != None:
                runtime.text = myEp.season.show["runtime"]

            cast = etree.SubElement(episode, "actor")
            for actor in myEp.season.show['_actors']:
                cast_actor = etree.SubElement(cast, "name")
                cast_actor.text = actor['name']

            director = etree.SubElement(episode, "director")
            director_text = myEp['director']
            if director_text != None:
                director.text = director_text

            Writer = etree.SubElement(episode, "writer")
            Writer_text = myEp['writer']
            if Writer_text != None:
                Writer.text = Writer_text

            gueststar = etree.SubElement(episode, "gueststars")
            gueststar_text = myEp['gueststars']
            if gueststar_text != None:
                gueststar.text = gueststar_text

            network = etree.SubElement(episode, "network")
            if curEpToWrite.show.network != None:
                network.text = curEpToWrite.show.network

            Language = etree.SubElement(episode, "language")
            Language.text = myEp['language']

            Rating = etree.SubElement(episode, "rating")
            rating_text = myEp['rating']
            if rating_text != None:
                Rating.text = rating_text               
            
            filename = etree.SubElement(episode, "filename")
            if curEpToWrite.location != None:
                filename.text = curEpToWrite.location

            # Make it purdy
            helpers.indentXML(rootNode)
            data = etree.ElementTree(rootNode)

        return data
    
    def retrieveShowMetadata(self, dir):
        return (None, None)

    def write_show_file(self, show_obj):
        """
        Generates and writes show_obj's metadata under the given path to the
        filename given by get_show_file_path()
        Overwritten because of necessary XML declaration for Mede8er
        
        show_obj: TVShow object for which to create the metadata
        
        path: An absolute or relative path where we should put the file. Note that
                the file name will be the default show_file_name.
        """
        
        data = self._show_data(show_obj)
        
        if not data:
            return False
        
        nfo_file_path = self.get_show_file_path(show_obj)
        nfo_file_dir = ek.ek(os.path.dirname, nfo_file_path)

        try:
            if not ek.ek(os.path.isdir, nfo_file_dir):
                logger.log("Mede8er: Metadata dir didn't exist, creating it at "+nfo_file_dir, logger.DEBUG)
                ek.ek(os.makedirs, nfo_file_dir)
                helpers.chmodAsParent(nfo_file_dir)
    
            logger.log(u"Mede8er: Writing show nfo file to "+nfo_file_path)
            
            nfo_file = ek.ek(open, nfo_file_path, 'w')
    
            data.write(nfo_file, encoding="utf-8")
            nfo_file.close()
            helpers.chmodAsParent(nfo_file_path)
        except IOError, e:
            logger.log(u"Mede8er: Unable to write file to "+nfo_file_path+" - are you sure the folder is writable? "+ex(e), logger.ERROR)
            return False
        
        return True

    def write_ep_file(self, ep_obj):
        """
        Generates and writes ep_obj's metadata under the given path with the
        given filename root. Uses the episode's name with the extension in
        _ep_nfo_extension.
        Overwritten because of necessary XML declaration for Mede8er
        
        ep_obj: TVEpisode object for which to create the metadata
        
        file_name_path: The file name to use for this metadata. Note that the extension
                will be automatically added based on _ep_nfo_extension. This should
                include an absolute path.
        """
        
        data = self._ep_data(ep_obj)
        
        if not data:
            return False
        
        nfo_file_path = self.get_episode_file_path(ep_obj)
        nfo_file_dir = ek.ek(os.path.dirname, nfo_file_path)
        
        try:
            if not ek.ek(os.path.isdir, nfo_file_dir):
                logger.log("Mede8er: Metadata dir didn't exist, creating it at "+nfo_file_dir, logger.DEBUG)
                ek.ek(os.makedirs, nfo_file_dir)
                helpers.chmodAsParent(nfo_file_dir)
            
            logger.log(u"Mede8er: Writing episode nfo file to "+nfo_file_path)
            
            nfo_file = ek.ek(open, nfo_file_path, 'w')
    
            data.write(nfo_file, encoding="utf-8")
            nfo_file.close()
            helpers.chmodAsParent(nfo_file_path)
        except IOError, e:
            logger.log(u"Mede8er: Unable to write file to "+nfo_file_path+" - are you sure the folder is writable? "+ex(e), logger.ERROR)
            return False
        
        return True

# present a standard "interface"
metadata_class = Mede8erMetadata
