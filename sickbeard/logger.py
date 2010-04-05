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

import logging
import logging.handlers

from exceptions import *

import sickbeard

from sickbeard import classes

ERROR = logging.ERROR
WARNING = logging.WARNING
MESSAGE = logging.INFO
DEBUG = logging.DEBUG

reverseNames = {u'ERROR': ERROR,
                u'WARNING': WARNING,
                u'INFO': MESSAGE,
                u'DEBUG': DEBUG}

logFile = ''

def initLogging(consoleLogging=True):
    global logFile

    logFile = os.path.join(sickbeard.LOG_DIR, 'sickbeard.log')
            
    fileHandler = logging.handlers.RotatingFileHandler(
                  logFile,
                  maxBytes=25000000,
                  backupCount=5)

    fileHandler.setLevel(logging.DEBUG)
    fileHandler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', '%b-%d %H:%M:%S'))

    logging.getLogger('sickbeard').addHandler(fileHandler)
    
    # define a Handler which writes INFO messages or higher to the sys.stderr
    if consoleLogging:
        console = logging.StreamHandler()
        
        console.setLevel(logging.INFO)
    
        # set a format which is simpler for console use
        console.setFormatter(logging.Formatter('%(asctime)s %(levelname)s::%(message)s', '%H:%M:%S'))
    
        # add the handler to the root logger
        logging.getLogger('sickbeard').addHandler(console)

    logging.getLogger('sickbeard').setLevel(logging.DEBUG)
    
def log(toLog, logLevel=MESSAGE):
    
    meThread = threading.currentThread().getName()
    message = meThread + " :: " + toLog
    
    outLine = message.encode('utf-8')

    sbLogger = logging.getLogger('sickbeard')

    if logLevel == DEBUG:
        sbLogger.debug(outLine)
    elif logLevel == MESSAGE:
        sbLogger.info(outLine)
    elif logLevel == WARNING:
        sbLogger.warning(outLine)
    elif logLevel == ERROR:
        sbLogger.error(outLine)
        
        # add errors to the UI logger
        classes.ErrorViewer.add(classes.UIError(message))
    else:
        sbLogger.log(logLevel, outLine)