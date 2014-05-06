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

import traceback

import sickbeard

from lib.tvdb_api import tvdb_exceptions, tvdb_api

from sickbeard.common import SKIPPED, WANTED

from sickbeard.tv import TVShow
from sickbeard import exceptions, logger, ui, db
from sickbeard import generic_queue
from sickbeard import name_cache
from sickbeard.exceptions import ex


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
        return [x for x in self.queue + [self.currentItem] if x != None and x.isLoading]

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

        self.add_item(queueItemObj)

        return queueItemObj

    def refreshShow(self, show, force=False):

        if self.isBeingRefreshed(show) and not force:
            raise exceptions.CantRefreshException("This show is already being refreshed, not refreshing again.")

        if (self.isBeingUpdated(show) or self.isInUpdateQueue(show)) and not force:
            logger.log(u"A refresh was attempted but there is already an update queued or in progress. Since updates do a refresh at the end anyway I'm skipping this request.", logger.DEBUG)
            return

        queueItemObj = QueueItemRefresh(show)

        self.add_item(queueItemObj)

        return queueItemObj

    def renameShowEpisodes(self, show, force=False):

        queueItemObj = QueueItemRename(show)

        self.add_item(queueItemObj)

        return queueItemObj

    def addShow(self, tvdb_id, showDir, default_status=None, quality=None, flatten_folders=None, lang="en"):

        queueItemObj = QueueItemAdd(tvdb_id, showDir, default_status, quality, flatten_folders, lang)

        self.add_item(queueItemObj)

        return queueItemObj


class ShowQueueActions:
    REFRESH = 1
    ADD = 2
    UPDATE = 3
    FORCEUPDATE = 4
    RENAME = 5

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
        return self in sickbeard.showQueueScheduler.action.queue + [sickbeard.showQueueScheduler.action.currentItem]  # @UndefinedVariable

    def _getName(self):
        return str(self.show.tvdbid)

    def _isLoading(self):
        return False

    show_name = property(_getName)

    isLoading = property(_isLoading)


