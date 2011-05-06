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

class JRMCMetadata(generic.GenericMetadata):
    """
    Metadata generation class for JRiver Media Center.
    
    The following file structure is used:
    
    show_root/folder.jpg                                         (poster)
    show_root/backdrop.jpg                                       (fanart)
    show_root/Season 01/folder.jpg                               (season thumb)
    show_root/Season 01/show - 1x01 - episode.avi                (* example of existing ep of course)
    show_root/Season 01/show - 1x01 - episode_avi_JRSidecar.xml  (episode metadata)
    show_root/thumbnails/show - 1x01 - episode.jpg               (episode thumb)
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
        self._ep_nfo_append = '_JRSidecar.xml'

        self.name = 'JRMC'

        self.eg_show_metadata = "<i>not supported</i>"
        self.eg_episode_metadata = "Season##\\<i>filename</i>_<i>ext</i>_JRSidecar.xml"
        self.eg_fanart = "backdrop.jpg"
        self.eg_poster = "folder.jpg"
        self.eg_episode_thumbnails = "Season##\\thumbnails\\<i>filename</i>.jpg"
        self.eg_season_thumbnails = "Season##\\folder.jpg"

    def create_show_metadata(self, show_obj):
        pass
    
    def get_episode_file_path(self, ep_obj):
        """
        Returns a full show dir/metadata/episode.xml path for JRMC
        episode metadata files
        
        ep_obj: a TVEpisode object to get the path for
        """

        if ek.ek(os.path.isfile, ep_obj.location):
            sep_name = ek.ek(os.path.basename, ep_obj.location).rpartition(".")
            xml_file_name = sep_name[0] + "_" + sep_name[2] + self._ep_nfo_append
            metadata_dir_name = ek.ek(os.path.dirname, ep_obj.location)
            xml_file_path = ek.ek(os.path.join, metadata_dir_name, xml_file_name)
        else:
            logger.log(u"Episode location doesn't exist: " + str(ep_obj.location), logger.DEBUG)
            return ''
        
        return xml_file_path

    def get_episode_thumb_path(self, ep_obj):
        """
        Returns a full show dir/thumbnails/episode.jpg path for JRMC
        episode thumbs.
        
        ep_obj: a TVEpisode object to get the path from
        """

        if ek.ek(os.path.isfile, ep_obj.location):
            tbn_file_name = helpers.replaceExtension(ek.ek(os.path.basename, ep_obj.location), 'jpg')
            metadata_dir_name = ek.ek(os.path.join, ek.ek(os.path.dirname, ep_obj.location), 'thumbnails')
            tbn_file_path = ek.ek(os.path.join, metadata_dir_name, tbn_file_name)
        else:
            return None
        
        return tbn_file_path
    
    def get_season_thumb_path(self, show_obj, season):
        """
        Season thumbs for JRMC go in Show Dir/Season X/folder.jpg
        
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

    def _ep_data(self, ep_obj):
        """
        Creates an elementTree XML structure for a JRMC sidecar file
        and returns the resulting data object.
        
        ep_obj: a TVEpisode object to create the sidecar for
        """
        
        tvdb_lang = ep_obj.show.lang
    
        try:
            # There's gotta be a better way of doing this but we don't wanna
            # change the language value elsewhere
            ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

            if tvdb_lang and not tvdb_lang == 'en':
                ltvdb_api_parms['language'] = tvdb_lang

            t = tvdb_api.Tvdb(actors=True, **ltvdb_api_parms)
            my_show = t[ep_obj.show.tvdbid]
        except tvdb_exceptions.tvdb_shownotfound, e:
            raise exceptions.ShowNotFoundException(e.message)
        except tvdb_exceptions.tvdb_error, e:
            logger.log("Unable to connect to TVDB while creating meta files - skipping - " + ex(e), logger.ERROR)
            return False

        rootNode = etree.Element("MPL", {"Version": "2.0", "Title": "JRSidecar"})

        # Set our namespace correctly
        for ns in XML_NSMAP.keys():
            rootNode.set(ns, XML_NSMAP[ns])
        
        try:
            my_ep = my_show[ep_obj.season][ep_obj.episode]
        except (tvdb_exceptions.tvdb_episodenotfound, tvdb_exceptions.tvdb_seasonnotfound):
            logger.log("Unable to find episode " + str(ep_obj.season) + "x" + str(ep_obj.episode) + " on tvdb... has it been removed? Should I delete from db?")
            return None
        
        if my_ep["firstaired"] == None and ep_obj.season == 0:
            my_ep["firstaired"] = str(datetime.date.fromordinal(1))
        
        if my_ep["episodename"] == None or my_ep["firstaired"] == None:
            return None

        episode = etree.SubElement(rootNode, "Item")

        filename = etree.SubElement(episode, "Field", {"Name": "Filename"})
        filename.text = ep_obj.location

        media_sub_type = etree.SubElement(episode, "Field", {"Name": "Media Sub Type"})
        media_sub_type.text = "TV Show"

        ep = etree.SubElement(episode, "Field", {"Name": "Episode"})
        ep.text = str(ep_obj.episode)
        
        director = etree.SubElement(episode, "Field", {"Name": "Director"})
        director_text = my_ep['director']
        if director_text != None:
            director.text = director_text
            
        season = etree.SubElement(episode, "Field", {"Name": "Season"})
        season.text = str(ep_obj.season)
        
        series = etree.SubElement(episode, "Field", {"Name": "Series"})
        if my_show["seriesname"] != None:
            series.text = my_show["seriesname"]
        
        name = etree.SubElement(episode, "Field", {"Name": "Name"})
        if ep_obj.name != None:
            name.text = ep_obj.name
        
        actors = etree.SubElement(episode, "Field", {"Name": "Actors"})
        if my_show["actors"] != None:
            actorText = my_show["actors"].lstrip("|").rstrip("|")
            actorText = actorText.replace("|", "; ")
            actors.text = actorText
            
        description = etree.SubElement(episode, "Field", {"Name": "Description"})
        if ep_obj.description != None:
            description.text = ep_obj.description
            
        image_path = self.get_episode_thumb_path(ep_obj)
        if image_path != None:
            image = etree.SubElement(episode, "Field", {"Name": "Image File"})
            image.text = image_path
        
        if my_ep["firstaired"] != None:
            jrmc_epoch = datetime.date(1899, 12, 30)
            first_aired_str = my_ep["firstaired"]
            first_aired = datetime.datetime.strptime(first_aired_str, "%Y-%m-%d").date()
            delta = first_aired - jrmc_epoch
            date_ = etree.SubElement(episode, "Field", {"Name": "Date"})
            date_.text = str(delta.days)

        # Make it purdy
        helpers.indentXML(rootNode)
        data = etree.ElementTree(rootNode)

        return data
    
    def retrieveShowMetadata(self, dir):
        return (None, None)

# present a standard "interface"
metadata_class = JRMCMetadata
