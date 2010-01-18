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
import base64
import time, struct

#import config

import sickbeard

from sickbeard.logging import *

XBMC_TIMEOUT = 10

# prevent it from dying if the XBMC call hangs
def notifyXBMC(input, title="midgetPVR", host=None, username=None, password=None):

    global XBMC_TIMEOUT

    if host == None:
        host = sickbeard.XBMC_HOST
    if username == None:
        username = sickbeard.XBMC_USERNAME
    if password == None:
        password = sickbeard.XBMC_PASSWORD    

    Logger().log("Sending notification for " + input, DEBUG)
    
    fileString = title + "," + input
    param = urllib.urlencode({'a': fileString.encode('utf-8')})
    encodedParam = param.split("=")[1]
    
    Logger().log("Encoded message is " + encodedParam, DEBUG)
    
    for curHost in [x.strip() for x in host.split(",")]:
    
        try:
            url = "http://" + curHost + "/xbmcCmds/xbmcHttp?command=ExecBuiltIn&parameter=Notification(" + encodedParam + ")"
            Logger().log("Sending notification to XBMC via URL: "+url +" username: "+ username + " password: " + password, DEBUG)
            req = urllib2.Request(url)
            if password != '':
                base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
                authheader =  "Basic %s" % base64string
                req.add_header("Authorization", authheader)
                Logger().log("Adding Password to XBMC url", DEBUG)
            handle = urllib2.urlopen(req, timeout=XBMC_TIMEOUT)
        except IOError as e:
            Logger().log("Warning: Couldn't contact XBMC HTTP server at " + curHost + ": " + str(e))
    
def updateLibrary(path=None):

    global XBMC_TIMEOUT

    Logger().log("Updating library in XBMC", DEBUG)
    
    host = sickbeard.XBMC_HOST
    username = sickbeard.XBMC_USERNAME
    password = sickbeard.XBMC_PASSWORD
    
    for curHost in [x.strip() for x in host.split(",")]:
        
        try:
            if path == None:
                path = ""
            else:
                path = ""
                #path = "," + urllib.quote_plus(path)
            url = "http://" + curHost + "/xbmcCmds/xbmcHttp?command=ExecBuiltIn&parameter=XBMC.updatelibrary(video" + path + ")"
            req = urllib2.Request(url)
            if password != '':
                base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
                authheader =  "Basic %s" % base64string
                req.add_header("Authorization", authheader)
                Logger().log("Adding Password to XBMC url", DEBUG)
            handle = urllib2.urlopen(req, timeout=XBMC_TIMEOUT)
        except IOError as e:
            Logger().log("Warning: Couldn't contact XBMC HTTP server at " + curHost + ": " + str(e))
            return False

    return True

# Wake function
def wakeOnLan(ethernet_address):
    addr_byte = ethernet_address.split(':')
    hw_addr = struct.pack('BBBBBB', int(addr_byte[0], 16),
    int(addr_byte[1], 16),
    int(addr_byte[2], 16),
    int(addr_byte[3], 16),
    int(addr_byte[4], 16),
    int(addr_byte[5], 16))
    
    # Build the Wake-On-LAN "Magic Packet"...
    msg = '\xff' * 6 + hw_addr * 16
    
    # ...and send it to the broadcast address using UDP
    ss = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ss.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    ss.sendto(msg, ('<broadcast>', 9))
    ss.close()
 
# Test Connection function
def isHostUp(host,port):

    (family, socktype, proto, garbage, address) = socket.getaddrinfo(host, port)[0]
    s = socket.socket(family, socktype, proto)

    try:
        s.connect(address)
        return "Up"
    except:
        return "Down"


def checkHost(host, port):

    # we should try to get this programmatically from the IP
    mac = ""
    
    i=1
    while isHostUp(host,port)=="Down" and i<4:
        wakeOnLan(mac)
        time.sleep(20)
        i=i+1