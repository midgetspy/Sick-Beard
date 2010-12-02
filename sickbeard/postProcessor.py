import glob
import os
import os.path
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
from sickbeard import sceneHelpers

from sickbeard import encodingKludge as ek

from sickbeard.name_parser.parser import NameParser, InvalidNameException

from lib.tvdb_api import tvdb_api, tvdb_exceptions

class PostProcessor(object):

    EXISTS_LARGER = 1
    EXISTS_SAME = 2
    EXISTS_SMALLER = 3
    DOESNT_EXIST = 4

    def __init__(self, file_path, nzb_name = None):
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
    
        self.log = ''
    
    def _log(self, message, level=logger.MESSAGE):
        logger.log(message, level)
        self.log += message + '\n'
    
    def _checkForExistingFile(self, existing_file):
    
        if not existing_file:
            self._log("There is no existing file so there's no worries about replacing it", logger.DEBUG)
            return PostProcessor.DOESNT_EXIST
    
        # if the new file exists, return the appropriate code depending on the size
        if ek.ek(os.path.isfile, existing_file):
    
            # see if it's bigger than our old file
            if ek.ek(os.path.getsize, existing_file) > ek.ek(os.path.getsize, self.file_path):
                self._log("File "+existing_file+" is larger than "+self.file_path, logger.DEBUG)
                return PostProcessor.EXISTS_LARGER

            elif ek.ek(os.path.getsize, existing_file) == ek.ek(os.path.getsize, self.file_path):
                self._log("File "+existing_file+" is the same size as "+self.file_path, logger.DEBUG)
                return PostProcessor.EXISTS_SAME
    
            else:
                self._log("File "+existing_file+" is smaller than "+self.file_path, logger.DEBUG)
                return PostProcessor.EXISTS_SMALL
    
        else:
            self._log("File "+existing_file+" doesn't exist so there's no worries about replacing it", logger.DEBUG)
            return PostProcessor.DOESNT_EXIST

    def _list_associated_files(self, file_path):
    
        if not file_path or not ek.ek(os.path.isfile, file_path):
            return []

        file_path_list = []
    
        base_name = file_path.rpartition('.')[0]+'.'
    
        for associated_file_path in ek.ek(glob.glob, base_name+'*'):
            # only list it if the only non-shared part is the extension
            if '.' in associated_file_path[len(base_name):]:
                continue

            file_path_list.append(associated_file_path)
        
        return file_path_list

    def _destination_file_name(self, new_name):
        existing_extension = self.file_name.rpartition('.')[-1]
        
        if sickbeard.RENAME_EPISODES:
            return new_name + '.' + existing_extension
        else:
            return self.file_name 

    def _delete(self, file_path, associated_files=False):
        
        if associated_files:
            file_list = self._list_associated_files(file_path)
        else:
            file_list = [file_path]

        if not file_list:
            self._log("There were no files associated with "+file_path+", not deleting anything", logger.DEBUG)
            return
        
        for cur_file in file_list:
            self._log("Deleting file "+cur_file, logger.DEBUG)
            ek.ek(os.remove, cur_file)

    def _rename(self, file_path, new_base_name, associated_files=False):
        
        if associated_files:
            file_list = self._list_associated_files(file_path)
        else:
            file_list = [file_path]

        if not file_list:
            self._log("There were no files associated with "+file_path+", not renaming anything", logger.DEBUG)
            return
        
        for cur_file_path in file_list:

            # get the extension
            cur_extension = cur_file_path.rpartition('.')[-1]
            
            # replace .nfo with .nfo-orig to avoid conflicts
            if cur_extension == 'nfo':
                cur_extension = 'nfo-orig'
            
            new_path = ek.ek(os.path.join, ek.ek(os.path.dirname, cur_file_path), new_base_name+'.'+cur_extension)
            
            if ek.ek(os.path.abspath, cur_file_path) == ek.ek(os.path.abspath, new_path):
                self._log("File "+cur_file_path+" is already named properly, no rename needed", logger.DEBUG)
                continue
            
            self._log("Renaming file "+cur_file_path+" to "+new_path, logger.DEBUG)
            ek.ek(os.rename, cur_file_path, new_path)

    def _move(self, file_path, new_path, associated_files=False):

        if associated_files:
            file_list = self._list_associated_files(file_path)
        else:
            file_list = [file_path]

        if not file_list:
            self._log("There were no files associated with "+file_path+", not moving anything", logger.DEBUG)
            return
        
        for cur_file_path in file_list:

            cur_file_name = ek.ek(os.path.basename, cur_file_path)
            new_file_path = ek.ek(os.path.join, new_path, cur_file_name)

            self._log("Moving file from "+cur_file_path+" to "+new_file_path, logger.DEBUG)
            try:
                helpers.moveFile(cur_file_path, new_file_path)
            except (IOError, OSError), e:
                logger.log("Unable to move file "+cur_file_path+" to "+new_file_path+": "+str(e).decode('utf-8'), logger.ERROR)
                
    def _copy(self, file_path, new_path, associated_files=False):

        if associated_files:
            file_list = self._list_associated_files(file_path)
        else:
            file_list = [file_path]

        if not file_list:
            self._log("There were no files associated with "+file_path+", not copying anything", logger.DEBUG)
            return
        
        for cur_file_path in file_list:

            cur_file_name = ek.ek(os.path.basename, cur_file_path)
            new_file_path = ek.ek(os.path.join, new_path, cur_file_name)

            self._log("Copying file from "+cur_file_path+" to "+new_file_path, logger.DEBUG)
            try:
                helpers.copyFile(cur_file_path, new_file_path)
            except (IOError, OSError), e:
                logger.log("Unable to copy file "+cur_file_path+" to "+new_file_path+": "+str(e).decode('utf-8'), logger.ERROR)

    def _find_ep_destination_folder(self, ep_obj):
        
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
                if ep_obj.show.is_air_by_date:
                    season_folder = str(ep_obj.airdate.year)
                else:
                    season_folder = sickbeard.SEASON_FOLDERS_FORMAT % (ep_obj.season)
        
        dest_folder = ek.ek(os.path.join, ep_obj.show.location, season_folder)
        
        return dest_folder

    def _history_lookup(self):
        """
        Look up the NZB name in the history and see if it contains a record for self.nzb_name
        
        Returns a (tvdb_id, season, [episodes]) tuple. The first two may be None and episodes may be []
        if none were found.
        """
        
        to_return = (None, None, [])
        
        if not self.nzb_name:
            self.in_history = False
            return to_return
    
        names = [self.nzb_name, self.nzb_name.rpartition(".")[0]]
    
        myDB = db.DBConnection()
    
        for curName in names:
            sql_results = myDB.select("SELECT * FROM history WHERE resource LIKE ?", [re.sub("[\.\-\ ]", "_", curName)])
    
            if len(sql_results) == 0:
                continue
    
            tvdb_id = int(sql_results[0]["showid"])
            season = int(sql_results[0]["season"])
            episodes = []
    
            for cur_result in sql_results:
                episodes.append(int(cur_result["episode"]))            

            self.in_history = True
            return (tvdb_id, season, list(set(episodes)))
        
        self.in_history = False
        return to_return
    
    def _analyze_name(self, name, file=True):
        """
        Takes a name and tries to figure out a show, season, and episode from it.
        
        Returns a (tvdb_id, season, [episodes]) tuple. The first two may be None and episodes may be []
        if none were found.
        """
    
        to_return = (None, None, [])
    
        if not name:
            return to_return
    
        # parse the name to break it into show name, season, and episode
        np = NameParser(file)
        parse_result = np.parse(name)
    
        if parse_result.air_by_date:
            season = -1
            episodes = [parse_result.air_date]
        else:
            season = parse_result.season_number
            episodes = parse_result.episode_numbers 
    
        # do a scene reverse-lookup to get a list of all possible names
        name_list = sceneHelpers.sceneToNormalShowNames(parse_result.series_name)
        
        # reverse-lookup the scene exceptions
        for exceptionID in common.sceneExceptions:
            for curException in common.sceneExceptions[exceptionID]:
                for cur_name in name_list:
                    if cur_name == curException:
                        self._log(u"Scene exception lookup got tvdb id "+str(exceptionID)+u", using that", logger.DEBUG)
                        self.release_group = parse_result.release_group
                        return (exceptionID, season, episodes)

        # see if we can find the name directly in the DB, if so use it
        for cur_name in name_list:
            self._log(u"Looking up "+cur_name+u" in the DB", logger.DEBUG)
            db_result = helpers.searchDBForShow(cur_name)
            if db_result:
                self._log(u"Lookup successful, using tvdb id "+str(db_result[0]), logger.DEBUG)
                self.release_group = parse_result.release_group
                return (int(db_result[0]), season, episodes)
        
        # see if we can find the name with a TVDB lookup
        for cur_name in name_list:
            try:
                t = tvdb_api.Tvdb(custom_ui=classes.ShowListUI, **sickbeard.TVDB_API_PARMS)
    
                self._log(u"Looking up name "+cur_name+u" on TVDB", logger.DEBUG)
                showObj = t[cur_name]
            except (tvdb_exceptions.tvdb_exception, IOError), e:
                continue
            
            self._log(u"Lookup successful, using tvdb id "+str(showObj["id"]), logger.DEBUG)
            self.release_group = parse_result.release_group
            return (int(showObj["id"]), season, episodes)
    
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

                        # try to analyze the nzb name
                        lambda: self._analyze_name(self.nzb_name),
                        ]
    
        # attempt every possible method to get our info
        for cur_attempt in attempt_list:
            
            try:
                (cur_tvdb_id, cur_season, cur_episodes) = cur_attempt()
            except InvalidNameException, e:
                logger.log(u"Unable to parse, skipping: "+str(e), logger.DEBUG)
                continue
            
            if cur_tvdb_id:
                tvdb_id = cur_tvdb_id
            if cur_season != None:
                season = cur_season
            if cur_episodes:
                episodes = cur_episodes
            
            # for air-by-date shows we need to look up the season/episode from tvdb
            if season == -1 and tvdb_id:
                self._log(u"Looks like this is an air-by-date show, attempting to convert the date to season/episode", logger.DEBUG)
                try:
                    t = tvdb_api.Tvdb(**sickbeard.TVDB_API_PARMS)
                    epObj = t[cur_tvdb_id].airedOn(episodes[0])[0]
                    season = int(epObj["seasonnumber"])
                    episodes = [int(epObj["episodenumber"])]
                    self._log("Got season "+str(season)+" episodes "+str(episodes), logger.DEBUG)
                except tvdb_exceptions.tvdb_episodenotfound, e:
                    self._log(u"Unable to find episode with date "+str(episodes[0])+u" for show "+str(cur_tvdb_id)+u", skipping", logger.DEBUG)
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

        self._log("Loading show object for tvdb_id "+str(tvdb_id), logger.DEBUG)
        # find the show in the showlist
        try:
            show_obj = helpers.findCertainShow(sickbeard.showList, tvdb_id)
        except exceptions.MultipleShowObjectsException:
            raise #TODO: later I'll just log this, for now I want to know about it ASAP

        root_ep = None
        for cur_episode in episodes:
            episode = int(cur_episode)
    
            self._log(u"Retrieving episode object for " + str(season) + "x" + str(episode), logger.DEBUG)
    
            # now that we've figured out which episode this file is just load it manually
            try:
                curEp = show_obj.getEpisode(season, episode)
            except exceptions.EpisodeNotFoundException, e:
                self._log(u"Unable to create episode: "+str(e).decode('utf-8'), logger.DEBUG)
                raise exceptions.PostProcessingFailed()
    
            if root_ep == None:
                root_ep = curEp
                root_ep.relatedEps = []
            else:
                root_ep.relatedEps.append(curEp)
        
        return root_ep
    
    def _get_quality(self, ep_obj):
        
        ep_quality = common.Quality.UNKNOWN
        oldStatus = None
        # make sure the quality is set right before we continue
        if ep_obj.status in common.Quality.SNATCHED + common.Quality.SNATCHED_PROPER:
            oldStatus, ep_quality = common.Quality.splitCompositeStatus(ep_obj.status)
            self._log(u"The old status had a quality in it, using that: "+common.Quality.qualityStrings[ep_quality], logger.DEBUG)
            return ep_quality

        name_list = [self.nzb_name, self.folder_name, self.file_name]
    
        # search all possible names for our new quality, in case the file or dir doesn't have it
        for cur_name in name_list:
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
    
    def _run_extra_scripts(self, ep_obj):
        for curScriptName in sickbeard.EXTRA_SCRIPTS:
            script_cmd = shlex.split(curScriptName) + [ep_obj.location, self.file_path, str(ep_obj.show.tvdbid), str(ep_obj.season), str(ep_obj.episode), str(ep_obj.airdate)]
            self._log(u"Executing command "+str(script_cmd))
            self._log(u"Absolute path to script: "+ek.ek(os.path.abspath, script_cmd[0]), logger.DEBUG)
            try:
                p = subprocess.Popen(script_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=sickbeard.PROG_DIR)
                out, err = p.communicate()
                self._log(u"Script result: "+str(out), logger.DEBUG)
            except OSError, e:
                self._log(u"Unable to run extra_script: "+str(e).decode('utf-8'))
    
    def process(self):
        """
        Post-process a given file
        """
        
        self._log(u"Processing "+self.file_path+" ("+str(self.nzb_name)+")")
        
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
        ep_quality = self._get_quality(ep_obj)
        
        # see if this is a priority download (is it snatched, in history, or PROPER)
        priority_download = self.in_history or ep_obj.status in common.Quality.SNATCHED + common.Quality.SNATCHED_PROPER
        
        # set the status of the episodes
        for curEp in [ep_obj] + ep_obj.relatedEps:
            curEp.status = common.Quality.compositeStatus(common.SNATCHED, ep_quality)
        
        # check for an existing file
        existing_file_status = self._checkForExistingFile(ep_obj.location)
        
        # if there's an existing file and we don't want to replace it then stop here
        if existing_file_status in (PostProcessor.EXISTS_LARGER, PostProcessor.EXISTS_SAME, PostProcessor.EXISTS_SMALLER) and not priority_download:
            self._log("File exists and we are not going to replace it, quitting post-processing", logger.DEBUG)
        
        # if renaming is turned on then rename the episode (and associated files, if necessary)
        if sickbeard.RENAME_EPISODES:
            self._log("Renaming all associated files", logger.DEBUG)
            self._rename(self.file_path, ep_obj.prettyName(), sickbeard.MOVE_ASSOCIATED_FILES)

            # remember the new name of the file
            new_file_path = ek.ek(os.path.join, self.folder_path, ep_obj.prettyName() + '.' + self.file_name.rpartition('.')[-1])
        else:
            new_file_path = self.file_path


        # delete the existing file (and company)
        self._delete(ep_obj.location, associated_files=True)
        
        # find the destination folder
        dest_path = self._find_ep_destination_folder(ep_obj)
        
        # if the dir doesn't exist (new season folder) then make it
        if not ek.ek(os.path.isdir, dest_path):
            self._log(u"Season folder didn't exist, creating it", logger.DEBUG)
            ek.ek(os.mkdir, dest_path)

        # move the episode to the show dir
        if sickbeard.KEEP_PROCESSED_DIR:
            self._copy(new_file_path, dest_path, sickbeard.MOVE_ASSOCIATED_FILES)
        else:
            self._move(new_file_path, dest_path, sickbeard.MOVE_ASSOCIATED_FILES)
        
        # update the statuses before we rename so the quality goes into the name properly
        for cur_ep in [ep_obj] + ep_obj.relatedEps:
            with cur_ep.lock:
                cur_ep.location = ek.ek(os.path.join, dest_path, self._destination_file_name(ep_obj.prettyName()))
                cur_ep.status = common.Quality.compositeStatus(common.DOWNLOADED, ep_quality)
                cur_ep.saveToDB()
        
        # log it to history
        history.logDownload(ep_obj, self.file_path)

        # send notifications
        notifiers.notify(common.NOTIFY_DOWNLOAD, ep_obj.prettyName(True))

        # generate nfo/tbn
        ep_obj.createMetaFiles()
        ep_obj.saveToDB()

        # this needs to be factored out into the notifiers
        if sickbeard.XBMC_UPDATE_LIBRARY:
            for curHost in [x.strip() for x in sickbeard.XBMC_HOST.split(",")]:
                # do a per-show update first, if possible
                if not notifiers.xbmc.updateLibrary(curHost, showName=ep_obj.show.name) and sickbeard.XBMC_UPDATE_FULL:
                    # do a full update if requested
                    self._log(u"Update of show directory failed on " + curHost + ", trying full update as requested")
                    notifiers.xbmc.updateLibrary(curHost)

        # run extra_scripts
        self._run_extra_scripts(ep_obj)

        return True
        
        # e
