# Author: Marvin Pinto <me@marvinp.ca>
# Author: Dennis Lutter <lad1337@gmail.com>
# Author: Aaron Bieber <deftly@gmail.com>
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

import urllib, urllib2
import time

import sickbeard

from sickbeard import logger
from sickbeard.common import notifyStrings, NOTIFY_SNATCH, NOTIFY_DOWNLOAD
from sickbeard.exceptions import ex

API_URL = "https://api.pushover.net/1/messages.json"
API_KEY = "OKCXmkvHN1syU2e8xvpefTnyvVWGv5"

class PushoverNotifier:

    def test_notify(self, userKey=None):
        return self._sendPushover("This is a test notification from SickBeard", 'Test', userKey )

    def _sendPushover(self, msg, title, userKey=None ):
        """
        Sends a pushover notification to the address provided
        
        msg: The message to send (unicode)
        title: The title of the message
        userKey: The pushover user id to send the message to (or to subscribe with)
        
        returns: True if the message succeeded, False otherwise
        """

        if not userKey:
            userKey = sickbeard.PUSHOVER_USERKEY
        
        # build up the URL and parameters
        msg = msg.strip()
        curUrl = API_URL

        data = urllib.urlencode({
            'token': API_KEY,
            'title': title,
            'user': userKey,
            'message': msg.encode('utf-8'),
            'timestamp': int(time.time())
			})


        # send the request to pushover
        try:
            req = urllib2.Request(curUrl)
            handle = urllib2.urlopen(req, data)
            handle.close()
            
        except urllib2.URLError, e:
            # if we get an error back that doesn't have an error code then who knows what's really happening
            if not hasattr(e, 'code'):
                logger.log("Pushover notification failed." + ex(e), logger.ERROR)
                return False
            else:
                logger.log("Pushover notification failed. Error code: " + str(e.code), logger.WARNING)

            # HTTP status 404 if the provided email address isn't a Pushover user.
            if e.code == 404:
                logger.log("Username is wrong/not a pushover email. Pushover will send an email to it", logger.WARNING)
                return False
            
            # For HTTP status code 401's, it is because you are passing in either an invalid token, or the user has not added your service.
            elif e.code == 401:
                
                #HTTP status 401 if the user doesn't have the service added
                subscribeNote = self._sendPushover(msg, title, userKey )
                if subscribeNote:
                    logger.log("Subscription send", logger.DEBUG)
                    return True
                else:
                    logger.log("Subscription could not be send", logger.ERROR)
                    return False
            
            # If you receive an HTTP status code of 400, it is because you failed to send the proper parameters
            elif e.code == 400:
                logger.log("Wrong data sent to pushover", logger.ERROR)
                return False

        logger.log("Pushover notification successful.", logger.DEBUG)
        return True

    def notify_snatch(self, ep_name, title=notifyStrings[NOTIFY_SNATCH]):
        if sickbeard.PUSHOVER_NOTIFY_ONSNATCH:
            self._notifyPushover(title, ep_name)
            

    def notify_download(self, ep_name, title=notifyStrings[NOTIFY_DOWNLOAD]):
        if sickbeard.PUSHOVER_NOTIFY_ONDOWNLOAD:
            self._notifyPushover(title, ep_name)

    def _notifyPushover(self, title, message, userKey=None ):
        """
        Sends a pushover notification based on the provided info or SB config

        title: The title of the notification to send
        message: The message string to send
        userKey: The userKey to send the notification to 
        """

        if not sickbeard.USE_PUSHOVER:
            logger.log("Notification for Pushover not enabled, skipping this notification", logger.DEBUG)
            return False

        # if no userKey was given then use the one from the config
        if not userKey:
            userKey = sickbeard.PUSHOVER_USERKEY

        logger.log("Sending notification for " + message, logger.DEBUG)

        # self._sendPushover(message, title, userKey)
        self._sendPushover(message, title)
        return True

notifier = PushoverNotifier
