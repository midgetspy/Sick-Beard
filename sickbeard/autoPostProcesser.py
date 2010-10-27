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

import sickbeard
from sickbeard import helpers
from sickbeard import logger

from sickbeard import encodingKludge as ek
from sickbeard import processTV
from sickbeard import db

import os.path


class PostProcesser():

    def run(self):
        if not sickbeard.PROCESS_AUTOMATICALLY:
            return

        if not ek.ek(os.path.isdir, sickbeard.TV_DOWNLOAD_DIR):
            logger.log("Automatic post-processing attempted but dir "+sickbeard.TV_DOWNLOAD_DIR+" doesn't exist", logger.ERROR)
            return

        if not ek.ek(os.path.isabs, sickbeard.TV_DOWNLOAD_DIR):
            logger.log("Automatic post-processing attempted but dir "+sickbeard.TV_DOWNLOAD_DIR+" is relative (and probably not what you really want to process)", logger.ERROR)
            return

        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM tv_shows WHERE location = ? OR location LIKE ?",
                                 [os.path.abspath(sickbeard.TV_DOWNLOAD_DIR),
                                  ek.ek(os.path.join, os.path.abspath(sickbeard.TV_DOWNLOAD_DIR), '%')])

        processTV.processDir(sickbeard.TV_DOWNLOAD_DIR)
