# Author: Dennis Lutter <lad1337@gmail.com>
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

import os.path

import sickbeard

from sickbeard import db
from sickbeard import logger
from sickbeard import encodingKludge as ek
from sickbeard import processTV
from sickbeard import sab

class SabPoller():

    def run(self):
        if not sickbeard.NZB_METHOD == "sabnzbd" or not sickbeard.SAB_POLL:
            return False

        history = sab.getHistory()
        if not history:
            logger.log("no history from sab please look for previous log messages", logger.WARNING)
            return False

        mySlots = []
        historySlots = history['history']['slots']
        historySlots.reverse() # reverse slot order to have a old->new order... fifo
        for slot in historySlots:
            if slot['category'] == sickbeard.SAB_CATEGORY and slot['status'] == "Completed" and not checkSuccessfulPP(slot['storage']):
                mySlots.append(slot)

        if len(mySlots) == 0:
            logger.log("Nothing new in the sab history this time", logger.DEBUG)
            return False

        for slot in mySlots:
            curPath = slot['storage']
            if not ek.ek(os.path.isdir, curPath):
                logger.log(u"Post-processing attempted but " + curPath + " dir doesn't exist", logger.DEBUG)
                continue

            if not ek.ek(os.path.isabs, curPath):
                logger.log(u"Post-processing attempted but dir " + curPath + " is relative (and probably not what you really want to process)", logger.DEBUG)
                continue

            processTV.processDir(curPath, nzbName=slot['nzb_name'])

        return True

def checkSuccessfulPP(path):
    myDB = db.DBConnection()
    sql_results = myDB.select("SELECT * FROM history WHERE resource LIKE ?", [path + '%'])
    return bool(len(sql_results))
