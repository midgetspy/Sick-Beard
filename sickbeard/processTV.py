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
import sys
import re
from shutil import Error

from sickbeard import notifiers
from sickbeard import exceptions
from sickbeard import helpers
from sickbeard import notifiers
from sickbeard import sqlite3
from sickbeard import db
from sickbeard import history
from sickbeard import classes

from sickbeard import encodingKludge as ek

from sickbeard import logger
from sickbeard.common import *

from sickbeard.notifiers import xbmc

from lib.tvdb_api import tvnamer, tvdb_api, tvdb_exceptions

from lib.tvnamer.utils import FileParser
from lib.tvnamer import tvnamer_exceptions
#from tvdb_api.nfogen import createXBMCInfo

sample_ratio = 0.3

def renameFile(curFile, newName):

    filePath = os.path.split(curFile)
    oldFile = os.path.splitext(filePath[1])

    newFilename = ek.ek(os.path.join, filePath[0], helpers.sanitizeFileName(newName) + oldFile[1])
    
    logger.log("Renaming from " + curFile + " to " + newFilename)

    try:
        ek.ek(os.rename, curFile, newFilename)
    except (OSError, IOError), e:
        logger.log("Failed renaming " + curFile + " to " + os.path.basename(newFilename) + ": " + str(e), logger.ERROR)
        return False

    return newFilename

def copyFile(srcFile, destFile):
    shutil.copyfile(srcFile, destFile)
    try:
        shutil.copymode(srcFile, destFile)
    except OSError:
        pass

def moveFile(srcFile, destFile):
    try:
        os.rename(srcFile, destFile)
    except OSError:
        copyFile(srcFile, destFile)
        os.unlink(srcFile)


# #########################
# Find the file we're dealing with
# #########################
def findMainFile (show_dir):
    # init vars
    biggest_file = None
    biggest_file_size = 0
    next_biggest_file_size = 0

    # find the biggest file in the folder
    for file in filter(helpers.isMediaFile, ek.ek(os.listdir, show_dir)):
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
    if ek.ek(os.path.isfile, newFile):
        
        # see if it's bigger than our old file
        if ek.ek(os.path.getsize, newFile) > ek.ek(os.path.getsize, oldFile):
            return 1
        
        else:
            return -1
    
    else:
        return 0


def findInHistory(nzbName):

    nzbName = nzbName.rpartition(".")[0]
    
    if not nzbName:
        return None
    
    myDB = db.DBConnection()
    sqlResults = myDB.select("SELECT * FROM history WHERE resource = ?", [nzbName])
    
    if len(sqlResults) == 1:
        return (int(sqlResults[0]["showid"]), int(sqlResults[0]["season"]), int(sqlResults[0]["episode"]))

    else:
        return None
            

def logHelper (logMessage, logLevel=logger.MESSAGE):
    logger.log(logMessage, logLevel)
    return logMessage + "\n"


