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

import datetime
import time

import sickbeard
from sickbeard import db, logger, common, exceptions, helpers
from sickbeard import generic_queue
from sickbeard import search
from sickbeard import ui

BACKLOG_SEARCH = 10
RSS_SEARCH = 20
MANUAL_SEARCH = 30


class SearchQueue(generic_queue.GenericQueue):

    def __init__(self):
        generic_queue.GenericQueue.__init__(self)
        self.queue_name = "SEARCHQUEUE"

    def is_in_queue(self, show, segment):
        for cur_item in self.queue:
            if isinstance(cur_item, BacklogQueueItem) and cur_item.show == show and cur_item.segment == segment:
                return True
        return False

    def is_ep_in_queue(self, ep_obj):
        for cur_item in self.queue:
            if isinstance(cur_item, ManualSearchQueueItem) and cur_item.ep_obj == ep_obj:
                return True
        return False

    def pause_backlog(self):
        self.min_priority = generic_queue.QueuePriorities.HIGH

    def unpause_backlog(self):
        self.min_priority = 0

    def is_backlog_paused(self):
        # backlog priorities are NORMAL, this should be done properly somewhere
        return self.min_priority >= generic_queue.QueuePriorities.NORMAL

    def is_backlog_in_progress(self):
        for cur_item in self.queue + [self.currentItem]:
            if isinstance(cur_item, BacklogQueueItem):
                return True
        return False

    def add_item(self, item):
        if isinstance(item, RSSSearchQueueItem):
            generic_queue.GenericQueue.add_item(self, item)
        # don't do duplicates
        elif isinstance(item, BacklogQueueItem) and not self.is_in_queue(item.show, item.segment):
            generic_queue.GenericQueue.add_item(self, item)
        elif isinstance(item, ManualSearchQueueItem) and not self.is_ep_in_queue(item.ep_obj):
            generic_queue.GenericQueue.add_item(self, item)
        else:
            logger.log(u"Not adding item, it's already in the queue", logger.DEBUG)


class ManualSearchQueueItem(generic_queue.QueueItem):
    def __init__(self, ep_obj):
        generic_queue.QueueItem.__init__(self, 'Manual Search', MANUAL_SEARCH)
        self.priority = generic_queue.QueuePriorities.HIGH

        self.ep_obj = ep_obj

        self.success = None

    def execute(self):
        generic_queue.QueueItem.execute(self)

        logger.log(u"Beginning manual search for " + self.ep_obj.prettyName())

        foundEpisode = search.findEpisode(self.ep_obj, manualSearch=True)
        result = False

        if not foundEpisode:
            ui.notifications.message('No downloads were found', "Couldn't find a download for <i>%s</i>" % self.ep_obj.prettyName())
            logger.log(u"Unable to find a download for " + self.ep_obj.prettyName())

        else:

            # just use the first result for now
            logger.log(u"Downloading episode from " + foundEpisode.url)
            result = search.snatchEpisode(foundEpisode)
            providerModule = foundEpisode.provider
            if not result:
                ui.notifications.error('Error while attempting to snatch ' + foundEpisode.name + ', check your logs')
            elif providerModule == None:
                ui.notifications.error('Provider is configured incorrectly, unable to download')

        self.success = result

    def finish(self):
        # don't let this linger if something goes wrong
        if self.success == None:
            self.success = False
        generic_queue.QueueItem.finish(self)


class RSSSearchQueueItem(generic_queue.QueueItem):
    def __init__(self):
        generic_queue.QueueItem.__init__(self, 'RSS Search', RSS_SEARCH)

    def execute(self):
        generic_queue.QueueItem.execute(self)

        self._changeMissingEpisodes()

        logger.log(u"Beginning search for new episodes on RSS")

        foundResults = search.searchForNeededEpisodes()

        if not len(foundResults):
            logger.log(u"No needed episodes found on the RSS feeds")
        else:
            for curResult in foundResults:
                search.snatchEpisode(curResult)
                time.sleep(2)

        generic_queue.QueueItem.finish(self)

    def _changeMissingEpisodes(self):

        logger.log(u"Changing all old missing episodes to status WANTED")

        curDate = datetime.date.today().toordinal()

        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE status = ? AND season > 0 AND airdate < ?", [common.UNAIRED, curDate])

        for sqlEp in sqlResults:

            try:
                show = helpers.findCertainShow(sickbeard.showList, int(sqlEp["showid"]))
            except exceptions.MultipleShowObjectsException:
                logger.log(u"ERROR: expected to find a single show matching " + sqlEp["showid"])
                return None

            if show == None:
                logger.log(u"Unable to find the show with ID " + str(sqlEp["showid"]) + " in your show list! DB value was " + str(sqlEp), logger.ERROR)
                return None

            ep = show.getEpisode(sqlEp["season"], sqlEp["episode"])
            with ep.lock:
                if ep.show.paused:
                    ep.status = common.SKIPPED
                else:
                    ep.status = common.WANTED
                ep.saveToDB()


class BacklogQueueItem(generic_queue.QueueItem):
    def __init__(self, show, segment):
        generic_queue.QueueItem.__init__(self, 'Backlog', BACKLOG_SEARCH)
        self.priority = generic_queue.QueuePriorities.LOW
        self.thread_name = 'BACKLOG-' + str(show.tvdbid)

        self.show = show
        self.segment = segment

        logger.log(u"Seeing if we need any episodes from " + self.show.name + " season " + str(self.segment))

        myDB = db.DBConnection()

        # see if there is anything in this season worth searching for
        if not self.show.air_by_date:
            statusResults = myDB.select("SELECT status FROM tv_episodes WHERE showid = ? AND season = ?", [self.show.tvdbid, self.segment])
        else:
            segment_year, segment_month = map(int, self.segment.split('-'))
            min_date = datetime.date(segment_year, segment_month, 1)

            # it's easier to just hard code this than to worry about rolling the year over or making a month length map
            if segment_month == 12:
                max_date = datetime.date(segment_year, 12, 31)
            else:
                max_date = datetime.date(segment_year, segment_month + 1, 1) - datetime.timedelta(days=1)

            statusResults = myDB.select("SELECT status FROM tv_episodes WHERE showid = ? AND airdate >= ? AND airdate <= ?",
                                        [self.show.tvdbid, min_date.toordinal(), max_date.toordinal()])

        anyQualities, bestQualities = common.Quality.splitQuality(self.show.quality)  # @UnusedVariable
        self.wantSeason = self._need_any_episodes(statusResults, bestQualities)

    def execute(self):

        generic_queue.QueueItem.execute(self)

        results = search.findSeason(self.show, self.segment)

        # download whatever we find
        for curResult in results:
            if curResult:
                search.snatchEpisode(curResult)
                time.sleep(5)

        self.finish()

    def _need_any_episodes(self, statusResults, bestQualities):

        wantSeason = False

        # check through the list of statuses to see if we want any
        for curStatusResult in statusResults:
            curCompositeStatus = int(curStatusResult["status"])
            curStatus, curQuality = common.Quality.splitCompositeStatus(curCompositeStatus)

            if bestQualities:
                highestBestQuality = max(bestQualities)
            else:
                highestBestQuality = 0

            # if we need a better one then say yes
            if (curStatus in (common.DOWNLOADED, common.SNATCHED, common.SNATCHED_PROPER) and curQuality < highestBestQuality) or curStatus == common.WANTED:
                wantSeason = True
                break

        return wantSeason
