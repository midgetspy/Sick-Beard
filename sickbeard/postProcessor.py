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
import shlex
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

    def __init__(self, file_path, nzb_name = None):
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
    
        self.in_history = False
        self.release_group = None
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
            self._log(u"There is no existing file so there's no worries about replacing it", logger.DEBUG)
            return PostProcessor.DOESNT_EXIST
    
        # if the new file exists, return the appropriate code depending on the size
        if ek.ek(os.path.isfile, existing_file):
    
            # see if it's bigger than our old file
            if ek.ek(os.path.getsize, existing_file) > ek.ek(os.path.getsize, self.file_path):
                self._log(u"File "+existing_file+" is larger than "+self.file_path, logger.DEBUG)
                return PostProcessor.EXISTS_LARGER

            elif ek.ek(os.path.getsize, existing_file) == ek.ek(os.path.getsize, self.file_path):
                self._log(u"File "+existing_file+" is the same size as "+self.file_path, logger.DEBUG)
                return PostProcessor.EXISTS_SAME
    
            else:
                self._log(u"File "+existing_file+" is smaller than "+self.file_path, logger.DEBUG)
                return PostProcessor.EXISTS_SMALLER
    
        else:
            self._log(u"File "+existing_file+" doesn't exist so there's no worries about replacing it", logger.DEBUG)
            return PostProcessor.DOESNT_EXIST

    def _list_associated_files(self, file_path):
        """
        For a given file path searches for files with the same name but different extension and returns them.
        
        file_path: The file to check for associated files
        
        Returns: A list containing all files which are associated to the given file
        """
    
        if not file_path:
            return []

        file_path_list = []
    
        base_name = file_path.rpartition('.')[0]+'.'
        
        # don't confuse glob with chars we didn't mean to use
        base_name = re.sub(r'[\[\]\*\?]', r'[\g<0>]', base_name)
    
        for associated_file_path in ek.ek(glob.glob, base_name+'*'):
            # only list it if the only non-shared part is the extension
            if '.' in associated_file_path[len(base_name):]:
                continue

            file_path_list.append(associated_file_path)
        
        return file_path_list

    def _delete(self, file_path, associated_files=False):
        """
        Deletes the file and optionall all associated files.
        
        file_path: The file to delete
        associated_files: True to delete all files which differ only by extension, False to leave them
        """
        
        if not file_path:
            return
        
        # figure out which files we want to delete
        if associated_files:
            file_list = self._list_associated_files(file_path)
        else:
            file_list = [file_path]

        if not file_list:
            self._log(u"There were no files associated with "+file_path+", not deleting anything", logger.DEBUG)
            return
        
        # delete the file and any other files which we want to delete
        for cur_file in file_list:
            self._log(u"Deleting file "+cur_file, logger.DEBUG)
            if ek.ek(os.path.isfile, cur_file):
                ek.ek(os.remove, cur_file)
                
    def _combined_file_operation (self, file_path, new_path, new_base_name, associated_files=False, action=None):
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

        if associated_files:
            file_list = self._list_associated_files(file_path)
        else:
            file_list = [file_path]

        if not file_list:
            self._log(u"There were no files associated with "+file_path+", not moving anything", logger.DEBUG)
            return
        
        for cur_file_path in file_list:

            cur_file_name = ek.ek(os.path.basename, cur_file_path)
            
            # get the extension
            cur_extension = cur_file_path.rpartition('.')[-1]
        
            # replace .nfo with .nfo-orig to avoid conflicts
            if cur_extension == 'nfo':
                cur_extension = 'nfo-orig'

            # If new base name then convert name
            if new_base_name:
                new_file_name = new_base_name +'.' + cur_extension
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

            self._log(u"Moving file from "+cur_file_path+" to "+new_file_path, logger.DEBUG)
            try:
                helpers.moveFile(cur_file_path, new_file_path)
                helpers.chmodAsParent(new_file_path)
            except (IOError, OSError), e:
                self._log("Unable to move file "+cur_file_path+" to "+new_file_path+": "+ex(e), logger.ERROR)
                raise e
                
        self._combined_file_operation(file_path, new_path, new_base_name, associated_files, action=_int_move)
                
    def _copy(self, file_path, new_path, new_base_name, associated_files=False):
        """
        file_path: The full path of the media file to copy
        new_path: Destination path where we want to copy the file to 
        new_base_name: The base filename (no extension) to use during the copy. Use None to keep the same name.
        associated_files: Boolean, whether we should copy similarly-named files too
        """

        def _int_copy (cur_file_path, new_file_path):

            self._log(u"Copying file from "+cur_file_path+" to "+new_file_path, logger.DEBUG)
            try:
                helpers.copyFile(cur_file_path, new_file_path)
                helpers.chmodAsParent(new_file_path)
            except (IOError, OSError), e:
                logger.log("Unable to copy file "+cur_file_path+" to "+new_file_path+": "+ex(e), logger.ERROR)
                raise e

        self._combined_file_operation(file_path, new_path, new_base_name, associated_files, action=_int_copy)

    def _find_ep_destination_folder(self, ep_obj):
        """
        Finds the final folder where the episode should go. If season folders are enabled
        and an existing season folder can be found then it is used, otherwise a new one
        is created in accordance with the config settings. If season folders aren't enabled
        then this function should simply return the show dir.
        
        ep_obj: The TVEpisode object to figure out the location for 
        """
        
        # if we're supposed to put it in a season folder then figure out what folder to use
        season_folder = ''
        if ep_obj.show.seasonfolders:
    
            # search the show dir for season folders
            for curDir in ek.ek(os.listdir, ep_obj.show.location):
    
                if not ek.ek(os.path.isdir, ek.ek(os.path.join, ep_obj.show.location, curDir)):
                    continue
    
                # if it's a season folder, check if it's the one we want
                match = re.match(".*season\s*(\d+)", curDir, re.IGNORECASE)
                if match:
                    # if it's the correct season folder then stop looking
                    if int(match.group(1)) == int(ep_obj.season):
                        season_folder = curDir
                        break
    
            # if we couldn't find the right one then just use the season folder defaut format
            if season_folder == '':
                # for air-by-date shows use the year as the season folder
                if ep_obj.show.air_by_date:
                    season_folder = str(ep_obj.airdate.year)
                else:
                    try:
                        season_folder = sickbeard.SEASON_FOLDERS_FORMAT % (ep_obj.season)
                    except TypeError:
                        logger.log(u"Error: Your season folder format is incorrect, try setting it back to the default")
        
        dest_folder = ek.ek(os.path.join, ep_obj.show.location, season_folder)
        
        return dest_folder

    def _history_lookup(self):
        """
        Look up the NZB name in the history and see if it contains a record for self.nzb_name
        
        Returns a (tvdb_id, season, []) tuple. The first two may be None if none were found.
        """
        
        to_return = (None, None, [])
        
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
            sql_results = myDB.select("SELECT * FROM history WHERE resource LIKE ?", [re.sub("[\.\-\ ]", "_", curName)])
    
            if len(sql_results) == 0:
                continue
    
            tvdb_id = int(sql_results[0]["showid"])
            season = int(sql_results[0]["season"])

            self.in_history = True
            to_return = (tvdb_id, season, [])
            self._log("Found result in history: "+str(to_return), logger.DEBUG)
            return to_return
        
        self.in_history = False
        return to_return
    
    def _analyze_name(self, name, file=True):
        """
        Takes a name and tries to figure out a show, season, and episode from it.
        
        name: A string which we want to analyze to determine show info from (unicode)
        
        Returns a (tvdb_id, season, [episodes]) tuple. The first two may be None and episodes may be []
        if none were found.
        """

        logger.log(u"Analyzing name "+repr(name))
    
        to_return = (None, None, [])
    
        if not name:
            return to_return
    
        # parse the name to break it into show name, season, and episode
        np = NameParser(file)
        parse_result = np.parse(name)
        self._log("Parsed "+name+" into "+str(parse_result).decode('utf-8'), logger.DEBUG)

        if parse_result.air_by_date:
            season = -1
            episodes = [parse_result.air_date]
        else:
            season = parse_result.season_number
            episodes = parse_result.episode_numbers 

        to_return = (None, season, episodes)
    
        # do a scene reverse-lookup to get a list of all possible names
        name_list = show_name_helpers.sceneToNormalShowNames(parse_result.series_name)

        if not name_list:
            return (None, season, episodes)
        
        def _finalize(parse_result):
            self.release_group = parse_result.release_group
            if parse_result.extra_info:
                self.is_proper = re.search('(^|[\. _-])(proper|repack)([\. _-]|$)', parse_result.extra_info, re.I) != None
        
        # for each possible interpretation of that scene name
        for cur_name in name_list:
            self._log(u"Checking scene exceptions for a match on "+cur_name, logger.DEBUG)
            scene_id = scene_exceptions.get_scene_exception_by_name(cur_name)
            if scene_id:
                self._log(u"Scene exception lookup got tvdb id "+str(scene_id)+u", using that", logger.DEBUG)
                _finalize(parse_result)
                return (scene_id, season, episodes)

        # see if we can find the name directly in the DB, if so use it
        for cur_name in name_list:
            self._log(u"Looking up "+cur_name+u" in the DB", logger.DEBUG)
            db_result = helpers.searchDBForShow(cur_name)
            if db_result:
                self._log(u"Lookup successful, using tvdb id "+str(db_result[0]), logger.DEBUG)
                _finalize(parse_result)
                return (int(db_result[0]), season, episodes)
        
        # see if we can find the name with a TVDB lookup
        for cur_name in name_list:
            try:
                t = tvdb_api.Tvdb(custom_ui=classes.ShowListUI, **sickbeard.TVDB_API_PARMS)
    
                self._log(u"Looking up name "+cur_name+u" on TVDB", logger.DEBUG)
                showObj = t[cur_name]
            except (tvdb_exceptions.tvdb_exception):
                # if none found, search on all languages
                try:
                    # There's gotta be a better way of doing this but we don't wanna
                    # change the language value elsewhere
                    ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

                    ltvdb_api_parms['search_all_languages'] = True
                    t = tvdb_api.Tvdb(custom_ui=classes.ShowListUI, **ltvdb_api_parms)

                    self._log(u"Looking up name "+cur_name+u" in all languages on TVDB", logger.DEBUG)
                    showObj = t[cur_name]
                except (tvdb_exceptions.tvdb_exception, IOError):
                    pass

                continue
            except (IOError):
                continue
            
            self._log(u"Lookup successful, using tvdb id "+str(showObj["id"]), logger.DEBUG)
            _finalize(parse_result)
            return (int(showObj["id"]), season, episodes)
    
        _finalize(parse_result)
        return to_return
    
    
    def _find_info(self):
        """
        For a given file try to find the showid, season, and episode.
        """
    
        tvdb_id = season = None
        episodes = []
        
                        # try to look up the nzb in history
        attempt_list = [self._history_lookup,
    
                        # try to analyze the episode name
                        lambda: self._analyze_name(self.file_path),

                        # try to analyze the file name
                        lambda: self._analyze_name(self.file_name),

                        # try to analyze the dir name
                        lambda: self._analyze_name(self.folder_name),

                        # try to analyze the file+dir names together
                        lambda: self._analyze_name(self.file_path),

                        # try to analyze the nzb name
                        lambda: self._analyze_name(self.nzb_name),
                        ]
    
        # attempt every possible method to get our info
        for cur_attempt in attempt_list:
            
            try:
                (cur_tvdb_id, cur_season, cur_episodes) = cur_attempt()
            except InvalidNameException, e:
                logger.log(u"Unable to parse, skipping: "+ex(e), logger.DEBUG)
                continue
            
            # if we already did a successful history lookup then keep that tvdb_id value
            if cur_tvdb_id and not (self.in_history and tvdb_id):
                tvdb_id = cur_tvdb_id
            if cur_season != None:
                season = cur_season
            if cur_episodes:
                episodes = cur_episodes
            
            # for air-by-date shows we need to look up the season/episode from tvdb
            if season == -1 and tvdb_id and episodes:
                self._log(u"Looks like this is an air-by-date show, attempting to convert the date to season/episode", logger.DEBUG)
                
                # try to get language set for this show
                tvdb_lang = None
                try:
                    showObj = helpers.findCertainShow(sickbeard.showList, tvdb_id)
                    if(showObj != None):
                        tvdb_lang = showObj.lang
                except exceptions.MultipleShowObjectsException:
                    raise #TODO: later I'll just log this, for now I want to know about it ASAP

                try:
                    # There's gotta be a better way of doing this but we don't wanna
                    # change the language value elsewhere
                    ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

                    if tvdb_lang and not tvdb_lang == 'en':
                        ltvdb_api_parms['language'] = tvdb_lang

                    t = tvdb_api.Tvdb(**ltvdb_api_parms)
                    epObj = t[tvdb_id].airedOn(episodes[0])[0]
                    season = int(epObj["seasonnumber"])
                    episodes = [int(epObj["episodenumber"])]
                    self._log(u"Got season "+str(season)+" episodes "+str(episodes), logger.DEBUG)
                except tvdb_exceptions.tvdb_episodenotfound, e:
                    self._log(u"Unable to find episode with date "+str(episodes[0])+u" for show "+str(tvdb_id)+u", skipping", logger.DEBUG)

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
            
            if tvdb_id and season != None and episodes:
                return (tvdb_id, season, episodes)
    
        return (tvdb_id, season, episodes)
    
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

        self._log(u"Loading show object for tvdb_id "+str(tvdb_id), logger.DEBUG)
        # find the show in the showlist
        try:
            show_obj = helpers.findCertainShow(sickbeard.showList, tvdb_id)
        except exceptions.MultipleShowObjectsException:
            raise #TODO: later I'll just log this, for now I want to know about it ASAP

        # if we can't find the show then there's nothing we can really do
        if not show_obj:
            self._log(u"This show isn't in your list, you need to add it to SB before post-processing an episode", logger.ERROR)
            raise exceptions.PostProcessingFailed()

        root_ep = None
        for cur_episode in episodes:
            episode = int(cur_episode)
    
            self._log(u"Retrieving episode object for " + str(season) + "x" + str(episode), logger.DEBUG)
    
            # now that we've figured out which episode this file is just load it manually
            try:
                curEp = show_obj.getEpisode(season, episode)
            except exceptions.EpisodeNotFoundException, e:
                self._log(u"Unable to create episode: "+ex(e), logger.DEBUG)
                raise exceptions.PostProcessingFailed()
    
            # associate all the episodes together under a single root episode
            if root_ep == None:
                root_ep = curEp
                root_ep.relatedEps = []
            else:
                root_ep.relatedEps.append(curEp)
        
        return root_ep
    
    def _get_quality(self, ep_obj):
        """
        Determines the quality of the file that is being post processed, first by checking if it is directly
        available in the TVEpisode's status or otherwise by parsing through the data available.
        
        ep_obj: The TVEpisode object related to the file we are post processing
        
        Returns: A quality value found in common.Quality
        """
        
        ep_quality = common.Quality.UNKNOWN

        # if there is a quality available in the status then we don't need to bother guessing from the filename
        if ep_obj.status in common.Quality.SNATCHED + common.Quality.SNATCHED_PROPER:
            oldStatus, ep_quality = common.Quality.splitCompositeStatus(ep_obj.status) #@UnusedVariable
            if ep_quality != common.Quality.UNKNOWN:
                self._log(u"The old status had a quality in it, using that: "+common.Quality.qualityStrings[ep_quality], logger.DEBUG)
                return ep_quality

        # nzb name is the most reliable if it exists, followed by folder name and lastly file name
        name_list = [self.nzb_name, self.folder_name, self.file_name]
    
        # search all possible names for our new quality, in case the file or dir doesn't have it
        for cur_name in name_list:
            
            # some stuff might be None at this point still
            if not cur_name:
                continue

            ep_quality = common.Quality.nameQuality(cur_name)
            self._log(u"Looking up quality for name "+cur_name+u", got "+common.Quality.qualityStrings[ep_quality], logger.DEBUG)
            
            # if we find a good one then use it
            if ep_quality != common.Quality.UNKNOWN:
                logger.log(cur_name+u" looks like it has quality "+common.Quality.qualityStrings[ep_quality]+", using that", logger.DEBUG)
                return ep_quality

        # if we didn't get a quality from one of the names above, try assuming from each of the names
        ep_quality = common.Quality.assumeQuality(self.file_name)
        self._log(u"Guessing quality for name "+self.file_name+u", got "+common.Quality.qualityStrings[ep_quality], logger.DEBUG)
        if ep_quality != common.Quality.UNKNOWN:
            logger.log(self.file_name+u" looks like it has quality "+common.Quality.qualityStrings[ep_quality]+", using that", logger.DEBUG)
            return ep_quality
        
        return ep_quality
    
    def _run_extra_scripts(self, ep_obj):
        """
        Executes any extra scripts defined in the config.
        
        ep_obj: The object to use when calling the extra script
        """
        for curScriptName in sickbeard.EXTRA_SCRIPTS:
            
            # generate a safe command line string to execute the script and provide all the parameters
            script_cmd = shlex.split(curScriptName) + [ep_obj.location, self.file_path, str(ep_obj.show.tvdbid), str(ep_obj.season), str(ep_obj.episode), str(ep_obj.airdate)]
            
            # use subprocess to run the command and capture output
            self._log(u"Executing command "+str(script_cmd))
            self._log(u"Absolute path to script: "+ek.ek(os.path.abspath, script_cmd[0]), logger.DEBUG)
            try:
                p = subprocess.Popen(script_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=sickbeard.PROG_DIR)
                out, err = p.communicate() #@UnusedVariable
                self._log(u"Script result: "+str(out), logger.DEBUG)
            except OSError, e:
                self._log(u"Unable to run extra_script: "+ex(e))
    
    def _is_priority(self, ep_obj, new_ep_quality):
        """
        Determines if the episode is a priority download or not (if it is expected). Episodes which are expected
        (snatched) or larger than the existing episode are priority, others are not.
        
        ep_obj: The TVEpisode object in question
        new_ep_quality: The quality of the episode that is being processed
        
        Returns: True if the episode is priority, False otherwise.
        """
        
        # if SB downloaded this on purpose then this is a priority download
        if self.in_history or ep_obj.status in common.Quality.SNATCHED + common.Quality.SNATCHED_PROPER:
            self._log(u"SB snatched this episode so I'm marking it as priority", logger.DEBUG)
            return True
        
        # if the user downloaded it manually and it's higher quality than the existing episode then it's priority
        if new_ep_quality > ep_obj and new_ep_quality != common.Quality.UNKNOWN:
            self._log(u"This was manually downloaded but it appears to be better quality than what we have so I'm marking it as priority", logger.DEBUG)
            return True
        
        # if the user downloaded it manually and it appears to be a PROPER/REPACK then it's priority
        old_ep_status, old_ep_quality = common.Quality.splitCompositeStatus(ep_obj.status) #@UnusedVariable
        if self.is_proper and new_ep_quality >= old_ep_quality:
            self._log(u"This was manually downloaded but it appears to be a proper so I'm marking it as priority", logger.DEBUG)
            return True 
        
        return False
    
    def process(self):
        """
        Post-process a given file
        """
        
        self._log(u"Processing "+self.file_path+" ("+str(self.nzb_name)+")")
        
        if os.path.isdir( self.file_path ):
            self._log(u"File "+self.file_path+" seems to be a directory")
            return False
        # reset per-file stuff
        self.in_history = False
        
        # try to find the file info
        (tvdb_id, season, episodes) = self._find_info()
        
        # if we don't have it then give up
        if not tvdb_id or season == None or not episodes:
            return False
        
        # retrieve/create the corresponding TVEpisode objects
        ep_obj = self._get_ep_obj(tvdb_id, season, episodes)
        
        # get the quality of the episode we're processing
        new_ep_quality = self._get_quality(ep_obj)
        logger.log(u"Quality of the episode we're processing: "+str(new_ep_quality), logger.DEBUG)
        
        # see if this is a priority download (is it snatched, in history, or PROPER)
        priority_download = self._is_priority(ep_obj, new_ep_quality) 
        self._log(u"Is ep a priority download: "+str(priority_download), logger.DEBUG)
        
        # set the status of the episodes
        for curEp in [ep_obj] + ep_obj.relatedEps:
            curEp.status = common.Quality.compositeStatus(common.SNATCHED, new_ep_quality)
        
        # check for an existing file
        existing_file_status = self._checkForExistingFile(ep_obj.location)

        # if it's not priority then we don't want to replace smaller files in case it was a mistake
        if not priority_download:
        
            # if there's an existing file that we don't want to replace stop here
            if existing_file_status in (PostProcessor.EXISTS_LARGER, PostProcessor.EXISTS_SAME):
                self._log(u"File exists and we are not going to replace it because it's not smaller, quitting post-processing", logger.DEBUG)
                return False
            elif existing_file_status == PostProcessor.EXISTS_SMALLER:
                self._log(u"File exists and is smaller than the new file so I'm going to replace it", logger.DEBUG)
            elif existing_file_status != PostProcessor.DOESNT_EXIST:
                self._log(u"Unknown existing file status. This should never happen, please log this as a bug.", logger.ERROR)
                return False
        
        # if the file is priority then we're going to replace it even if it exists
        else:
            self._log(u"This download is marked a priority download so I'm going to replace an existing file if I find one", logger.DEBUG)
        
        # delete the existing file (and company)
        for cur_ep in [ep_obj] + ep_obj.relatedEps:
            try:
                self._delete(cur_ep.location, associated_files=True)
            except OSError, IOError:
                raise exceptions.PostProcessingFailed("Unable to delete the existing files")
        
        # find the destination folder
        try:
            dest_path = self._find_ep_destination_folder(ep_obj)
        except exceptions.ShowDirNotFoundException:
            raise exceptions.PostProcessingFailed(u"Unable to post-process an episode if the show dir doesn't exist, quitting")
            
        self._log(u"Destination folder for this episode: "+dest_path, logger.DEBUG)
        
        # if the dir doesn't exist (new season folder) then make it
        if not ek.ek(os.path.isdir, dest_path):
            self._log(u"Season folder didn't exist, creating it", logger.DEBUG)
            try:
                ek.ek(os.mkdir, dest_path)
                helpers.chmodAsParent(dest_path)
            except OSError, IOError:
                raise exceptions.PostProcessingFailed("Unable to create the episode's destination folder: "+dest_path)

        # update the statuses before we rename so the quality goes into the name properly
        for cur_ep in [ep_obj] + ep_obj.relatedEps:
            with cur_ep.lock:
                cur_ep.status = common.Quality.compositeStatus(common.DOWNLOADED, new_ep_quality)
                cur_ep.saveToDB()

        # figure out the base name of the resulting episode file
        if sickbeard.RENAME_EPISODES:
            orig_extension = self.file_name.rpartition('.')[-1]
            new_base_name = helpers.sanitizeFileName(ep_obj.prettyName())
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
        except OSError, IOError:
            raise exceptions.PostProcessingFailed("Unable to move the files to their new home")
        
        # put the new location in the database
        for cur_ep in [ep_obj] + ep_obj.relatedEps:
            with cur_ep.lock:
                cur_ep.location = ek.ek(os.path.join, dest_path, new_file_name)
                cur_ep.saveToDB()
        
        # log it to history
        history.logDownload(ep_obj, self.file_path)

        # send notifications
        notifiers.notify_download(ep_obj.prettyName(True))

        # generate nfo/tbn
        ep_obj.createMetaFiles()
        ep_obj.saveToDB()

        # do the library update
        notifiers.xbmc_notifier.update_library(ep_obj.show.name)

        # do the library update for Plex Media Server
        notifiers.plex_notifier.update_library()

        # do the library update for synoindex
        notifiers.synoindex_notifier.update_library(ep_obj)

        # do the library update for trakt
        notifiers.trakt_notifier.update_library(ep_obj)
        
        # do the library update for pyTivo
        notifiers.pytivo_notifier.update_library(ep_obj)
        
        self._run_extra_scripts(ep_obj)

        return True
