import os.path
import threading
import sickbeard

from sickbeard import exceptions
from sickbeard.tv import TVShow
from sickbeard.logging import *

from lib.tvdb_api import tvdb_exceptions
        
class LoadingTVShow():
    def __init__(self, dir):
        self.dir = dir
        self.name = "Unknown (" + self.dir + ")"
        
def addShowsFromRootDir(dir):
    
    returnStr = ""
    
    if not os.path.isdir(dir):
        return "Couldn't find directory " + dir
    
    for curDir in os.listdir(dir):
        showDir = os.path.join(dir, curDir)
        logStr = "Attempting to load show in " + showDir
        Logger().log(logStr, DEBUG)
        returnStr += logStr + "<br />\n"

        sickbeard.loadingShowList[showDir] = LoadingTVShow(showDir)

        try:
            #myAdder = ShowAdder(showDir)
            #myAdder.start()
            sickbeard.showAddScheduler.addShowToQueue(showDir)
        except exceptions.NoNFOException:
            logStr = "Unable to automatically add the show in " + showDir
            Logger().log(logStr, ERROR)
            returnStr += logStr + "<br />\n"
            del sickbeard.loadingShowList[showDir]

    return returnStr

