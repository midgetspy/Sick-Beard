# Author: Philippe DePass <depassp@gmail.com>
# Based on work by wdudokvanheel <oss@bitechular.com>
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

import sickbeard
import lib.xmpp as xmpp

from sickbeard import logger
from sickbeard import common

class XMPPNotifier:
    
    def __init__(self):
        self.connected = False
        
    def _connect(self, username=None, password=None, server=None, port=None):
        if not sickbeard.USE_XMPP:
            return None
        
        if username is None:
            username = sickbeard.XMPP_USERNAME
        if password is None:
            password = sickbeard.XMPP_PASSWORD
        if server is None:
            server = sickbeard.XMPP_SERVER
        if port is None:
            port = int(sickbeard.XMPP_PORT)
        
        #Get the username and domain
        (user, domain) = username.split("@")
        
        self.cnx = xmpp.Client(domain, debug=[])
        
        #Connect to the server
        serverport=(server, port)
        logger.log("[XMPP] Connecting to " + server + ":" + str(port), logger.DEBUG)
        if not self.cnx.connect(serverport):
            logger.log("[XMPP] Error during XMPP connection, make sure the server is correct", logger.ERROR)
            return "Error during XMPP connection, make sure the server is correct."
        
        logger.log("[XMPP] Connected successfully", logger.DEBUG)
        #Authenticate user
        logger.log("[XMPP] Authenticating as " + user + "@" + domain, logger.DEBUG)

        if self.cnx.auth(user, password, 'SickBeard Notifier'):
            logger.log("[XMPP] Authenticated successfully", logger.DEBUG)
            self.connected = True
        else:
            logger.log("[XMPP] Authentication Failed", logger.ERROR)
            return "Failed to authenticate. Please make sure the username & password are correct."

    def notify_download(self, ep_name):
        if sickbeard.USE_XMPP and sickbeard.XMPP_NOTIFY_ONDOWNLOAD:
            return self._sendMessage(message=' '.join(['Sick Beard', common.notifyStrings[common.NOTIFY_DOWNLOAD], ep_name]))
    
    def notify_snatch(self, ep_name):
        if sickbeard.USE_XMPP and sickbeard.XMPP_NOTIFY_ONSNATCH:
            return self._sendMessage(message=' '.join(['Sick Beard', common.notifyStrings[common.NOTIFY_SNATCH], ep_name]))
   
    def test_notify(self, username, password, server, port, recipient):
        return self._sendMessage(username, password, server, port, recipient, message='Test message from Sick Beard')
        
    def _sendMessage(self, recipient=None, message='Test message from Sick Beard'):
        if not self.connected:
            self._connect()
        if recipient is None:
            recipient = sickbeard.XMPP_RECIPIENT
            
        #Send Message
        logger.log("[XMPP] Sending message '" + message + "' to recipient " + recipient, logger.DEBUG)
        try:
            self.cnx.send(xmpp.Message(recipient, message))
        except Exception, e:
            logger.log(e, logger.ERROR)
        else:
            return "Message sent successfully"
