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


class MediaBrowserMetadata(generic.GenericMetadata):
    """
    Metadata generation class for Media Browser 2.x/3.x - Standard Mode.

    The following file structure is used:

    show_root/series.xml                       (show metadata)
    show_root/folder.jpg                       (poster)
    show_root/backdrop.jpg                     (fanart)
    show_root/Season ##/folder.jpg             (season thumb)
    show_root/Season ##/filename.ext           (*)
    show_root/Season ##/metadata/filename.xml  (episode metadata)
    show_root/Season ##/metadata/filename.jpg  (episode thumb)
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

        self.name = "MediaBrowser"

        self._ep_nfo_extension = "xml"
        self._show_metadata_filename = "series.xml"

        self.fanart_name = "backdrop.jpg"
        self.poster_name = "folder.jpg"

        # web-ui metadata template
        self.eg_show_metadata = "series.xml"
        self.eg_episode_metadata = "Season##\\metadata\\<i>filename</i>.xml"
        self.eg_fanart = "backdrop.jpg"
        self.eg_poster = "folder.jpg"
        self.eg_banner = "banner.jpg"
        self.eg_episode_thumbnails = "Season##\\metadata\\<i>filename</i>.jpg"
        self.eg_season_posters = "Season##\\folder.jpg"
        self.eg_season_banners = "Season##\\banner.jpg"
        self.eg_season_all_poster = "<i>not supported</i>"
        self.eg_season_all_banner = "<i>not supported</i>"

    # Override with empty methods for unsupported features
    def retrieveShowMetadata(self, folder):
        # while show metadata is generated, it is not supported for our lookup
        return (None, None)

    def create_season_all_poster(self, show_obj):
        pass

    def create_season_all_banner(self, show_obj):
        pass

    def get_episode_file_path(self, ep_obj):
        """
        Returns a full show dir/metadata/episode.xml path for MediaBrowser
        episode metadata files

        ep_obj: a TVEpisode object to get the path for
        """

        if ek.ek(os.path.isfile, ep_obj.location):
            xml_file_name = helpers.replaceExtension(ek.ek(os.path.basename, ep_obj.location), self._ep_nfo_extension)
            metadata_dir_name = ek.ek(os.path.join, ek.ek(os.path.dirname, ep_obj.location), 'metadata')
            xml_file_path = ek.ek(os.path.join, metadata_dir_name, xml_file_name)
        else:
            logger.log(u"Episode location doesn't exist: " + str(ep_obj.location), logger.DEBUG)
            return ''

        return xml_file_path

    def get_episode_thumb_path(self, ep_obj):
        """
        Returns a full show dir/metadata/episode.jpg path for MediaBrowser
        episode thumbs.

        ep_obj: a TVEpisode object to get the path from
        """

        if ek.ek(os.path.isfile, ep_obj.location):
            tbn_file_name = helpers.replaceExtension(ek.ek(os.path.basename, ep_obj.location), 'jpg')
            metadata_dir_name = ek.ek(os.path.join, ek.ek(os.path.dirname, ep_obj.location), 'metadata')
            tbn_file_path = ek.ek(os.path.join, metadata_dir_name, tbn_file_name)
        else:
            return None

        return tbn_file_path

    def get_season_poster_path(self, show_obj, season):
        """
        Season thumbs for MediaBrowser go in Show Dir/Season X/folder.jpg

        If no season folder exists, None is returned
        """

        dir_list = [x for x in ek.ek(os.listdir, show_obj.location) if ek.ek(os.path.isdir, ek.ek(os.path.join, show_obj.location, x))]

        season_dir_regex = '^Season\s+(\d+)$'

        season_dir = None

        for cur_dir in dir_list:
            # MediaBrowser 1.x only supports 'Specials'
            # MediaBrowser 2.x looks to only support 'Season 0'
            # MediaBrowser 3.x looks to mimic XBMC/Plex support
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

    def get_season_banner_path(self, show_obj, season):
        """
        Season thumbs for MediaBrowser go in Show Dir/Season X/banner.jpg

        If no season folder exists, None is returned
        """

        dir_list = [x for x in ek.ek(os.listdir, show_obj.location) if ek.ek(os.path.isdir, ek.ek(os.path.join, show_obj.location, x))]

        season_dir_regex = '^Season\s+(\d+)$'

        season_dir = None

        for cur_dir in dir_list:
            # MediaBrowser 1.x only supports 'Specials'
            # MediaBrowser 2.x looks to only support 'Season 0'
            # MediaBrowser 3.x looks to mimic XBMC/Plex support
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

        logger.log(u"Using " + str(season_dir) + "/banner.jpg as season dir for season " + str(season), logger.DEBUG)

        return ek.ek(os.path.join, show_obj.location, season_dir, 'banner.jpg')

    def _show_data(self, show_obj):
        """
        Creates an elementTree XML structure for a MediaBrowser-style series.xml
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

        try:
            myShow = t[int(show_obj.tvdbid)]
        except tvdb_exceptions.tvdb_shownotfound:
            logger.log(u"Unable to find show with id " + str(show_obj.tvdbid) + " on tvdb, skipping it", logger.ERROR)
            raise

        except tvdb_exceptions.tvdb_error:
            logger.log(u"TVDB is down, can't use its data to make the NFO", logger.ERROR)
            raise

        # check for title and id
        try:
            if myShow['seriesname'] == None or myShow['seriesname'] == "" or myShow['id'] == None or myShow['id'] == "":
                logger.log(u"Incomplete info for show with id " + str(show_obj.tvdbid) + " on tvdb, skipping it", logger.ERROR)
                return False
        except tvdb_exceptions.tvdb_attributenotfound:
            logger.log(u"Incomplete info for show with id " + str(show_obj.tvdbid) + " on tvdb, skipping it", logger.ERROR)
            return False

        tvdbid = etree.SubElement(tv_node, "id")
        if myShow['id'] != None:
            tvdbid.text = myShow['id']

        SeriesName = etree.SubElement(tv_node, "SeriesName")
        if myShow['seriesname'] != None:
            SeriesName.text = myShow['seriesname']

        Status = etree.SubElement(tv_node, "Status")
        if myShow['status'] != None:
            Status.text = myShow['status']

        Network = etree.SubElement(tv_node, "Network")
        if myShow['network'] != None:
            Network.text = myShow['network']

        Airs_Time = etree.SubElement(tv_node, "Airs_Time")
        if myShow['airs_time'] != None:
            Airs_Time.text = myShow['airs_time']

        Airs_DayOfWeek = etree.SubElement(tv_node, "Airs_DayOfWeek")
        if myShow['airs_dayofweek'] != None:
            Airs_DayOfWeek.text = myShow['airs_dayofweek']

        FirstAired = etree.SubElement(tv_node, "FirstAired")
        if myShow['firstaired'] != None:
            FirstAired.text = myShow['firstaired']

        ContentRating = etree.SubElement(tv_node, "ContentRating")
        MPAARating = etree.SubElement(tv_node, "MPAARating")
        certification = etree.SubElement(tv_node, "certification")
        if myShow['contentrating'] != None:
            ContentRating.text = myShow['contentrating']
            MPAARating.text = myShow['contentrating']
            certification.text = myShow['contentrating']

        MetadataType = etree.SubElement(tv_node, "Type")
        MetadataType.text = "Series"

        Overview = etree.SubElement(tv_node, "Overview")
        if myShow['overview'] != None:
            Overview.text = myShow['overview']

        PremiereDate = etree.SubElement(tv_node, "PremiereDate")
        if myShow['firstaired'] != None:
            PremiereDate.text = myShow['firstaired']

        Rating = etree.SubElement(tv_node, "Rating")
        if myShow['rating'] != None:
            Rating.text = myShow['rating']

        ProductionYear = etree.SubElement(tv_node, "ProductionYear")
        if myShow['firstaired'] != None:
            try:
                year_text = str(datetime.datetime.strptime(myShow['firstaired'], '%Y-%m-%d').year)
                if year_text:
                    ProductionYear.text = year_text
            except:
                pass

        RunningTime = etree.SubElement(tv_node, "RunningTime")
        Runtime = etree.SubElement(tv_node, "Runtime")
        if myShow['runtime'] != None:
            RunningTime.text = myShow['runtime']
            Runtime.text = myShow['runtime']

        IMDB_ID = etree.SubElement(tv_node, "IMDB_ID")
        IMDB = etree.SubElement(tv_node, "IMDB")
        IMDbId = etree.SubElement(tv_node, "IMDbId")
        if myShow['imdb_id'] != None:
            IMDB_ID.text = myShow['imdb_id']
            IMDB.text = myShow['imdb_id']
            IMDbId.text = myShow['imdb_id']

        Zap2ItId = etree.SubElement(tv_node, "Zap2ItId")
        if myShow['zap2it_id'] != None:
            Zap2ItId.text = myShow['zap2it_id']

        Genres = etree.SubElement(tv_node, "Genres")
        if myShow["genre"] != None:
            for genre in myShow['genre'].split('|'):
                if genre and genre.strip():
                    cur_genre = etree.SubElement(Genres, "Genre")
                    cur_genre.text = genre.strip()

        Genre = etree.SubElement(tv_node, "Genre")
        if myShow["genre"] != None:
            Genre.text = "|".join([x.strip() for x in myShow["genre"].split('|') if x and x.strip()])

        Studios = etree.SubElement(tv_node, "Studios")
        Studio = etree.SubElement(Studios, "Studio")
        if myShow["network"] != None:
            Studio.text = myShow['network']

        Persons = etree.SubElement(tv_node, "Persons")

        if myShow["_actors"] != None:
            for actor in myShow["_actors"]:
                cur_actor_name_text = actor['name']

                if cur_actor_name_text != None and cur_actor_name_text.strip():
                    cur_actor = etree.SubElement(Persons, "Person")
                    cur_actor_name = etree.SubElement(cur_actor, "Name")
                    cur_actor_name.text = cur_actor_name_text.strip()

                    cur_actor_type = etree.SubElement(cur_actor, "Type")
                    cur_actor_type.text = "Actor"

                    cur_actor_role = etree.SubElement(cur_actor, "Role")
                    cur_actor_role_text = actor['role']
                    if cur_actor_role_text != None:
                        cur_actor_role.text = cur_actor_role_text

        helpers.indentXML(tv_node)

        data = etree.ElementTree(tv_node)

        return data

    def _ep_data(self, ep_obj):
        """
        Creates an elementTree XML structure for a MediaBrowser style episode.xml
        and returns the resulting data object.

        show_obj: a TVShow instance to create the NFO for
        """

        eps_to_write = [ep_obj] + ep_obj.relatedEps

        persons_dict = {}
        persons_dict['Director'] = []
        persons_dict['GuestStar'] = []
        persons_dict['Writer'] = []

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

        rootNode = etree.Element("Item")

        # write an MediaBrowser XML containing info for all matching episodes
        for curEpToWrite in eps_to_write:

            try:
                myEp = myShow[curEpToWrite.season][curEpToWrite.episode]
            except (tvdb_exceptions.tvdb_episodenotfound, tvdb_exceptions.tvdb_seasonnotfound):
                logger.log(u"Unable to find episode " + str(curEpToWrite.season) + "x" + str(curEpToWrite.episode) + " on tvdb... has it been removed? Should I delete from db?")
                return None

            if curEpToWrite == ep_obj:
                # root (or single) episode

                # default to today's date for specials if firstaired is not set
                if myEp['firstaired'] == None and ep_obj.season == 0:
                    myEp['firstaired'] = str(datetime.date.fromordinal(1))

                if myEp['episodename'] == None or myEp['firstaired'] == None:
                    return None

                episode = rootNode

                EpisodeName = etree.SubElement(episode, "EpisodeName")
                if curEpToWrite.name != None:
                    EpisodeName.text = curEpToWrite.name
                else:
                    EpisodeName.text = ""

                EpisodeNumber = etree.SubElement(episode, "EpisodeNumber")
                EpisodeNumber.text = str(ep_obj.episode)

                if ep_obj.relatedEps:
                    EpisodeNumberEnd = etree.SubElement(episode, "EpisodeNumberEnd")
                    EpisodeNumberEnd.text = str(curEpToWrite.episode)

                SeasonNumber = etree.SubElement(episode, "SeasonNumber")
                SeasonNumber.text = str(curEpToWrite.season)

                if not ep_obj.relatedEps:
                    absolute_number = etree.SubElement(episode, "absolute_number")
                    absolute_number.text = myEp['absolute_number']

                FirstAired = etree.SubElement(episode, "FirstAired")
                if curEpToWrite.airdate != datetime.date.fromordinal(1):
                    FirstAired.text = str(curEpToWrite.airdate)
                else:
                    FirstAired.text = ""

                MetadataType = etree.SubElement(episode, "Type")
                MetadataType.text = "Episode"

                Overview = etree.SubElement(episode, "Overview")
                if curEpToWrite.description != None:
                    Overview.text = curEpToWrite.description
                else:
                    Overview.text = ""

                if not ep_obj.relatedEps:
                    Rating = etree.SubElement(episode, "Rating")
                    rating_text = myEp['rating']
                    if rating_text != None:
                        Rating.text = rating_text

                    IMDB_ID = etree.SubElement(episode, "IMDB_ID")
                    IMDB = etree.SubElement(episode, "IMDB")
                    IMDbId = etree.SubElement(episode, "IMDbId")
                    if myShow['imdb_id'] != None:
                        IMDB_ID.text = myShow['imdb_id']
                        IMDB.text = myShow['imdb_id']
                        IMDbId.text = myShow['imdb_id']

                TvDbId = etree.SubElement(episode, "TvDbId")
                TvDbId.text = str(curEpToWrite.tvdbid)

                Persons = etree.SubElement(episode, "Persons")

                Language = etree.SubElement(episode, "Language")
                Language.text = myEp['language']

                thumb = etree.SubElement(episode, "filename")
                # TODO: See what this is needed for.. if its still needed
                # just write this to the NFO regardless of whether it actually exists or not
                # note: renaming files after nfo generation will break this, tough luck
                thumb_text = self.get_episode_thumb_path(ep_obj)
                if thumb_text:
                    thumb.text = thumb_text

            else:
                # append data from (if any) related episodes
                EpisodeNumberEnd.text = str(curEpToWrite.episode)

                if curEpToWrite.name:
                    if not EpisodeName.text:
                        EpisodeName.text = curEpToWrite.name
                    else:
                        EpisodeName.text = EpisodeName.text + ", " + curEpToWrite.name

                if curEpToWrite.description:
                    if not Overview.text:
                        Overview.text = curEpToWrite.description
                    else:
                        Overview.text = Overview.text + "\r" + curEpToWrite.description

            # collect all directors, guest stars and writers
            if myEp['director']:
                persons_dict['Director'] += [x.strip() for x in myEp['director'].split('|') if x and x.strip()]
            if myEp['gueststars']:
                persons_dict['GuestStar'] += [x.strip() for x in myEp['gueststars'].split('|') if x and x.strip()]
            if myEp['writer']:
                persons_dict['Writer'] += [x.strip() for x in myEp['writer'].split('|') if x and x.strip()]

        # fill in Persons section with collected directors, guest starts and writers
        for person_type, names in persons_dict.iteritems():
            # remove doubles
            names = list(set(names))
            for cur_name in names:
                Person = etree.SubElement(Persons, "Person")
                cur_person_name = etree.SubElement(Person, "Name")
                cur_person_name.text = cur_name
                cur_person_type = etree.SubElement(Person, "Type")
                cur_person_type.text = person_type

        helpers.indentXML(rootNode)
        data = etree.ElementTree(rootNode)

        return data


# present a standard "interface" from the module
metadata_class = MediaBrowserMetadata
