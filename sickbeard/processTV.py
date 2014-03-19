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
import stat

import sickbeard
from sickbeard import postProcessor
from sickbeard import db, helpers, exceptions
from sickbeard import encodingKludge as ek
from sickbeard.exceptions import ex
from sickbeard import logger
from sickbeard.name_parser.parser import NameParser, InvalidNameException
from sickbeard import common

from sickbeard import failedProcessor

from lib.unrar2 import RarFile, RarInfo
from lib.unrar2.rar_exceptions import *

def logHelper (logMessage, logLevel=logger.MESSAGE):
    logger.log(logMessage, logLevel)
    return logMessage + u"\n"

def processDir(dirName, nzbName=None, process_method=None, force=False, is_priority=None, failed=False, type="automatic"):
    """
    Scans through the files in dirName and processes whatever media files it finds

    dirName: The folder name to look in
    nzbName: The NZB name which resulted in this folder being downloaded
    force: True to postprocess already postprocessed files
    failed: Boolean for whether or not the download failed
    type: Type of postprocessing automatic or manual
    """

    global process_result, returnStr

    returnStr = ''

    returnStr += logHelper(u"Processing folder " + dirName, logger.DEBUG)

    returnStr += logHelper(u"TV_DOWNLOAD_DIR: " + sickbeard.TV_DOWNLOAD_DIR, logger.DEBUG)

    # if they passed us a real dir then assume it's the one we want
    if ek.ek(os.path.isdir, dirName):
        dirName = ek.ek(os.path.realpath, dirName)

    # if the client and Sickbeard are not on the same machine translate the Dir in a network dir
    elif sickbeard.TV_DOWNLOAD_DIR and ek.ek(os.path.isdir, sickbeard.TV_DOWNLOAD_DIR) \
    and helpers.real_path(dirName) != helpers.real_path(sickbeard.TV_DOWNLOAD_DIR):
        dirName = ek.ek(os.path.join, sickbeard.TV_DOWNLOAD_DIR, ek.ek(os.path.abspath, dirName).split(os.path.sep)[-1])
        returnStr += logHelper(u"Trying to use folder " + dirName, logger.DEBUG)

    # if we didn't find a real dir then quit
    if not ek.ek(os.path.isdir, dirName):
        returnStr += logHelper(u"Unable to figure out what folder to process. If your downloader and Sick Beard aren't on the same PC make sure you fill out your TV download dir in the config.", logger.DEBUG)
        return returnStr

    path, dirs, files = get_path_dir_files(dirName, nzbName, type)

    returnStr += logHelper(u"PostProcessing Path: " + path, logger.DEBUG)
    returnStr += logHelper(u"PostProcessing Dirs: " + str(dirs), logger.DEBUG)

    rarFiles = filter(helpers.isRarFile, files)
    rarContent = unRAR(path, rarFiles, force)
    files += rarContent
    videoFiles = filter(helpers.isMediaFile, files)
    videoInRar = filter(helpers.isMediaFile, rarContent)

    returnStr += logHelper(u"PostProcessing Files: " + str(files), logger.DEBUG)
    returnStr += logHelper(u"PostProcessing VideoFiles: " + str(videoFiles), logger.DEBUG)
    returnStr += logHelper(u"PostProcessing RarContent: " + str(rarContent), logger.DEBUG)
    returnStr += logHelper(u"PostProcessing VideoInRar: " + str(videoInRar), logger.DEBUG)

    # If nzbName is set and there's more than one videofile in the folder, files will be lost (overwritten).
    nzbNameOriginal = nzbName
    if len(videoFiles) >= 2:
        nzbName = None

    if not process_method:
        process_method = sickbeard.PROCESS_METHOD

    process_result = True

    #Don't Link media when the media is extracted from a rar in the same path
    if process_method in ('hardlink', 'symlink') and videoInRar:
        process_media(path, videoInRar, nzbName, 'move', force, is_priority)
        delete_files(path, rarContent)
        for video in set(videoFiles) - set(videoInRar):
            process_media(path, [video], nzbName, process_method, force, is_priority)
    else:
        for video in videoFiles:
            process_media(path, [video], nzbName, process_method, force, is_priority)

    #Process Video File in all TV Subdir
    for dir in [x for x in dirs if validateDir(path, x, nzbNameOriginal, failed)]:

        process_result = True

        for processPath, processDir, fileList in ek.ek(os.walk, ek.ek(os.path.join, path, dir), topdown=False):

            rarFiles = filter(helpers.isRarFile, fileList)
            rarContent = unRAR(processPath, rarFiles, force)
            fileList = set(fileList + rarContent)
            videoFiles = filter(helpers.isMediaFile, fileList)
            videoInRar = filter(helpers.isMediaFile, rarContent)
            notwantedFiles = [x for x in fileList if x not in videoFiles]

            #Don't Link media when the media is extracted from a rar in the same path
            if process_method in ('hardlink', 'symlink') and videoInRar:
                process_media(processPath, videoInRar, nzbName, 'move', force, is_priority)
                process_media(processPath, set(videoFiles) - set(videoInRar), nzbName, process_method, force, is_priority)
                delete_files(processPath, rarContent)
            else:
                process_media(processPath, videoFiles, nzbName, process_method, force, is_priority)

                #Avoid to delete files
                if process_method != "move" or not process_result \
                or type == "manual":
                    continue

                delete_files(processPath, notwantedFiles)

                if process_method == "move" \
                and helpers.real_path(processPath) != helpers.real_path(sickbeard.TV_DOWNLOAD_DIR):
                    delete_dir(processPath)

    return returnStr

