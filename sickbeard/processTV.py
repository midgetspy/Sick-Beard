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

from __future__ import with_statement

import os
import shutil
import time

import sickbeard
from sickbeard import common
from sickbeard import postProcessor

from sickbeard import db, helpers, exceptions

from sickbeard import encodingKludge as ek
from sickbeard.exceptions import ex

from sickbeard import logger


def delete_folder(folder, check_empty=True):

    # check if it's a folder
    if not ek.ek(os.path.isdir, folder):
        return False

    # check if it isn't TV_DOWNLOAD_DIR
    if sickbeard.TV_DOWNLOAD_DIR:
        if helpers.real_path(folder) == helpers.real_path(sickbeard.TV_DOWNLOAD_DIR):
            return False

    # check if it's empty folder when wanted checked
    if check_empty:
        check_files = ek.ek(os.listdir, folder)
        if check_files:
            return False

    # try deleting folder
    try:
        logger.log(u"Deleting folder: " + folder)
        shutil.rmtree(folder)
    except (OSError, IOError), e:
        logger.log(u"Warning: unable to delete folder: " + folder + ": " + ex(e), logger.WARNING)
        return False

    return True


def logHelper(logMessage, logLevel=logger.MESSAGE):
    logger.log(logMessage, logLevel)
    return logMessage + u"\n"


