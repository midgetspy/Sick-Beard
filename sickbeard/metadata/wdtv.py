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

from sickbeard import logger, exceptions, helpers
from sickbeard import encodingKludge as ek
from lib.tvdb_api import tvdb_api, tvdb_exceptions
from sickbeard.exceptions import ex

import xml.etree.cElementTree as etree

class WDTVMetadata(generic.GenericMetadata):
    """
    Metadata generation class for WDTV

    The following file structure is used:
    
    show_root/folder.jpg                                     (poster)
    show_root/Season 01/folder.jpg                           (season thumb)
    show_root/Season 01/show - 1x01 - episode.metathumb      (episode thumb)
    show_root/Season 01/show - 1x01 - episode.xml            (episode metadata)
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
        
        self._ep_nfo_extension = 'xml'

        self.name = 'WDTV'

        self.eg_show_metadata = "<i>not supported</i>"
        self.eg_episode_metadata = "Season##\\<i>filename</i>.xml"
        self.eg_fanart = "<i>not supported</i>"
        self.eg_poster = "folder.jpg"
        self.eg_episode_thumbnails = "Season##\\<i>filename</i>.metathumb"
        self.eg_season_thumbnails = "Season##\\folder.jpg"
    
    # all of the following are not supported, so do nothing
    def create_show_metadata(self, show_obj):
        pass
    
    def create_fanart(self, show_obj):
        pass
    
    def get_episode_thumb_path(self, ep_obj):
        """
        Returns the path where the episode thumbnail should be stored. Defaults to
        the same path as the episode file but with a .metathumb extension.
        
        ep_obj: a TVEpisode instance for which to create the thumbnail
        """
        if ek.ek(os.path.isfile, ep_obj.location):
            tbn_filename = helpers.replaceExtension(ep_obj.location, 'metathumb')
        else:
            return None

        return tbn_filename
    
    def get_season_thumb_path(self, show_obj, season):
        """
        Season thumbs for WDTV go in Show Dir/Season X/folder.jpg
        
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
        Creates an elementTree XML structure for a WDTV style episode.xml
        and returns the resulting data object.
        
        ep_obj: a TVShow instance to create the NFO for
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

        rootNode = etree.Element("details")

        # write an WDTV XML containing info for all matching episodes
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
                episode = etree.SubElement(rootNode, "details")
            else:
                episode = rootNode
            
            #To do get right EpisodeID
            episodeID = etree.SubElement(episode, "id")
            episodeID.text = str(curEpToWrite.tvdbid)

            title = etree.SubElement(episode, "title")
            title.text = ep_obj.prettyName()

            seriesName = etree.SubElement(episode, "series_name")
            if myShow["seriesname"] != None:
                seriesName.text = myShow["seriesname"]

            episodeName = etree.SubElement(episode, "episode_name")
            if curEpToWrite.name != None:
                episodeName.text = curEpToWrite.name

            seasonNumber = etree.SubElement(episode, "season_number")
            seasonNumber.text = str(curEpToWrite.season)
                
            episodeNum = etree.SubElement(episode, "episode_number")
            episodeNum.text = str(curEpToWrite.episode)
            
            firstAired = etree.SubElement(episode, "firstaired")
            if curEpToWrite.airdate != datetime.date.fromordinal(1):
                firstAired.text = str(curEpToWrite.airdate)

            genre = etree.SubElement(episode, "genre")
            if myShow["genre"] != None:
                genre.text = " / ".join([x for x in myShow["genre"].split('|') if x])

            director = etree.SubElement(episode, "director")
            director_text = myEp['director']
            if director_text != None:
                director.text = director_text

            actor = etree.SubElement(episode, "actor")
            if myShow["actors"] != None:
                actor.text = " / ".join([x for x in myShow["actors"].split('|') if x])

            overview = etree.SubElement(episode, "overview")
            if curEpToWrite.description != None:
                overview.text = curEpToWrite.description

            # Make it purdy
            helpers.indentXML(rootNode)
            data = etree.ElementTree(rootNode)

        return data

    def retrieveShowMetadata(self, dir):
        return (None, None)

# present a standard "interface"
metadata_class = WDTVMetadata
