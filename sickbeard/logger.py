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
import codecs

import logging
import logging.handlers

from exceptions import *

import sickbeard


ERROR = 2
MESSAGE = 1
DEBUG = 0


def initLogging(consoleLogging=True):
            
    fileHandler = logging.handlers.RotatingFileHandler(
                  os.path.join(sickbeard.LOG_DIR, 'sickbeard.log'), maxBytes=25000000, backupCount=5)

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
    outLine = meThread + " :: " + toLog
    
    outLine = outLine.encode('utf-8')

    sbLogger = logging.getLogger('sickbeard')

    if logLevel == DEBUG:
        sbLogger.debug(outLine)
    elif logLevel == MESSAGE:
        sbLogger.info(outLine)
    elif logLevel == ERROR:
        sbLogger.error(outLine)
    else:
        sbLogger.log(logLevel, outLine)