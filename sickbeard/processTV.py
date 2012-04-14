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

from sickbeard import ui, search_queue
from sickbeard.common import WANTED, statusStrings


def logHelper (logMessage, logLevel=logger.MESSAGE):
    logger.log(logMessage, logLevel)
    return logMessage + u"\n"

def setWanted(show, season, episode):
    returnStr = ''
    if show == None or season == None or episode == None:
        errMsg = "Programming error: invalid setWanted paramaters"
        ui.notifications.error('Error', errMsg)
        returnStr += logHelper(u"Programming error: invalid setWanted paramaters")
        return returnStr

    showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, show)

    if showObj == None:
        errMsg = "Show not in show list"
        ui.notifications.error('Error', errMsg)
        returnStr += logHelper(u"Error: show not in show list", logger.ERROR)
        return returnStr

    returnStr += logHelper(u"Attempting to set status on episode "+str(episode)+" to "+statusStrings[WANTED], logger.DEBUG)

    epObj = showObj.getEpisode(season, episode)

    if epObj == None:
        returnStr += logHelper(u"Error: Episode couldn't be retrieved", logger.ERROR)
        return returnStr

    # figure out what segment the episode is in and remember it so we can backlog it
    if epObj.show.air_by_date:
        ep_segment = str(epObj.airdate)[:7]
    else:
        ep_segment = epObj.season


    with epObj.lock:
        epObj.status = int(WANTED)
        epObj.saveToDB()

    msg = "Backlog was automatically started for the following seasons of <b>"+showObj.name+"</b>:<br />"
    msg += "<li>Season "+str(ep_segment)+"</li>"
    returnStr += logHelper(u"Sending backlog for "+showObj.name+" season "+str(ep_segment)+" because some eps were set to wanted")
    cur_backlog_queue_item = search_queue.BacklogQueueItem(showObj, ep_segment)
    sickbeard.searchQueueScheduler.action.add_item(cur_backlog_queue_item)
    msg += "</ul>"

    ui.notifications.message("Backlog started", msg)

    returnStr += logHelper(u"Successfully set to wanted", logger.DEBUG)

    return returnStr

def processDir (dirName, nzbName=None, recurse=False, failed=False):
    """
    Scans through the files in dirName and processes whatever media files it finds
    
    dirName: The folder name to look in
    nzbName: The NZB name which resulted in this folder being downloaded
    recurse: Boolean for whether we should descend into subfolders or not
    failed: Boolean for whether or not the download failed
    """

    returnStr = ''

    returnStr += logHelper(u"Processing folder "+dirName, logger.DEBUG)

    if failed:
        if nzbName != None:
            # Assume we're being passed an nzb name
            # Will break on files w/o extensions but w/ periods in their name
            if '.' in nzbName:
                nzbName = nzbName.rpartition(".")[0]
        else:
            # Assume folder name = resource name
            nzbName = ek.ek(os.path.basename, dirName)
            returnStr += logHelper(u"nzb name not provided. Guessing from dir name: " + nzbName)

        returnStr += logHelper(u"Failed download detected: " + nzbName)

        myDB = db.DBConnection()
        myDB.select("UPDATE history SET failed=1 WHERE resource=?", [nzbName])

        if sickbeard.DELETE_FAILED:
            returnStr += logHelper(u"Deleting folder of failed download " + dirName, logger.DEBUG)
            try:
                shutil.rmtree(dirName)
            except (OSError, IOError), e:
                returnStr += logHelper(u"Warning: Unable to remove the failed folder " + dirName + ": " + ex(e), logger.WARNING)

        returnStr += logHelper(u"Setting episode back to Wanted")

        sql_results = myDB.select("SELECT showid, season, episode FROM history WHERE resource=?", [nzbName])

        if len(sql_results) == 0:
            returnStr += logHelper(u"Not found in history, still considered Snatched: " + nzbName, logger.ERROR)
            return returnStr

        show = sql_results[0]["showid"]
        season = sql_results[0]["season"]
        episode = sql_results[0]["episode"]

        returnStr += setWanted(show, season, episode)

        return returnStr

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

    if ek.ek(os.path.basename, dirName).startswith('_UNDERSIZED_'):
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
