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

import contactXBMC
import exceptions
import helpers
import sickbeard
import sqlite3
import db
import history

from logging import *
from common import *

from sickbeard import classes
from lib.tvdb_api import tvnamer, tvdb_api, tvdb_exceptions

#from tvdb_api.nfogen import createXBMCInfo

sample_ratio = 0.3

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
        Logger().log("Multiple files in the folder are comparably large, giving up", ERROR)
        return None

    return os.path.join(show_dir, biggest_file)


# ########################
# Checks if another file exists already, if it
# does then we replace only if it's larger.
# ########################      
def moveEpisode(file, ep):

    # if the ep already has an associated file
    if ep.location != None and os.path.isfile(ep.location):
        
        Logger().log("The episode already has a file downloaded", DEBUG)
        
        # see if it's smaller than our new file
        if os.path.getsize(file) > os.path.getsize(ep.location):
            
            Logger().log("The old file is smaller, replacing it", DEBUG)

            try:
                os.remove(ep.location)
                Logger().log("Deleted " + str(ep.location), DEBUG)
                with ep.lock:
                    ep.location = None
            except OSError as e:
                Logger().log("Unable to delete existing file, it's probably in use (" + str(e) + ")", ERROR)

    # move it to the right folder
    if ep.show.seasonfolders == True:
        seasonFolder = 'Season ' + str(ep.season)
    else:
        seasonFolder = ''
    Logger().log("Seasonfolders were " + str(ep.show.seasonfolders) + " which gave " + seasonFolder, DEBUG)

    destDir = os.path.join(ep.show.location, seasonFolder)
    
    # if the dir doesn't exist (new season folder) then make it
    if not os.path.isdir(destDir):
        Logger().log("Season folder didn't exist, creating it", DEBUG)
        os.mkdir(destDir)

    Logger().log("Moving from " + file + " to " + destDir, DEBUG)
    try:
        shutil.move(file, destDir)
        for curEp in [ep] + ep.relatedEps:
            with curEp.lock:
                curEp.location = os.path.join(destDir, os.path.basename(file))
                
                # don't mess up the status - if this is a legit download it should be SNATCHED
                if curEp.status != PREDOWNLOADED:
                    curEp.status = DOWNLOADED
                curEp.saveToDB()

    except IOError as e:
        Logger().log("Unable to move the file: " + str(e), ERROR)
        return False

    return True


def renameFile(curFile, newName):

    filePath = os.path.split(curFile)
    oldFile = os.path.splitext(filePath[1])

    newFilename = os.path.join(filePath[0], helpers.sanitizeFileName(newName) + oldFile[1])
    Logger().log("Renaming from " + curFile + " to " + newFilename)

    try:
        os.rename(curFile, newFilename)
    except (OSError, IOError) as e:
        Logger().log("Failed renaming " + curFile + " to " + os.path.basename(newFilename) + ": " + str(e), ERROR)
        return False

    return newFilename


