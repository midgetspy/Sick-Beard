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
from sickbeard.name_parser.parser import NameParser, InvalidNameException


def logHelper (logMessage, logLevel=logger.MESSAGE):
    logger.log(logMessage, logLevel)
    return logMessage + u"\n"

def processDir (dirName, nzbName=None, recurse=False):
    """
    Scans through the files in dirName and processes whatever media files it finds
    
    dirName: The folder name to look in
    nzbName: The NZB name which resulted in this folder being downloaded
    """

    REMOTE_DBG = True
    
    if REMOTE_DBG:
            # Make pydev debugger works for auto reload.
            # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
        try:
            import pysrc.pydevd as pydevd
            # stdoutToServer and stderrToServer redirect stdout and stderr to eclipse console
            pydevd.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True)
        except ImportError:
            sys.stderr.write("Error: " +
                    "You must add org.python.pydev.debug.pysrc to your PYTHONPATH.")
            sys.exit(1) 

    returnStr = ''

    returnStr += logHelper(u"Processing folder "+dirName, logger.DEBUG)

    if dirName == sickbeard.TV_DOWNLOAD_DIR: #Automatic Post Processing Active
        #Get at first all the subdir in the dirName
        for path, dirs, files in ek.ek(os.walk, dirName):
            break
    else:
        path, dirs = ek.ek(os.path.split, dirName)
        files = ek.ek(os.listdir, dirName)
        dirs = [dirs]

    process_result = False
    videoFiles = filter(helpers.isMediaFile, files)

    # If nzbName is set and there's more than one videofile in the folder, files will be lost (overwritten).
    if nzbName != None and len(videoFiles) >= 2:
        nzbName = None

    #Process Video File in the current Path
    for cur_video_file in videoFiles:

        cur_video_file_path = ek.ek(os.path.join, dirName, cur_video_file)
            
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
    for dir in [x for x in dirs if validateDir(path, x, returnStr)]:

        process_result = False

        for processPath, processDir, fileList in ek.ek(os.walk, ek.ek(os.path.join, path, dir), topdown=False):

            videoFiles = filter(helpers.isMediaFile, fileList)
            notwantedFiles = [x for x in fileList if x not in videoFiles]

            # If nzbName is set and there's more than one videofile in the folder, files will be lost (overwritten).
            if nzbName != None and len(videoFiles) >= 2:
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
                    
            #Delete all file not needed
            for cur_file in notwantedFiles:
                if sickbeard.KEEP_PROCESSED_DIR or not process_result:
                    break

                cur_file_path = ek.ek(os.path.join, processPath, cur_file)
                    
                try:
                    processor = postProcessor.PostProcessor(cur_file_path, nzbName)
                    processor._delete(cur_file_path)
                    returnStr += logHelper(u"Deleting succeeded for " + cur_file_path, logger.DEBUG)
                except exceptions.PostProcessingFailed, e:
                    process_fail_message = ex(e)

                returnStr += processor.log

            if not sickbeard.KEEP_PROCESSED_DIR and \
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

def validateDir(path, dirName, returnStr):

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

    try:
        np = NameParser(dirName)
        parse_result = np.parse(dirName)
    except InvalidNameException:
        
        #Try to parse files name if any 
        fileList = ek.ek(os.listdir, ek.ek(os.path.join, path, dirName))
        videoFiles = filter(helpers.isMediaFile, fileList)
        
        if not videoFiles:
            return False
        
        #Be strict for bad named folder
        for cur_video_file in videoFiles:
            try:
                np = NameParser(cur_video_file)
                parse_result = np.parse(cur_video_file)
            except InvalidNameException:
                returnStr += logHelper(u"Folder " + dirName +  " seems to Not Contain TV, skipping it", logger.DEBUG)
                return False
    
    # make sure the dir isn't inside a show dir
    myDB = db.DBConnection()
    sqlResults = myDB.select("SELECT * FROM tv_shows")
    for sqlShow in sqlResults:
        if dirName.lower().startswith(ek.ek(os.path.realpath, sqlShow["location"]).lower()+os.sep) or dirName.lower() == ek.ek(os.path.realpath, sqlShow["location"]).lower():
            returnStr += logHelper(u"You're trying to post process an episode that's already been moved to its show dir", logger.ERROR)
            return False
    
    return True
