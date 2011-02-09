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

import os.path
import threading
import traceback

from lib.tvdb_api import tvdb_exceptions

from sickbeard.common import *

from sickbeard.tv import TVShow
from sickbeard import exceptions, helpers, logger, ui
from sickbeard import generic_queue

class ShowQueue(generic_queue.GenericQueue):

    def __init__(self):
        generic_queue.GenericQueue.__init__(self)
        self.queue_name = "SHOWQUEUE"


    def _isInQueue(self, show, actions):
        return show in [x.show for x in self.queue if x.action_id in actions]

    def _isBeingSomethinged(self, show, actions):
        return self.currentItem != None and show == self.currentItem.show and \
                self.currentItem.action_id in actions

    def isInUpdateQueue(self, show):
        return self._isInQueue(show, (ShowQueueActions.UPDATE, ShowQueueActions.FORCEUPDATE))

    def isInRefreshQueue(self, show):
        return self._isInQueue(show, (ShowQueueActions.REFRESH,))

    def isInRenameQueue(self, show):
        return self._isInQueue(show, (ShowQueueActions.RENAME,))

    def isBeingAdded(self, show):
        return self._isBeingSomethinged(show, (ShowQueueActions.ADD,))

    def isBeingUpdated(self, show):
        return self._isBeingSomethinged(show, (ShowQueueActions.UPDATE, ShowQueueActions.FORCEUPDATE))

    def isBeingRefreshed(self, show):
        return self._isBeingSomethinged(show, (ShowQueueActions.REFRESH,))

    def isBeingRenamed(self, show):
        return self._isBeingSomethinged(show, (ShowQueueActions.RENAME,))

    def _getLoadingShowList(self):
        return [x for x in self.queue+[self.currentItem] if x != None and x.isLoading]

    loadingShowList = property(_getLoadingShowList)

    def updateShow(self, show, force=False):

        if self.isBeingAdded(show):
            raise exceptions.CantUpdateException("Show is still being added, wait until it is finished before you update.")

        if self.isBeingUpdated(show):
            raise exceptions.CantUpdateException("This show is already being updated, can't update again until it's done.")

        if self.isInUpdateQueue(show):
            raise exceptions.CantUpdateException("This show is already being updated, can't update again until it's done.")

        if not force:
            queueItemObj = QueueItemUpdate(show)
        else:
            queueItemObj = QueueItemForceUpdate(show)

        self.queue.append(queueItemObj)

        return queueItemObj

    def refreshShow(self, show, force=False):

        if self.isBeingRefreshed(show) and not force:
            raise exceptions.CantRefreshException("This show is already being refreshed, not refreshing again.")

        if (self.isBeingUpdated(show) or self.isInUpdateQueue(show)) and not force:
            logger.log(u"A refresh was attempted but there is already an update queued or in progress. Since updates do a refres at the end anyway I'm skipping this request.", logger.DEBUG)
            return

        queueItemObj = QueueItemRefresh(show)
        
        self.queue.append(queueItemObj)

        return queueItemObj

    def renameShowEpisodes(self, show, force=False):

        queueItemObj = QueueItemRename(show)

        self.queue.append(queueItemObj)

        return queueItemObj

    def addShow(self, tvdb_id, showDir, lang="en"):
        queueItemObj = QueueItemAdd(tvdb_id, showDir, lang)
        self.queue.append(queueItemObj)

        return queueItemObj

class ShowQueueActions:
    REFRESH=1
    ADD=2
    UPDATE=3
    FORCEUPDATE=4
    RENAME=5
    
    names = {REFRESH: 'Refresh',
                    ADD: 'Add',
                    UPDATE: 'Update',
                    FORCEUPDATE: 'Force Update',
                    RENAME: 'Rename',
                    }

class ShowQueueItem(generic_queue.QueueItem):
    """
    Represents an item in the queue waiting to be executed

    Can be either:
    - show being added (may or may not be associated with a show object)
    - show being refreshed
    - show being updated
    - show being force updated
    """
    def __init__(self, action_id, show):
        generic_queue.QueueItem.__init__(self, ShowQueueActions.names[action_id], action_id)
        self.show = show
    
    def isInQueue(self):
        return self in sickbeard.showQueueScheduler.action.queue+[sickbeard.showQueueScheduler.action.currentItem]

    def _getName(self):
        return str(self.show.tvdbid)

    def _isLoading(self):
        return False

    show_name = property(_getName)

    isLoading = property(_isLoading)


