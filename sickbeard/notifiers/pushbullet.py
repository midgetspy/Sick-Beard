# Author: Pedro Correia (http://github.com/pedrocorreia/)
# Based on pushalot.py by Nic Wolfe <nic@wolfeden.ca>
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard. If not, see <http://www.gnu.org/licenses/>.


import base64
from httplib import HTTPSConnection, HTTPException
from urllib import urlencode
from ssl import SSLError
import sickbeard
from sickbeard import logger, common

class PushbulletNotifier:

    def test_notify(self, pushbullet_api):
        return self._sendPushbullet(pushbullet_api, event="Test", message="Testing Pushbullet settings from Sick Beard", method="POST", notificationType="note", force=True)

    def get_devices(self, pushbullet_api):
        return self._sendPushbullet(pushbullet_api, method="GET", force=True)

    def notify_snatch(self, ep_name):
        if sickbeard.PUSHBULLET_NOTIFY_ONSNATCH:
            self._sendPushbullet(pushbullet_api=None, event=common.notifyStrings[common.NOTIFY_SNATCH], message=ep_name, notificationType="note", method="POST")

    def notify_download(self, ep_name):
        if sickbeard.PUSHBULLET_NOTIFY_ONDOWNLOAD:
            self._sendPushbullet(pushbullet_api=None, event=common.notifyStrings[common.NOTIFY_DOWNLOAD], message=ep_name, notificationType="note", method="POST")

    def notify_subtitle_download(self, ep_name, lang):
        if sickbeard.PUSHBULLET_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._sendPushbullet(pushbullet_api=None, event=common.notifyStrings[common.NOTIFY_SUBTITLE_DOWNLOAD], message=ep_name + ": " + lang, notificationType="note", method="POST")

    def _sendPushbullet(self, pushbullet_api=None, pushbullet_device=None, event=None, message=None, notificationType=None, method=None, force=False):
        
        if not sickbeard.USE_PUSHBULLET and not force:
                return False
        
        if pushbullet_api == None:
            pushbullet_api = sickbeard.PUSHBULLET_API
        if pushbullet_device == None:
            pushbullet_device = sickbeard.PUSHBULLET_DEVICE

        if method == 'POST':
            uri = '/api/pushes'
        else:
            uri = '/api/devices'
        
        logger.log(u"Pushbullet event: " + str(event), logger.DEBUG)
        logger.log(u"Pushbullet message: " + str(message), logger.DEBUG)
        logger.log(u"Pushbullet api: " + str(pushbullet_api), logger.DEBUG)
        logger.log(u"Pushbullet devices: " + str(pushbullet_device), logger.DEBUG)
        logger.log(u"Pushbullet notification type: " + str(notificationType), logger.DEBUG)
        
        http_handler = HTTPSConnection("api.pushbullet.com")

        authString = base64.encodestring('%s:' % (pushbullet_api)).replace('\n', '')

        if notificationType == None:
            testMessage = True
            try:
                logger.log(u"Testing Pushbullet authentication and retrieving the device list.", logger.DEBUG)
                http_handler.request(method, uri, None, headers={'Authorization':'Basic %s:' % authString})
            except (SSLError, HTTPException):
                logger.log(u"Pushbullet notification failed.", logger.ERROR)
                return False
        else:
            testMessage = False
            try:
                data = {
                    'title': event.encode('utf-8'),
                    'body': message.encode('utf-8'),
                    'device_iden': pushbullet_device,
                    'type': notificationType}
                http_handler.request(method, uri, body = urlencode(data), headers={'Authorization':'Basic %s' % authString})
                pass
            except (SSLError, HTTPException):
                return False

        response = http_handler.getresponse()
        request_body = response.read()
        request_status = response.status

        if request_status == 200:
                if testMessage:
                    return request_body
                else:
                    logger.log(u"Pushbullet notifications sent.", logger.DEBUG)
                    return True
        elif request_status == 410:
                logger.log(u"Pushbullet auth failed: %s" % response.reason, logger.ERROR)
                return False
        else:
                logger.log(u"Pushbullet notification failed.", logger.ERROR)
                return False
                
notifier = PushbulletNotifier

