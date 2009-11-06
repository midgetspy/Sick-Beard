import sickbeard

import tv
import sqlite3
import db
import threading
import traceback
import time

from sickbeard.logging import *

from lib.tvdb_api import tvdb_exceptions

from sickbeard.tv import TVShow
from sickbeard import exceptions
from sickbeard import ui

class ShowAddScheduler():

    def __init__(self):
        
        self.addQueue = []
        
        self.addThread = None
        
        self.thread = None
        self.initThread()

        self.abort = False

    def initThread(self):
        if self.thread == None:
            self.thread = threading.Thread(None, self.scheduleShows, "SHOWADDER")

    def addShowToQueue(self, dir):
        try:
            self.addQueue.append(ShowAdder(dir))
        except exceptions.NoNFOException:
            Logger().log(" Unable to add show from " + dir + ", show will not be added", ERROR)
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
                
        
    def scheduleShows(self):
        
        while True:
            
            self._doAddShow()
            
            if self.abort:
                self.abort = False
                self.addThread = None
                return
            
            time.sleep(3) 

class ShowAdder:
    
    def __init__(self, showDir):
        if not os.path.isdir(showDir) or not os.path.isfile(os.path.join(showDir, "tvshow.nfo")):
            raise exceptions.NoNFOException()
        
        self.showDir = showDir

    def run(self):

        sickbeard.loadingShowList[self.showDir] = ui.LoadingTVShow(self.showDir)

        try:
            newShow = TVShow(self.showDir)
            
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
    
        if sickbeard.loadingShowList.has_key(self.showDir):
            sickbeard.loadingShowList[self.showDir].name = newShow.name

        try:
            newShow.loadEpisodesFromDir()
        except Exception as e:
            Logger().log("Error searching dir for episodes: " + str(e), ERROR)
    
        try:
            newShow.loadEpisodesFromTVDB()
        except tvdb_exceptions.tvdb_error as e:
            Logger().log("Error with TVDB, not creating episode list: " + str(e), ERROR)
    
        try:
            newShow.saveToDB()
        except Exception as e:
            Logger().log("Error saving the episode to the database: " + str(e), ERROR)
        
        # take the show out of the loading list
        del sickbeard.loadingShowList[self.showDir]
        
        # add it to the real list
        sickbeard.showList.append(newShow)
