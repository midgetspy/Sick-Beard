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

import mediabrowser

from sickbeard import logger, exceptions, helpers
from lib.tvdb_api import tvdb_api, tvdb_exceptions
from sickbeard.exceptions import ex

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import elementtree.ElementTree as etree


class Mede8erMetadata(mediabrowser.MediaBrowserMetadata):
    """
    Metadata generation class for Mede8er based on the MediaBrowser.

    The following file structure is used:

    show_root/series.xml                    (show metadata)
    show_root/folder.jpg                    (poster)
    show_root/fanart.jpg                    (fanart)
    show_root/Season ##/folder.jpg          (season thumb)
    show_root/Season ##/filename.ext        (*)
    show_root/Season ##/filename.xml        (episode metadata)
    show_root/Season ##/filename.jpg        (episode thumb)
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

        mediabrowser.MediaBrowserMetadata.__init__(self,
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

        self.name = "Mede8er"

        self.fanart_name = "fanart.jpg"

        # web-ui metadata template
        # self.eg_show_metadata = "series.xml"
        self.eg_episode_metadata = "Season##\\<i>filename</i>.xml"
        self.eg_fanart = "fanart.jpg"
        # self.eg_poster = "folder.jpg"
        # self.eg_banner = "banner.jpg"
        self.eg_episode_thumbnails = "Season##\\<i>filename</i>.jpg"
        # self.eg_season_posters = "Season##\\folder.jpg"
        # self.eg_season_banners = "Season##\\banner.jpg"
        # self.eg_season_all_poster = "<i>not supported</i>"
        # self.eg_season_all_banner = "<i>not supported</i>"

    def get_episode_file_path(self, ep_obj):
        return helpers.replaceExtension(ep_obj.location, self._ep_nfo_extension)

    def get_episode_thumb_path(self, ep_obj):
        return helpers.replaceExtension(ep_obj.location, 'jpg')

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

        rootNode = etree.Element("details")
        tv_node = etree.SubElement(rootNode, "movie")
        tv_node.attrib["isExtra"] = "false"
        tv_node.attrib["isSet"] = "false"
        tv_node.attrib["isTV"] = "true"

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

        SeriesName = etree.SubElement(tv_node, "title")
        if myShow['seriesname'] != None:
            SeriesName.text = myShow['seriesname']
        else:
            SeriesName.text = ""

        Genres = etree.SubElement(tv_node, "genres")
        if myShow["genre"] != None:
            for genre in myShow['genre'].split('|'):
                if genre and genre.strip():
                    cur_genre = etree.SubElement(Genres, "Genre")
                    cur_genre.text = genre.strip()

        FirstAired = etree.SubElement(tv_node, "premiered")
        if myShow['firstaired'] != None:
            FirstAired.text = myShow['firstaired']

        year = etree.SubElement(tv_node, "year")
        if myShow["firstaired"] != None:
            try:
                year_text = str(datetime.datetime.strptime(myShow["firstaired"], '%Y-%m-%d').year)
                if year_text:
                    year.text = year_text
            except:
                pass

        if myShow['rating'] != None:
            try:
                rating = int((float(myShow['rating']) * 10))
            except ValueError:
                rating = 0
            Rating = etree.SubElement(tv_node, "rating")
            rating_text = str(rating)
            if rating_text != None:
                Rating.text = rating_text

        Status = etree.SubElement(tv_node, "status")
        if myShow['status'] != None:
            Status.text = myShow['status']

        mpaa = etree.SubElement(tv_node, "mpaa")
        if myShow["contentrating"] != None:
            mpaa.text = myShow["contentrating"]

        IMDB_ID = etree.SubElement(tv_node, "id")
        if myShow['imdb_id'] != None:
            IMDB_ID.attrib["moviedb"] = "imdb"
            IMDB_ID.text = myShow['imdb_id']

        tvdbid = etree.SubElement(tv_node, "tvdbid")
        if myShow['id'] != None:
            tvdbid.text = myShow['id']

        Runtime = etree.SubElement(tv_node, "runtime")
        if myShow['runtime'] != None:
            Runtime.text = myShow['runtime']

        cast = etree.SubElement(tv_node, "cast")

        if myShow["_actors"] != None:
            for actor in myShow['_actors']:
                cur_actor_name_text = actor['name']

                if cur_actor_name_text != None and cur_actor_name_text.strip():
                    cur_actor = etree.SubElement(cast, "actor")
                    cur_actor.text = cur_actor_name_text.strip()

        helpers.indentXML(rootNode)

        data = etree.ElementTree(rootNode)

        return data

    def _ep_data(self, ep_obj):
        """
        Creates an elementTree XML structure for a MediaBrowser style episode.xml
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
            logger.log(u"Unable to connect to TVDB while creating meta files - skipping - " + ex(e), logger.ERROR)
            return False

        rootNode = etree.Element("details")
        movie = etree.SubElement(rootNode, "movie")

        movie.attrib["isExtra"] = "false"
        movie.attrib["isSet"] = "false"
        movie.attrib["isTV"] = "true"

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

                episode = movie

                EpisodeName = etree.SubElement(episode, "title")
                if curEpToWrite.name != None:
                    EpisodeName.text = curEpToWrite.name
                else:
                    EpisodeName.text = ""

                SeasonNumber = etree.SubElement(episode, "season")
                SeasonNumber.text = str(curEpToWrite.season)

                EpisodeNumber = etree.SubElement(episode, "episode")
                EpisodeNumber.text = str(ep_obj.episode)

                year = etree.SubElement(episode, "year")
                if myShow["firstaired"] != None:
                    try:
                        year_text = str(datetime.datetime.strptime(myShow["firstaired"], '%Y-%m-%d').year)
                        if year_text:
                            year.text = year_text
                    except:
                        pass

                plot = etree.SubElement(episode, "plot")
                if myShow["overview"] != None:
                    plot.text = myShow["overview"]

                Overview = etree.SubElement(episode, "episodeplot")
                if curEpToWrite.description != None:
                    Overview.text = curEpToWrite.description
                else:
                    Overview.text = ""

                mpaa = etree.SubElement(episode, "mpaa")
                if myShow["contentrating"] != None:
                    mpaa.text = myShow["contentrating"]

                if not ep_obj.relatedEps:
                    if myEp["rating"] != None:
                        try:
                            rating = int((float(myEp['rating']) * 10))
                        except ValueError:
                            rating = 0
                        Rating = etree.SubElement(episode, "rating")
                        rating_text = str(rating)
                        if rating_text != None:
                            Rating.text = rating_text

                director = etree.SubElement(episode, "director")
                director_text = myEp['director']
                if director_text != None:
                    director.text = director_text

                credits = etree.SubElement(episode, "credits")
                credits_text = myEp['writer']
                if credits_text != None:
                    credits.text = credits_text

                cast = etree.SubElement(episode, "cast")

                if myShow["_actors"] != None:
                    for actor in myShow['_actors']:
                        cur_actor_name_text = actor['name']

                        if cur_actor_name_text != None and cur_actor_name_text.strip():
                            cur_actor = etree.SubElement(cast, "actor")
                            cur_actor.text = cur_actor_name_text.strip()

            else:
                # append data from (if any) related episodes

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

        helpers.indentXML(rootNode)
        data = etree.ElementTree(rootNode)

        return data


# present a standard "interface" from the module
metadata_class = Mede8erMetadata
