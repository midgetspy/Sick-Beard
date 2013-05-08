# Author: Tyler Fenby <tylerfenby@gmail.com>
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

from __future__ import with_statement

import logger
import os
from glob import glob

import sickbeard
from sickbeard import exceptions
from sickbeard import show_name_helpers
from sickbeard import helpers
from sickbeard import search_queue
from sickbeard import failed_history
from sickbeard import scene_exceptions
from sickbeard import common

from sickbeard import encodingKludge as ek
from sickbeard.name_parser.parser import NameParser, InvalidNameException


class FailedProcessor(object):
    """Take appropriate action when a download fails to complete"""

    def __init__(self, dirName, nzbName):
        """
        dirName: Full path to the folder of the failed download
        nzbName: Full name of the nzb file that failed
        """
        self.dir_name = dirName
        self.nzb_name = nzbName

        self._show_obj = None

        self.log = ""

    def process(self):
        self._log(u"Failed download detected: (" + str(self.nzb_name) + ", " + self.dir_name + ")")

        releaseName = self._get_release_name()
        if releaseName is None:
            self._log(u"Warning: unable to find a valid release name.", logger.WARNING)
            raise exceptions.FailedProcessingFailed()

        parser = NameParser(False)
        try:
            parsed = parser.parse(releaseName)
        except InvalidNameException as e:
            self._log(u"Error: release name is invalid: " + releaseName, logger.WARNING)
            raise exceptions.FailedProcessingFailed()

        logger.log(u"name_parser info: ", logger.DEBUG)
        logger.log(u" - " + str(parsed.series_name), logger.DEBUG)
        logger.log(u" - " + str(parsed.season_number), logger.DEBUG)
        logger.log(u" - " + str(parsed.episode_numbers), logger.DEBUG)
        logger.log(u" - " + str(parsed.extra_info), logger.DEBUG)
        logger.log(u" - " + str(parsed.release_group), logger.DEBUG)
        logger.log(u" - " + str(parsed.air_date), logger.DEBUG)

        show_id = self._get_show_id(parsed.series_name)
        if show_id is None:
            self._log(u"Warning: couldn't find show ID", logger.WARNING)
            raise exceptions.FailedProcessingFailed()

        self._log(u"Found show_id: " + str(show_id), logger.DEBUG)

        self._show_obj = helpers.findCertainShow(sickbeard.showList, show_id)
        if self._show_obj is None:
            self._log(u"Could not create show object. Either the show hasn't been added to SickBeard, or it's still loading (if SB was restarted recently)", logger.WARNING)
            raise exceptions.FailedProcessingFailed()

        self._revert_episode_statuses(parsed.season_number, parsed.episode_numbers)

        cur_backlog_queue_item = search_queue.BacklogQueueItem(self._show_obj, parsed.season_number)

        sickbeard.searchQueueScheduler.action.add_item(cur_backlog_queue_item)

        self._log(u"Marking release as bad: " + releaseName)
        failed_history.logFailed(releaseName)

        return True

    def _log(self, message, level=logger.MESSAGE):
        """Log to regular logfile and save for return for PP script log"""
        logger.log(message, level)
        self.log += message + "\n"

    def _get_release_name(self):
        """Try to find a valid-looking release name"""

        if self.nzb_name is not None:
            self._log(u"Using self.nzb_name for release name.")
            return self.nzb_name.rpartition('.')[0]

        # try to get the release name from nzb/nfo
        self._log(u"No self.nzb_name given. Trying to guess release name.")
        file_types = ["*.nzb", "*.nfo"]
        for search in file_types:
            search_path = ek.ek(os.path.join, self.dir_name, search)
            results = ek.ek(glob, search_path)
            if len(results) == 1:
                found_file = ek.ek(os.path.basename, results[0])
                found_file = found_file.rpartition('.')[0]
                if show_name_helpers.filterBadReleases(found_file):
                    self._log(u"Release name (" + found_file + ") found from file (" + results[0] + ")")
                    return found_file

        # If that fails, we try the folder
        folder = ek.ek(os.path.basename, self.dir_name)
        if show_name_helpers.filterBadReleases(folder):
            # NOTE: Multiple failed downloads will change the folder name.
            # (e.g., appending #s)
            # Should we handle that?
            self._log(u"Folder name (" + folder + ") appears to be a valid release name. Using it.")
            return folder

        return None

    def _get_show_id(self, series_name):
        """Find and return show ID by searching exceptions, then DB"""

        show_names = show_name_helpers.sceneToNormalShowNames(series_name)

        logger.log(u"show_names: " + str(show_names), logger.DEBUG)

        for show_name in show_names:
            exception = scene_exceptions.get_scene_exception_by_name(show_name)
            if exception is not None:
                return exception

        for show_name in show_names:
            found_info = helpers.searchDBForShow(show_name)
            if found_info is not None:
                return(found_info[0])

        return None

    def _revert_episode_statuses(self, season, episodes):
        """
        Revert episodes from Snatched to their former state

        season: int
        episodes: (int, ...)
        """

        if len(episodes) > 0:
            for cur_episode in episodes:
                ep_obj = None
                try:
                    ep_obj = self._show_obj.getEpisode(season, cur_episode)
                except exceptions.EpisodeNotFoundException, e:
                    self._log(u"Unable to create episode, please set its status manually: " + exceptions.ex(e), logger.WARNING)

                with ep_obj.lock:
                    # FIXME: Revert, don't just set wanted
                    self._log(u"Setting episode to WANTED: (" + str(season) + ", " + str(cur_episode) + ") " + ep_obj.name)
                    ep_obj.status = common.WANTED
                    ep_obj.saveToDB()

                # Could we hit a race condition where newly-wanted eps aren't included in the backlog search?
                #queue_item = search_queue.ManualSearchQueueItem(curEp)
                #sickbeard.searchQueueScheduler.action.add_item(queue_item)
        else:
            # Whole season
            self._log(u"Setting season to wanted: " + str(season))
            for cur_episode in self._show_obj.getAllEpisodes(season):
                with cur_episode.lock:
                    # FIXME: As above
                    logger.log(u"Setting episode to WANTED: (" + str(season) + ", " + str(cur_episode.episode) + ") " + cur_episode.name, logger.DEBUG)
                    cur_episode.status = common.WANTED
                    cur_episode.saveToDB()
