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
import threading

import sickbeard
from lib import peewee

from sickbeard.db_peewee import Info, TvEpisode, TvShow
from sickbeard import scheduler
from sickbeard import search_queue
from sickbeard import logger
from sickbeard import ui
#from sickbeard.common import *

class BacklogSearchScheduler(scheduler.Scheduler):

    def forceSearch(self):
        self.action._set_lastBacklog(1)
        self.lastRun = datetime.datetime.fromordinal(1)

    def nextRun(self):
        if self.action._lastBacklog <= 1:
            return datetime.date.today()
        else:
            return datetime.date.fromordinal(self.action._lastBacklog + self.action.cycleTime)

class BacklogSearcher:

    def __init__(self):

        self._lastBacklog = self._get_lastBacklog()
        self.cycleTime = 7
        self.lock = threading.Lock()
        self.amActive = False
        self.amPaused = False
        self.amWaiting = False

        self._resetPI()

    def _resetPI(self):
        self.percentDone = 0
        self.currentSearchInfo = {'title': 'Initializing'}

    def getProgressIndicator(self):
        if self.amActive:
            return ui.ProgressIndicator(self.percentDone, self.currentSearchInfo)
        else:
            return None

    def am_running(self):
        logger.log(u"amWaiting: "+str(self.amWaiting)+", amActive: "+str(self.amActive), logger.DEBUG)
        return (not self.amWaiting) and self.amActive

    def searchBacklog(self, which_shows=None):

        if which_shows:
            show_list = which_shows
        else:
            show_list = sickbeard.showList

        if self.amActive == True:
            logger.log(u"Backlog is still running, not starting it again", logger.DEBUG)
            return

        self._get_lastBacklog()

        curDate = datetime.date.today().toordinal()
        fromDate = datetime.date.fromordinal(1)

        if not which_shows and not curDate - self._lastBacklog >= self.cycleTime:
            logger.log(u"Running limited backlog on recently missed episodes only")
            fromDate = datetime.date.today() - datetime.timedelta(days=7)

        self.amActive = True
        self.amPaused = False

        # get separate lists of the season/date shows
        #season_shows = [x for x in show_list if not x.air_by_date]
        air_by_date_shows = [x for x in show_list if x.air_by_date]

        # figure out how many segments of air by date shows we're going to do
        air_by_date_segments = []
        for cur_id in [x.tvdbid for x in air_by_date_shows]:
            air_by_date_segments += self._get_air_by_date_segments(cur_id, fromDate) 

        logger.log(u"Air-by-date segments: "+str(air_by_date_segments), logger.DEBUG)

        #totalSeasons = float(len(numSeasonResults) + len(air_by_date_segments))
        #numSeasonsDone = 0.0

        # go through non air-by-date shows and see if they need any episodes
        for curShow in show_list:

            if curShow.paused:
                continue

            if curShow.air_by_date:
                segments = [x[1] for x in self._get_air_by_date_segments(curShow.tvdbid, fromDate)]
            else:
                segments = self._get_season_segments(curShow.tvdbid, fromDate)

            for cur_segment in segments:

                self.currentSearchInfo = {'title': curShow.name + " Season "+str(cur_segment)}

                backlog_queue_item = search_queue.BacklogQueueItem(curShow, cur_segment)

                if not backlog_queue_item.wantSeason:
                    logger.log(u"Nothing in season "+str(cur_segment)+" needs to be downloaded, skipping this season", logger.DEBUG)
                else:
                    sickbeard.searchQueueScheduler.action.add_item(backlog_queue_item)  #@UndefinedVariable

        # don't consider this an actual backlog search if we only did recent eps
        # or if we only did certain shows
        if fromDate == datetime.date.fromordinal(1) and not which_shows:
            self._set_lastBacklog(curDate)

        self.amActive = False
        self._resetPI()

    def _get_lastBacklog(self):

        logger.log(u"Retrieving the last check time from the DB", logger.DEBUG)

        result = Info.select().first()

        if result is None:
            lastBacklog = 1
        elif result.last_backlog is None or result.last_backlog == "":
            lastBacklog = 1
        else:
            lastBacklog = result.last_backlog

        self._lastBacklog = lastBacklog
        return self._lastBacklog

    def _get_season_segments(self, tvdb_id, fromDate):
        results = TvEpisode.select(
            peewee.fn.Distinct(TvEpisode.season).alias('season')).where(
                (TvEpisode.show == tvdb_id) &
                (TvEpisode.season > 0) &
                (TvEpisode.airdate > fromDate.toordinal())
            )
        return [x.season for x in results]

    def _get_air_by_date_segments(self, tvdb_id, fromDate):
        # query the DB for all dates for this show
        query = TvEpisode.select(
            TvEpisode, TvShow.paused
        ).where(
            (TvEpisode.season != 0) &
            (TvEpisode.show == tvdb_id) &
            (TvEpisode.airdate > fromDate.toordinal())
        ).join(TvShow)

        # break them apart into month/year strings
        air_by_date_segments = []
        for cur_result in query:
            if cur_result.show.paused:
                continue
            cur_date = datetime.date.fromordinal(cur_result.airdate)
            cur_date_str = str(cur_date)[:7]
            cur_tvdb_id = cur_result.show.tvdb_id

            cur_result_tuple = (cur_tvdb_id, cur_date_str)
            if cur_result_tuple not in air_by_date_segments:
                air_by_date_segments.append(cur_result_tuple)

        return air_by_date_segments

    def _set_lastBacklog(self, when):

        logger.log(u"Setting the last backlog in the DB to " + str(when), logger.DEBUG)

        info = Info.select().first()
        if info is None:
            Info(
                last_backlog=when,
                last_tvdb=0
            ).save()
        else:
            info.last_backlog = when
            info.save()


    def run(self):
        try:
            self.searchBacklog()
        except:
            self.amActive = False
            raise
