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

from sickbeard.common import XML_NSMAP
from sickbeard import logger, exceptions, helpers
from sickbeard.exceptions import ex

from lib.tvdb_api import tvdb_api, tvdb_exceptions

import xml.etree.cElementTree as etree

class XBMCMetadata(generic.GenericMetadata):
    
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
        
        self.name = 'XBMC'

        self.eg_show_metadata = "tvshow.nfo"
        self.eg_episode_metadata = "Season##\\<i>filename</i>.nfo"
        self.eg_fanart = "fanart.jpg"
        self.eg_poster = "folder.jpg"
        self.eg_episode_thumbnails = "Season##\\<i>filename</i>.tbn"
        self.eg_season_thumbnails = "season##.tbn"
    
    def _show_data(self, show_obj):
        """
        Creates an elementTree XML structure for an XBMC-style tvshow.nfo and
        returns the resulting data object.
        
        show_obj: a TVShow instance to create the NFO for
        """

        show_ID = show_obj.tvdbid

        tvdb_lang = show_obj.lang
        # There's gotta be a better way of doing this but we don't wanna
        # change the language value elsewhere
        ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

        if tvdb_lang and not tvdb_lang == 'en':
            ltvdb_api_parms['language'] = tvdb_lang

        t = tvdb_api.Tvdb(actors=True, **ltvdb_api_parms)
    
        tv_node = etree.Element("tvshow")
        for ns in XML_NSMAP.keys():
            tv_node.set(ns, XML_NSMAP[ns])
    
        try:
            myShow = t[int(show_ID)]
        except tvdb_exceptions.tvdb_shownotfound:
            logger.log(u"Unable to find show with id " + str(show_ID) + " on tvdb, skipping it", logger.ERROR)
            raise
    
        except tvdb_exceptions.tvdb_error:
            logger.log(u"TVDB is down, can't use its data to add this show", logger.ERROR)
            raise
    
        # check for title and id
        try:
            if myShow["seriesname"] == None or myShow["seriesname"] == "" or myShow["id"] == None or myShow["id"] == "":
                logger.log(u"Incomplete info for show with id " + str(show_ID) + " on tvdb, skipping it", logger.ERROR)
    
                return False
        except tvdb_exceptions.tvdb_attributenotfound:
            logger.log(u"Incomplete info for show with id " + str(show_ID) + " on tvdb, skipping it", logger.ERROR)
    
            return False
    
        title = etree.SubElement(tv_node, "title")
        if myShow["seriesname"] != None:
            title.text = myShow["seriesname"]
    
        rating = etree.SubElement(tv_node, "rating")
        if myShow["rating"] != None:
            rating.text = myShow["rating"]
    
        plot = etree.SubElement(tv_node, "plot")
        if myShow["overview"] != None:
            plot.text = myShow["overview"]
    
        episodeguide = etree.SubElement(tv_node, "episodeguide")
        episodeguideurl = etree.SubElement( episodeguide, "url")
        episodeguideurl2 = etree.SubElement(tv_node, "episodeguideurl")
        if myShow["id"] != None:
            showurl = sickbeard.TVDB_BASE_URL + '/series/' + myShow["id"] + '/all/en.zip'
            episodeguideurl.text = showurl
            episodeguideurl2.text = showurl
    
        mpaa = etree.SubElement(tv_node, "mpaa")
        if myShow["contentrating"] != None:
            mpaa.text = myShow["contentrating"]
    
        tvdbid = etree.SubElement(tv_node, "id")
        if myShow["id"] != None:
            tvdbid.text = myShow["id"]
    
        genre = etree.SubElement(tv_node, "genre")
        if myShow["genre"] != None:
            genre.text = " / ".join([x for x in myShow["genre"].split('|') if x])
    
        premiered = etree.SubElement(tv_node, "premiered")
        if myShow["firstaired"] != None:
            premiered.text = myShow["firstaired"]
    
        studio = etree.SubElement(tv_node, "studio")
        if myShow["network"] != None:
            studio.text = myShow["network"]
    
        for actor in myShow['_actors']:
    
            cur_actor = etree.SubElement(tv_node, "actor")
    
            cur_actor_name = etree.SubElement( cur_actor, "name")
            cur_actor_name.text = actor['name']
            cur_actor_role = etree.SubElement( cur_actor, "role")
            cur_actor_role_text = actor['role']
    
            if cur_actor_role_text != None:
                cur_actor_role.text = cur_actor_role_text
    
            cur_actor_thumb = etree.SubElement( cur_actor, "thumb")
            cur_actor_thumb_text = actor['image']
    
            if cur_actor_thumb_text != None:
                cur_actor_thumb.text = cur_actor_thumb_text
    
        # Make it purdy
        helpers.indentXML(tv_node)

        data = etree.ElementTree(tv_node)

        return data
    
    def _ep_data(self, ep_obj):
        """
        Creates an elementTree XML structure for an XBMC-style episode.nfo and
        returns the resulting data object.
        
        show_obj: a TVEpisode instance to create the NFO for
        """

        eps_to_write = [ep_obj] + ep_obj.relatedEps

        tvdb_lang = ep_obj.show.lang
        # There's gotta be a better way of doing this but we don't wanna
        # change the language value elsewhere
        ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

        if tvdb_lang and not tvdb_lang == 'en':
            ltvdb_api_parms['language'] = tvdb_lang

        try:
            t = tvdb_api.Tvdb(actors=True, **ltvdb_api_parms)
            myShow = t[ep_obj.show.tvdbid]
        except tvdb_exceptions.tvdb_shownotfound, e:
            raise exceptions.ShowNotFoundException(e.message)
        except tvdb_exceptions.tvdb_error, e:
            logger.log(u"Unable to connect to TVDB while creating meta files - skipping - "+ex(e), logger.ERROR)
            return

        if len(eps_to_write) > 1:
            rootNode = etree.Element( "xbmcmultiepisode" )
        else:
            rootNode = etree.Element( "episodedetails" )

        # Set our namespace correctly
        for ns in XML_NSMAP.keys():
            rootNode.set(ns, XML_NSMAP[ns])

        # write an NFO containing info for all matching episodes
        for curEpToWrite in eps_to_write:

            try:
                myEp = myShow[curEpToWrite.season][curEpToWrite.episode]
            except (tvdb_exceptions.tvdb_episodenotfound, tvdb_exceptions.tvdb_seasonnotfound):
                logger.log(u"Unable to find episode " + str(curEpToWrite.season) + "x" + str(curEpToWrite.episode) + " on tvdb... has it been removed? Should I delete from db?")
                return None

            if not myEp["firstaired"]:
                myEp["firstaired"] = str(datetime.date.fromordinal(1))

            if not myEp["episodename"]:
                logger.log(u"Not generating nfo because the ep has no title", logger.DEBUG)
                return None

            logger.log(u"Creating metadata for episode "+str(ep_obj.season)+"x"+str(ep_obj.episode), logger.DEBUG)

            if len(eps_to_write) > 1:
                episode = etree.SubElement( rootNode, "episodedetails" )
            else:
                episode = rootNode

            title = etree.SubElement( episode, "title" )
            if curEpToWrite.name != None:
                title.text = curEpToWrite.name

            season = etree.SubElement( episode, "season" )
            season.text = str(curEpToWrite.season)

            episodenum = etree.SubElement( episode, "episode" )
            episodenum.text = str(curEpToWrite.episode)

            aired = etree.SubElement( episode, "aired" )
            if curEpToWrite.airdate != datetime.date.fromordinal(1):
                aired.text = str(curEpToWrite.airdate)
            else:
                aired.text = ''

            plot = etree.SubElement( episode, "plot" )
            if curEpToWrite.description != None:
                plot.text = curEpToWrite.description

            displayseason = etree.SubElement( episode, "displayseason" )
            if myEp.has_key('airsbefore_season'):
                displayseason_text = myEp['airsbefore_season']
                if displayseason_text != None:
                    displayseason.text = displayseason_text

            displayepisode = etree.SubElement( episode, "displayepisode" )
            if myEp.has_key('airsbefore_episode'):
                displayepisode_text = myEp['airsbefore_episode']
                if displayepisode_text != None:
                    displayepisode.text = displayepisode_text

            thumb = etree.SubElement( episode, "thumb" )
            thumb_text = myEp['filename']
            if thumb_text != None:
                thumb.text = thumb_text

            watched = etree.SubElement( episode, "watched" )
            watched.text = 'false'

            credits = etree.SubElement( episode, "credits" )
            credits_text = myEp['writer']
            if credits_text != None:
                credits.text = credits_text

            director = etree.SubElement( episode, "director" )
            director_text = myEp['director']
            if director_text != None:
                director.text = director_text

            rating = etree.SubElement( episode, "rating" )
            rating_text = myEp['rating']
            if rating_text != None:
                rating.text = rating_text

            gueststar_text = myEp['gueststars']
            if gueststar_text != None:
                for actor in gueststar_text.split('|'):
                    cur_actor = etree.SubElement( episode, "actor" )
                    cur_actor_name = etree.SubElement(
                        cur_actor, "name"
                        )
                    cur_actor_name.text = actor

            for actor in myShow['_actors']:
                cur_actor = etree.SubElement( episode, "actor" )

                cur_actor_name = etree.SubElement( cur_actor, "name" )
                cur_actor_name.text = actor['name']

                cur_actor_role = etree.SubElement( cur_actor, "role" )
                cur_actor_role_text = actor['role']
                if cur_actor_role_text != None:
                    cur_actor_role.text = cur_actor_role_text

                cur_actor_thumb = etree.SubElement( cur_actor, "thumb" )
                cur_actor_thumb_text = actor['image']
                if cur_actor_thumb_text != None:
                    cur_actor_thumb.text = cur_actor_thumb_text

        #
        # Make it purdy
        helpers.indentXML( rootNode )

        data = etree.ElementTree( rootNode )

        return data

# present a standard "interface" from the module
metadata_class = XBMCMetadata
