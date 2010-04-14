import datetime

from sickbeard.common import *

from sickbeard import logger
from sickbeard import exceptions
from sickbeard import ui

class ShowUpdater():
    
    def __init__(self):
        self.updateInterval = datetime.timedelta(hours=1) 
    
    def run(self, force=False):

        # update at 3 AM
        updateTime = datetime.time(hour=3)
        
        logger.log("Checking update interval", logger.DEBUG)

        hourDiff = datetime.datetime.today().time().hour - updateTime.hour
        
        # if it's less than an interval after the update time then do an update (or if we're forcing it)
        if hourDiff >= 0 and hourDiff < self.updateInterval.seconds/3600 or force:
            logger.log("Doing full update on all shows")
        else:
            return

        piList = []
        
        for curShow in sickbeard.showList:
            
            try:
            
                # either update or refresh depending on the time
                if curShow.status == "Ended":
                    #TODO: maybe I should still update specials?
                    logger.log("Doing refresh only for show "+curShow.name+" because it's marked as ended.", logger.DEBUG)
                    curQueueItem = sickbeard.showQueueScheduler.action.refreshShow(curShow)
                else:
                    curQueueItem = sickbeard.showQueueScheduler.action.updateShow(curShow, True)
                
                piList.append(curQueueItem)

            except (exceptions.CantUpdateException, exceptions.CantRefreshException), e:
                logger.log("Automatic update failed: " + str(e), logger.ERROR) 

        ui.ProgressIndicators.setIndicator('dailyUpdate', ui.QueueProgressIndicator("Daily Update", piList))
