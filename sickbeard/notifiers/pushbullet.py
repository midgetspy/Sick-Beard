###################################################################################################
# Author: Jodi Jones <venom@gen-x.co.nz>
# URL: https://github.com/VeNoMouS/Sick-Beard
#
# Concept Author: Alexandre Espinosa Menor <aemenor@gmail.com>
# URL: https://github.com/alexandregz/Sick-Beard
#
# URL: https://github.com/junalmeida/Sick-Beard
# 
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
###################################################################################################

import requests

try:
    import json
except ImportError:
    from lib import simplejson as json

import sickbeard

from sickbeard import logger
from sickbeard.common import notifyStrings, NOTIFY_SNATCH, NOTIFY_DOWNLOAD
from sickbeard.exceptions import ex

API_URL = "https://api.pushbullet.com/v2/"

class PushbulletNotifier:
    ###################################################################################################
    
    def test_notify(self,apiKey=None,device=None):
        logger.log("[Pushbullet] Attemping to send test notification.",logger.DEBUG)
        return self._sendPushbullet("This is a test notification from SickBeard.", "Pushbullet Test",apiKey,device)

    ###################################################################################################

    def _retriveDevices(self,apiKey=None):
        session = requests.Session()
        if apiKey:
            session.auth = (apiKey, '')
        else:
            session.auth = (sickbeard.PUSHBULLET_APIKEY, '')
        
        response = session.get(API_URL + "devices",timeout=30)
        
        try:
            jdata = json.loads(response.content)
        except ValueError, e:
            logger.log("[Pushbullet] _retriveDevices() invalid data retriving device list")
            return False;

        return response.content
        
        
    ###################################################################################################
    
    def _sendPushbullet(self, msg, title,apiKey=None, device=None):        
        if not apiKey and not sickbeard.PUSHBULLET_APIKEY:
            logger.log("[Pushbullet] API Key missing...", logger.ERROR)
            return False
        
        session = requests.Session()
        session.auth = (apiKey, '')
        session.headers.update({'Content-Type': 'application/json'})
        
        payload = {'type':'note', 'title': title, 'body':  msg.strip()}

        if device:
            payload['device_iden'] = device
            
        response = session.post(API_URL + "pushes", data=json.dumps(payload),timeout=30)
        if response.status_code != 200:
                logger.log("[Pushbullet] Wrong data sent to pushbullet", logger.ERROR)
                return False

        if response.json()['active'] == True and response.json()['dismissed'] == False:
            logger.log("[Pushbullet] notification successful.", logger.DEBUG)
            return True
        
        logger.log("[Pushbullet] notification failed.", logger.ERROR)
        return False

    ###################################################################################################

    def notify_snatch(self, ep_name, title=notifyStrings[NOTIFY_SNATCH]):
        if sickbeard.PUSHBULLET_NOTIFY_ONSNATCH:
            self._notifyPushbullet(title, ep_name)

    ###################################################################################################

    def notify_download(self, ep_name, title=notifyStrings[NOTIFY_DOWNLOAD]):
        if sickbeard.PUSHBULLET_NOTIFY_ONDOWNLOAD:
            self._notifyPushbullet(title, ep_name)

    ###################################################################################################
    
    def _notifyPushbullet(self, title, message, device=None):
        """
        Sends a pushbullet notification 

        title: The title of the notification to send
        message: The message string to send
        device: Device to send. None to send all devices
        """

        if not sickbeard.USE_PUSHBULLET:
            logger.log("[Pushbullet] Notification not enabled, skipping this notification", logger.DEBUG)
            return False

        logger.log("[Pushbullet] Sending notification for " + message, logger.DEBUG)

        if not device:
            if sickbeard.PUSHBULLET_DEVICE:
                device = sickbeard.PUSHBULLET_DEVICE


        self._sendPushbullet(message, title,sickbeard.PUSHBULLET_APIKEY,device)
        return True

###################################################################################################

notifier = PushbulletNotifier