def doIt(downloadDir, showList):
    
    returnStr = ""
    
    if not os.path.isdir(downloadDir):
        return "Uh, this is not a directory: " + str(downloadDir)
    
    # pretty up the path, just in case
    downloadDir = os.path.abspath(downloadDir)
    logStr = "Pretty'd up folder is " + downloadDir
    Logger().log(logStr, DEBUG)
    returnStr += logStr + "\n"
    
    # TODO: check if it's failed and deal with it if it is
    if downloadDir.startswith('_FAILED_'):
        logStr = "The directory name indicates it failed to extract, cancelling"
        Logger().log(logStr, DEBUG)
        returnStr += logStr + "\n"
        return returnStr
    
    # find the file we're dealing with
    biggest_file = findMainFile(downloadDir)
    if biggest_file == None:
        logStr = "Unable to find the biggest file - is this really a TV download?"
        Logger().log(logStr, DEBUG)
        returnStr += logStr + "\n"
        return returnStr
        
    logStr = "The biggest file in the dir is: " + biggest_file
    Logger().log(logStr, DEBUG)
    returnStr += logStr + "\n"
    
    # try to use the file name to get the episode
    result = None
    for curName in (biggest_file, downloadDir.split(os.path.sep)[-1]):
    
        result = tvnamer.processSingleName(curName)
        logStr = curName + " parsed into: " + str(result)
        Logger().log(logStr, DEBUG)
        returnStr += logStr + "\n"
    
        # if this one doesn't work try the next one
        if result == None:
            logStr = "Unable to parse this name"
            Logger().log(logStr, DEBUG)
            returnStr += logStr + "\n"
            continue

        try:
            t = tvdb_api.Tvdb(custom_ui=classes.ShowListUI, lastTimeout=sickbeard.LAST_TVDB_TIMEOUT)
            showObj = t[result["file_seriesname"]]
            showInfo = (int(showObj["id"]), showObj["seriesname"])
        except (tvdb_exceptions.tvdb_error, IOError) as e:

            logStr = "TVDB didn't respond, trying to look up the show in the DB instead"
            Logger().log(logStr, DEBUG)
            returnStr += logStr + "\n"

            showInfo = helpers.searchDBForShow(result["file_seriesname"])
            
        # if we didn't get anything from TVDB or the DB then try the next option
        if showInfo == None:
            continue

        # find the show in the showlist
        try:
            showResults = helpers.findCertainShow(showList, showInfo[0])
        except exceptions.MultipleShowObjectsException:
            raise #TODO: later I'll just log this, for now I want to know about it ASAP
        
        if showResults != None:
            logStr = "Found the show in our list, continuing"
            Logger().log(logStr, DEBUG)
            returnStr += logStr + "\n"
            break
    
    # end for
        
    if result == None:
        logStr = "Unable to figure out what this episode is, giving up"
        Logger().log(logStr, DEBUG)
        returnStr += logStr + "\n"
        return returnStr

    if showResults == None:
        logStr = "The episode doesn't match a show in my list - bad naming?"
        Logger().log(logStr, DEBUG)
        returnStr += logStr + "\n"
        return returnStr

    
    # get or create the episode (should be created probably, but not for sure)
    season = int(result["seasno"])

    rootEp = None
    for curEpisode in result["epno"]:
        episode = int(curEpisode)
    
        logStr = "TVDB thinks the file is " + showInfo[1] + str(season) + "x" + str(episode)
        Logger().log(logStr, DEBUG)
        returnStr += logStr + "\n"
        
        # now that we've figured out which episode this file is just load it manually
        curEp = showResults.getEpisode(season, episode, True)
        
        if rootEp == None:
            rootEp = curEp
            rootEp.relatedEps = []
        else:
            rootEp.relatedEps.append(curEp)

    # log it to history
    history.logDownload(rootEp, biggest_file)


    # wait for the copy to finish

    if sickbeard.XBMC_NOTIFY_ONDOWNLOAD == True:
        contactXBMC.notifyXBMC(rootEp.prettyName(), "Download finished")

    # move it to the show folder
    #result = moveEpisode(os.path.join(downloadDir, os.path.basename(result)), rootEp)
    result = moveEpisode(biggest_file, rootEp)
    if result == True:
        logStr = "File was moved successfully"
        Logger().log(logStr, DEBUG)
        returnStr += logStr + "\n"
    else:
        logStr = "I couldn't move it, giving up"
        Logger().log(logStr, DEBUG)
        returnStr += logStr + "\n"
        return returnStr

    # rename it
    logStr = "Renaming the file " + rootEp.location + " to " + rootEp.prettyName()
    Logger().log(logStr, DEBUG)
    returnStr += logStr + "\n"
    
    result = renameFile(rootEp.location, rootEp.prettyName())

    if result == False:
        logStr = "ERROR: Unable to rename the file " + rootEp.location
        Logger().log(logStr, DEBUG)
        returnStr += logStr + "\n"
        return logStr

    with rootEp.lock:
        rootEp.location = result
        rootEp.saveToDB()
    
    # generate nfo/tbn
    rootEp.createMetaFiles()
    rootEp.saveToDB()

    logStr = "Deleting folder " + downloadDir
    Logger().log(logStr, DEBUG)
    returnStr += logStr + "\n"
    
    # we don't want to put predownloads in the library until we can deal with removing them
    if sickbeard.XBMC_UPDATE_LIBRARY == True and rootEp.status != PREDOWNLOADED:
        contactXBMC.updateLibrary(rootEp.show.location)

    # delete the old folder full of useless files
    try:
        shutil.rmtree(downloadDir)
    except (OSError, IOError) as e:
        logStr = "Warning: unable to remove the folder " + downloadDir + ": " + str(e)
        Logger().log(logStr, ERROR)
        returnStr += logStr + "\n"

    return returnStr

if __name__ == "__main__":
    doIt(sys.argv[1])
