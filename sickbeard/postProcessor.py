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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import with_statement

import glob
import os
import re
import subprocess

import sickbeard

from sickbeard import db
from sickbeard import classes
from sickbeard import common
from sickbeard import exceptions
from sickbeard import helpers
from sickbeard import history
from sickbeard import logger
from sickbeard import notifiers
from sickbeard import show_name_helpers
from sickbeard import scene_exceptions

from sickbeard import encodingKludge as ek
from sickbeard.exceptions import ex

from sickbeard.name_parser.parser import NameParser, InvalidNameException

from lib.tvdb_api import tvdb_api, tvdb_exceptions


class PostProcessor(object):
    """
    A class which will process a media file according to the post processing settings in the config.
    """

    EXISTS_LARGER = 1
    EXISTS_SAME = 2
    EXISTS_SMALLER = 3
    DOESNT_EXIST = 4

    NZB_NAME = 1
    FOLDER_NAME = 2
    FILE_NAME = 3

    def __init__(self, file_path, nzb_name=None, pp_options={}):
        """
        Creates a new post processor with the given file path and optionally an NZB name.

        file_path: The path to the file to be processed
        nzb_name: The name of the NZB which resulted in this file being downloaded (optional)
        """
        # absolute path to the folder that is being processed
        self.folder_path = ek.ek(os.path.dirname, ek.ek(os.path.abspath, file_path))

        # full path to file
        self.file_path = file_path

        # file name only
        self.file_name = ek.ek(os.path.basename, file_path)

        # the name of the folder only
        self.folder_name = ek.ek(os.path.basename, self.folder_path)

        # name of the NZB that resulted in this folder
        self.nzb_name = nzb_name

        self.force_replace = pp_options.get('force_replace', False)

        self.in_history = False

        self.release_group = None

        self.release_name = None

        self.is_proper = False

        self.log = ''

    def _log(self, message, level=logger.MESSAGE):
        """
        A wrapper for the internal logger which also keeps track of messages and saves them to a string for later.

        message: The string to log (unicode)
        level: The log level to use (optional)
        """
        logger.log(message, level)
        self.log += message + '\n'

    def _checkForExistingFile(self, existing_file):
        """
        Checks if a file exists already and if it does whether it's bigger or smaller than
        the file we are post processing

        existing_file: The file to compare to

        Returns:
            DOESNT_EXIST if the file doesn't exist
            EXISTS_LARGER if the file exists and is larger than the file we are post processing
            EXISTS_SMALLER if the file exists and is smaller than the file we are post processing
            EXISTS_SAME if the file exists and is the same size as the file we are post processing
        """

        if not existing_file:
            self._log(u"There is no existing file", logger.DEBUG)
            return PostProcessor.DOESNT_EXIST

        # if the new file exists, return the appropriate code depending on the size
        if ek.ek(os.path.isfile, existing_file):

            # see if it's bigger than our old file
            if ek.ek(os.path.getsize, existing_file) > ek.ek(os.path.getsize, self.file_path):
                self._log(u"File " + existing_file + " is larger than " + self.file_path, logger.DEBUG)
                return PostProcessor.EXISTS_LARGER

            elif ek.ek(os.path.getsize, existing_file) == ek.ek(os.path.getsize, self.file_path):
                self._log(u"File " + existing_file + " is the same size as " + self.file_path, logger.DEBUG)
                return PostProcessor.EXISTS_SAME

            else:
                self._log(u"File " + existing_file + " is smaller than " + self.file_path, logger.DEBUG)
                return PostProcessor.EXISTS_SMALLER

        else:
            self._log(u"File " + existing_file + " doesn't exist", logger.DEBUG)
            return PostProcessor.DOESNT_EXIST

    def list_associated_files(self, file_path, base_name_only=False):
        """
        For a given file path searches for files with the same name but different extension and returns their absolute paths

        file_path: The file to check for associated files
        base_name_only: False add extra '.' (conservative search) to file_path minus extension
        Returns: A list containing all files which are associated to the given file
        """

        if not file_path:
            return []

        file_path_list = []
        base_name = file_path.rpartition('.')[0]

        if not base_name_only:
            base_name = base_name + '.'

        # don't strip it all and use cwd by accident
        if not base_name:
            return []

        # don't confuse glob with chars we didn't mean to use
        base_name = re.sub(r'[\[\]\*\?]', r'[\g<0>]', base_name)

        for associated_file_path in ek.ek(glob.glob, base_name + '*'):
            # only add associated to list
            if associated_file_path == file_path:
                continue

            if ek.ek(os.path.isfile, associated_file_path):
                file_path_list.append(associated_file_path)

        return file_path_list

    def _delete(self, file_path, associated_files=False):
        """
        Deletes the file and optionally all associated files.

        file_path: The file to delete
        associated_files: True to delete all files which differ only by extension, False to leave them
        """

        if not file_path:
            return

        # figure out which files we want to delete
        file_list = [file_path]
        if associated_files:
            file_list = file_list + self.list_associated_files(file_path, base_name_only=True)

        if not file_list:
            self._log(u"There were no files associated with " + file_path + ", not deleting anything", logger.DEBUG)
            return

        # delete the file and any other files which we want to delete
        for cur_file in file_list:
            if ek.ek(os.path.isfile, cur_file):
                self._log(u"Deleting file " + cur_file, logger.DEBUG)
                ek.ek(os.remove, cur_file)
                # do the library update for synoindex
                notifiers.synoindex_notifier.deleteFile(cur_file)

    def _combined_file_operation(self, file_path, new_path, new_base_name, associated_files=False, action=None):
        """
        Performs a generic operation (move or copy) on a file. Can rename the file as well as change its location,
        and optionally move associated files too.

        file_path: The full path of the media file to act on
        new_path: Destination path where we want to move/copy the file to
        new_base_name: The base filename (no extension) to use during the copy. Use None to keep the same name.
        associated_files: Boolean, whether we should copy similarly-named files too
        action: function that takes an old path and new path and does an operation with them (move/copy)
        """

        if not action:
            self._log(u"Must provide an action for the combined file operation", logger.ERROR)
            return

        file_list = [file_path]
        if associated_files:
            file_list = file_list + self.list_associated_files(file_path)

        if not file_list:
            self._log(u"There were no files associated with " + file_path + ", not moving anything", logger.DEBUG)
            return

        # create base name with file_path (media_file without .extension)
        old_base_name = file_path.rpartition('.')[0]
        old_base_name_length = len(old_base_name)

        # deal with all files
        for cur_file_path in file_list:
            cur_file_name = ek.ek(os.path.basename, cur_file_path)
            # get the extension without .
            cur_extension = cur_file_path[old_base_name_length + 1:]

            # replace .nfo with .nfo-orig to avoid conflicts
            if cur_extension == 'nfo':
                cur_extension = 'nfo-orig'

            # If new base name then convert name
            if new_base_name:
                new_file_name = new_base_name + '.' + cur_extension
            # if we're not renaming we still want to change extensions sometimes
            else:
                new_file_name = helpers.replaceExtension(cur_file_name, cur_extension)

            new_file_path = ek.ek(os.path.join, new_path, new_file_name)

            action(cur_file_path, new_file_path)

    def _move(self, file_path, new_path, new_base_name, associated_files=False):
        """
        file_path: The full path of the media file to move
        new_path: Destination path where we want to move the file to
        new_base_name: The base filename (no extension) to use during the move. Use None to keep the same name.
        associated_files: Boolean, whether we should move similarly-named files too
        """

        def _int_move(cur_file_path, new_file_path):

            self._log(u"Moving file from " + cur_file_path + " to " + new_file_path, logger.DEBUG)
            try:
                helpers.moveFile(cur_file_path, new_file_path)
                helpers.chmodAsParent(new_file_path)
            except (IOError, OSError), e:
                self._log("Unable to move file " + cur_file_path + " to " + new_file_path + ": " + ex(e), logger.ERROR)
                raise e

        self._combined_file_operation(file_path, new_path, new_base_name, associated_files, action=_int_move)

    def _copy(self, file_path, new_path, new_base_name, associated_files=False):
        """
        file_path: The full path of the media file to copy
        new_path: Destination path where we want to copy the file to
        new_base_name: The base filename (no extension) to use during the copy. Use None to keep the same name.
        associated_files: Boolean, whether we should copy similarly-named files too
        """

        def _int_copy(cur_file_path, new_file_path):

            self._log(u"Copying file from " + cur_file_path + " to " + new_file_path, logger.DEBUG)
            try:
                helpers.copyFile(cur_file_path, new_file_path)
                helpers.chmodAsParent(new_file_path)
            except (IOError, OSError), e:
                logger.log(u"Unable to copy file " + cur_file_path + " to " + new_file_path + ": " + ex(e), logger.ERROR)
                raise e

        self._combined_file_operation(file_path, new_path, new_base_name, associated_files, action=_int_copy)

    def _history_lookup(self):
        """
        Look up the NZB name in the history and see if it contains a record for self.nzb_name

        Returns a (tvdb_id, season, [], quality) tuple. tvdb_id, season, quality may be None and episodes may be [].
        """

        to_return = (None, None, [], None)

        # if we don't have either of these then there's nothing to use to search the history for anyway
        if not self.nzb_name and not self.folder_name:
            self.in_history = False
            return to_return

        # make a list of possible names to use in the search
        names = []
        if self.nzb_name:
            names.append(self.nzb_name)
            if '.' in self.nzb_name:
                names.append(self.nzb_name.rpartition(".")[0])
        if self.folder_name:
            names.append(self.folder_name)

        myDB = db.DBConnection()

        # search the database for a possible match and return immediately if we find one
        for curName in names:
            # The underscore character ( _ ) represents a single character to match a pattern from a word or string
            search_name = re.sub("[\.\-\ ]", "_", curName)
            sql_results = myDB.select("SELECT * FROM history WHERE resource LIKE ?", [search_name])

            if len(sql_results) == 0:
                continue

            tvdb_id = int(sql_results[0]["showid"])
            season = int(sql_results[0]["season"])
            quality = int(sql_results[0]["quality"])

            if quality == common.Quality.UNKNOWN:
                quality = None

            self.in_history = True
            to_return = (tvdb_id, season, [], quality)
            self._log("Found result in history: " + str(to_return), logger.DEBUG)

            return to_return

        self.in_history = False
        return to_return

    def _analyze_name(self, name, file_name=True):
        """
        Takes a name and tries to figure out a show, season, and episode from it.

        name: A string which we want to analyze to determine show info from (unicode)

        Returns a (tvdb_id, season, [episodes], quality) tuple. tvdb_id, season, quality may be None and episodes may be [].
        if none were found.
        """

        logger.log(u"Analyzing name " + repr(name))

        to_return = (None, None, [], None)

        if not name:
            return to_return

        name = helpers.remove_non_release_groups(helpers.remove_extension(name))

        # parse the name to break it into show name, season, and episode
        np = NameParser(False)
        parse_result = np.parse(name)
        self._log(u"Parsed " + name + " into " + str(parse_result).decode('utf-8', 'xmlcharrefreplace'), logger.DEBUG)

        if parse_result.air_by_date:
            season = -1
            episodes = [parse_result.air_date]
        else:
            season = parse_result.season_number
            episodes = parse_result.episode_numbers

        to_return = (None, season, episodes, None)

        # do a scene reverse-lookup to get a list of all possible names
        name_list = show_name_helpers.sceneToNormalShowNames(parse_result.series_name)

        if not name_list:
            return (None, season, episodes, None)

        # try finding name in DB
        for cur_name in name_list:
            self._log(u"Looking up " + cur_name + u" in the DB", logger.DEBUG)
            db_result = helpers.searchDBForShow(cur_name)
            if db_result:
                self._log(u"Lookup successful, using tvdb id " + str(db_result[0]), logger.DEBUG)
                self._finalize(parse_result)
                return (int(db_result[0]), season, episodes, None)

        # try finding name in scene exceptions
        for cur_name in name_list:
            self._log(u"Checking scene exceptions for a match on " + cur_name, logger.DEBUG)
            scene_id = scene_exceptions.get_scene_exception_by_name(cur_name)
            if scene_id:
                self._log(u"Scene exception lookup got tvdb id " + str(scene_id) + u", using that", logger.DEBUG)
                self._finalize(parse_result)
                return (scene_id, season, episodes, None)

        # try finding name on TVDB
        for cur_name in name_list:
            try:
                t = tvdb_api.Tvdb(custom_ui=classes.ShowListUI, **sickbeard.TVDB_API_PARMS)

                self._log(u"Looking up name " + cur_name + u" on TVDB", logger.DEBUG)
                showObj = t[cur_name]
            except (tvdb_exceptions.tvdb_exception):
                # if none found, search on all languages
                try:
                    # There's gotta be a better way of doing this but we don't wanna
                    # change the language value elsewhere
                    ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

                    ltvdb_api_parms['search_all_languages'] = True
                    t = tvdb_api.Tvdb(custom_ui=classes.ShowListUI, **ltvdb_api_parms)

                    self._log(u"Looking up name " + cur_name + u" in all languages on TVDB", logger.DEBUG)
                    showObj = t[cur_name]
                except (tvdb_exceptions.tvdb_exception, IOError):
                    pass

                continue
            except (IOError):
                continue

            self._log(u"Lookup successful, using tvdb id " + str(showObj["id"]), logger.DEBUG)
            self._finalize(parse_result)
            return (int(showObj["id"]), season, episodes, None)

        self._finalize(parse_result)
        return to_return

    def _finalize(self, parse_result):
        self.release_group = parse_result.release_group

        # remember whether it's a proper
        self.is_proper = parse_result.is_proper

        # if the result is complete then remember that for later
        if parse_result.series_name and parse_result.season_number is not None and parse_result.episode_numbers and parse_result.release_group:
            if not self.release_name:
                self.release_name = helpers.remove_extension(ek.ek(os.path.basename, parse_result.original_name))

        else:
            logger.log(u"Parse result not sufficient (all following have to be set). will not save release name", logger.DEBUG)
            logger.log(u"Parse result(series_name): " + str(parse_result.series_name), logger.DEBUG)
            logger.log(u"Parse result(season_number): " + str(parse_result.season_number), logger.DEBUG)
            logger.log(u"Parse result(episode_numbers): " + str(parse_result.episode_numbers), logger.DEBUG)
            logger.log(u"Parse result(release_group): " + str(parse_result.release_group), logger.DEBUG)

    def _find_info(self):
        """
        For a given file try to find the showid, season, and episode.
        """

        tvdb_id = season = quality = None
        episodes = []

                        # try to look up the nzb in history
        attempt_list = [self._history_lookup,

                        # try to analyze the nzb name
                        lambda: self._analyze_name(self.nzb_name),

                        # try to analyze the file name
                        lambda: self._analyze_name(self.file_name),

                        # try to analyze the dir name
                        lambda: self._analyze_name(self.folder_name),

                        # try to analyze the file + dir names together
                        lambda: self._analyze_name(self.file_path),

                        # try to analyze the dir + file name together as one name
                        lambda: self._analyze_name(self.folder_name + u' ' + self.file_name)

                        ]

        # attempt every possible method to get our info
        for cur_attempt in attempt_list:

            try:
                (cur_tvdb_id, cur_season, cur_episodes, cur_quality) = cur_attempt()
            except InvalidNameException, e:
                logger.log(u"Unable to parse, skipping: " + ex(e), logger.DEBUG)
                continue

            # if we already did a successful history lookup then keep that tvdb_id value
            if cur_tvdb_id and not (self.in_history and tvdb_id):
                tvdb_id = cur_tvdb_id

            if cur_quality and not (self.in_history and quality):
                quality = cur_quality

            if cur_season is not None:
                season = cur_season

            if cur_episodes:
                episodes = cur_episodes

            # for air-by-date shows we need to look up the season/episode from database
            if season == -1 and tvdb_id and episodes:
                self._log(u"Looks like this is an air-by-date show, attempting to convert the date to season/episode", logger.DEBUG)
                airdate = episodes[0].toordinal()
                myDB = db.DBConnection()
                sql_result = myDB.select("SELECT season, episode FROM tv_episodes WHERE showid = ? and airdate = ?", [tvdb_id, airdate])

                if sql_result:
                    season = int(sql_result[0][0])
                    episodes = [int(sql_result[0][1])]
                else:
                    self._log(u"Unable to find episode with date " + str(episodes[0]) + u" for show " + str(tvdb_id) + u", skipping", logger.DEBUG)
                    # we don't want to leave dates in the episode list if we couldn't convert them to real episode numbers
                    episodes = []
                    continue

            # if there's no season then we can hopefully just use 1 automatically
            elif season == None and tvdb_id:
                myDB = db.DBConnection()
                numseasonsSQlResult = myDB.select("SELECT COUNT(DISTINCT season) as numseasons FROM tv_episodes WHERE showid = ? and season != 0", [tvdb_id])
                if int(numseasonsSQlResult[0][0]) == 1 and season == None:
                    self._log(u"Don't have a season number, but this show appears to only have 1 season, setting seasonnumber to 1...", logger.DEBUG)
                    season = 1

            if tvdb_id and season and episodes:
                return (tvdb_id, season, episodes, quality)

        return (tvdb_id, season, episodes, quality)

    def _get_ep_obj(self, tvdb_id, season, episodes):
        """
        Retrieve the TVEpisode object requested.

        tvdb_id: The TVDBID of the show (int)
        season: The season of the episode (int)
        episodes: A list of episodes to find (list of ints)

        If the episode(s) can be found then a TVEpisode object with the correct related eps will
        be instantiated and returned. If the episode can't be found then None will be returned.
        """

        show_obj = None

        self._log(u"Loading show object for tvdb_id " + str(tvdb_id), logger.DEBUG)
        # find the show in the showlist
        try:
            show_obj = helpers.findCertainShow(sickbeard.showList, tvdb_id)
        except exceptions.MultipleShowObjectsException:
            raise  # TODO: later I'll just log this, for now I want to know about it ASAP

        # if we can't find the show then there's nothing we can really do
        if not show_obj:
            error_msg = u"This show isn't in your list, you need to add it to SB before post-processing an episode"
            self._log(error_msg, logger.ERROR)
            raise exceptions.PostProcessingFailed(error_msg)

        root_ep = None
        for cur_episode in episodes:
            episode = int(cur_episode)

            self._log(u"Retrieving episode object for " + str(season) + "x" + str(episode), logger.DEBUG)

            # now that we've figured out which episode this file is just load it manually
            try:
                curEp = show_obj.getEpisode(season, episode)
            except exceptions.EpisodeNotFoundException, e:
                error_msg = u"Unable to create episode: " + ex(e)
                self._log(error_msg, logger.DEBUG)
                raise exceptions.PostProcessingFailed(error_msg)

            # associate all the episodes together under a single root episode
            if root_ep == None:
                root_ep = curEp
                root_ep.relatedEps = []
            elif curEp not in root_ep.relatedEps:
                root_ep.relatedEps.append(curEp)

        return root_ep

    def _get_quality(self, ep_obj):
        """
        Determines the quality of the file that is being post processed by parsing through the data available.

        ep_obj: The TVEpisode object related to the file we are post processing

        Returns: A quality value found in common.Quality
        """

        ep_quality = common.Quality.UNKNOWN

        # nzb name is the most reliable if it exists, followed by folder name and lastly file name
        name_list = [self.nzb_name, self.folder_name, self.file_name]

        # search all possible names for our new quality, in case the file or dir doesn't have it
        for cur_name in name_list:

            # some stuff might be None at this point still
            if not cur_name:
                continue

            ep_quality = common.Quality.nameQuality(cur_name)
            self._log(u"Looking up quality for name " + cur_name + u", got " + common.Quality.qualityStrings[ep_quality], logger.DEBUG)

            # if we find a good one then use it
            if ep_quality != common.Quality.UNKNOWN:
                logger.log(cur_name + u" looks like it has quality " + common.Quality.qualityStrings[ep_quality] + ", using that", logger.DEBUG)
                return ep_quality

        # Try getting quality from the episode (snatched) status
        if ep_obj.status in common.Quality.SNATCHED + common.Quality.SNATCHED_PROPER:
            oldStatus, ep_quality = common.Quality.splitCompositeStatus(ep_obj.status)  # @UnusedVariable
            if ep_quality != common.Quality.UNKNOWN:
                self._log(u"The old status had a quality in it, using that: " + common.Quality.qualityStrings[ep_quality], logger.DEBUG)
                return ep_quality

        # Try guessing quality from the file name
        ep_quality = common.Quality.assumeQuality(self.file_name)
        self._log(u"Guessing quality for name " + self.file_name + u", got " + common.Quality.qualityStrings[ep_quality], logger.DEBUG)
        if ep_quality != common.Quality.UNKNOWN:
            logger.log(self.file_name + u" looks like it has quality " + common.Quality.qualityStrings[ep_quality] + ", using that", logger.DEBUG)
            return ep_quality

        return ep_quality

    def _run_extra_scripts(self, ep_obj):
        """
        Executes any extra scripts defined in the config.

        ep_obj: The object to use when calling the extra script
        """
        for curScriptName in sickbeard.EXTRA_SCRIPTS:

            # generate a safe command line string to execute the script and provide all the parameters
            try:
                script_cmd = [piece for piece in re.split("( |\\\".*?\\\"|'.*?')", curScriptName) if piece.strip()]

                script_cmd = script_cmd + [ep_obj.location.encode(sickbeard.SYS_ENCODING),
                                           self.file_path.encode(sickbeard.SYS_ENCODING),
                                           str(ep_obj.show.tvdbid),
                                           str(ep_obj.season),
                                           str(ep_obj.episode),
                                           str(ep_obj.airdate)
                                           ]

                # use subprocess to run the command and capture output
                self._log(u"Executing command " + str(script_cmd))

                p = subprocess.Popen(script_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=sickbeard.PROG_DIR)
                out, err = p.communicate()  # @UnusedVariable
                self._log(u"Script result: " + str(out), logger.DEBUG)

            except Exception, e:
                self._log(u"Unable to run extra_script: " + ex(e))

    def _safe_replace(self, ep_obj, new_ep_quality):
        """
        Determines if the new episode can safely replace old episode.
        Episodes which are expected (snatched) or larger than the existing episode are priority, others are not.

        ep_obj: The TVEpisode object in question
        new_ep_quality: The quality of the episode that is being processed

        Returns: True if the episode can safely replace old episode, False otherwise.
        """

        # if SB snatched this then assume it's safe
        if ep_obj.status in common.Quality.SNATCHED + common.Quality.SNATCHED_PROPER:
            self._log(u"Sick Beard snatched this episode, marking it safe to replace", logger.DEBUG)
            return True

        old_ep_status, old_ep_quality = common.Quality.splitCompositeStatus(ep_obj.status)

        # if old episode is not downloaded/archived then it's safe
        if old_ep_status != common.DOWNLOADED and old_ep_status != common.ARCHIVED:
            self._log(u"Existing episode status is not downloaded/archived, marking it safe to replace", logger.DEBUG)
            return True

        if old_ep_status == common.ARCHIVED:
            self._log(u"Existing episode status is archived, marking it unsafe to replace", logger.DEBUG)
            return False

        # Status downloaded. Quality/ size checks

        # if manual post process option is set to force_replace then it's safe
        if self.force_replace:
            self._log(u"Processed episode is set to force replace existing episode, marking it safe to replace", logger.DEBUG)
            return True

        # if the file processed is higher quality than the existing episode then it's safe
        if new_ep_quality > old_ep_quality:
            if new_ep_quality != common.Quality.UNKNOWN:
                self._log(u"Existing episode status is not snatched but processed episode appears to be better quality than existing episode, marking it safe to replace", logger.DEBUG)
                return True

            else:
                self._log(u"Episode already exists in database and processed episode has unknown quality, marking it unsafe to replace", logger.DEBUG)
                return False

        # if there's an existing downloaded file with same quality, check filesize to decide
        if new_ep_quality == old_ep_quality:
            self._log(u"Episode already exists in database and has same quality as processed episode", logger.DEBUG)

            # check for an existing file
            self._log(u"Checking size of existing file: " + ep_obj.location, logger.DEBUG)
            existing_file_status = self._checkForExistingFile(ep_obj.location)

            if existing_file_status in (PostProcessor.EXISTS_LARGER, PostProcessor.EXISTS_SAME):
                self._log(u"File exists and new file is same/smaller, marking it unsafe to replace", logger.DEBUG)
                return False

            elif existing_file_status == PostProcessor.EXISTS_SMALLER:
                self._log(u"File exists and new file is larger, marking it safe to replace", logger.DEBUG)
                return True

            elif existing_file_status == PostProcessor.DOESNT_EXIST:
                if not ek.ek(os.path.isdir, ep_obj.show._location) and not sickbeard.CREATE_MISSING_SHOW_DIRS:
                    self._log(u"File and Show location doesn't exist, marking it unsafe to replace", logger.DEBUG)
                    return False

                else:
                    self._log(u"File doesn't exist, marking it safe to replace", logger.DEBUG)
                    return True

            else:
                self._log(u"Unknown file status for: " + ep_obj.location + "This should never happen, please log this as a bug.", logger.ERROR)
                return False

        # if there's an existing file with better quality
        if new_ep_quality < old_ep_quality and old_ep_quality != common.Quality.UNKNOWN:
            self._log(u"Episode already exists in database and processed episode has lower quality, marking it unsafe to replace", logger.DEBUG)
            return False

        self._log(u"None of the conditions were met, marking it unsafe to replace", logger.DEBUG)

        return False

    def process(self):
        """
        Post-process a given file
        """

        self._log(u"Processing " + self.file_path + " (" + str(self.nzb_name) + ")")

        if ek.ek(os.path.isdir, self.file_path):
            self._log(u"File " + self.file_path + " seems to be a directory")
            return False

        # reset per-file stuff
        self.in_history = False

        # try to find the file info
        (tvdb_id, season, episodes, quality) = self._find_info()

        # if we don't have it then give up
        if not tvdb_id or season == None or not episodes:
            self._log(u"Not enough information to determine what episode this is", logger.DEBUG)
            self._log(u"Quitting post-processing", logger.DEBUG)
            return False

        # retrieve/create the corresponding TVEpisode objects
        ep_obj = self._get_ep_obj(tvdb_id, season, episodes)

        # get the quality of the episode we're processing
        if quality:
            self._log(u"Snatch history had a quality in it, using that: " + common.Quality.qualityStrings[quality], logger.DEBUG)
            new_ep_quality = quality
        else:
            new_ep_quality = self._get_quality(ep_obj)

        logger.log(u"Quality of the processing episode: " + str(new_ep_quality), logger.DEBUG)

        # see if it's safe to replace existing episode (is download snatched, PROPER, better quality)
        safe_replace = self._safe_replace(ep_obj, new_ep_quality)

        # if it's not safe to replace, stop here
        if not safe_replace:
            self._log(u"Quitting post-processing", logger.DEBUG)
            return False

        # if the file is safe to replace then we're going to replace it even if it exists
        else:
            self._log(u"This download is marked as safe to replace existing file", logger.DEBUG)

        # delete the existing file (and company)
        for cur_ep in [ep_obj] + ep_obj.relatedEps:
            try:
                self._delete(cur_ep.location, associated_files=True)
                # clean up any left over folders
                if cur_ep.location:
                    helpers.delete_empty_folders(ek.ek(os.path.dirname, cur_ep.location), keep_dir=ep_obj.show._location)
            except (OSError, IOError):
                raise exceptions.PostProcessingFailed(u"Unable to delete the existing files")

        # if the show directory doesn't exist then make it if allowed
        if not ek.ek(os.path.isdir, ep_obj.show._location) and sickbeard.CREATE_MISSING_SHOW_DIRS:
            self._log(u"Show directory doesn't exist, creating it", logger.DEBUG)
            try:
                ek.ek(os.mkdir, ep_obj.show._location)
                # do the library update for synoindex
                notifiers.synoindex_notifier.addFolder(ep_obj.show._location)

            except (OSError, IOError):
                raise exceptions.PostProcessingFailed(u"Unable to create the show directory: " + ep_obj.show._location)

            # get metadata for the show (but not episode because it hasn't been fully processed)
            ep_obj.show.writeMetadata(True)

        # update the ep info before we rename so the quality & release name go into the name properly
        for cur_ep in [ep_obj] + ep_obj.relatedEps:

            if self.release_name:
                self._log("Found release name " + self.release_name, logger.DEBUG)
                cur_ep.release_name = self.release_name
            else:
                cur_ep.release_name = ""

            cur_ep.status = common.Quality.compositeStatus(common.DOWNLOADED, new_ep_quality)

        # find the destination folder
        try:
            proper_path = ep_obj.proper_path()
            proper_absolute_path = ek.ek(os.path.join, ep_obj.show.location, proper_path)
            dest_path = ek.ek(os.path.dirname, proper_absolute_path)

        except exceptions.ShowDirNotFoundException:
            raise exceptions.PostProcessingFailed(u"Unable to post-process an episode if the show dir doesn't exist, quitting")

        self._log(u"Destination folder for this episode: " + dest_path, logger.DEBUG)

        # create any folders we need
        if not helpers.make_dirs(dest_path):
            raise exceptions.PostProcessingFailed(u"Unable to create destination folder: " + dest_path)

        # figure out the base name of the resulting episode file
        if sickbeard.RENAME_EPISODES:
            orig_extension = self.file_name.rpartition('.')[-1]
            new_base_name = ek.ek(os.path.basename, proper_path)
            new_file_name = new_base_name + '.' + orig_extension

        else:
            # if we're not renaming then there's no new base name, we'll just use the existing name
            new_base_name = None
            new_file_name = self.file_name

        try:
            # move the episode and associated files to the show dir
            if sickbeard.KEEP_PROCESSED_DIR:
                self._copy(self.file_path, dest_path, new_base_name, sickbeard.MOVE_ASSOCIATED_FILES)
            else:
                self._move(self.file_path, dest_path, new_base_name, sickbeard.MOVE_ASSOCIATED_FILES)
        except (OSError, IOError):
            raise exceptions.PostProcessingFailed(u"Unable to move the files to destination folder: " + dest_path)

        # put the new location in the database
        for cur_ep in [ep_obj] + ep_obj.relatedEps:
            with cur_ep.lock:
                cur_ep.location = ek.ek(os.path.join, dest_path, new_file_name)
                cur_ep.saveToDB()

        # log it to history
        history.logDownload(ep_obj, self.file_path, new_ep_quality, self.release_group)

        # send notifications
        notifiers.notify_download(ep_obj.prettyName())

        # generate nfo/tbn
        ep_obj.createMetaFiles()
        ep_obj.saveToDB()

        # do the library update for XBMC
        notifiers.xbmc_notifier.update_library(ep_obj.show.name)

        # do the library update for Plex
        notifiers.plex_notifier.update_library()

        # do the library update for NMJ
        # nmj_notifier kicks off its library update when the notify_download is issued (inside notifiers)

        # do the library update for Synology Indexer
        notifiers.synoindex_notifier.addFile(ep_obj.location)

        # do the library update for pyTivo
        notifiers.pytivo_notifier.update_library(ep_obj)

        # do the library update for Trakt
        notifiers.trakt_notifier.update_library(ep_obj)

        self._run_extra_scripts(ep_obj)

        return True
