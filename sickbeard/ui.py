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



import os.path
import threading
import sickbeard

from sickbeard import exceptions
from sickbeard.tv import TVShow
from sickbeard import logger

from lib.tvdb_api import tvdb_exceptions
        
class LoadingTVShow():
    def __init__(self, dir):
        self.dir = dir
        self.show = None
        
def addShowsFromRootDir(dir):
    
    returnStr = ""
    
    if not os.path.isdir(dir):
        return "Couldn't find directory " + dir
    
    for curDir in os.listdir(unicode(dir)):
        showDir = os.path.join(dir, curDir)
        logStr = "Attempting to load show in " + showDir
        logger.log(logStr, logger.DEBUG)
        returnStr += logStr + "<br />\n"

        sickbeard.loadingShowList[showDir] = LoadingTVShow(showDir)

        try:
            #myAdder = ShowAdder(showDir)
            #myAdder.start()
            sickbeard.showAddScheduler.action.addShowToQueue(showDir)
        except exceptions.NoNFOException:
            logStr = "Unable to automatically add the show in " + showDir
            logger.log(logStr, logger.ERROR)
            returnStr += logStr + "<br />\n"
            del sickbeard.loadingShowList[showDir]
        except exceptions.MultipleShowObjectsException:
            logStr = "Show in "+showDir+" already exists, skipping..."
            logger.log(logStr, logger.ERROR)
            returnStr += logStr + "<br />\n"
            del sickbeard.loadingShowList[showDir]

    return returnStr