def processDir (dirName, nzbName=None, recurse=False):

    returnStr = ''

    returnStr += logHelper("Processing folder "+dirName, logger.DEBUG)

    # if they passed us a real dir then assume it's the one we want
    if os.path.isdir(dirName):
        dirName = ek.ek(os.path.realpath, dirName)
    
    # if they've got a download dir configured then use it
    elif sickbeard.TV_DOWNLOAD_DIR and os.path.isdir(sickbeard.TV_DOWNLOAD_DIR) \
            and os.path.normpath(dirName) != os.path.normpath(sickbeard.TV_DOWNLOAD_DIR):
        dirName = ek.ek(os.path.join, sickbeard.TV_DOWNLOAD_DIR, os.path.abspath(dirName).split(os.path.sep)[-1])
        returnStr += logHelper("Trying to use folder "+dirName, logger.DEBUG)

    # if we didn't find a real dir then quit
    if not ek.ek(os.path.isdir, dirName):
        returnStr += logHelper("Unable to figure out what folder to process. If your downloader and Sick Beard aren't on the same PC make sure you fill out your TV download dir in the config.", logger.DEBUG)
        return returnStr

    # TODO: check if it's failed and deal with it if it is
    if dirName.startswith('_FAILED_'):
        returnStr += logHelper("The directory name indicates it failed to extract, cancelling", logger.DEBUG)
        return returnStr
    
    # make sure the dir isn't inside a show dir
    myDB = db.DBConnection()
    sqlResults = myDB.select("SELECT * FROM tv_shows")
    for sqlShow in sqlResults:
        if dirName.lower().startswith(ek.ek(os.path.realpath, sqlShow["location"]).lower()+os.sep) or dirName.lower() == ek.ek(os.path.realpath, sqlShow["location"]).lower():
            returnStr += logHelper("You're trying to post process an episode that's already been moved to its show dir", logger.ERROR)
            return returnStr

    fileList = ek.ek(os.listdir, dirName)
    
    # split the list into video files and folders
    folders = filter(lambda x: ek.ek(os.path.isdir, ek.ek(os.path.join, dirName, x)), fileList)
    videoFiles = filter(helpers.isMediaFile, fileList)

    # recursively process all the folders
    for curFolder in folders:
        returnStr += logHelper("Recursively processing a folder: "+curFolder, logger.DEBUG)
        returnStr += processDir(ek.ek(os.path.join, dirName, curFolder), recurse=True)

    remainingFolders = filter(lambda x: ek.ek(os.path.isdir, ek.ek(os.path.join, dirName, x)), fileList)

    # process any files in the dir
    for curFile in videoFiles:
        
        curFile = ek.ek(os.path.join, dirName, curFile)
        
        # if there's only one video file in the dir we can use the dirname to process too
        if len(videoFiles) == 1:
            returnStr += logHelper("Auto processing file: "+curFile+" ("+dirName+")")
            result = processFile(curFile, dirName, nzbName)

            # as long as the postprocessing was successful delete the old folder unless the config wants us not to
            if type(result) == list:
                returnStr += result[0]

                if not sickbeard.KEEP_PROCESSED_DIR and not sickbeard.KEEP_PROCESSED_FILE and \
                    os.path.normpath(dirName) != os.path.normpath(sickbeard.TV_DOWNLOAD_DIR) and \
                    len(remainingFolders) == 0:
                    
                    returnStr += logHelper("Deleting folder " + dirName, logger.DEBUG)
                    
                    try:
                        shutil.rmtree(dirName)
                    except (OSError, IOError), e:
                        returnStr += logHelper("Warning: unable to remove the folder " + dirName + ": " + str(e), logger.ERROR)

                returnStr += logHelper("Processing succeeded for "+curFile)

            else:
                returnStr += result
                returnStr += logHelper("Processing failed for "+curFile)
            
        else:
            returnStr += logHelper("Auto processing file: "+curFile)
            result = processFile(curFile, None, nzbName)
            if type(result) == list:
                returnStr += result[0]
                returnStr += logHelper("Processing succeeded for "+curFile)
            else:
                returnStr += result
                returnStr += logHelper("Processing failed for "+curFile)

    return returnStr
            

