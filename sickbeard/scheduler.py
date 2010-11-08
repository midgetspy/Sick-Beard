import datetime
import time
import threading
import traceback

from lib.tvdb_api import tvdb_exceptions

from sickbeard import logger

class Scheduler:

    def __init__(self, action, cycleTime=datetime.timedelta(minutes=10), runImmediately=True, threadName="ScheduledThread", silent=False):

        if runImmediately:
            self.lastRun = datetime.datetime.fromordinal(1)
        else:
            self.lastRun = datetime.datetime.now()

        self.action = action
        self.cycleTime = cycleTime

        self.thread = None
        self.threadName = threadName
        self.silent = silent

        self.initThread()

        self.abort = False

    def initThread(self):
        if self.thread == None or not self.thread.isAlive():
            self.thread = threading.Thread(None, self.runAction, self.threadName)

    def timeLeft(self):
        return self.cycleTime - (datetime.datetime.now() - self.lastRun)

    def forceRun(self):
        if not self.action.amActive:
            self.lastRun = datetime.datetime.fromordinal(1)
            return True
        return False

    def runAction(self):

        while True:

            currentTime = datetime.datetime.now()

            if currentTime - self.lastRun > self.cycleTime:
                self.lastRun = currentTime
                try:
                    if not self.silent:
                        logger.log(u"Starting new thread: "+self.threadName, logger.DEBUG)
                    self.action.run()
                except Exception, e:
                    logger.log(u"Exception generated in thread "+self.threadName+": " + str(e), logger.ERROR)
                    logger.log(traceback.format_exc(), logger.DEBUG)

            if self.abort:
                self.abort = False
                self.thread = None
                return

            time.sleep(1)
