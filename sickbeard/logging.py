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




import datetime
import os.path
import threading
import unicodedata

from exceptions import *

import sickbeard

ERROR = 2
MESSAGE = 1
DEBUG = 0

logLevelStrings = {}
logLevelStrings[ERROR] = "ERROR"
logLevelStrings[MESSAGE] = "MESSAGE"
logLevelStrings[DEBUG] = "DEBUG"


class Logger:
    """ A python singleton """

    class __impl:
        """ Implementation of the singleton interface """

        def __init__(self, loglevel=DEBUG):
            
            self.curDate = datetime.date.today()
            
            self.logLock = threading.Lock()
            
            self.loglevel = loglevel
            
            self.fileObj = self._logObject()
                    
        def _logName(self):
            return "sickbeard." + str(self.curDate) + ".log"

        def _logObject(self):
            
            # if there's no log folder there's no file
            if sickbeard.LOG_DIR == None or not os.path.isdir(sickbeard.LOG_DIR):
                return None
            
            #TODO: try catch
            fileObj = open(os.path.join(sickbeard.LOG_DIR, self._logName()), "a+")
            return fileObj
        
        def shutdown(self):

            if self.fileObj == None:
                return
            
            with self.logLock:
                self.fileObj.close()
                self.fileObj = None
        
        def log(self, message, logLevel=MESSAGE):
            
            # if the message has lower level than our log level, don't log it 
            if logLevel < self.loglevel:
                return

            meThread = threading.currentThread().name
            timestamp = datetime.datetime.now().strftime("%I:%M:%S %p")
            outLine = "[" + timestamp + "] <" + meThread + "::" + logLevelStrings[logLevel] + "> " + message
            outLine = outLine.decode('ascii', 'ignore')
            
            if self.fileObj == None:
                self.fileObj = self._logObject()
            
            if self.fileObj != None:
                with self.logLock:
                
                    # check the filename, change the file if needed
                    now = datetime.date.today()
                    if now > self.curDate:
                        self.fileObj.close()
                        self.curDate = now
                        self.fileObj = self._logObject()
                    
                    self.fileObj.write(outLine + "\n")
                    self.fileObj.flush()
                
            #TODO: this should be done better, but right now I only print stuff that's MESSAGE or higher
            if logLevel >= MESSAGE:
                print outLine

    # storage for the instance reference
    __instance = None

    def __init__(self, loglevel=DEBUG):
        """ Create singleton instance """
        # Check whether we already have an instance
        if Logger.__instance is None:
            # Create and remember instance
            Logger.__instance = Logger.__impl(loglevel)

        # Store instance reference as the only member in the handle
        self.__dict__['_Logger__instance'] = Logger.__instance

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)
