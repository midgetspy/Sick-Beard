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



import os
import shutil
import sys
import re

from sickbeard import notifiers
from sickbeard import exceptions
from sickbeard import helpers
from sickbeard import notifiers
from sickbeard import sqlite3
from sickbeard import db
from sickbeard import history
from sickbeard import classes

from sickbeard import logger
from sickbeard.common import *

from sickbeard.notifiers import xbmc

from lib.tvdb_api import tvnamer, tvdb_api, tvdb_exceptions

#from tvdb_api.nfogen import createXBMCInfo

sample_ratio = 0.3

def renameFile(curFile, newName):

    filePath = os.path.split(curFile)
    oldFile = os.path.splitext(filePath[1])

    newFilename = os.path.join(filePath[0], helpers.sanitizeFileName(newName) + oldFile[1])
    logger.log("Renaming from " + curFile + " to " + newFilename)

    try:
        os.rename(curFile, newFilename)
    except (OSError, IOError) as e:
        logger.log("Failed renaming " + curFile + " to " + os.path.basename(newFilename) + ": " + str(e), logger.ERROR)
        return False

    return newFilename


# #########################
# Find the file we're dealing with
# #########################
def findMainFile (show_dir):
    # init vars
    biggest_file = None
    biggest_file_size = 0
    next_biggest_file_size = 0

    # find the biggest file in the folder
    for file in filter(helpers.isMediaFile, os.listdir(show_dir)):
        cur_size = os.path.getsize(os.path.join(show_dir, file))
        if cur_size > biggest_file_size:
            biggest_file = file
            next_biggest_file_size = biggest_file_size
            biggest_file_size = cur_size

    if biggest_file == None:
        return biggest_file

    # it should be by far the biggest file in the folder. If it isn't, we have a problem (multi-show nzb or something, not going to deal with it)
    if float(next_biggest_file_size) / float(biggest_file_size) > sample_ratio:
        logger.log("Multiple files in the folder are comparably large, giving up", logger.ERROR)
        return None

    return os.path.join(show_dir, biggest_file)


def _checkForExistingFile(newFile, oldFile):

    # if the new file exists, return the appropriate code depending on the size
    if os.path.isfile(newFile):
        
        # see if it's bigger than our old file
        if os.path.getsize(newFile) > os.path.getsize(oldFile):
            return 1
        
        else:
            return -1
    
    else:
        return 0
            