def validateDir(path, dirName, nzbNameOriginal, failed):

    global process_result, returnStr

    returnStr += logHelper(u"Processing folder " + dirName, logger.DEBUG)

    if ek.ek(os.path.basename, dirName).startswith('_FAILED_'):
        returnStr += logHelper(u"The directory name indicates it failed to extract.", logger.DEBUG)
        failed = True
    elif ek.ek(os.path.basename, dirName).startswith('_UNDERSIZED_'):
        returnStr += logHelper(u"The directory name indicates that it was previously rejected for being undersized.", logger.DEBUG)
        failed = True
    elif ek.ek(os.path.basename, dirName).startswith('_UNPACK_'):
        returnStr += logHelper(u"The directory name indicates that this release is in the process of being unpacked.", logger.DEBUG)
        return False

    if failed:
        process_failed(ek.ek(os.path.join, path, dirName), nzbNameOriginal)
        return False

    if helpers.is_hidden_folder(dirName):
        returnStr += logHelper(u"Ignoring hidden folder: " + dirName, logger.DEBUG)
        return False

    # make sure the dir isn't inside a show dir
    myDB = db.DBConnection()
    sqlResults = myDB.select("SELECT * FROM tv_shows")
    for sqlShow in sqlResults:
        if dirName.lower().startswith(ek.ek(os.path.realpath, sqlShow["location"]).lower()+os.sep) or dirName.lower() == ek.ek(os.path.realpath, sqlShow["location"]).lower():
            returnStr += logHelper(u"You're trying to post process an episode that's already been moved to its show dir, skipping", logger.ERROR)
            return False

    # Get the videofile list for the next checks
    allFiles = []
    allDirs = []
    for processPath, processDir, fileList in ek.ek(os.walk, ek.ek(os.path.join, path, dirName), topdown=False):
        allDirs += processDir
        allFiles += fileList

    videoFiles = filter(helpers.isMediaFile, allFiles)
    allDirs.append(dirName)

    #check if the dir have at least one tv video file
    for video in videoFiles:
        try:
            NameParser().parse(video)
            return True
        except InvalidNameException:
            pass

    for dir in allDirs:
        try:
            NameParser().parse(dir)
            return True
        except InvalidNameException:
            pass

    if sickbeard.UNPACK:
        #Search for packed release
        packedFiles = filter(helpers.isRarFile, allFiles)

        for packed in packedFiles:
            try:
                NameParser().parse(packed)
                return True
            except InvalidNameException:
                pass

    return False

