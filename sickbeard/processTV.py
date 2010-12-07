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

import os, subprocess, shlex, os.path
import shutil
import re
import glob
from shutil import Error

from sickbeard import exceptions
from sickbeard import notifiers
from sickbeard import db, classes, helpers, sceneHelpers
from sickbeard import history

from sickbeard import encodingKludge as ek

from sickbeard import logger
from sickbeard.common import *

from sickbeard.notifiers import xbmc

from lib.tvdb_api import tvnamer, tvdb_api, tvdb_exceptions

from lib.tvnamer.utils import FileParser
from lib.tvnamer import tvnamer_exceptions
#from tvdb_api.nfogen import createXBMCInfo

sample_ratio = 0.3

def renameFile(movedFilePath, newName):

    filePath = os.path.split(movedFilePath)
    oldFile = os.path.splitext(filePath[1])

    renamedFilePathname = ek.ek(os.path.join, filePath[0], helpers.sanitizeFileName(newName) + oldFile[1])

    logger.log(u"Renaming from " + movedFilePath + " to " + renamedFilePathname)

    try:
        ek.ek(os.rename, movedFilePath, renamedFilePathname)
    except (OSError, IOError), e:
        logger.log(u"Failed renaming " + movedFilePath + " to " + ek.ek(os.path.basename, renamedFilePathname) + ": " + str(e), logger.ERROR)
        return False

    return renamedFilePathname

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

def deleteAssociatedFiles(file):

    if not ek.ek(os.path.isfile, file):
        return

    baseName = file.rpartition('.')[0]+'.'

    for associatedFilePath in ek.ek(glob.glob, baseName+'*'):
        # only delete it if the only non-shared part is the extension
        if '.' in associatedFilePath[len(baseName):]:
            logger.log(u"Not deleting file "+associatedFilePath+u" because it looks like it's not related", logger.DEBUG)
            continue
        logger.log(u"Deleting file "+associatedFilePath+u" because it is associated with "+file, logger.DEBUG)
        ek.ek(os.remove, associatedFilePath)

def _checkForExistingFile(renamedFilePath, oldFile):

    # if the new file exists, return the appropriate code depending on the size
    if ek.ek(os.path.isfile, renamedFilePath):

        # see if it's bigger than our old file
        if ek.ek(os.path.getsize, renamedFilePath) >= ek.ek(os.path.getsize, oldFile):
            return 1

        else:
            return -1

    else:
        return 0


def findInHistory(nzbName):

    names = [nzbName, nzbName.rpartition(".")[0]]

    if not nzbName:
        return None

    myDB = db.DBConnection()

    for curName in names:
        sqlResults = myDB.select("SELECT * FROM history WHERE resource LIKE ?", [re.sub("[\.\-\ ]", "_", curName)])

        if len(sqlResults) == 0:
            continue

        tvdb_id = int(sqlResults[0]["showid"])
        season = int(sqlResults[0]["season"])
        episodes = []

        for cur_result in sqlResults:
            episodes.append(int(cur_result["episode"]))            

        return (tvdb_id, season, list(set(episodes)))

    return None


def logHelper (logMessage, logLevel=logger.MESSAGE):
    logger.log(logMessage, logLevel)
    return logMessage + u"\n"


def processDir (dirName, nzbName=None, recurse=False):

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

    # process any files in the dir
    for movedFilePath in videoFiles:

        movedFilePath = ek.ek(os.path.join, dirName, movedFilePath)

        # if there's only one video file in the dir we can use the dirname to process too
        if len(videoFiles) == 1:
            returnStr += logHelper(u"Auto processing file: "+movedFilePath+u" ("+dirName+u")")
            result = processFile(movedFilePath, dirName, nzbName)

            # as long as the postprocessing was successful delete the old folder unless the config wants us not to
            if type(result) == list:
                returnStr += result[0]

                if not sickbeard.KEEP_PROCESSED_DIR and \
                    ek.ek(os.path.normpath, dirName) != ek.ek(os.path.normpath, sickbeard.TV_DOWNLOAD_DIR) and \
                    len(remainingFolders) == 0:

                    returnStr += logHelper(u"Deleting folder " + dirName, logger.DEBUG)

                    try:
                        shutil.rmtree(dirName)
                    except (OSError, IOError), e:
                        returnStr += logHelper(u"Warning: unable to remove the folder " + dirName + ": " + str(e), logger.ERROR)

                returnStr += logHelper(u"Processing succeeded for "+movedFilePath)

            else:
                returnStr += result
                returnStr += logHelper(u"Processing failed for "+movedFilePath)

        else:
            returnStr += logHelper(u"Auto processing file: "+movedFilePath)
            result = processFile(movedFilePath, dirName, nzbName, multi_file=True)
            if type(result) == list:
                returnStr += result[0]
                returnStr += logHelper(u"Processing succeeded for "+movedFilePath)
            else:
                returnStr += result
                returnStr += logHelper(u"Processing failed for "+movedFilePath)

    return returnStr


