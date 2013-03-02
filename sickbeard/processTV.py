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

import sickbeard 
from sickbeard import postProcessor
from sickbeard import db, helpers, exceptions

from sickbeard import encodingKludge as ek
from sickbeard.exceptions import ex

from sickbeard import logger

def logHelper (logMessage, logLevel=logger.MESSAGE):
    logger.log(logMessage, logLevel)
    return logMessage + u"\n"

def processDir (dirName, nzbName=None, recurse=False):
    """
    Scans through the files in dirName and processes whatever media files it finds
    
    dirName: The folder name to look in
    nzbName: The NZB name which resulted in this folder being downloaded
    recurse: Boolean for whether we should descend into subfolders or not
    """

    returnStr = ''

    returnStr += logHelper(u"Processing folder "+dirName, logger.DEBUG)

    # if they passed us a real dir then assume it's the one we want
    if ek.ek(os.path.isdir, dirName):
        dirName = ek.ek(os.path.realpath, dirName)

    # if they've got a download dir configured then use it
    elif sickbeard.TV_DOWNLOAD_DIR and ek.ek(os.path.isdir, sickbeard.TV_DOWNLOAD_DIR) \
            and ek.ek(os.path.normpath, dirName) != ek.ek(os.path.normpath, sickbeard.TV_DOWNLOAD_DIR):
        dirName = ek.ek(os.path.join, sickbeard.TV_DOWNLOAD_DIR, ek.ek(os.path.abspath, dirName).split(os.path.sep)[-1])
        returnStr += logHelper(u"Trying to use folder "+dirName, logger.DEBUG)

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
    elif ek.ek(os.path.basename, dirName).startswith('_UNPACK_'):
        returnStr += logHelper(u"The directory name indicates that this release is in the process of being unpacked, skipping", logger.DEBUG)
        return returnStr

    # make sure the dir isn't inside a show dir
    myDB = db.DBConnection()
    sqlResults = myDB.select("SELECT * FROM tv_shows")
    for sqlShow in sqlResults:
        if dirName.lower().startswith(ek.ek(os.path.realpath, sqlShow["location"]).lower()+os.sep) or dirName.lower() == ek.ek(os.path.realpath, sqlShow["location"]).lower():
            returnStr += logHelper(u"You're trying to post process an episode that's already been moved to its show dir", logger.ERROR)
            return returnStr

    fileList = ek.ek(os.listdir, dirName)

    # split the list into video files and folders
    folders = filter(lambda x: ek.ek(os.path.isdir, ek.ek(os.path.join, dirName, x)), fileList)
    videoFiles = filter(helpers.isMediaFile, fileList)

    # recursively process all the folders
    for curFolder in folders:
        returnStr += logHelper(u"Recursively processing a folder: "+curFolder, logger.DEBUG)
        returnStr += processDir(ek.ek(os.path.join, dirName, curFolder), recurse=True)

    remainingFolders = filter(lambda x: ek.ek(os.path.isdir, ek.ek(os.path.join, dirName, x)), fileList)

    # If nzbName is set and there's more than one videofile in the folder, files will be lost (overwritten).
    if nzbName != None and len(videoFiles) >= 2:
        nzbName = None
    
    # process any files in the dir
    for cur_video_file_path in videoFiles:

        cur_video_file_path = ek.ek(os.path.join, dirName, cur_video_file_path)

        try:
            processor = postProcessor.PostProcessor(cur_video_file_path, nzbName)
            process_result = processor.process()
            process_fail_message = ""
        except exceptions.PostProcessingFailed, e:
            process_result = False
            process_fail_message = ex(e)

        returnStr += processor.log 

        # as long as the postprocessing was successful delete the old folder unless the config wants us not to
        if process_result:

            if len(videoFiles) == 1 and not sickbeard.KEEP_PROCESSED_DIR and \
                ek.ek(os.path.normpath, dirName) != ek.ek(os.path.normpath, sickbeard.TV_DOWNLOAD_DIR) and \
                len(remainingFolders) == 0:

                returnStr += logHelper(u"Deleting folder " + dirName, logger.DEBUG)

                try:
                    shutil.rmtree(dirName)
                except (OSError, IOError), e:
                    returnStr += logHelper(u"Warning: unable to remove the folder " + dirName + ": " + ex(e), logger.WARNING)

            returnStr += logHelper(u"Processing succeeded for "+cur_video_file_path)
            
        else:
            returnStr += logHelper(u"Processing failed for "+cur_video_file_path+": "+process_fail_message, logger.WARNING)

    return returnStr
