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
import base64
import time, struct

import sickbeard

from sickbeard import logger
from sickbeard import common
from sickbeard.exceptions import ex
from sickbeard.encodingKludge import fixStupidEncodings

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

try:
    import lib.simplejson as json
except:
    import json

class XBMCNotifier:
    
    apiversion = 0
    
    def notify_snatch(self, ep_name):
        if sickbeard.XBMC_NOTIFY_ONSNATCH:
            if (self._jsonapiversion() <= 4):
                logger.log(u"Detected XBMC version <= 11, using XBMC HTTP API", logger.DEBUG)
                self._notifyXBMC(ep_name, common.notifyStrings[common.NOTIFY_SNATCH])
            else:
                logger.log(u"Detected XBMC version >= 12, using XBMC JSON API", logger.DEBUG)
                self._notifyXBMC_json(ep_name, common.notifyStrings[common.NOTIFY_SNATCH])

    def notify_download(self, ep_name):
        if sickbeard.XBMC_NOTIFY_ONDOWNLOAD:
            if (self._jsonapiversion() <= 4):
                self._notifyXBMC(ep_name, common.notifyStrings[common.NOTIFY_DOWNLOAD])
            else:
                self._notifyXBMC_json(ep_name, common.notifyStrings[common.NOTIFY_DOWNLOAD])

    def test_notify(self, host, username, password):
        if (self._jsonapiversion() <= 4):
            logger.log(u"Detected XBMC version <= 11, using XBMC HTTP API", logger.DEBUG)
            return self._notifyXBMC("Testing XBMC notifications from Sick Beard", "Test Notification", host, username, password, force=True)
        else:
            logger.log(u"Detected XBMC version >= 12, using XBMC JSON API", logger.DEBUG)
            return self._notifyXBMC_json("Testing XBMC notifications from Sick Beard", "Test Notification", host, username, password, force=True)

    def update_library(self, host, showName=None):
        if sickbeard.XBMC_UPDATE_LIBRARY:
            if (self._jsonapiversion() <= 4):
                if not self._update_library(host, showName) and sickbeard.XBMC_UPDATE_FULL:
                    # do a full update if requested
                    return self._update_library(host)
                else:
                    return True

            else:
                if not self._update_library_json(host, showName) and sickbeard.XBMC_UPDATE_FULL:
                    # do a full update if requested
                    logger.log("Single show update failed, running full update", logger.ERROR)
                    return self._update_library_json(host)
                else:
                    return True

    def _username(self):
        return sickbeard.XBMC_USERNAME

    def _password(self):
        return sickbeard.XBMC_PASSWORD

    def _use_me(self):
        return sickbeard.USE_XBMC

    def _hostname(self):
        return sickbeard.XBMC_HOST
    
    def _jsonapiversion(self):
        # buffer the api version, so we don't hammer the server with useless requests
        if (self.apiversion == 0):
            self.apiversion = self._checkJSON_version()
        return self.apiversion

    def _sendToXBMC(self, command, host, username=None, password=None):
        '''
        Handles communication with XBMC servers
    
        command - Dictionary of field/data pairs, encoded via urllib.urlencode and
        passed to /xbmcCmds/xbmcHttp
    
        host - host/ip + port (foo:8080)
        '''
    
        if not username:
            username = self._username()
        if not password:
            password = self._password()
    
        for key in command:
            if type(command[key]) == unicode:
                command[key] = command[key].encode('utf-8')
    
        enc_command = urllib.urlencode(command)
        logger.log(u"Encoded command is " + enc_command, logger.DEBUG)
        # Web server doesn't like POST, GET is the way to go
        url = 'http://%s/xbmcCmds/xbmcHttp/?%s' % (host, enc_command)
    
        try:
            # If we have a password, use authentication
            req = urllib2.Request(url)
            if password:
                logger.log(u"Adding Password to XBMC url", logger.DEBUG)
                base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
                authheader =  "Basic %s" % base64string
                req.add_header("Authorization", authheader)
    
            logger.log(u"Contacting XBMC via url: " + url, logger.DEBUG)
            handle = urllib2.urlopen(req)
            response = handle.read().decode(sickbeard.SYS_ENCODING)
            logger.log(u"response: " + response, logger.DEBUG)
        except IOError, e:
            logger.log(u"Warning: Couldn't contact XBMC HTTP server at " + fixStupidEncodings(host) + ": " + ex(e))
            response = ''
    
        return response

    def _notifyXBMC(self, input, title="Sick Beard", host=None, username=None, password=None, force=False):
    
        if not self._use_me() and not force:
            logger.log(u"Notification for XBMC not enabled, skipping this notification", logger.DEBUG)
            return False
    
        if not host:
            host = self._hostname()
        if not username:
            username = self._username()
        if not password:
            password = self._password()
    
        logger.log(u"Sending notification for " + input, logger.DEBUG)
    
        fileString = title + "," + input
    
        result = ''
    
        for curHost in [x.strip() for x in host.split(",")]:
            command = {'command': 'ExecBuiltIn', 'parameter': 'Notification(' +fileString + ')' }
            logger.log(u"Sending notification to XBMC via host: "+ curHost +"username: "+ username + " password: " + password, logger.DEBUG)
            if result:
                result += ', '
            result += curHost + ':' + self._sendToXBMC(command, curHost, username, password)

        return result

    def _update_library(self, host, showName=None):
        
        if not self._use_me():
            logger.log(u"Notifications for XBMC not enabled, skipping library update", logger.DEBUG)
            return False
    
        logger.log(u"Updating library in XBMC", logger.DEBUG)
    
        if not host:
            logger.log(u'No host specified, no updates done', logger.DEBUG)
            return False
    
        # if we're doing per-show
        if showName:
            pathSql = 'select path.strPath from path, tvshow, tvshowlinkpath where ' \
                'tvshow.c00 = "%s" and tvshowlinkpath.idShow = tvshow.idShow ' \
                'and tvshowlinkpath.idPath = path.idPath' % (showName)
    
            # Use this to get xml back for the path lookups
            xmlCommand = {'command': 'SetResponseFormat(webheader;false;webfooter;false;header;<xml>;footer;</xml>;opentag;<tag>;closetag;</tag>;closefinaltag;false)'}
            # Sql used to grab path(s)
            sqlCommand = {'command': 'QueryVideoDatabase(%s)' % (pathSql)}
            # Set output back to default
            resetCommand = {'command': 'SetResponseFormat()'}
    
            # Set xml response format, if this fails then don't bother with the rest
            request = self._sendToXBMC(xmlCommand, host)
            if not request:
                return False
    
            sqlXML = self._sendToXBMC(sqlCommand, host)
            request = self._sendToXBMC(resetCommand, host)
    
            if not sqlXML:
                logger.log(u"Invalid response for " + showName + " on " + host, logger.DEBUG)
                return False
    
            encSqlXML = urllib.quote(sqlXML,':\\/<>')
            try:
                et = etree.fromstring(encSqlXML)
            except SyntaxError, e:
                logger.log("Unable to parse XML returned from XBMC: "+ex(e), logger.ERROR)
                return False
    
            paths = et.findall('.//field')
    
            if not paths:
                logger.log(u"No valid paths found for " + showName + " on " + host, logger.DEBUG)
                return False
    
            for path in paths:
                # Don't need it double-encoded, gawd this is dumb
                unEncPath = urllib.unquote(path.text).decode(sickbeard.SYS_ENCODING)
                logger.log(u"XBMC Updating " + showName + " on " + host + " at " + unEncPath, logger.DEBUG)
                updateCommand = {'command': 'ExecBuiltIn', 'parameter': 'XBMC.updatelibrary(video, %s)' % (unEncPath)}
                request = self._sendToXBMC(updateCommand, host)
                if not request:
                    logger.log(u"Update of show directory failed on " + showName + " on " + host + " at " + unEncPath, logger.ERROR)
                    return False
                # Sleep for a few seconds just to be sure xbmc has a chance to finish
                # each directory
                if len(paths) > 1:
                    time.sleep(5)
        else:
            logger.log(u"Do a full update as requested", logger.DEBUG)
            logger.log(u"XBMC Updating " + host, logger.DEBUG)
            updateCommand = {'command': 'ExecBuiltIn', 'parameter': 'XBMC.updatelibrary(video)'}
            request = self._sendToXBMC(updateCommand, host)
    
            if not request:
                logger.log(u"Full update failed on " + host, logger.ERROR)
                return False
    
        return True

    def _checkJSON_version(self):
        '''
        returns XBMC JSONRPC Api version
        4 = Xbmc Eden(11), 5 = Xbmc Frodo(12)
        '''
        host = self._hostname()
        username = self._username()
        password = self._password()
            
        checkCommand = '{"id":1,"jsonrpc":"2.0","method":"JSONRPC.Version"}'
        result = self._sendToXBMC_json(checkCommand, host, username, password)
        if result:
            return result["result"]["version"]
        else:
            return False
        
    def _sendToXBMC_json(self, command, host, username=None, password=None):
        '''
        Handles communication with XBMC servers via JSONRPC 
    
        command - JSON request passed to http://host/jsonrpc
        returns: dict or False on error
    
        host - host/ip + port (foo:8080)
        '''

        if not username:
            username = self._username()
        if not password:
            password = self._password()
    
        command = command.encode('utf-8')
        logger.log(u"Command is " + command, logger.DEBUG)
        url = 'http://%s/jsonrpc' % (host)
                    
        try:
            req = urllib2.Request(url, command)
            req.add_header("Content-type", "application/json")
            # If we have a password, use authentication
            if password:
                logger.log(u"Adding Password to XBMC url", logger.DEBUG)
                base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
                authheader =  "Basic %s" % base64string
                req.add_header("Authorization", authheader)
    
            logger.log(u"Contacting XBMC via url: " + url, logger.DEBUG)
            response = urllib2.urlopen(req)
            
        except IOError, e:
            logger.log(u"Warning: Couldn't contact XBMC JSON api at " + fixStupidEncodings(url) + ": " + ex(e), logger.ERROR)
            return False

        # Parse the json result
        try:
            result = json.load(response)
            response.close()
            logger.log(u"response: " + str(result), logger.DEBUG)
            return result
        
        except ValueError, e:
            logger.log(u"Unable to decode JSON: "+response, logger.ERROR)
            return False
        
     
    def _notifyXBMC_json(self, msg, title="Sick Beard", host=None, username=None, password=None, force=False):
    
        if not self._use_me() and not force:
            logger.log(u"Notification for XBMC not enabled, skipping this notification", logger.DEBUG)
            return False
    
        if not host:
            host = self._hostname()
        if not username:
            username = self._username()
        if not password:
            password = self._password()
    
        logger.log(u"Sending notification for " + msg, logger.DEBUG)
    
        result = ''
        for curHost in [x.strip() for x in host.split(",")]:
            command = '{"id":1,"jsonrpc":"2.0","method":"GUI.ShowNotification","params":{"title":"Sick Beard","message":"%s"}}' % msg
            logger.log(u"Sending notification to XBMC via host: "+ curHost +" username: "+ username + " password: " + password, logger.DEBUG)
            notifyResult = self._sendToXBMC_json(command, curHost, username, password)
            if (notifyResult != False):
                result += ', '+ curHost + ':' + notifyResult["result"].decode(sickbeard.SYS_ENCODING)
        
        return result

    def _update_library_json(self, host, showName=None):
        
        username = self._username()
        password = self._password()
    
        if not self._use_me():
            logger.log("Notifications for XBMC not enabled, skipping library update", logger.DEBUG)
            return False
    
        logger.log(u"Updating library in XBMC", logger.DEBUG)
    
        if not host:
            logger.log(u'No host specified, no updates done', logger.DEBUG)
            return False
    
        # if we're doing per-show
        if showName:
            tvshowid = -1
            
            # get tvshowid by showName
            showsCommand = '{"id":1,"jsonrpc":"2.0","method":"VideoLibrary.GetTVShows"}'
            showsResponse = self._sendToXBMC_json(showsCommand, host)
            if (showsResponse == False):
                return False
            shows = showsResponse["result"]["tvshows"] 
            
            for show in shows:
                if (show["label"] == showName):
                    tvshowid = show["tvshowid"]
            if (tvshowid == -1):
                # we didn't find the show, will trigger a full update if enabled
                return False
            
            # this can be big, so free some memory
            del shows
            
            # JSON to get the TV-Show path
            pathCommand = '{"id":1,"jsonrpc":"2.0","method":"VideoLibrary.GetTVShowDetails","params":{"tvshowid":%d, "properties": ["file"]}}' % (tvshowid)
            pathResponse = self._sendToXBMC_json(pathCommand, host)

            path = pathResponse["result"]["tvshowdetails"]["file"]
            logger.log(u"Received Show: " + show["label"] + " with ID: " + str(tvshowid) + " Path: " + path, logger.DEBUG)

            if (len(path) < 1):
                logger.log(u"No valid path found for " + showName + " with ID: " + str(tvshowid) + " on " + host, logger.ERROR)
                return False

            logger.log(u"XBMC Updating " + showName + " on " + host + " at " + path, logger.DEBUG)
            updateCommand = '{"id":1,"jsonrpc":"2.0","method":"VideoLibrary.Scan","params":{"directory":"%s"}}' % (path)
            request = self._sendToXBMC_json(updateCommand, host)
            if not request:
                    logger.log(u"Update of show directory failed on " + showName + " on " + host + " at " + path, logger.ERROR)
                    return False
            
        else:
            logger.log(u"Do a full update as requested", logger.DEBUG)
            logger.log(u"XBMC Updating " + host, logger.DEBUG)
            updateCommand = '{"id":1,"jsonrpc":"2.0","method":"VideoLibrary.Scan"}'
            request = self._sendToXBMC_json(updateCommand, host, username, password)
            if not request:
                logger.log(u"Full update failed on " + host, logger.ERROR)
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

    (family, socktype, proto, garbage, address) = socket.getaddrinfo(host, port)[0] #@UnusedVariable
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

notifier = XBMCNotifier