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

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import elementtree.ElementTree as etree


class WDTVMetadata(generic.GenericMetadata):
    """
    Metadata generation class for WDTV

    The following file structure is used:

    show_root/folder.jpg                    (poster)
    show_root/Season ##/folder.jpg          (season thumb)
    show_root/Season ##/filename.ext        (*)
    show_root/Season ##/filename.metathumb  (episode thumb)
    show_root/Season ##/filename.xml        (episode metadata)
    """

    def __init__(self,
                 show_metadata=False,
                 episode_metadata=False,
                 fanart=False,
                 poster=False,
                 banner=False,
                 episode_thumbnails=False,
                 season_posters=False,
                 season_banners=False,
                 season_all_poster=False,
                 season_all_banner=False):

        generic.GenericMetadata.__init__(self,
                                         show_metadata,
                                         episode_metadata,
                                         fanart,
                                         poster,
                                         banner,
                                         episode_thumbnails,
                                         season_posters,
                                         season_banners,
                                         season_all_poster,
                                         season_all_banner)

        self.name = 'WDTV'

        self._ep_nfo_extension = 'xml'

        self.poster_name = "folder.jpg"

        # web-ui metadata template
        self.eg_show_metadata = "<i>not supported</i>"
        self.eg_episode_metadata = "Season##\\<i>filename</i>.xml"
        self.eg_fanart = "<i>not supported</i>"
        self.eg_poster = "folder.jpg"
        self.eg_banner = "<i>not supported</i>"
        self.eg_episode_thumbnails = "Season##\\<i>filename</i>.metathumb"
        self.eg_season_posters = "Season##\\folder.jpg"
        self.eg_season_banners = "<i>not supported</i>"
        self.eg_season_all_poster = "<i>not supported</i>"
        self.eg_season_all_banner = "<i>not supported</i>"

    # Override with empty methods for unsupported features
    def retrieveShowMetadata(self, folder):
        # no show metadata generated, we abort this lookup function
        return (None, None)

    def create_show_metadata(self, show_obj):
        pass

    def get_show_file_path(self, show_obj):
        pass

    def create_fanart(self, show_obj):
        pass

    def create_banner(self, show_obj):
        pass

    def create_season_banners(self, show_obj):
        pass

    def create_season_all_poster(self, show_obj):
        pass

    def create_season_all_banner(self, show_obj):
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

    def get_season_poster_path(self, show_obj, season):
        """
        Season thumbs for WDTV go in Show Dir/Season X/folder.jpg

        If no season folder exists, None is returned
        """

        dir_list = [x for x in ek.ek(os.listdir, show_obj.location) if ek.ek(os.path.isdir, ek.ek(os.path.join, show_obj.location, x))]

        season_dir_regex = '^Season\s+(\d+)$'

        season_dir = None

        for cur_dir in dir_list:
            if season == 0 and cur_dir == "Specials":
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
            logger.log(u"Unable to find a season dir for season " + str(season), logger.DEBUG)
            return None

        logger.log(u"Using " + str(season_dir) + "/folder.jpg as season dir for season " + str(season), logger.DEBUG)

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
            logger.log(u"Unable to connect to TVDB while creating meta files - skipping - " + ex(e), logger.ERROR)
            return False

        rootNode = etree.Element("details")

        # write an WDTV XML containing info for all matching episodes
        for curEpToWrite in eps_to_write:

            try:
                myEp = myShow[curEpToWrite.season][curEpToWrite.episode]
            except (tvdb_exceptions.tvdb_episodenotfound, tvdb_exceptions.tvdb_seasonnotfound):
                logger.log(u"Unable to find episode " + str(curEpToWrite.season) + "x" + str(curEpToWrite.episode) + " on tvdb... has it been removed? Should I delete from db?")
                return None

            if myEp["firstaired"] is None and ep_obj.season == 0:
                myEp["firstaired"] = str(datetime.date.fromordinal(1))

            if myEp["episodename"] is None or myEp["firstaired"] is None:
                return None

            if len(eps_to_write) > 1:
                episode = etree.SubElement(rootNode, "details")
            else:
                episode = rootNode

            # TODO: get right EpisodeID
            episodeID = etree.SubElement(episode, "id")
            episodeID.text = str(curEpToWrite.tvdbid)

            title = etree.SubElement(episode, "title")
            title.text = ep_obj.prettyName()

            seriesName = etree.SubElement(episode, "series_name")
            if myShow["seriesname"] is not None:
                seriesName.text = myShow["seriesname"]

            episodeName = etree.SubElement(episode, "episode_name")
            if curEpToWrite.name is not None:
                episodeName.text = curEpToWrite.name

            seasonNumber = etree.SubElement(episode, "season_number")
            seasonNumber.text = str(curEpToWrite.season)

            episodeNum = etree.SubElement(episode, "episode_number")
            episodeNum.text = str(curEpToWrite.episode)

            firstAired = etree.SubElement(episode, "firstaired")

            if curEpToWrite.airdate != datetime.date.fromordinal(1):
                firstAired.text = str(curEpToWrite.airdate)

            year = etree.SubElement(episode, "year")
            if myShow["firstaired"] is not None:
                try:
                    year_text = str(datetime.datetime.strptime(myShow["firstaired"], '%Y-%m-%d').year)
                    if year_text:
                        year.text = year_text
                except:
                    pass

            runtime = etree.SubElement(episode, "runtime")
            if curEpToWrite.season != 0:
                if myShow["runtime"] is not None:
                    runtime.text = myShow["runtime"]

            genre = etree.SubElement(episode, "genre")
            if myShow["genre"] is not None:
                genre.text = " / ".join([x.strip() for x in myShow["genre"].split('|') if x and x.strip()])

            director = etree.SubElement(episode, "director")
            director_text = myEp['director']
            if director_text is not None:
                director.text = director_text

            if myShow["_actors"] is not None:
                for actor in myShow["_actors"]:
                    cur_actor_name_text = actor['name']

                    if cur_actor_name_text is not None and cur_actor_name_text.strip():
                        cur_actor = etree.SubElement(episode, "actor")
                        cur_actor_name = etree.SubElement(cur_actor, "name")
                        cur_actor_name.text = cur_actor_name_text.strip()

                        cur_actor_role = etree.SubElement(cur_actor, "role")
                        cur_actor_role_text = actor['role']
                        if cur_actor_role_text is not None:
                            cur_actor_role.text = cur_actor_role_text

            overview = etree.SubElement(episode, "overview")
            if curEpToWrite.description is not None:
                overview.text = curEpToWrite.description

            # Make it purdy
            helpers.indentXML(rootNode)
            data = etree.ElementTree(rootNode)

        return data


# present a standard "interface" from the module
metadata_class = WDTVMetadata
