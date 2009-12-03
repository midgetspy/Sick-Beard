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



import urllib, urllib2
import socket
import sys

#import config

import sickbeard

from sickbeard.logging import *

XBMC_TIMEOUT = 10

# prevent it from dying if the XBMC call hangs
def notifyXBMC(input, title="midgetPVR"):

    global XBMC_TIMEOUT

    Logger().log("Sending notification for " + input, DEBUG)
    
    fileString = title + "," + input
    param = urllib.urlencode({'a':fileString})
    encodedParam = param.split("=")[1]
    
    Logger().log("Encoded message is " + encodedParam, DEBUG)
    
    host = sickbeard.XBMC_HOST
    
    try:
        urllib2.urlopen("http://" + host + "/xbmcCmds/xbmcHttp?command=ExecBuiltIn&parameter=Notification(" + encodedParam + ")", timeout=XBMC_TIMEOUT).close()
    except IOError as e:
        Logger().log("Warning: Couldn't contact XBMC HTTP server at " + host + ": " + str(e))
    
def updateLibrary(path=None):

    global XBMC_TIMEOUT

    Logger().log("Updating library in XBMC", DEBUG)
    
    host = sickbeard.XBMC_HOST
    
    try:
        if path == None:
            path = ""
        else:
            path = ""
            #path = "," + urllib.quote_plus(path)
        urllib2.urlopen("http://" + host + "/xbmcCmds/xbmcHttp?command=ExecBuiltIn&parameter=XBMC.updatelibrary(video" + path + ")", timeout=XBMC_TIMEOUT).close()
    except IOError as e:
        Logger().log("Warning: Couldn't contact XBMC HTTP server at " + host + ": " + str(e))
        return False

    return True

