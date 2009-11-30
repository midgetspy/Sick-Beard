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

import threading
import traceback
import time

from sickbeard.logging import *
from sickbeard.tv import TVShow
from lib.tvdb_api import tvdb_exceptions


import exceptions
import ui
import helpers

class ShowAddQueue():

    def __init__(self):
        
        self.addQueue = []
        self.addThread = None

    def addShowToQueue(self, dir):
        try:
            self.addQueue.append(ShowAdder(dir))
        except exceptions.NoNFOException:
            Logger().log(" Unable to add show from " + dir + ", NFO must be created first", ERROR)
            raise

    def _doAddShow(self):
        # only start a new add task if one isn't already going
        if self.addThread == None or self.addThread.isAlive() == False:

            # if there's something in the queue then run it in a thread and take it out of the queue
            if len(self.addQueue) > 0:
                Logger().log("Starting new add task for dir " + self.addQueue[0].showDir)
                self.addThread = threading.Thread(None, self.addQueue[0].run, "ADDSHOW")
                self.addThread.start()
                del self.addQueue[0]

    def run(self):
        self._doAddShow()

    

class ShowAdder:
    
    def __init__(self, showDir):
        
        if not os.path.isdir(showDir):
            # if we can't create the dir, bail
            if not helpers.makeDir(showDir):
                raise exceptions.NoNFOException()

        if not os.path.isfile(os.path.join(showDir, "tvshow.nfo")):
            raise exceptions.NoNFOException()

        self.showDir = showDir

    def run(self):

        sickbeard.loadingShowList[self.showDir] = ui.LoadingTVShow(self.showDir)

        try:
            newShow = TVShow(self.showDir)
            newShow.loadFromTVDB()
            
        except exceptions.NoNFOException:
            Logger().log("Unable to load show from NFO", ERROR)
            # take the show out of the loading list
            del sickbeard.loadingShowList[self.showDir]
            return
            
        except exceptions.ShowNotFoundException:
            Logger().log("The show in " + self.showDir + " couldn't be found on theTVDB, skipping", ERROR)
            # take the show out of the loading list
            del sickbeard.loadingShowList[self.showDir]
            return
    
        except exceptions.MultipleShowObjectsException:
            Logger().log("The show in " + self.showDir + " is already in your show list, skipping", ERROR)
            # take the show out of the loading list
            del sickbeard.loadingShowList[self.showDir]
            return
        
        except Exception:
            del sickbeard.loadingShowList[self.showDir]
            raise
    
        if sickbeard.loadingShowList.has_key(self.showDir):
            sickbeard.loadingShowList[self.showDir].name = newShow.name

        try:
            newShow.loadEpisodesFromDir()
        except Exception as e:
            Logger().log("Error searching dir for episodes: " + str(e), ERROR)
            Logger().log(traceback.format_exc(), DEBUG)
    
        try:
            newShow.loadEpisodesFromTVDB()
        except Exception as e:
            Logger().log("Error with TVDB, not creating episode list: " + str(e), ERROR)
            Logger().log(traceback.format_exc(), DEBUG)
    
        try:
            newShow.saveToDB()
        except Exception as e:
            Logger().log("Error saving the episode to the database: " + str(e), ERROR)
            Logger().log(traceback.format_exc(), DEBUG)
        
        newShow.flushEpisodes()
        
        # take the show out of the loading list
        del sickbeard.loadingShowList[self.showDir]
        
        # add it to the real list
        sickbeard.showList.append(newShow)