def unRAR(path, rarFiles, force):

    global process_result, returnStr

    unpacked_files = []

    if sickbeard.UNPACK and rarFiles:

        returnStr += logHelper(u"Packed Releases detected: " + str(rarFiles), logger.DEBUG)

        for archive in rarFiles:

            returnStr += logHelper(u"Unpacking archive: " + archive, logger.DEBUG)

            try:
                rar_handle = RarFile(ek.ek(os.path.join, path, archive))
                # Skip extraction if any file in archive has previously been extracted
                skip_file = False
                for file_in_archive in [ek.ek(os.path.basename, x.filename) for x in rar_handle.infolist() if not x.isdir]:
                    if already_postprocessed(path, file_in_archive, force):
                        returnStr += logHelper(u"Archive file already post-processed, extraction skipped: " + file_in_archive, logger.DEBUG)
                        skip_file = True
                        break

                if skip_file:
                    continue

                rar_handle.extract(path = path, withSubpath = False, overwrite = False)
                unpacked_files += [ek.ek(os.path.basename, x.filename) for x in rar_handle.infolist() if not x.isdir]
                del rar_handle
            except Exception, e:
                 returnStr += logHelper(u"Failed Unrar archive " + archive + ': ' + ex(e), logger.ERROR)
                 process_result = False
                 continue

        returnStr += logHelper(u"UnRar content: " + str(unpacked_files), logger.DEBUG)

    return unpacked_files

def already_postprocessed(dirName, videofile, force):

    global returnStr

    if force:
        return False

    #Needed for accessing DB with a unicode DirName
    if not isinstance(dirName, unicode):
        dirName = unicode(dirName, 'utf_8')

    # Avoid processing the same dir again if we use a process method <> move
    myDB = db.DBConnection()
    sqlResult = myDB.select("SELECT * FROM tv_episodes WHERE release_name = ?", [dirName])
    if sqlResult:
        returnStr += logHelper(u"You're trying to post process a dir that's already been processed, skipping", logger.DEBUG)
        return True

    # This is needed for video whose name differ from dirName
    if not isinstance(videofile, unicode):
        videofile = unicode(videofile, 'utf_8')

    sqlResult = myDB.select("SELECT * FROM tv_episodes WHERE release_name = ?", [videofile.rpartition('.')[0]])
    if sqlResult:
        returnStr += logHelper(u"You're trying to post process a video that's already been processed, skipping", logger.DEBUG)
        return True

    #Needed if we have downloaded the same episode @ different quality
    search_sql = "SELECT tv_episodes.tvdbid, history.resource FROM tv_episodes INNER JOIN history ON history.showid=tv_episodes.showid"
    search_sql += " WHERE history.season=tv_episodes.season and history.episode=tv_episodes.episode"
    search_sql += " and tv_episodes.status IN (" + ",".join([str(x) for x in common.Quality.DOWNLOADED]) + ")"
    search_sql += " and history.resource LIKE ?"
    sqlResult = myDB.select(search_sql, [u'%' + videofile])
    if sqlResult:
        returnStr += logHelper(u"You're trying to post process a video that's already been processed, skipping", logger.DEBUG)
        return True

    return False