class QueueItemAdd(ShowQueueItem):
    def __init__(self, tvdb_id, showDir, lang="en"):

        self.tvdb_id = tvdb_id
        self.showDir = showDir
        self.lang = lang

        self.show = None

        # this will initialize self.show to None
        ShowQueueItem.__init__(self, ShowQueueActions.ADD, self.show)
        
    def _getName(self):
        if self.show == None:
            return self.showDir
        return self.show.name

    show_name = property(_getName)

    def _isLoading(self):
        if self.show == None:
            return True
        return False

    isLoading = property(_isLoading)

    def execute(self):

        ShowQueueItem.execute(self)

        logger.log(u"Starting to add show "+self.showDir)

        try:
            newShow = TVShow(self.tvdb_id, self.lang)
            newShow.loadFromTVDB()

            self.show = newShow

            # set up initial values
            self.show.location = self.showDir
            self.show.quality = sickbeard.QUALITY_DEFAULT
            self.show.seasonfolders = sickbeard.SEASON_FOLDERS_DEFAULT
            self.show.paused = False

        except tvdb_exceptions.tvdb_exception, e:
            logger.log(u"Unable to add show due to an error with TVDB: "+str(e).decode('utf-8'), logger.ERROR)
            if self.show:
                ui.flash.error("Unable to add "+str(self.show.name)+" due to an error with TVDB")
            else:
                ui.flash.error("Unable to add show due to an error with TVDB")
            self._finishEarly()
            return

        except exceptions.MultipleShowObjectsException:
            logger.log(u"The show in " + self.showDir + " is already in your show list, skipping", logger.ERROR)
            ui.flash.error('Show skipped', "The show in " + self.showDir + " is already in your show list")
            self._finishEarly()
            return

        except Exception, e:
            logger.log(u"Error trying to add show: "+str(e).decode('utf-8'), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
            self._finishEarly()
            raise

        # add it to the show list
        sickbeard.showList.append(self.show)

        try:
            self.show.loadEpisodesFromDir()
        except Exception, e:
            logger.log(u"Error searching dir for episodes: " + str(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)

        try:
            self.show.loadEpisodesFromTVDB()
            self.show.setTVRID()

            self.show.writeMetadata()
            self.show.populateCache()
            
        except Exception, e:
            logger.log(u"Error with TVDB, not creating episode list: " + str(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)

        try:
            self.show.saveToDB()
        except Exception, e:
            logger.log(u"Error saving the episode to the database: " + str(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)

        self.show.flushEpisodes()

        self.finish()

    def _finishEarly(self):
        if self.show != None:
            self.show.deleteShow()

        self.finish()


class QueueItemRefresh(ShowQueueItem):
    def __init__(self, show=None):
        ShowQueueItem.__init__(self, ShowQueueActions.REFRESH, show)

        # do refreshes first because they're quick
        self.priority = generic_queue.QueuePriorities.HIGH

    def execute(self):

        ShowQueueItem.execute(self)

        logger.log(u"Performing refresh on "+self.show.name)

        self.show.refreshDir()
        self.show.writeMetadata()
        self.show.populateCache()

        self.inProgress = False

class QueueItemRename(ShowQueueItem):
    def __init__(self, show=None):
        ShowQueueItem.__init__(self, ShowQueueActions.RENAME, show)

    def execute(self):

        ShowQueueItem.execute(self)

        logger.log(u"Performing rename on "+self.show.name)

        self.show.fixEpisodeNames()

        self.inProgress = False

class QueueItemUpdate(ShowQueueItem):
    def __init__(self, show=None):
        ShowQueueItem.__init__(self, ShowQueueActions.UPDATE, show)
        self.force = False

    def execute(self):

        ShowQueueItem.execute(self)

        logger.log(u"Beginning update of "+self.show.name)

        logger.log(u"Retrieving show info from TVDB", logger.DEBUG)
        self.show.loadFromTVDB(cache=not self.force)

        # either update or refresh depending on the time
        if self.show.status == "Ended" and not self.force:
            #TODO: maybe I should still update specials?
            logger.log(u"Not updating episodes for show "+self.show.name+" because it's marked as ended.", logger.DEBUG)
            sickbeard.showQueueScheduler.action.refreshShow(self.show, True)
            return

        # get episode list from DB
        logger.log(u"Loading all episodes from the database", logger.DEBUG)
        DBEpList = self.show.loadEpisodesFromDB()

        # get episode list from TVDB
        logger.log(u"Loading all episodes from theTVDB", logger.DEBUG)
        try:
            TVDBEpList = self.show.loadEpisodesFromTVDB(cache=not self.force)
        except tvdb_exceptions.tvdb_exception, e:
            logger.log(u"Unable to get info from TVDB, the show info will not be refreshed: "+str(e).decode('utf-8'), logger.ERROR)
            TVDBEpList = None

        if TVDBEpList == None:
            logger.log(u"No data returned from TVDB, unable to update this show", logger.ERROR)

        else:

            # for each ep we found on TVDB delete it from the DB list
            for curSeason in TVDBEpList:
                for curEpisode in TVDBEpList[curSeason]:
                    logger.log(u"Removing "+str(curSeason)+"x"+str(curEpisode)+" from the DB list", logger.DEBUG)
                    if curSeason in DBEpList and curEpisode in DBEpList[curSeason]:
                        del DBEpList[curSeason][curEpisode]

            # for the remaining episodes in the DB list just delete them from the DB
            for curSeason in DBEpList:
                for curEpisode in DBEpList[curSeason]:
                    logger.log(u"Permanently deleting episode "+str(curSeason)+"x"+str(curEpisode)+" from the database", logger.MESSAGE)
                    curEp = self.show.getEpisode(curSeason, curEpisode)
                    try:
                        curEp.deleteEpisode()
                    except exceptions.EpisodeDeletedException:
                        pass

        # now that we've updated the DB from TVDB see if there's anything we can add from TVRage
        with self.show.lock:
            logger.log(u"Attempting to supplement show info with info from TVRage", logger.DEBUG)
            self.show.loadLatestFromTVRage()
            if self.show.tvrid == 0:
                self.show.setTVRID()

        sickbeard.showQueueScheduler.action.refreshShow(self.show, True)

class QueueItemForceUpdate(QueueItemUpdate):
    def __init__(self, show=None):
        ShowQueueItem.__init__(self, ShowQueueActions.FORCEUPDATE, show)
        self.force = True
