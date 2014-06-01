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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import time
import threading
import traceback

from sickbeard import logger
from sickbeard.exceptions import ex


class Scheduler:

    def __init__(self, action, cycleTime=datetime.timedelta(minutes=10), run_delay=datetime.timedelta(minutes=0), start_time=None, threadName="ScheduledThread", silent=False):

        self.lastRun = datetime.datetime.now() + run_delay - cycleTime

        self.action = action
        self.cycleTime = cycleTime
        self.start_time = start_time

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

            current_time = datetime.datetime.now()
            should_run = False

            # check if interval has passed
            if current_time - self.lastRun >= self.cycleTime:
                # check if wanting to start around certain time taking interval into account
                if self.start_time:
                    hour_diff = current_time.time().hour - self.start_time.hour
                    if hour_diff >= 0 and hour_diff < self.cycleTime.seconds / 3600:
                        should_run = True
                    else:
                        # set lastRun to only check start_time after another cycleTime
                        self.lastRun = current_time
                else:
                    should_run = True

            if should_run:
                self.lastRun = current_time
                try:
                    if not self.silent:
                        logger.log(u"Starting new thread: " + self.threadName, logger.DEBUG)
                    self.action.run()
                except Exception, e:
                    logger.log(u"Exception generated in thread " + self.threadName + ": " + ex(e), logger.ERROR)
                    logger.log(repr(traceback.format_exc()), logger.DEBUG)

            if self.abort:
                self.abort = False
                self.thread = None
                return

            time.sleep(1)