class QueueItemAdd(ShowQueueItem):
    def __init__(self, tvdb_id, showDir, default_status, quality, flatten_folders, lang):

        self.tvdb_id = tvdb_id
        self.showDir = showDir
        self.default_status = default_status
        self.quality = quality
        self.flatten_folders = flatten_folders
        self.lang = lang

        self.show = None

        # this will initialize self.show to None
        ShowQueueItem.__init__(self, ShowQueueActions.ADD, self.show)

    def _getName(self):
        """
        Returns the show name if there is a show object created, if not returns
        the dir that the show is being added to.
        """
        if self.show == None:
            return self.showDir
        return self.show.name

    show_name = property(_getName)

    def _isLoading(self):
        """
        Returns True if we've gotten far enough to have a show object, or False
        if we still only know the folder name.
        """
        if self.show == None:
            return True
        return False

    isLoading = property(_isLoading)

    def execute(self):

        ShowQueueItem.execute(self)

        logger.log(u"Starting to add show " + self.showDir)

        try:
            # make sure the tvdb ids are valid
            try:
                ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()
                if self.lang:
                    ltvdb_api_parms['language'] = self.lang

                logger.log(u"TVDB: " + repr(ltvdb_api_parms))

                t = tvdb_api.Tvdb(**ltvdb_api_parms)
                s = t[self.tvdb_id]

                # this usually only happens if they have an NFO in their show dir which gave us a TVDB ID that has no proper english version of the show
                if not s['seriesname']:
                    logger.log(u"Show in " + self.showDir + " has no name on TVDB, probably the wrong language used to search with.", logger.ERROR)
                    ui.notifications.error("Unable to add show", "Show in " + self.showDir + " has no name on TVDB, probably the wrong language. Delete .nfo and add manually in the correct language.")
                    self._finishEarly()
                    return
                # if the show has no episodes/seasons
                if not s:
                    logger.log(u"Show " + str(s['seriesname']) + " is on TVDB but contains no season/episode data.", logger.ERROR)
                    ui.notifications.error("Unable to add show", "Show " + str(s['seriesname']) + " is on TVDB but contains no season/episode data.")
                    self._finishEarly()
                    return
            except tvdb_exceptions.tvdb_exception, e:
                logger.log(u"Error contacting TVDB: " + ex(e), logger.ERROR)
                ui.notifications.error("Unable to add show", "Unable to look up the show in " + self.showDir + " on TVDB, not using the NFO. Delete .nfo and add manually in the correct language.")
                self._finishEarly()
                return

            # clear the name cache
            name_cache.clearCache()

            newShow = TVShow(self.tvdb_id, self.lang)
            newShow.loadFromTVDB()

            self.show = newShow

            # set up initial values
            self.show.location = self.showDir
            self.show.quality = self.quality if self.quality else sickbeard.QUALITY_DEFAULT
            self.show.flatten_folders = self.flatten_folders if self.flatten_folders != None else sickbeard.FLATTEN_FOLDERS_DEFAULT
            self.show.paused = 0

            # be smartish about this
            if self.show.genre and "talk show" in self.show.genre.lower():
                self.show.air_by_date = 1
            if self.show.genre and "documentary" in self.show.genre.lower():
                self.show.air_by_date = 0

        except tvdb_exceptions.tvdb_exception, e:
            logger.log(u"Unable to add show due to an error with TVDB: " + ex(e), logger.ERROR)
            if self.show:
                ui.notifications.error("Unable to add " + str(self.show.name) + " due to an error with TVDB")
            else:
                ui.notifications.error("Unable to add show due to an error with TVDB")
            self._finishEarly()
            return

        except exceptions.MultipleShowObjectsException:
            logger.log(u"The show in " + self.showDir + " is already in your show list, skipping", logger.ERROR)
            ui.notifications.error('Show skipped', "The show in " + self.showDir + " is already in your show list")
            self._finishEarly()
            return

        except Exception, e:
            logger.log(u"Error trying to add show: " + ex(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
            self._finishEarly()
            raise

        try:
            self.show.saveToDB()

        except Exception, e:
            logger.log(u"Error saving the show to the database: " + ex(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
            self._finishEarly()
            raise

        # add it to the show list
        sickbeard.showList.append(self.show)

        try:
            self.show.loadEpisodesFromTVDB()

        except Exception, e:
            logger.log(u"Error with TVDB, not creating episode list: " + ex(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)

        try:
            self.show.setTVRID()

        except Exception, e:
            logger.log(u"Error with TVRage, not setting tvrid" + ex(e), logger.ERROR)

        try:
            self.show.loadEpisodesFromDir()

        except Exception, e:
            logger.log(u"Error searching dir for episodes: " + ex(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)

        # if they gave a custom status then change all the eps to it
        if self.default_status != SKIPPED:
            logger.log(u"Setting all episodes to the specified default status: " + str(self.default_status))
            myDB = db.DBConnection()
            myDB.action("UPDATE tv_episodes SET status = ? WHERE status = ? AND showid = ? AND season > 0", [self.default_status, SKIPPED, self.show.tvdbid])

        # if they started with WANTED eps then run the backlog
        if self.default_status == WANTED:
            logger.log(u"Launching backlog for this show since its episodes are WANTED")
            sickbeard.backlogSearchScheduler.action.searchBacklog([self.show])  # @UndefinedVariable

        self.show.writeMetadata()
        self.show.populateCache()

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

        logger.log(u"Performing refresh on " + self.show.name)

        self.show.refreshDir()
        self.show.writeMetadata()
        self.show.populateCache()

        self.inProgress = False


class QueueItemRename(ShowQueueItem):
    def __init__(self, show=None):
        ShowQueueItem.__init__(self, ShowQueueActions.RENAME, show)

    def execute(self):

        ShowQueueItem.execute(self)

        logger.log(u"Performing rename on " + self.show.name)

        try:
            show_loc = self.show.location  # @UnusedVariable
        except exceptions.ShowDirNotFoundException:
            logger.log(u"Can't perform rename on " + self.show.name + " when the show dir is missing.", logger.WARNING)
            return

        ep_obj_rename_list = []

        ep_obj_list = self.show.getAllEpisodes(has_location=True)
        for cur_ep_obj in ep_obj_list:
            # Only want to rename if we have a location
            if cur_ep_obj.location:
                if cur_ep_obj.relatedEps:
                    # do we have one of multi-episodes in the rename list already
                    have_already = False
                    for cur_related_ep in cur_ep_obj.relatedEps + [cur_ep_obj]:
                        if cur_related_ep in ep_obj_rename_list:
                            have_already = True
                            break
                    if not have_already:
                        ep_obj_rename_list.append(cur_ep_obj)

                else:
                    ep_obj_rename_list.append(cur_ep_obj)

        for cur_ep_obj in ep_obj_rename_list:
            cur_ep_obj.rename()

        self.inProgress = False


class QueueItemUpdate(ShowQueueItem):
    def __init__(self, show=None):
        ShowQueueItem.__init__(self, ShowQueueActions.UPDATE, show)
        self.force = False

    def execute(self):

        ShowQueueItem.execute(self)

        logger.log(u"Beginning update of " + self.show.name)

        logger.log(u"Retrieving show info from TVDB", logger.DEBUG)
        try:
            self.show.loadFromTVDB(cache=not self.force)

        except tvdb_exceptions.tvdb_error, e:
            logger.log(u"Unable to contact TVDB, aborting: " + ex(e), logger.WARNING)
            return

        except tvdb_exceptions.tvdb_attributenotfound, e:
            logger.log(u"Data retrieved from TVDB was incomplete, aborting: " + ex(e), logger.ERROR)
            return

        # get episode list from DB
        logger.log(u"Loading all episodes from the database", logger.DEBUG)
        DBEpList = self.show.loadEpisodesFromDB()

        # get episode list from TVDB
        logger.log(u"Loading all episodes from theTVDB", logger.DEBUG)
        try:
            TVDBEpList = self.show.loadEpisodesFromTVDB(cache=not self.force)

        except tvdb_exceptions.tvdb_exception, e:
            logger.log(u"Unable to get info from TVDB, the show info will not be refreshed: " + ex(e), logger.ERROR)
            TVDBEpList = None

        if TVDBEpList == None:
            logger.log(u"No data returned from TVDB, unable to update this show", logger.ERROR)

        else:

            # for each ep we found on TVDB delete it from the DB list
            for curSeason in TVDBEpList:
                for curEpisode in TVDBEpList[curSeason]:
                    logger.log(u"Removing " + str(curSeason) + "x" + str(curEpisode) + " from the DB list", logger.DEBUG)
                    if curSeason in DBEpList and curEpisode in DBEpList[curSeason]:
                        del DBEpList[curSeason][curEpisode]

            # for the remaining episodes in the DB list just delete them from the DB
            for curSeason in DBEpList:
                for curEpisode in DBEpList[curSeason]:
                    logger.log(u"Permanently deleting episode " + str(curSeason) + "x" + str(curEpisode) + " from the database", logger.MESSAGE)
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

        sickbeard.showQueueScheduler.action.refreshShow(self.show, True)  # @UndefinedVariable


class QueueItemForceUpdate(QueueItemUpdate):
    def __init__(self, show=None):
        ShowQueueItem.__init__(self, ShowQueueActions.FORCEUPDATE, show)
        self.force = True
