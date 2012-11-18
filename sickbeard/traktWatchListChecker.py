# Author: Frank Fenton
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
import time
import os

import sickbeard
from sickbeard import encodingKludge as ek
from sickbeard import logger
from sickbeard import helpers
from sickbeard import search_queue
from sickbeard.common import SNATCHED, SNATCHED_PROPER, DOWNLOADED, SKIPPED, UNAIRED, IGNORED, ARCHIVED, WANTED, UNKNOWN
from lib.trakt import *

class TraktChecker():
    def __init__(self):
        self.todoWanted = []
        self.todoBacklog = []

    def run(self):
        if sickbeard.TRAKT_USE_WATCHLIST:
            self.todoWanted = []  #its about to all get re-added
            if len(sickbeard.ROOT_DIRS.split('|')) < 2:
                logger.log(u"No default root directory", logger.ERROR)
                return
            self.updateShows()
            self.updateEpisodes()


    def updateShows(self):
        logger.log(u"Starting trakt show watchlist check", logger.DEBUG)
        watchlist = TraktCall("user/watchlist/shows.json/%API%/" + sickbeard.TRAKT_USERNAME, sickbeard.TRAKT_API, sickbeard.TRAKT_USERNAME, sickbeard.TRAKT_PASSWORD)
        if watchlist is None:
            logger.log(u"Could not connect to trakt service, aborting watchlist update", logger.ERROR)
            return
        for show in watchlist:
            if int(sickbeard.TRAKT_METHOD_ADD) != 2:
                self.addDefaultShow(show["tvdb_id"], show["title"], SKIPPED)
            else:
                self.addDefaultShow(show["tvdb_id"], show["title"], WANTED)

            if int(sickbeard.TRAKT_METHOD_ADD) == 1:
                newShow = helpers.findCertainShow(sickbeard.showList, int(show["tvdb_id"]))
                if newShow is not None:
                    self.setEpisodeToWanted(newShow, 1, 1)
                    self.startBacklog(newShow)
                else:
                    self.todoWanted.append((int(show["tvdb_id"]), 1, 1))
            self.todoWanted.append((int(show["tvdb_id"]), -1, -1)) #used to pause new shows if the settings say to

    def updateEpisodes(self):
        """
        Sets episodes to wanted that are in trakt watchlist
        """
        logger.log(u"Starting trakt episode watchlist check", logger.DEBUG)
        watchlist = TraktCall("user/watchlist/episodes.json/%API%/" + sickbeard.TRAKT_USERNAME, sickbeard.TRAKT_API, sickbeard.TRAKT_USERNAME, sickbeard.TRAKT_PASSWORD)
        if watchlist is None:
            logger.log(u"Could not connect to trakt service, aborting watchlist update", logger.ERROR)
            return
        for show in watchlist:
            self.addDefaultShow(show["tvdb_id"], show["title"], SKIPPED)
            newShow = helpers.findCertainShow(sickbeard.showList, int(show["tvdb_id"]))
            for episode in show["episodes"]:
                if newShow is not None:
                    self.setEpisodeToWanted(newShow, episode["season"], episode["number"])
                else:
                    self.todoWanted.append((int(show["tvdb_id"]), episode["season"], episode["number"]))
            self.startBacklog(newShow)

    def addDefaultShow(self, tvdbid, name, status):
        """
        Adds a new show with the default settings
        """
        showObj = helpers.findCertainShow(sickbeard.showList, int(tvdbid))
        if showObj != None:
            return
        logger.log(u"Adding show " + tvdbid)
        root_dirs = sickbeard.ROOT_DIRS.split('|')
        location = root_dirs[int(root_dirs[0]) + 1]

        showPath = ek.ek(os.path.join, location, helpers.sanitizeFileName(name))
        dir_exists = helpers.makeDir(showPath)
        if not dir_exists:
            logger.log(u"Unable to create the folder " + showPath + ", can't add the show", logger.ERROR)
            return
        else:
            helpers.chmodAsParent(showPath)
        sickbeard.showQueueScheduler.action.addShow(int(tvdbid), showPath, status, int(sickbeard.QUALITY_DEFAULT), int(sickbeard.FLATTEN_FOLDERS_DEFAULT), "en")

    def setEpisodeToWanted(self, show, s, e):
        """
        Sets an episode to wanted, only is it is currently skipped
        """
        epObj = show.getEpisode(int(s), int(e))
        if epObj == None:
            return
        with epObj.lock:
            if epObj.status != SKIPPED:
                return
            logger.log(u"Setting episode s"+str(s)+"e"+str(e)+" of show " + show.name + " to wanted")
            # figure out what segment the episode is in and remember it so we can backlog it
            if epObj.show.air_by_date:
                ep_segment = str(epObj.airdate)[:7]
            else:
                ep_segment = epObj.season

            epObj.status = WANTED
            epObj.saveToDB()
            backlog = (show, ep_segment)
            if self.todoBacklog.count(backlog)==0:
                self.todoBacklog.append(backlog)


    def manageNewShow(self, show):
        episodes = [i for i in self.todoWanted if i[0] == show.tvdbid]
        for episode in episodes:
            self.todoWanted.remove(episode)
            if episode[1] == -1 and sickbeard.TRAKT_START_PAUSED:
                show.paused = 1
                continue
            self.setEpisodeToWanted(show, episode[1], episode[2])
        self.startBacklog(show)

    def startBacklog(self, show):
        segments = [i for i in self.todoBacklog if i[0] == show]
        for segment in segments:
            cur_backlog_queue_item = search_queue.BacklogQueueItem(show, segment[1])
            sickbeard.searchQueueScheduler.action.add_item(cur_backlog_queue_item)
            logger.log(u"Starting backlog for " + show.name + " season " + str(segment[1]) + " because some eps were set to wanted")
            self.todoBacklog.remove(segment)