def doIt(downloaderDir, nzbName=None):
    
    returnStr = ""

    downloadDir = ''

    # if they passed us a real dir then assume it's the one we want
    if os.path.isdir(downloaderDir):
        downloadDir = os.path.abspath(downloaderDir)
    
    # if they've got a download dir configured then use it
    elif sickbeard.TV_DOWNLOAD_DIR != '' and os.path.isdir(sickbeard.TV_DOWNLOAD_DIR):
        downloadDir = os.path.join(sickbeard.TV_DOWNLOAD_DIR, os.path.abspath(downloaderDir).split(os.path.sep)[-1])

        logStr = "Trying to use folder "+downloadDir
        logger.log(logStr, logger.DEBUG)
        returnStr += logStr + "\n"

    # if we didn't find a real dir then quit
    if not os.path.isdir(downloadDir):
        logStr = "Unable to figure out what folder to process. If your downloader and Sick Beard aren't on the same PC make sure you fill out your TV download dir in the config."
        logger.log(logStr, logger.DEBUG)
        returnStr += logStr + "\n"
        return returnStr

    logStr = "Final folder name is " + downloadDir
    logger.log(logStr, logger.DEBUG)
    returnStr += logStr + "\n"
    
    # TODO: check if it's failed and deal with it if it is
    if downloadDir.startswith('_FAILED_'):
        logStr = "The directory name indicates it failed to extract, cancelling"
        logger.log(logStr, logger.DEBUG)
        returnStr += logStr + "\n"
        return returnStr
    
    # find the file we're dealing with
    biggest_file = findMainFile(downloadDir)
    if biggest_file == None:
        logStr = "Unable to find the biggest file - is this really a TV download?"
        logger.log(logStr, logger.DEBUG)
        returnStr += logStr + "\n"
        return returnStr
        
    logStr = "The biggest file in the dir is: " + biggest_file
    logger.log(logStr, logger.DEBUG)
    returnStr += logStr + "\n"
    
    # use file name, folder name, and NZB name (in that order) to try to figure out the episode info
    result = None
    nameList = [biggest_file, downloadDir.split(os.path.sep)[-1]]
    if nzbName != None:
        nameList.append(nzbName)
    
    showResults = None
    
    for curName in nameList:
    
        result = tvnamer.processSingleName(curName)
        logStr = curName + " parsed into: " + str(result)
        logger.log(logStr, logger.DEBUG)
        returnStr += logStr + "\n"
    
        # if this one doesn't work try the next one
        if result == None:
            logStr = "Unable to parse this name"
            logger.log(logStr, logger.DEBUG)
            returnStr += logStr + "\n"
            continue

        try:
            t = tvdb_api.Tvdb(custom_ui=classes.ShowListUI, lastTimeout=sickbeard.LAST_TVDB_TIMEOUT)
            showObj = t[result["file_seriesname"]]
            showInfo = (int(showObj["id"]), showObj["seriesname"])
        except (tvdb_exceptions.tvdb_exception, IOError) as e:

            logStr = "TVDB didn't respond, trying to look up the show in the DB instead"
            logger.log(logStr, logger.DEBUG)
            returnStr += logStr + "\n"

            showInfo = helpers.searchDBForShow(result["file_seriesname"])
            
        # if we didn't get anything from TVDB or the DB then try the next option
        if showInfo == None:
            continue

        # find the show in the showlist
        try:
            showResults = helpers.findCertainShow(sickbeard.showList, showInfo[0])
        except exceptions.MultipleShowObjectsException:
            raise #TODO: later I'll just log this, for now I want to know about it ASAP
        
        if showResults != None:
            logStr = "Found the show in our list, continuing"
            logger.log(logStr, logger.DEBUG)
            returnStr += logStr + "\n"
            break
    
    # end for
        
    if result == None:
        logStr = "Unable to figure out what this episode is, giving up"
        logger.log(logStr, logger.DEBUG)
        returnStr += logStr + "\n"
        return returnStr

    if showResults == None:
        logStr = "The episode doesn't match a show in my list - bad naming?"
        logger.log(logStr, logger.DEBUG)
        returnStr += logStr + "\n"
        return returnStr

    if not os.path.isdir(showResults._location):
        logStr = "The show dir doesn't exist, canceling postprocessing"
        logger.log(logStr, logger.DEBUG)
        returnStr += logStr + "\n"
        return returnStr

    
    # get or create the episode (should be created probably, but not for sure)
    season = int(result["seasno"])

    rootEp = None
    for curEpisode in result["epno"]:
        episode = int(curEpisode)
    
        logStr = "TVDB thinks the file is " + showInfo[1] + str(season) + "x" + str(episode)
        logger.log(logStr, logger.DEBUG)
        returnStr += logStr + "\n"
        
        # now that we've figured out which episode this file is just load it manually
        curEp = showResults.getEpisode(season, episode)
        
        if rootEp == None:
            rootEp = curEp
            rootEp.relatedEps = []
        else:
            rootEp.relatedEps.append(curEp)

    # log it to history
    history.logDownload(rootEp, biggest_file)

    # wait for the copy to finish

    notifiers.notify(NOTIFY_DOWNLOAD, rootEp.prettyName())


    # figure out the new filename
    biggestFileName = os.path.basename(biggest_file)
    biggestFileExt = os.path.splitext(biggestFileName)[1]

    # if we're supposed to put it in a season folder then figure out what folder to use
    seasonFolder = ''
    if rootEp.show.seasonfolders == True:
        
        # search the show dir for season folders
        for curDir in os.listdir(rootEp.show.location):

            if not os.path.isdir(os.path.join(rootEp.show.location, curDir)):
                continue
            
            # if it's a season folder, check if it's the one we want
            match = re.match("[Ss]eason\s*(\d+)", curDir)
            if match != None:
                # if it's the correct season folder then stop looking
                if int(match.group(1)) == int(rootEp.season):
                    seasonFolder = curDir
                    break 

        # if we couldn't find the right one then just assume "Season X" format is what we want
        if seasonFolder == '':
            seasonFolder = 'Season ' + str(rootEp.season)

    logStr = "Seasonfolders were " + str(rootEp.show.seasonfolders) + " which gave " + seasonFolder
    logger.log(logStr, logger.DEBUG)
    returnStr += logStr + "\n"

    destDir = os.path.join(rootEp.show.location, seasonFolder)
    
    newFile = os.path.join(destDir, helpers.sanitizeFileName(rootEp.prettyName())+biggestFileExt)
    logStr = "The ultimate destination for " + biggest_file + " is " + newFile
    logger.log(logStr, logger.DEBUG)
    returnStr += logStr + "\n"

    existingResult = _checkForExistingFile(newFile, biggest_file)
    
    # if there's no file with that exact filename then check for a different episode file (in case we're going to delete it)
    if existingResult == 0:
        existingResult = _checkForExistingFile(rootEp.location, biggest_file)
        if existingResult == -1:
            existingResult = -2
    
    # see if the existing file is bigger - if it is, bail
    if existingResult == 1:
        logStr = "There is already a file that's bigger at "+newFile+" - not processing this episode."
        logger.log(logStr, logger.DEBUG)
        returnStr += logStr + "\n"
        return returnStr
        
    # if the dir doesn't exist (new season folder) then make it
    if not os.path.isdir(destDir):
        logStr = "Season folder didn't exist, creating it"
        logger.log(logStr, logger.DEBUG)
        returnStr += logStr + "\n"
        os.mkdir(destDir)

    logger.log("Moving from " + biggest_file + " to " + destDir, logger.DEBUG)
    try:
        shutil.move(biggest_file, destDir)
        
        logStr = "File was moved successfully"
        logger.log(logStr, logger.DEBUG)
        returnStr += logStr + "\n"
        
    except IOError as e:
        logStr = "Unable to move the file: " + str(e)
        logger.log(logStr, logger.ERROR)
        returnStr += logStr + "\n"
        return returnStr

    # if the file existed and was smaller then lets delete it
    if existingResult < 0:
        if existingResult == -1:
            existingFile = newFile
        elif existingResult == -2:
            existingFile = rootEp.location
        
        logStr = existingFile + " already exists but it's smaller than the new file so I'm replacing it"
        logger.log(logStr, logger.DEBUG)
        returnStr += logStr + "\n"
        os.remove(existingFile)

    curFile = os.path.join(destDir, biggestFileName)

    try:
        os.rename(curFile, newFile)
        logStr = "Renaming the file " + curFile + " to " + newFile
        logger.log(logStr, logger.DEBUG)
        returnStr += logStr + "\n"
    except (OSError, IOError) as e:
        logStr = "Failed renaming " + curFile + " to " + newFile + ": " + str(e)
        logger.log(logStr, logger.ERROR)
        returnStr += logStr + "\n"
        return returnStr

    for curEp in [rootEp] + rootEp.relatedEps:
        with curEp.lock:
            curEp.location = newFile
            
            # don't mess up the status - if this is a legit download it should be SNATCHED
            if curEp.status != PREDOWNLOADED:
                curEp.status = DOWNLOADED
            curEp.saveToDB()

    
    # generate nfo/tbn
    rootEp.createMetaFiles()
    rootEp.saveToDB()

    # we don't want to put predownloads in the library until we can deal with removing them
    if sickbeard.XBMC_UPDATE_LIBRARY == True and rootEp.status != PREDOWNLOADED:
        notifiers.xbmc.updateLibrary(rootEp.show.location)

    # delete the old folder unless the config wants us not to
    if not sickbeard.KEEP_PROCESSED_DIR:
        logStr = "Deleting folder " + downloadDir
        logger.log(logStr, logger.DEBUG)
        returnStr += logStr + "\n"
        
        try:
            shutil.rmtree(downloadDir)
        except (OSError, IOError) as e:
            logStr = "Warning: unable to remove the folder " + downloadDir + ": " + str(e)
            logger.log(logStr, logger.ERROR)
            returnStr += logStr + "\n"

    return returnStr

if __name__ == "__main__":
    doIt(sys.argv[1])
