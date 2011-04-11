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

from __future__ import with_statement 

import os
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

# number of log files to keep
NUM_LOGS = 3

# log size in bytes
LOG_SIZE = 50000

logFile = ''

# keep a record of this so we can remove/reset it when we roll the logs over
fileHandler = None

log_lock = threading.Lock()

def initLogging(consoleLogging=True):
    global logFile, fileHandler

    logFile = os.path.join(sickbeard.LOG_DIR, 'sickbeard.log')

    fileHandler = config_handler(logFile)

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

def config_handler(file_name):
    """
    Configure a file handler to log at file_name and return it.
    """

    fileHandler = logging.FileHandler(file_name)

    fileHandler.setLevel(logging.DEBUG)
    fileHandler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', '%b-%d %H:%M:%S'))

    return fileHandler

def log_file_name(i):
    """
    Returns a numbered log file name depending on i. If i==0 it just uses logName, if not it appends
    it to the extension (blah.log.3 for i == 3)
    
    i: Log number to ues
    """
    return logFile + ('.' + str(i) if i else '')


def num_logs():
    """
    Scans the log folder and figures out how many log files there are already on disk
    
    Returns: The number of the last used file (eg. mylog.log.3 would return 3). If there are no logs it returns -1
    """
    cur_log = 0
    while os.path.isfile(log_file_name(cur_log)):
        cur_log += 1
    return cur_log - 1

def rotate_logs():
    global fileHandler
    
    sb_logger = logging.getLogger('sickbeard')
    
    # delete the old handler
    if fileHandler:
        print "Closing fileHandler"
        fileHandler.flush()
        fileHandler.close()
        sb_logger.removeHandler(fileHandler)

    # rename or delete all the old log files
    for i in range(num_logs(), -1, -1):
        cur_file_name = log_file_name(i)
        if i >= NUM_LOGS:
            print "removing", cur_file_name
            os.remove(cur_file_name)
        else:
            print "renaming", cur_file_name, "to", log_file_name(i+1)
            os.rename(cur_file_name, log_file_name(i+1))
    
    # the new log handler will always be on the un-numbered .log file
    new_file_handler = config_handler(logFile)
    
    fileHandler = new_file_handler
    
    sb_logger.addHandler(new_file_handler)

def log(toLog, logLevel=MESSAGE):

    with log_lock:

        # check the size and see if we need to rotate
        if os.path.isfile(logFile) and os.path.getsize(logFile) >= LOG_SIZE:
            rotate_logs()

        meThread = threading.currentThread().getName()
        message = meThread + u" :: " + toLog
    
        outLine = message.encode('utf-8')
    
        sbLogger = logging.getLogger('sickbeard')

        try:
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
        except ValueError, e:
            pass