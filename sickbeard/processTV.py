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

from lib.unrar2 import RarFile, RarInfo
from lib.unrar2.rar_exceptions import *

def logHelper (logMessage, logLevel=logger.MESSAGE):
    logger.log(logMessage, logLevel)
    return logMessage + u"\n"

def processDir (dirName, nzbName=None, recurse=False):
    """
    Scans through the files in dirName and processes whatever media files it finds
    
    dirName: The folder name to look in
    nzbName: The NZB name which resulted in this folder being downloaded
    """

    global process_result, returnStr

    returnStr = ''

    returnStr += logHelper(u"Processing folder "+dirName, logger.DEBUG)

    returnStr += logHelper(u"TV_DOWNLOAD_DIR: " + sickbeard.TV_DOWNLOAD_DIR, logger.DEBUG)

    # if they passed us a real dir then assume it's the one we want
    if ek.ek(os.path.isdir, dirName):
        dirName = ek.ek(os.path.realpath, dirName)

    # if the client and Sickbeard are not on the same machine translate the Dir in a network dir 
    elif sickbeard.TV_DOWNLOAD_DIR and ek.ek(os.path.isdir, sickbeard.TV_DOWNLOAD_DIR) \
            and ek.ek(os.path.normpath, dirName) != ek.ek(os.path.normpath, sickbeard.TV_DOWNLOAD_DIR):
        dirName = ek.ek(os.path.join, sickbeard.TV_DOWNLOAD_DIR, ek.ek(os.path.abspath, dirName).split(os.path.sep)[-1])
        returnStr += logHelper(u"Trying to use folder "+dirName, logger.DEBUG)

    # if we didn't find a real dir then quit
    if not ek.ek(os.path.isdir, dirName):
        returnStr += logHelper(u"Unable to figure out what folder to process. If your downloader and Sick Beard aren't on the same PC make sure you fill out your TV download dir in the config.", logger.DEBUG)
        return returnStr

    if dirName == sickbeard.TV_DOWNLOAD_DIR and not nzbName: #Scheduled Post Processing Active
        #Get at first all the subdir in the dirName
        for path, dirs, files in ek.ek(os.walk, dirName):
            break
    else:
        path, dirs = ek.ek(os.path.split, dirName) #Script Post Processing
        if not nzbName is None and not nzbName.endswith('.nzb') and os.path.isfile(os.path.join(dirName, nzbName)): #For single torrent file without Dir
            dirs = []
            files = [os.path.join(dirName, nzbName)]
        else:
            dirs = [dirs]
            files = []

    returnStr += logHelper(u"PostProcessing Path: " + path, logger.DEBUG)
    returnStr += logHelper(u"PostProcessing Dirs: " + str(dirs), logger.DEBUG)
    
    rarFiles = filter(helpers.isRarFile, files)
    files += unRAR(path, rarFiles)
    videoFiles = filter(helpers.isMediaFile, files)

    returnStr += logHelper(u"PostProcessing Files: " + str(files), logger.DEBUG)
    returnStr += logHelper(u"PostProcessing VideoFiles: " + str(videoFiles), logger.DEBUG)

    # If nzbName is set and there's more than one videofile in the folder, files will be lost (overwritten).
    if len(videoFiles) >= 2:
        nzbName = None

    #Process Video File in the current Path
    for cur_video_file in videoFiles:

        cur_video_file_path = ek.ek(os.path.join, dirName, cur_video_file)

        # Avoid processing the same file again if we use KEEP_PROCESSING_DIR    
        if sickbeard.KEEP_PROCESSED_DIR:
            myDB = db.DBConnection()
            sqlresult = myDB.select("SELECT * FROM tv_episodes WHERE release_name = ?", [cur_video_file.rpartition('.')[0]])
            if sqlresult:
                returnStr += logHelper(u"You're trying to post process the file " + cur_video_file + " that's already been processed, skipping", logger.DEBUG)
                continue

        if helpers.isBeingWritten(cur_video_file_path):
            returnStr += logHelper(u"Ignoring file: " + cur_video_file_path + " for now. Modified < 60s ago, might still be being written to", logger.DEBUG)
            continue
            
        try:
            processor = postProcessor.PostProcessor(cur_video_file_path, nzbName)
            process_result = processor.process()
            process_fail_message = ""
        except exceptions.PostProcessingFailed, e:
            process_result = False
            process_fail_message = ex(e)
            
        returnStr += processor.log

        if process_result:
            returnStr += logHelper(u"Processing succeeded for "+cur_video_file_path)
        else:
            returnStr += logHelper(u"Processing failed for "+cur_video_file_path+": "+process_fail_message, logger.WARNING)

    #Process Video File in all TV Subdir
    for dir in [x for x in dirs if validateDir(path, x)]:
        
        process_result = True
        
        for processPath, processDir, fileList in ek.ek(os.walk, ek.ek(os.path.join, path, dir), topdown=False):

            rarFiles = filter(helpers.isRarFile, fileList)
            fileList += unRAR(processPath, rarFiles)
            videoFiles = filter(helpers.isMediaFile, set(fileList))
            notwantedFiles = [x for x in fileList if x not in videoFiles]

            # If nzbName is set and there's more than one videofile in the folder, files will be lost (overwritten).
            if len(videoFiles) >= 2:
                nzbName = None

            for cur_video_file in videoFiles:

                cur_video_file_path = ek.ek(os.path.join, processPath, cur_video_file)
            
                try:
                    processor = postProcessor.PostProcessor(cur_video_file_path, nzbName)
                    process_result = processor.process()
                    process_fail_message = ""
                except exceptions.PostProcessingFailed, e:
                    process_result = False
                    process_fail_message = ex(e)
            
                returnStr += processor.log
                    
                if process_result:
                    returnStr += logHelper(u"Processing succeeded for "+cur_video_file_path)
                else:
                    returnStr += logHelper(u"Processing failed for "+cur_video_file_path+": "+process_fail_message, logger.WARNING)
                
                #If something fail abort the processing on dir
                if not process_result:
                    break

            returnStr += logHelper(u"Cleaning up Folder " + processPath, logger.DEBUG)
                                
            #Delete all file not needed
            for cur_file in notwantedFiles:
                if sickbeard.PROCESS_METHOD != "move" or not process_result:
                    break

                cur_file_path = ek.ek(os.path.join, processPath, cur_file)

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

                    
            if sickbeard.PROCESS_METHOD == "move" and \
            ek.ek(os.path.normpath, processPath) != ek.ek(os.path.normpath, sickbeard.TV_DOWNLOAD_DIR):
            
                if not ek.ek(os.listdir, processPath) == []:
                    returnStr += logHelper(u"Skipping Deleting folder " + processPath + ' because some files was not deleted/processed', logger.DEBUG)
                    continue
                    
                returnStr += logHelper(u"Deleting folder " + processPath, logger.DEBUG)

                try:
                    shutil.rmtree(processPath)
                except (OSError, IOError), e:
                    returnStr += logHelper(u"Warning: unable to remove the folder " + dirName + ": " + ex(e), logger.WARNING)

    return returnStr

