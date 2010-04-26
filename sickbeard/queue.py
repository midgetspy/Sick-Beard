from __future__ import with_statement

import os.path
import threading
import traceback

from lib.tvdb_api import tvdb_exceptions

from sickbeard.common import *

#from sickbeard.tv import TVShow
from sickbeard import exceptions
from sickbeard import helpers
from sickbeard import logger
from sickbeard import tvclasses

from sickbeard.tvapi import tvapi_main

class ShowQueue:
    def __init__(self):

        self.currentItem = None
        self.queue = []
        
        self.thread = None

    def _isInQueue(self, show, actions):
        return show in [x.show for x in self.queue if x.action in actions]
    
    def _isBeingSomethinged(self, show, actions):
        return self.currentItem != None and show == self.currentItem.show and \
                self.currentItem.action in actions
    
    def isInUpdateQueue(self, show):
        return self._isInQueue(show, (QueueActions.UPDATE, QueueActions.FORCEUPDATE))

    def isInRefreshQueue(self, show):
        return self._isInQueue(show, (QueueActions.REFRESH,))

    def isInRenameQueue(self, show):
        return self._isInQueue(show, (QueueActions.RENAME,))

    def isBeingAdded(self, show):
        return self._isBeingSomethinged(show, (QueueActions.ADD,))

    def isBeingUpdated(self, show):
        return self._isBeingSomethinged(show, (QueueActions.UPDATE, QueueActions.FORCEUPDATE))

    def isBeingRefreshed(self, show):
        return self._isBeingSomethinged(show, (QueueActions.REFRESH,))

    def isBeingRenamed(self, show):
        return self._isBeingSomethinged(show, (QueueActions.RENAME,))

    def _getLoadingShowList(self):
        return [x for x in self.queue+[self.currentItem] if x != None and x.isLoading]

    loadingShowList = property(_getLoadingShowList)

    def run(self):
        
        # only start a new task if one isn't already going
        if self.thread == None or self.thread.isAlive() == False:

            # if the thread is dead then the current item should be finished
            if self.currentItem != None:
                self.currentItem.finish()
                self.currentItem = None

            # if there's something in the queue then run it in a thread and take it out of the queue
            if len(self.queue) > 0:
                
                queueItem = self.queue[0]
                
                logger.log("Starting new task: " + QueueActions.TEXT[queueItem.action] + " - " + queueItem.name)

                # launch the queue item in a thread
                # TODO: improve thread name
                threadName = "QUEUE-" + QueueActions.TEXT[queueItem.action].replace(" ","").upper()
                self.thread = threading.Thread(None, queueItem.execute, threadName)
                self.thread.start()

                self.currentItem = queueItem
                
                # take it out of the queue
                del self.queue[0]
        
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
            logger.log("A refresh was attempted but there is already an update queued or in progress. Since updates do a refres at the end anyway I'm skipping this request.", logger.DEBUG)
            return
        
        queueItemObj = QueueItemRefresh(show)
        
        # refresh gets put at the front cause it's quick
        self.queue.insert(0, queueItemObj)
        
        return queueItemObj
    
    def renameShowEpisodes(self, show, force=False):

        queueItemObj = QueueItemRename(show)
        
        self.queue.append(queueItemObj)
        
        return queueItemObj
    
    def addShow(self, tvdb_id, showDir):
        queueItemObj = QueueItemAdd(tvdb_id, showDir)
        self.queue.append(queueItemObj)
        
        return queueItemObj

class QueueActions:
    REFRESH=1
    ADD=2
    UPDATE=3
    FORCEUPDATE=4
    RENAME=5
    
    TEXT = {REFRESH: 'Refresh',
            ADD: 'Add',
            UPDATE: 'Update',
            FORCEUPDATE: 'Forced Update',
            RENAME: 'Rename'
    }

class QueueItem:
    """
    Represents an item in the queue waiting to be executed
    
    Can be either:
    - show being added (may or may not be associated with a show object)
    - show being refreshed
    - show being updated
    - show being force updated
    """
    def __init__(self, action, show=None):
        self.action = action
        self.show = show
        
        self.inProgress = False
    
    def _getName(self):
        return self.show.show_data.name

    def _isLoading(self):
        return False

    name = property(_getName)
    
    isLoading = property(_isLoading)
    
    def isInQueue(self):
        return self in sickbeard.showQueueScheduler.action.queue+[sickbeard.showQueueScheduler.action.currentItem]
    
    def execute(self):
        """Should subclass this"""
        
        logger.log("Beginning task")
        self.inProgress = True

    def finish(self):
        
        logger.log("Finished performing a task")
        self.inProgress = False
        
class QueueItemAdd(QueueItem):
    def __init__(self, tvdb_id, showDir):

        self.showDir = showDir
        self.tvdb_id = tvdb_id

        # this will initialize self.show to None
        QueueItem.__init__(self, QueueActions.ADD)

    def _getName(self):
        if self.show == None:
            return self.showDir
        return self.show.name

    name = property(_getName)

    def _isLoading(self):
        if self.show == None:
            return True
        return False

    isLoading = property(_isLoading)

    def execute(self):

        QueueItem.execute(self)

        logger.log("Starting to add show "+self.showDir)

        #TODO: fix this
        otherShow = helpers.findCertainShow(sickbeard.showList, self.tvdb_id)
        if otherShow != None:
            logger.log("Show is already in your list, not adding it again")
            self.finish()
            return

        self.show = tvclasses.TVShow.createTVShow(self.tvdb_id)
        
        # set up initial values
        self.show.location = self.showDir
        self.show.quality = sickbeard.QUALITY_DEFAULT
        self.show.seasonfolders = sickbeard.SEASON_FOLDERS_DEFAULT
        self.show.paused = False

        self.show.refreshDir()

        self.finish()
        

    def _finishEarly(self):
        if self.show != None:
            self.show.deleteShow()
        
        if self.initialShow != None:
            self.initialShow.deleteShow()
        
        self.finish()


class QueueItemRefresh(QueueItem):
    def __init__(self, show=None):
        QueueItem.__init__(self, QueueActions.REFRESH, show)
        self.show = show

    def execute(self):

        QueueItem.execute(self)
        
        logger.log("Performing refresh on "+self.show.show_data.name)

        self.show.refreshDir()
        self.show.getImages()
        self.show.writeEpisodeMetafiles()
        
        self.inProgress = False
        
class QueueItemRename(QueueItem):
    def __init__(self, show=None):
        QueueItem.__init__(self, QueueActions.RENAME, show)

    def execute(self):

        QueueItem.execute(self)

        logger.log("Performing rename on "+self.show.show_data.name)

        self.show.fixEpisodeNames()
        
        self.inProgress = False
        
class QueueItemUpdate(QueueItem):
    def __init__(self, show=None):
        QueueItem.__init__(self, QueueActions.UPDATE, show)
        self.force = False
    
    def execute(self):
        
        QueueItem.execute(self)
        
        logger.log("Beginning update of "+self.show.show_data.name)
        
        self.show.updateMetadata()

        sickbeard.showQueueScheduler.action.refreshShow(self.show, True)

class QueueItemForceUpdate(QueueItemUpdate):
    def __init__(self, show=None):
        QueueItem.__init__(self, QueueActions.FORCEUPDATE, show)
        self.force = True

        