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

import sickbeard

import threading
import traceback
import time

from sickbeard import logger
from sickbeard.tv import TVShow
from lib.tvdb_api import tvdb_exceptions


import exceptions
import ui
import helpers

class ShowAddQueue():

    def __init__(self):
        
        self.addQueue = []
        self.addThread = None
        self.currentlyAdding = None

    def isBeingAdded(self, show):
        return self.currentlyAdding != None and show == self.currentlyAdding.curShow

    def addShowToQueue(self, dir):
        try:
            self.addQueue.append(ShowAdder(dir))
        except exceptions.NoNFOException, e:
            logger.log("Unable to add show from " + dir + ", unable to create NFO: "+str(e), logger.DEBUG)
            raise

    def _doAddShow(self):
        # only start a new add task if one isn't already going
        if self.addThread == None or self.addThread.isAlive() == False:

            if self.currentlyAdding != None:
                self.currentlyAdding = None

            # if there's something in the queue then run it in a thread and take it out of the queue
            if len(self.addQueue) > 0:
                logger.log("Starting new add task for dir " + self.addQueue[0].showDir)
                self.addThread = threading.Thread(None, self.addQueue[0].run, "ADDSHOW")
                self.addThread.start()
                self.currentlyAdding = self.addQueue[0]
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
        self.curShow = None

        self.curShow = TVShow(self.showDir)

        sickbeard.loadingShowList[self.showDir] = ui.LoadingTVShow(self.showDir)
        

    def run(self):

        logger.log("Starting to add show "+self.showDir)

        try:
            self.curShow.getImages()
            self.curShow.loadFromTVDB()
            
        except exceptions.NoNFOException:
            logger.log("Unable to load show from NFO", logger.ERROR)
            # take the show out of the loading list
            del sickbeard.loadingShowList[self.showDir]
            return
            
        except exceptions.ShowNotFoundException:
            logger.log("The show in " + self.showDir + " couldn't be found on theTVDB, skipping", logger.ERROR)
            # take the show out of the loading list
            del sickbeard.loadingShowList[self.showDir]
            return
    
        except exceptions.MultipleShowObjectsException:
            logger.log("The show in " + self.showDir + " is already in your show list, skipping", logger.ERROR)
            # take the show out of the loading list
            del sickbeard.loadingShowList[self.showDir]
            return
        
        except Exception:
            del sickbeard.loadingShowList[self.showDir]
            raise
    
        sickbeard.loadingShowList[self.showDir].show = self.curShow

        # add it to the real list
        sickbeard.showList.append(self.curShow)

        try:
            self.curShow.loadEpisodesFromDir()
        except Exception, e:
            logger.log("Error searching dir for episodes: " + str(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
    
        try:
            self.curShow.loadEpisodesFromTVDB()
            self.curShow.setTVRID()
        except Exception, e:
            logger.log("Error with TVDB, not creating episode list: " + str(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
    
        try:
            self.curShow.saveToDB()
        except Exception, e:
            logger.log("Error saving the episode to the database: " + str(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
        
        self.curShow.flushEpisodes()
        
        # take the show out of the loading list
        del sickbeard.loadingShowList[self.showDir]
        
        sickbeard.updateAiringList()
        sickbeard.updateComingList()
        sickbeard.updateMissingList()
        