def validateDir(path, dirName):
    
    global process_result, returnStr
    
    returnStr += logHelper(u"Processing folder "+dirName, logger.DEBUG)

    # TODO: check if it's failed and deal with it if it is
    if ek.ek(os.path.basename, dirName).startswith('_FAILED_'):
        returnStr += logHelper(u"The directory name indicates it failed to extract, cancelling", logger.DEBUG)
        return False
    elif ek.ek(os.path.basename, dirName).startswith('_UNDERSIZED_'):
        returnStr += logHelper(u"The directory name indicates that it was previously rejected for being undersized, cancelling", logger.DEBUG)
        return False
    elif ek.ek(os.path.basename, dirName).startswith('_UNPACK_'):
        returnStr += logHelper(u"The directory name indicates that this release is in the process of being unpacked, skipping", logger.DEBUG)
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
    for processPath, processDir, fileList in ek.ek(os.walk, ek.ek(os.path.join, path, dirName), topdown=False):

        # Check if any file was modified less than 60 sec.
        for file in fileList:
            if helpers.isBeingWritten(ek.ek(os.path.join, processPath, file)):
                returnStr += logHelper(u"Ignoring Dir: " + processPath + " for now. Some files were Modified < 60s ago, might still be being written to", logger.DEBUG)
                return False
        
        allFiles += fileList
            
    # Avoid processing the same dir again if we use KEEP_PROCESSING_DIR    
    if sickbeard.KEEP_PROCESSED_DIR:
        numPostProcFiles = myDB.select("SELECT COUNT(release_name) as numfiles FROM tv_episodes WHERE release_name = ?", [dirName])
        if int(numPostProcFiles[0][0]) == len(videoFiles):
            returnStr += logHelper(u"You're trying to post process a dir that's already been processed, skipping", logger.DEBUG)
            return False

    videoFiles = filter(helpers.isMediaFile, allFiles)

    #check if the dir have at least one tv video file
    for video in videoFiles:
        try:
            NameParser().parse(video)
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

def unRAR(path, rarFiles):
    
    global process_result, returnStr
    
    unpacked_files = []
        
    if sickbeard.UNPACK and rarFiles:

        returnStr += logHelper(u"Packed Releases detected: " + str(rarFiles), logger.DEBUG)
    
        for archive in rarFiles:

            returnStr += logHelper(u"Unpacking archive: " + archive, logger.DEBUG)
    
            try:
                rar_handle = RarFile(os.path.join(path, archive))
                rar_handle.extract(path = path, withSubpath = False, overwrite = False)
                unpacked_files += [os.path.basename(x.filename) for x in rar_handle.infolist() if not x.isdir]
                del rar_handle
            except Exception, e:
                 returnStr += logHelper(u"Failed Unrar archive " + archive + ': ' + ex(e), logger.ERROR)
                 process_result = False
                 continue
     
        returnStr += logHelper(u"UnRar content: " + str(unpacked_files), logger.DEBUG)
        
    return unpacked_files
    