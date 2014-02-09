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

import sickbeard
from sickbeard import logger
from sickbeard import exceptions
from sickbeard import show_name_helpers
from sickbeard import helpers
from sickbeard import search_queue
from sickbeard import failed_history
from sickbeard import scene_exceptions

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
        self._log(u"Failed download detected: (" + str(self.nzb_name) + ", " + str(self.dir_name) + ")")

        releaseName = show_name_helpers.determineReleaseName(self.dir_name, self.nzb_name)
        if releaseName is None:
            self._log(u"Warning: unable to find a valid release name.", logger.WARNING)
            raise exceptions.FailedProcessingFailed()

        parser = NameParser(False)
        try:
            parsed = parser.parse(releaseName)
        except InvalidNameException:
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

#        # Revert before fail, as fail alters the history
#        self._log(u"Reverting episodes...")
#        self.log += failed_history.revertEpisodes(self._show_obj, parsed.season_number, parsed.episode_numbers)
#        self._log(u"Marking release as bad: " + releaseName)
#        self.log += failed_history.logFailed(releaseName)
        
        self.log += failed_history.markFailed(self._show_obj, parsed.season_number, parsed.episode_numbers)
        self._log(u"Marking release as Failed: " + releaseName)
        self.log += failed_history.logFailed(releaseName)
        
        cur_failed_queue_item = search_queue.FailedQueueItem(self._show_obj, parsed.season_number)
        sickbeard.searchQueueScheduler.action.add_item(cur_failed_queue_item)

        return True

    def _log(self, message, level=logger.MESSAGE):
        """Log to regular logfile and save for return for PP script log"""
        logger.log(message, level)
        self.log += message + "\n"

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
