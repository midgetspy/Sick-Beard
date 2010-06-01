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

from sickbeard import logger

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

def sendToXBMC(command, host, username=None, password=None):
    '''
    Handles communication with XBMC servers

    command - Dictionary of field/data pairs, encoded via urllib.urlencode and
    passed to /xbmcCmds/xbmcHttp

    host - host/ip + port (foo:8080) 
    '''

    if not username:
        username = sickbeard.XBMC_USERNAME
    if not password:
        password = sickbeard.XBMC_PASSWORD    

    enc_command = urllib.urlencode(command)
    logger.log("Encoded command is " + enc_command, logger.DEBUG)
    # Web server doesn't like POST, GET is the way to go
    url = 'http://%s/xbmcCmds/xbmcHttp/?%s' % (host, enc_command)

    try:
        # If we have a password, use authentication
        req = urllib2.Request(url)
        if password:
            logger.log("Adding Password to XBMC url", logger.DEBUG)
            base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
            authheader =  "Basic %s" % base64string
            req.add_header("Authorization", authheader)

        logger.log("Contacting XBMC via url: " + url, logger.DEBUG)
        handle = urllib2.urlopen(req)
        response = handle.read()
        logger.log("response: " + response, logger.DEBUG)
    except IOError, e:
        # print "Warning: Couldn't contact XBMC HTTP server at " + host + ": " + str(e)
        logger.log("Warning: Couldn't contact XBMC HTTP server at " + host + ": " + str(e))
        response = ''

    return response

def notifyXBMC(input, title="midgetPVR", host=None, username=None, password=None):

    global XBMC_TIMEOUT

    if not host:
        host = sickbeard.XBMC_HOST
    if not username:
        username = sickbeard.XBMC_USERNAME
    if not password:
        password = sickbeard.XBMC_PASSWORD    

    logger.log("Sending notification for " + input, logger.DEBUG)
    
    fileString = title + "," + input
    
    for curHost in [x.strip() for x in host.split(",")]:
        command = {'command': 'ExecBuiltIn', 'parameter': 'Notification(' +fileString + ')' }
        logger.log("Sending notification to XBMC via host: "+ curHost +"username: "+ username + " password: " + password, logger.DEBUG)
        request = sendToXBMC(command, curHost, username, password)
    
def updateLibrary(host, showName=None):

    global XBMC_TIMEOUT

    logger.log("Updating library in XBMC", logger.DEBUG)
    
    if not host:
        logger.log('No host specified, no updates done', logger.DEBUG)
        return False

    # if we're doing per-show
    if showName:
        pathSql = 'select path.strPath from path, tvshow, tvshowlinkpath where \
            tvshow.c00 = "%s" and tvshowlinkpath.idShow = tvshow.idShow \
            and tvshowlinkpath.idPath = path.idPath' % (showName)

        # Use this to get xml back for the path lookups
        xmlCommand = {'command': 'SetResponseFormat(webheader;false;webfooter;false;header;<xml>;footer;</xml>;opentag;<tag>;closetag;</tag>;closefinaltag;false)'}
        # Sql used to grab path(s)
        sqlCommand = {'command': 'QueryVideoDatabase(%s)' % (pathSql)}
        # Set output back to default
        resetCommand = {'command': 'SetResponseFormat()'}
    
        # Get our path for show
        request = sendToXBMC(xmlCommand, host)
        sqlXML = sendToXBMC(sqlCommand, host)
        request = sendToXBMC(resetCommand, host)

        if not sqlXML:
            logger.log("Invalid response for " + showName + " on " + host, logger.DEBUG)
            return False

        et = etree.fromstring(sqlXML)
        paths = et.findall('field')
    
        if not paths:
            logger.log("No valid paths found for " + showName + " on " + host, logger.DEBUG)
            return False
    
        for path in paths:
            logger.log("XBMC Updating " + showName + " on " + host + " at " + path.text, logger.DEBUG)
            updateCommand = {'command': 'ExecBuiltIn', 'parameter': 'XBMC.updatelibrary(video, %s)' % (path.text)}
            request = sendToXBMC(updateCommand, host)
            if not request:
                return False
            # Sleep for a few seconds just to be sure xbmc has a chance to finish
            # each directory
            if len(paths) > 1:
                time.sleep(5)
    else:
        logger.log("XBMC Updating " + host, logger.DEBUG)
        updateCommand = {'command': 'ExecBuiltIn', 'parameter': 'XBMC.updatelibrary(video)'}
        request = sendToXBMC(updateCommand, host)

        if not request:
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