def processFile(fileName, downloadDir=None, nzbName=None, multi_file=False):

    logger.log(u"fileName: "+repr(fileName)+u" downloadDir: "+repr(downloadDir)+u" nzbName: "+repr(nzbName), logger.DEBUG)

    returnStr = ''

    folderName = ''
    if downloadDir != None:
        folderName = downloadDir.split(os.path.sep)[-1]

    if not nzbName:
        nzbName = ''

    returnStr += logHelper(u"Processing file "+fileName+u" (with folder name "+folderName+u" and NZB name "+nzbName+u")", logger.DEBUG)

    finalNameList = []

    for curName in (fileName, folderName, nzbName):
        if curName != None:
            for curSceneName in sceneHelpers.sceneToNormalShowNames(curName):
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
            returnStr += logHelper(u"Result from history: "+str(historyResult)+u" from "+curName, logger.DEBUG)
            (tvdb_id, season, episodes) = historyResult
            showResults = helpers.findCertainShow(sickbeard.showList, tvdb_id)
            break

    # if we're parsing a multi-file folder then the folder name doesn't reflect the correct episode so ignore it
    if multi_file and episodes:
        returnStr += logHelper(u"Multi-file dir "+downloadDir+u" doesn't reflect all episode names, only using name & season", logger.DEBUG)
        episodes = []

    # if that didn't work then try manually parsing and searching them on TVDB
    for curName in finalNameList:

        # if we already have the info from the history then don't bother with this
        if tvdb_id != None and season != None and episodes != []:
            break

        # if we're doing a multi-file dir and we already got the tvdb_id/season but no episodes then assume it's right and carry it forward 
        # otherwise, reset it every time
        if not (tvdb_id and season and not episodes and multi_file):
            tvdb_id = None
            season = None
        episodes = []

        try:
            returnStr += logHelper(u"Attempting to parse name "+curName, logger.DEBUG)
            myParser = FileParser(curName)
            result = myParser.parse()

            season = result.seasonnumber if result.seasonnumber != None else 1
            episodes = result.episodenumbers

            returnStr += logHelper(u"Ended up with season "+str(season)+u" and episodes "+str(episodes), logger.DEBUG)

        except tvnamer_exceptions.InvalidFilename:
            returnStr += logHelper(u"Unable to parse the filename "+curName+u" into a valid episode", logger.DEBUG)
            continue

        if not result.seriesname:
            returnStr += logHelper(u"Filename "+curName+u" has no series name, unable to use this name for processing", logger.DEBUG)
            continue

        if not episodes:
            returnStr += logHelper(u"Unable to find an episode number in the filename "+curName+u", skipping", logger.DEBUG)
            continue

        # reverse-lookup the scene exceptions
        returnStr += logHelper(u"Checking scene exceptions for "+result.seriesname, logger.DEBUG)
        sceneID = None
        for exceptionID in sceneExceptions:
            for curException in sceneExceptions[exceptionID]:
                if result.seriesname == curException:
                    sceneID = exceptionID
                    break
            if sceneID:
                returnStr += logHelper(u"Scene exception lookup got tvdb id "+str(sceneID)+u", using that", logger.DEBUG)
                break

        if sceneID:
            tvdb_id = sceneID

        showObj = None
        try:
            t = tvdb_api.Tvdb(custom_ui=classes.ShowListUI, **sickbeard.TVDB_API_PARMS)

            # get the tvdb object from either the scene exception ID or the series name
            if tvdb_id:
                returnStr += logHelper(u"Looking up ID "+str(tvdb_id)+u" on TVDB", logger.DEBUG)
                showObj = t[tvdb_id]
            else:
                returnStr += logHelper(u"Looking up name "+result.seriesname+u" on TVDB", logger.DEBUG)
                showObj = t[result.seriesname]

            returnStr += logHelper(u"Got tvdb_id "+str(showObj["id"])+u" and series name "+showObj["seriesname"].decode('utf-8')+u" from TVDB", logger.DEBUG)

            showInfo = (int(showObj["id"]), showObj["seriesname"])

        except (tvdb_exceptions.tvdb_exception, IOError), e:

            returnStr += logHelper(u"Unable to look up show on TVDB: "+str(e).decode('utf-8'), logger.DEBUG)
            returnStr += logHelper(u"Looking up show in DB instead", logger.DEBUG)
            showInfo = helpers.searchDBForShow(result.seriesname)

        if showInfo:
            tvdb_id = showInfo[0]

        if showInfo and season == None:
            myDB = db.DBConnection()
            numseasonsSQlResult = myDB.select("SELECT COUNT(DISTINCT season) as numseasons FROM tv_episodes WHERE showid = ? and season != 0", [tvdb_id])
            numseasons = numseasonsSQlResult[0][0]
            if numseasons == 1 and season == None:
                returnStr += logHelper(u"Don't have a season number, but this show appears to only have 1 season, setting seasonnumber to 1...", logger.DEBUG)
                season = 1

        # if it is an air-by-date show and we successfully found it on TVDB, convert the date into a season/episode
        if season == -1 and showObj:
            returnStr += logHelper(u"Looks like this is an air-by-date show, attempting to parse...", logger.DEBUG)
            try:
                epObj = showObj.airedOn(episodes[0])[0]
                season = int(epObj["seasonnumber"])
                episodes = [int(epObj["episodenumber"])]
            except tvdb_exceptions.tvdb_episodenotfound, e:
                returnStr += logHelper(u"Unable to find episode with date "+str(episodes[0])+u" for show "+showObj["seriesname"]+u", skipping", logger.DEBUG)
                continue

        # if we couldn't get the necessary info from either of the above methods, try the next name
        if tvdb_id == None or season == None or episodes == []:
            returnStr += logHelper(u"Unable to get all the necessary info, ended up with tvdb_id "+str(tvdb_id)+u", season "+str(season)+u", and episodes "+str(episodes)+u". Skipping to the next name...", logger.DEBUG)
            continue

        # find the show in the showlist
        try:
            showResults = helpers.findCertainShow(sickbeard.showList, showInfo[0])
        except exceptions.MultipleShowObjectsException:
            raise #TODO: later I'll just log this, for now I want to know about it ASAP

        if showResults != None:
            returnStr += logHelper(u"Found the show in our list, continuing", logger.DEBUG)
            break

    # end for

    # if we came out of the loop with not enough info then give up
    if tvdb_id == None or season == None or episodes == []:
        # if we have a good enough result then fine, use it

        returnStr += logHelper(u"Unable to figure out what this episode is, giving up.  Ended up with tvdb_id "+str(tvdb_id)+u", season "+str(season)+u", and episodes "+str(episodes)+u".", logger.DEBUG)
        return returnStr

    # if we found enough info but it wasn't a show we know about, give up
    if showResults == None:
        returnStr += logHelper(u"The episode doesn't match a show in my list - bad naming?", logger.DEBUG)
        return returnStr

    # if we DO know about the show but its dir is offline, give up
    if not ek.ek(os.path.isdir, showResults._location):
        returnStr += logHelper(u"The show dir doesn't exist, canceling postprocessing", logger.DEBUG)
        return returnStr

    if season == -1:
        return returnStr

    # search all possible names for our new quality, in case the file or dir doesn't have it
    newQuality = Quality.UNKNOWN
    for curName in finalNameList:
        curNewQuality = Quality.nameQuality(curName)
        returnStr += logHelper(u"Looking up quality for name "+curName+u", got "+Quality.qualityStrings[curNewQuality], logger.DEBUG)
        # just remember if we find a good quality
        if curNewQuality != Quality.UNKNOWN and newQuality == Quality.UNKNOWN:
            newQuality = curNewQuality
            returnStr += logHelper(u"saved quality "+Quality.qualityStrings[newQuality], logger.DEBUG)

    # if we didn't get a quality from one of the names above, try assuming from each of the names
    for curName in finalNameList:
        if newQuality != Quality.UNKNOWN:
            break
        newQuality = Quality.assumeQuality(curName)
        returnStr += logHelper(u"Guessing quality for name "+curName+u", got "+Quality.qualityStrings[curNewQuality], logger.DEBUG)
        if newQuality != Quality.UNKNOWN:
            break

    returnStr += logHelper(u"Unless we're told otherwise, assuming the quality is "+Quality.qualityStrings[newQuality], logger.DEBUG)

    rootEp = None
    for curEpisode in episodes:
        episode = int(curEpisode)

        returnStr += logHelper(u"TVDB thinks the file is tvdb_id = " + str(tvdb_id) + " " + str(season) + "x" + str(episode), logger.DEBUG)

        # now that we've figured out which episode this file is just load it manually
        try:
            curEp = showResults.getEpisode(season, episode)
        except exceptions.EpisodeNotFoundException, e:
            returnStr += logHelper(u"Unable to create episode: "+str(e).decode('utf-8'), logger.DEBUG)
            return returnStr

        if rootEp == None:
            rootEp = curEp
            rootEp.relatedEps = []
        else:
            rootEp.relatedEps.append(curEp)

    oldStatus = None
    # make sure the quality is set right before we continue
    if rootEp.status in Quality.SNATCHED + Quality.SNATCHED_PROPER:
        oldStatus, newQuality = Quality.splitCompositeStatus(rootEp.status)
        returnStr += logHelper(u"The old status had a quality in it, using that: "+Quality.qualityStrings[newQuality], logger.DEBUG)
    else:
        for curEp in [rootEp] + rootEp.relatedEps:
            curEp.status = Quality.compositeStatus(SNATCHED, newQuality)

    # figure out the new filename
    biggestFileName = ek.ek(os.path.basename, fileName)
    biggestFileExt = ek.ek(os.path.splitext, biggestFileName)[1]

    # if we're supposed to put it in a season folder then figure out what folder to use
    seasonFolder = ''
    if rootEp.show.seasonfolders == True:

        # search the show dir for season folders
        for curDir in os.listdir(rootEp.show.location):

            if not ek.ek(os.path.isdir, ek.ek(os.path.join, rootEp.show.location, curDir)):
                continue

            # if it's a season folder, check if it's the one we want
            match = re.match(".*[Ss]eason\s*(\d+)", curDir)
            if match != None:
                # if it's the correct season folder then stop looking
                if int(match.group(1)) == int(rootEp.season):
                    seasonFolder = curDir
                    break

        # if we couldn't find the right one then just assume "Season X" format is what we want
        if seasonFolder == '':
            # for air-by-date shows use the year as the season folder
            if rootEp.show.is_air_by_date:
                seasonFolder = str(rootEp.airdate.year)
            else:
                seasonFolder = sickbeard.SEASON_FOLDERS_FORMAT % (rootEp.season)

    returnStr += logHelper(u"Season folders were " + str(rootEp.show.seasonfolders) + " which gave " + seasonFolder, logger.DEBUG)

    destDir = ek.ek(os.path.join, rootEp.show.location, seasonFolder)

    # movedFilePath is the full path to where we will move the file
    movedFilePath = ek.ek(os.path.join, destDir, biggestFileName)

    # renamedFilePath is the full path to the renamed file's eventual location
    if sickbeard.RENAME_EPISODES:
        renamedFilePath = ek.ek(os.path.join, destDir, helpers.sanitizeFileName(rootEp.prettyName())+biggestFileExt)
    else:
        renamedFilePath = movedFilePath
    returnStr += logHelper(u"The ultimate destination for " + fileName + " is " + renamedFilePath, logger.DEBUG)

    existingResult = _checkForExistingFile(renamedFilePath, fileName)

    # if there's no file with that exact filename then check for a different episode file (in case we're going to delete it)
    if existingResult == 0:
        existingResult = _checkForExistingFile(rootEp.location, fileName)
        if existingResult == -1:
            existingResult = -2
        if existingResult == 1:
            existingResult = 2

    returnStr += logHelper(u"Existing result: "+str(existingResult), logger.DEBUG)

    # see if the existing file is bigger - if it is, bail (unless it's a proper or better quality in which case we're forcing an overwrite)
    if existingResult > 0:
        if rootEp.status in Quality.SNATCHED_PROPER:
            returnStr += logHelper(u"There is already a file that's bigger at "+renamedFilePath+u" but I'm going to overwrite it with a PROPER", logger.DEBUG)
        elif oldStatus != None:
            returnStr += logHelper(u"There is already a file that's bigger at "+renamedFilePath+u" but I'm going to overwrite it because this one seems to have been downloaded on purpose", logger.DEBUG)
        else:
            returnStr += logHelper(u"There is already a file that's bigger at "+renamedFilePath+u" - not processing this episode.", logger.DEBUG)

            # tag the dir so we know what happened
            if downloadDir:
                try:
                    oldDirName = ek.ek(os.path.abspath, downloadDir)
                    baseDirPath = ek.ek(os.path.dirname, oldDirName)
                    endDirPath = ek.ek(os.path.basename, oldDirName)
                    newDirPath = ek.ek(os.path.join, baseDirPath, '_UNDERSIZED_'+endDirPath)
                    returnStr += logHelper(u"Renaming the parent folder to indicate that the post process was failed: "+downloadDir+u" -> "+newDirPath, logger.DEBUG)
                    os.rename(oldDirName, newDirPath)
                except (OSError, IOError), e:
                    returnStr += logHelper(u"Failed renaming " + oldDirName + " to " + newDirPath + ": " + str(e), logger.ERROR)

            return returnStr

    # if the dir doesn't exist (new season folder) then make it
    if not ek.ek(os.path.isdir, destDir):
        returnStr += logHelper(u"Season folder didn't exist, creating it", logger.DEBUG)
        os.mkdir(destDir)

    if sickbeard.KEEP_PROCESSED_DIR:
        returnStr += logHelper(u"Copying from " + fileName + " to " + destDir, logger.DEBUG)
        try:
            copyFile(fileName, movedFilePath)

            returnStr += logHelper(u"File was copied successfully", logger.DEBUG)

        except (Error, IOError, OSError), e:
            returnStr += logHelper(u"Unable to copy the file: " + str(e), logger.ERROR)
            return returnStr

    else:

        returnStr += logHelper(u"Moving from " + fileName + " to " + movedFilePath, logger.DEBUG)
        try:
            moveFile(fileName, movedFilePath)

            returnStr += logHelper(u"File was moved successfully", logger.DEBUG)

        except (Error, IOError, OSError), e:
            returnStr += logHelper(u"Unable to move the file: " + str(e), logger.ERROR)
            return returnStr

    existingFile = None

    # if we're deleting a file with a different name then just go ahead
    if existingResult in (-2, 2):
        existingFile = rootEp.location
        if rootEp.status in Quality.SNATCHED_PROPER:
            returnStr += logHelper(existingFile + " already exists and is the same size or larger but I'm deleting it to make way for the proper", logger.DEBUG)
        else:
            returnStr += logHelper(existingFile + " already exists but it's smaller than the new file so I'm replacing it", logger.DEBUG)

    elif ek.ek(os.path.isfile, renamedFilePath):
        returnStr += logHelper(renamedFilePath + " already exists but it's smaller or the same size as the new file so I'm replacing it", logger.DEBUG)
        existingFile = renamedFilePath

    if existingFile and ek.ek(os.path.normpath, movedFilePath) != ek.ek(os.path.normpath, existingFile):
        deleteAssociatedFiles(existingFile)

    # update the statuses before we rename so the quality goes into the name properly
    for curEp in [rootEp] + rootEp.relatedEps:
        with curEp.lock:
            curEp.location = renamedFilePath

            curEp.status = Quality.compositeStatus(DOWNLOADED, newQuality)

            curEp.saveToDB()

    if ek.ek(os.path.normpath, movedFilePath) != ek.ek(os.path.normpath, renamedFilePath):
        try:
            ek.ek(os.rename, movedFilePath, renamedFilePath)
            returnStr += logHelper(u"Renaming the file " + movedFilePath + " to " + renamedFilePath, logger.DEBUG)
        except (OSError, IOError), e:
            returnStr += logHelper(u"Failed renaming " + movedFilePath + " to " + renamedFilePath + ": " + str(e), logger.ERROR)
            return returnStr

    else:
        returnStr += logHelper(u"Renaming is disabled, leaving file as "+movedFilePath, logger.DEBUG)

    # log it to history
    history.logDownload(rootEp, fileName)

    notifiers.notify(NOTIFY_DOWNLOAD, rootEp.prettyName(True))

    # generate nfo/tbn
    rootEp.createMetaFiles()
    rootEp.saveToDB()

    # try updating just show path first
    if sickbeard.XBMC_UPDATE_LIBRARY:
        for curHost in [x.strip() for x in sickbeard.XBMC_HOST.split(",")]:
            if not notifiers.xbmc.updateLibrary(curHost, showName=rootEp.show.name) and sickbeard.XBMC_UPDATE_FULL:
                # do a full update if requested
                returnStr += logHelper(u"Update of show directory failed on " + curHost + ", trying full update as requested")
                notifiers.xbmc.updateLibrary(curHost)

    for curScriptName in sickbeard.EXTRA_SCRIPTS:
        script_cmd = shlex.split(curScriptName) + [rootEp.location, biggestFileName, str(tvdb_id), str(season), str(episode), str(rootEp.airdate)]
        returnStr += logHelper(u"Executing command "+str(script_cmd))
        logger.log(u"Absolute path to script: "+ek.ek(os.path.abspath, script_cmd[0]), logger.DEBUG)
        try:
            p = subprocess.Popen(script_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=sickbeard.PROG_DIR)
            out, err = p.communicate()
            returnStr += logHelper(u"Script result: "+str(out), logger.DEBUG)
        except OSError, e:
            returnStr += logHelper(u"Unable to run extra_script: "+str(e).decode('utf-8'))

    returnStr += logHelper(u"Post processing finished successfully", logger.DEBUG)

    return [returnStr]