def process_media(processPath, videoFiles, nzbName, process_method, force, is_priority):

    global process_result, returnStr

    for cur_video_file in videoFiles:

        if already_postprocessed(processPath, cur_video_file, force):
            continue

        cur_video_file_path = ek.ek(os.path.join, processPath, cur_video_file)

        try:
            processor = postProcessor.PostProcessor(cur_video_file_path, nzbName, process_method, is_priority)
            process_result = processor.process()
            process_fail_message = ""
        except exceptions.PostProcessingFailed, e:
            process_result = False
            process_fail_message = ex(e)

        returnStr += processor.log

        if process_result:
            returnStr += logHelper(u"Processing succeeded for " + cur_video_file_path)
        else:
            returnStr += logHelper(u"Processing failed for " + cur_video_file_path + ": " + process_fail_message, logger.WARNING)

        #If something fail abort the processing on dir
        if not process_result:
            break

def delete_files(processPath, notwantedFiles):

    global returnStr, process_result

    if not process_result:
        return

    #Delete all file not needed
    for cur_file in notwantedFiles:

        cur_file_path = ek.ek(os.path.join, processPath, cur_file)

        if not ek.ek(os.path.isfile, cur_file_path):
            continue #Prevent error when a notwantedfiles is an associated files

        returnStr += logHelper(u"Deleting file " + cur_file, logger.DEBUG)

        #check first the read-only attribute
        file_attribute = ek.ek(os.stat, cur_file_path)[0]
        if (not file_attribute & stat.S_IWRITE):
            # File is read-only, so make it writeable
            returnStr += logHelper(u"Changing ReadOnly Flag for file " + cur_file, logger.DEBUG)
            try:
                ek.ek(os.chmod,cur_file_path,stat.S_IWRITE)
            except OSError, e:
                returnStr += logHelper(u"Cannot change permissions of " + cur_file_path + ': ' + e.strerror, logger.DEBUG)
        try:
            ek.ek(os.remove, cur_file_path)
        except OSError, e:
            returnStr += logHelper(u"Unable to delete file " + cur_file + ': ' + e.strerror, logger.DEBUG)

def delete_dir(processPath):

    global returnStr

    if not ek.ek(os.listdir, processPath) == []:
        returnStr += logHelper(u"Skipping Deleting folder " + processPath + ' because some files was not deleted/processed', logger.DEBUG)
        return

    returnStr += logHelper(u"Deleting folder " + processPath, logger.DEBUG)

    try:
        shutil.rmtree(processPath)
    except (OSError, IOError), e:
        returnStr += logHelper(u"Warning: unable to remove the folder " + processPath + ": " + ex(e), logger.WARNING)

def get_path_dir_files(dirName, nzbName, type):

    if dirName == sickbeard.TV_DOWNLOAD_DIR and not nzbName or type =="manual": #Scheduled Post Processing Active
        #Get at first all the subdir in the dirName
        for path, dirs, files in ek.ek(os.walk, dirName):
            break
    else:
        path, dirs = ek.ek(os.path.split, dirName) #Script Post Processing
        if not nzbName is None and not nzbName.endswith('.nzb') and ek.ek(os.path.isfile, ek.ek(os.path.join, dirName, nzbName)): #For single torrent file without Dir
            dirs = []
            files = [ek.ek(os.path.join, dirName, nzbName)]
        else:
            dirs = [dirs]
            files = []

    return path, dirs, files

def process_failed(dirName, nzbName):
    """Process a download that did not complete correctly"""

    global returnStr

    if sickbeard.USE_FAILED_DOWNLOADS:
        try:
            processor = failedProcessor.FailedProcessor(dirName, nzbName)
            process_result = processor.process()
            process_fail_message = ""
        except exceptions.FailedProcessingFailed, e:
            process_result = False
            process_fail_message = ex(e)

        returnStr += processor.log

        if sickbeard.DELETE_FAILED and process_result:
            delete_dir(dirName)

        if process_result:
            returnStr += logHelper(u"Failed Download Processing succeeded: (" + str(nzbName) + ", " + dirName + ")")
        else:
            returnStr += logHelper(u"Failed Download Processing failed: (" + str(nzbName) + ", " + dirName + "): " + process_fail_message, logger.WARNING)
