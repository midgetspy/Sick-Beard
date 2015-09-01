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

from sickbeard import db
from sickbeard import search_queue
from sickbeard import logger
from sickbeard import ui


class PVRSearcher:

    def __init__(self):

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
        logger.log(u"amWaiting: " + str(self.amWaiting) + ", amActive: " + str(self.amActive), logger.DEBUG)
        return (not self.amWaiting) and self.amActive

    def searchPVR(self, which_shows=None):

        if which_shows:
            show_list = which_shows
        else:
            show_list = sickbeard.showList

        def titler(x):
            if not x:
                return x
            if not x.lower().startswith('a to ') and x.lower().startswith('a '):
                    x = x[2:]
            elif x.lower().startswith('an '):
                    x = x[3:]
            elif x.lower().startswith('the '):
                    x = x[4:]
            return x
        # sort shows the same way we show them, makes it easier to follow along
        show_list = sorted(show_list, lambda x, y: cmp(titler(x.name), titler(y.name)))

        if self.amActive is True:
            logger.log(u"Pvr search is still running, not starting it again", logger.DEBUG)
            return

        fromDate = datetime.date.fromordinal(1)

        self.amActive = True
        self.amPaused = False

        # get separate lists of the season/date shows
        #season_shows = [x for x in show_list if not x.air_by_date]
        air_by_date_shows = [x for x in show_list if x.air_by_date]

        # figure out how many segments of air by date shows we're going to do
        air_by_date_segments = []
        for cur_id in [x.tvdbid for x in air_by_date_shows]:
            air_by_date_segments += self._get_air_by_date_segments(cur_id, fromDate)

        logger.log(u"Air-by-date segments: " + str(air_by_date_segments), logger.DEBUG)

        # go through non air-by-date shows and see if they need any episodes
        for curShow in show_list:

            if curShow.paused:
                continue

            if curShow.air_by_date:
                segments = [x[1] for x in self._get_air_by_date_segments(curShow.tvdbid, fromDate)]
            else:
                segments = self._get_season_segments(curShow.tvdbid, fromDate)

            for cur_segment in segments:

                self.currentSearchInfo = {'title': curShow.name + " Season " + str(cur_segment)}

                pvr_queue_item = search_queue.PVRQueueItem(curShow, cur_segment)

                if not pvr_queue_item.wantSeason:
                    logger.log(u"Nothing in season " + str(cur_segment) + " needs to be downloaded, skipping this season", logger.DEBUG)
                else:
                    sickbeard.searchQueueScheduler.action.add_item(pvr_queue_item)  # @UndefinedVariable

        self.amActive = False
        self._resetPI()


    def _get_season_segments(self, tvdb_id, fromDate):
        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT DISTINCT(season) as season FROM tv_episodes WHERE showid = ? AND season > 0 and airdate > ?", [tvdb_id, fromDate.toordinal()])
        return [int(x["season"]) for x in sqlResults]

    def _get_air_by_date_segments(self, tvdb_id, fromDate):
        # query the DB for all dates for this show
        myDB = db.DBConnection()
        num_air_by_date_results = myDB.select("SELECT airdate, showid FROM tv_episodes ep, tv_shows show WHERE season != 0 AND ep.showid = show.tvdb_id AND show.paused = 0 ANd ep.airdate > ? AND ep.showid = ?",
                                 [fromDate.toordinal(), tvdb_id])

        # break them apart into month/year strings
        air_by_date_segments = []
        for cur_result in num_air_by_date_results:
            cur_date = datetime.date.fromordinal(int(cur_result["airdate"]))
            cur_date_str = str(cur_date)[:7]
            cur_tvdb_id = int(cur_result["showid"])

            cur_result_tuple = (cur_tvdb_id, cur_date_str)
            if cur_result_tuple not in air_by_date_segments:
                air_by_date_segments.append(cur_result_tuple)

        return air_by_date_segments

    def run(self):
        try:
            self.searchPVR()
        except:
            self.amActive = False
            raise