def processDir(dirName, nzbName=None, method=None, recurse=False, pp_options={}):
    """
    Scans through the files in dirName and processes whatever media files it finds

    dirName: The folder name to look in
    nzbName: The NZB name which resulted in this folder being downloaded
    method:  The method of postprocessing: Automatic, Script, Manual
    recurse: Boolean for whether we should descend into subfolders or not
    """

    returnStr = u""

    returnStr += logHelper(u"Processing folder: " + dirName, logger.DEBUG)

    # if they passed us a real dir then assume it's the one we want
    if ek.ek(os.path.isdir, dirName):
        dirName = ek.ek(os.path.realpath, dirName)

    # if they've got a download dir configured then use it
    elif sickbeard.TV_DOWNLOAD_DIR and ek.ek(os.path.isdir, sickbeard.TV_DOWNLOAD_DIR) \
            and ek.ek(os.path.normpath, dirName) != ek.ek(os.path.normpath, sickbeard.TV_DOWNLOAD_DIR):
        dirName = ek.ek(os.path.join, sickbeard.TV_DOWNLOAD_DIR, ek.ek(os.path.abspath, dirName).split(os.path.sep)[-1])
        returnStr += logHelper(u"Trying to use folder: " + dirName, logger.DEBUG)

    # if we didn't find a real dir then quit
    if not ek.ek(os.path.isdir, dirName):
        returnStr += logHelper(u"Unable to figure out what folder to process. If your downloader and Sick Beard aren't on the same PC make sure you fill out your TV download dir in the config.", logger.DEBUG)
        return returnStr

    # TODO: check if it's failed and deal with it if it is
    if ek.ek(os.path.basename, dirName).startswith('_FAILED_'):
        returnStr += logHelper(u"The directory name indicates it failed to extract, cancelling", logger.DEBUG)
        return returnStr
    elif ek.ek(os.path.basename, dirName).startswith('_UNDERSIZED_'):
        returnStr += logHelper(u"The directory name indicates that it was previously rejected for being undersized, cancelling", logger.DEBUG)
        return returnStr
    elif ek.ek(os.path.basename, dirName).upper().startswith('_UNPACK'):
        returnStr += logHelper(u"The directory name indicates that this release is in the process of being unpacked, skipping", logger.DEBUG)
        return returnStr

    # make sure the dir isn't inside a show dir
    myDB = db.DBConnection()
    sqlResults = myDB.select("SELECT * FROM tv_shows")
    for sqlShow in sqlResults:
        if dirName.lower().startswith(ek.ek(os.path.realpath, sqlShow["location"]).lower() + os.sep) or dirName.lower() == ek.ek(os.path.realpath, sqlShow["location"]).lower():
            returnStr += logHelper(u"You're trying to post process an existing show directory: " + dirName, logger.ERROR)
            returnStr += u"\n"
            return returnStr

    fileList = ek.ek(os.listdir, dirName)

    # split the list into video files and folders
    folders = filter(lambda x: ek.ek(os.path.isdir, ek.ek(os.path.join, dirName, x)), fileList)

    # videoFiles, sorted by size, process biggest file first. Leaves smaller same named file behind
    mediaFiles =  filter(lambda x: ek.ek(os.path.exists, ek.ek(os.path.join, dirName, x)), filter(helpers.isMediaFile, fileList))
    videoFiles = sorted(mediaFiles, key=lambda x: ek.ek(os.path.getsize, ek.ek(os.path.join, dirName, x)), reverse=True)
    remaining_video_files = list(videoFiles)

    num_videoFiles = len(videoFiles)

    # if there are no videofiles in parent and only one subfolder, pass the nzbName to child
    if num_videoFiles == 0 and len(folders) == 1:
        parent_nzbName = nzbName
    else:
        parent_nzbName = None

    # recursively process all the folders
    for cur_folder in folders:

        returnStr += u"\n"
        # use full path
        cur_folder = ek.ek(os.path.join, dirName, cur_folder)

        if helpers.is_hidden_folder(cur_folder):
            returnStr += logHelper(u"Ignoring hidden folder: " + cur_folder, logger.DEBUG)
        else:
            returnStr += logHelper(u"Recursively processing a folder: " + cur_folder, logger.DEBUG)
            returnStr += processDir(cur_folder, nzbName=parent_nzbName, recurse=True, method=method, pp_options=pp_options)

    remainingFolders = filter(lambda x: ek.ek(os.path.isdir, ek.ek(os.path.join, dirName, x)), fileList)

    if num_videoFiles == 0:
        returnStr += u"\n"
        returnStr += logHelper(u"There are no videofiles in folder: " + dirName, logger.DEBUG)

        # if there a no videofiles, try deleting empty folder
        if method != 'Manual':
            if delete_folder(dirName, check_empty=True):
                returnStr += logHelper(u"Deleted empty folder: " + dirName, logger.DEBUG)

    # if there's more than one videofile in the folder, files can be lost (overwritten) when nzbName contains only one episode.
    if num_videoFiles >= 2:
        nzbName = None

    # process any files in the dir
    for cur_video_file in videoFiles:

        cur_video_file_path = ek.ek(os.path.join, dirName, cur_video_file)

        if method == 'Automatic':
            # check if we processed this video file before
            cur_video_file_path_size = ek.ek(os.path.getsize, cur_video_file_path)

            myDB = db.DBConnection()
            search_sql = "SELECT tv_episodes.tvdbid, history.resource FROM tv_episodes INNER JOIN history ON history.showid=tv_episodes.showid"
            search_sql += " WHERE history.season=tv_episodes.season and history.episode=tv_episodes.episode"
            search_sql += " and tv_episodes.status IN (" + ",".join([str(x) for x in common.Quality.DOWNLOADED]) + ")"
            search_sql += " and history.resource LIKE ? and tv_episodes.file_size = ?"
            sql_results = myDB.select(search_sql, [cur_video_file_path, cur_video_file_path_size])

            if len(sql_results):
                returnStr += logHelper(u"Ignoring file: " + cur_video_file_path + " looks like it's been processed already", logger.DEBUG)
                continue

        try:
            returnStr += u"\n"
            processor = postProcessor.PostProcessor(cur_video_file_path, nzb_name=nzbName, pp_options=pp_options)
            process_result = processor.process()
            process_fail_message = ""

        except exceptions.PostProcessingFailed, e:
            process_result = False
            process_fail_message = ex(e)

        except Exception, e:
            process_result = False
            process_fail_message = "Post Processor returned unhandled exception: " + ex(e)

        returnStr += processor.log

        # as long as the postprocessing was successful delete the old folder unless the config wants us not to
        if process_result:

            remaining_video_files.remove(cur_video_file)

            if not sickbeard.KEEP_PROCESSED_DIR and len(remaining_video_files) == 0 and len(remainingFolders) == 0:
                if delete_folder(dirName, check_empty=False):
                    returnStr += logHelper(u"Deleted folder: " + dirName, logger.DEBUG)

            returnStr += logHelper(u"Processing succeeded for " + cur_video_file_path)

        else:
            returnStr += logHelper(u"Processing failed for " + cur_video_file_path + ": " + process_fail_message, logger.WARNING)

    return returnStr