def processFile(fileName, downloadDir=None, nzbName=None):

    returnStr = ''

    folderName = None
    if downloadDir != None:
        folderName = downloadDir.split(os.path.sep)[-1]
    
    returnStr += logHelper("Processing file "+fileName+" (with folder name "+str(folderName)+" and NZB name "+str(nzbName)+")", logger.DEBUG)

    finalNameList = []

    for curName in (fileName, folderName, nzbName):
        if curName != None:
            for curSceneName in helpers.sceneToNormalShowNames(curName):
                if curSceneName not in finalNameList:
                    finalNameList.append(curSceneName)

    showResults = None
    result = None
    
    tvdb_id = None
    season = None
    episodes = []
        
    # first try looking up every name in our history
    for curName in finalNameList:

        historyResult = findInHistory(curName)
        if historyResult:
            returnStr += logHelper("Result from history: "+str(historyResult)+" from "+curName, logger.DEBUG)
            (tvdb_id, season, episode) = historyResult
            episodes = [episode]
            showResults = helpers.findCertainShow(sickbeard.showList, tvdb_id)
            break

    # if that didn't work then try manually parsing and searching them on TVDB
    for curName in finalNameList:
        
        # if we already have the info from the history then don't bother with this
        if tvdb_id != None and season != None and episodes != []:
            break

        # set all search stuff to defaults so we don't carry results over from the last iteration
        tvdb_id = None
        season = None
        episodes = []
        
        try:
            returnStr += logHelper("Attempting to parse name "+curName, logger.DEBUG)
            myParser = FileParser(curName)
            result = myParser.parse()
            season = result.seasonnumber
            episodes = result.episodenumbers
        except tvnamer_exceptions.InvalidFilename:
            returnStr += logHelper("Unable to parse the filename "+curName+" into a valid episode", logger.DEBUG)
            continue

        if not result.seriesname:
            returnStr += logHelper("Filename "+curName+" has no series name, unable to use this name for processing", logger.DEBUG)
            continue

        try:
            returnStr += logHelper("Looking up name "+result.seriesname+" on TVDB", logger.DEBUG)
            t = tvdb_api.Tvdb(custom_ui=classes.ShowListUI, **sickbeard.TVDB_API_PARMS)
            showObj = t[result.seriesname]
            showInfo = (int(showObj["id"]), showObj["seriesname"])
        except (tvdb_exceptions.tvdb_exception, IOError), e:

            returnStr += logHelper("Unable to look up show on TVDB: "+str(e), logger.DEBUG)
            returnStr += logHelper("Looking up show in DB instead", logger.DEBUG)
            showInfo = helpers.searchDBForShow(result.seriesname)

        if showInfo:
            tvdb_id = showInfo[0]
            
        # if we couldn't get the necessary info from either of the above methods, try the next name
        if tvdb_id == None or season == None or episodes == []:
            continue

        # find the show in the showlist
        try:
            showResults = helpers.findCertainShow(sickbeard.showList, showInfo[0])
        except exceptions.MultipleShowObjectsException:
            raise #TODO: later I'll just log this, for now I want to know about it ASAP
        
        if showResults != None:
            returnStr += logHelper("Found the show in our list, continuing", logger.DEBUG)
            break
    
    # end for
        
    # if we came out of the loop with not enough info then give up
    if tvdb_id == None or season == None or episodes == []:
        returnStr += logHelper("Unable to figure out what this episode is, giving up", logger.DEBUG)
        return returnStr

    # if we found enough info but it wasn't a show we know about, give up
    if showResults == None:
        returnStr += logHelper("The episode doesn't match a show in my list - bad naming?", logger.DEBUG)
        return returnStr

    # if we DO know about the show but its dir is offline, give up
    if not os.path.isdir(showResults._location):
        returnStr += logHelper("The show dir doesn't exist, canceling postprocessing", logger.DEBUG)
        return returnStr


    rootEp = None
    for curEpisode in episodes:
        episode = int(curEpisode)
    
        returnStr += logHelper("TVDB thinks the file is tvdb_id = " + str(tvdb_id) + " " + str(season) + "x" + str(episode), logger.DEBUG)
        
        # now that we've figured out which episode this file is just load it manually
        try:        
            curEp = showResults.getEpisode(season, episode)
        except exceptions.EpisodeNotFoundException, e:
            returnStr += logHelper("Unable to create episode: "+str(e), logger.DEBUG)
            return returnStr
        
        if rootEp == None:
            rootEp = curEp
            rootEp.relatedEps = []
        else:
            rootEp.relatedEps.append(curEp)

    # figure out the new filename
    biggestFileName = os.path.basename(fileName)
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

    returnStr += logHelper("Seasonfolders were " + str(rootEp.show.seasonfolders) + " which gave " + seasonFolder, logger.DEBUG)

    destDir = os.path.join(rootEp.show.location, seasonFolder)
    
    curFile = os.path.join(destDir, biggestFileName)
    newFile = os.path.join(destDir, helpers.sanitizeFileName(rootEp.prettyName())+biggestFileExt)
    returnStr += logHelper("The ultimate destination for " + fileName + " is " + newFile, logger.DEBUG)

    existingResult = _checkForExistingFile(newFile, fileName)
    
    # if there's no file with that exact filename then check for a different episode file (in case we're going to delete it)
    if existingResult == 0:
        existingResult = _checkForExistingFile(rootEp.location, fileName)
        if existingResult == -1:
            existingResult = -2
        if existingResult == 1:
            existingResult = 2
    
    returnStr += logHelper("Existing result: "+str(existingResult), logger.DEBUG)
    
    # see if the existing file is bigger - if it is, bail (unless it's a proper in which case we're forcing an overwrite)
    if existingResult > 0:
        if rootEp.status == SNATCHED_PROPER:
            returnStr += logHelper("There is already a file that's bigger at "+newFile+" but I'm going to overwrite it with a PROPER", logger.DEBUG)
        else:
            returnStr += logHelper("There is already a file that's bigger at "+newFile+" - not processing this episode.", logger.DEBUG)
            return returnStr
        
    # if the dir doesn't exist (new season folder) then make it
    if not os.path.isdir(destDir):
        returnStr += logHelper("Season folder didn't exist, creating it", logger.DEBUG)
        os.mkdir(destDir)

    if sickbeard.KEEP_PROCESSED_FILE:
        returnStr += logHelper("Copying from " + fileName + " to " + destDir, logger.DEBUG)
        try:
            copyFile(fileName, curFile)
           
            returnStr += logHelper("File was copied successfully", logger.DEBUG)
            
        except (Error, IOError, OSError), e:
            returnStr += logHelper("Unable to copy the file: " + str(e), logger.ERROR)
            return returnStr

    else:

        returnStr += logHelper("Moving from " + fileName + " to " + destDir, logger.DEBUG)
        try:
            moveFile(fileName, curFile)
            
            returnStr += logHelper("File was moved successfully", logger.DEBUG)
            
        except (Error, IOError, OSError), e:
            returnStr += logHelper("Unable to move the file: " + str(e), logger.ERROR)
            return returnStr

    # if the file existed and was smaller then lets delete it
    # OR if the file existed, was bigger, but we want to replace it anyway cause it's a PROPER snatch
    if existingResult < 0 or (existingResult > 0 and rootEp.status == SNATCHED_PROPER):
        # if we're deleting a file with a different name then just go ahead
        if existingResult in (-2, 2):
            existingFile = rootEp.location
            if rootEp.status == SNATCHED_PROPER:
                returnStr += logHelper(existingFile + " already exists and is larger but I'm deleting it to make way for the proper", logger.DEBUG)
            else:
                returnStr += logHelper(existingFile + " already exists but it's smaller than the new file so I'm replacing it", logger.DEBUG)
            #TODO: delete old metadata?
        else:
            returnStr += logHelper(newFile + " already exists but it's smaller than the new file so I'm replacing it", logger.DEBUG)
            existingFile = newFile
        
        os.remove(existingFile)
            
    if sickbeard.RENAME_EPISODES:
        try:
            os.rename(curFile, newFile)
            returnStr += logHelper("Renaming the file " + curFile + " to " + newFile, logger.DEBUG)
        except (OSError, IOError), e:
            returnStr += logHelper("Failed renaming " + curFile + " to " + newFile + ": " + str(e), logger.ERROR)
            return returnStr

    else:
        returnStr += logHelper("Renaming is disabled, leaving file as "+curFile, logger.DEBUG)
        newFile = curFile

    for curEp in [rootEp] + rootEp.relatedEps:
        with curEp.lock:
            curEp.location = newFile
            
            # don't mess up the status - if this is a legit download it should be SNATCHED
            if curEp.status != PREDOWNLOADED:
                curEp.status = DOWNLOADED
            curEp.saveToDB()

    # log it to history
    history.logDownload(rootEp, fileName)

    notifiers.notify(NOTIFY_DOWNLOAD, rootEp.prettyName(True))

    
    # generate nfo/tbn
    rootEp.createMetaFiles()
    rootEp.saveToDB()

    # we don't want to put predownloads in the library until we can deal with removing them
    if sickbeard.XBMC_UPDATE_LIBRARY == True and rootEp.status != PREDOWNLOADED:
        notifiers.xbmc.updateLibrary(rootEp.show.location)

    returnStr += logHelper("Post processing finished successfully", logger.DEBUG)

    return [returnStr]
