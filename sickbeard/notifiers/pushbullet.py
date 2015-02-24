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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import urllib
import urllib2
import socket
import sickbeard

from sickbeard import logger
from sickbeard.common import notifyStrings, NOTIFY_SNATCH, NOTIFY_DOWNLOAD
from sickbeard.exceptions import ex

PUSHAPI_ENDPOINT = "https://api.pushbullet.com/v2/pushes"
DEVICEAPI_ENDPOINT = "https://api.pushbullet.com/v2/devices"


class PushbulletNotifier:

    def get_devices(self, accessToken=None):
        # fill in omitted parameters
        if not accessToken:
            accessToken = sickbeard.PUSHBULLET_ACCESS_TOKEN

        # get devices from pushbullet        
        req = urllib2.Request(DEVICEAPI_ENDPOINT)
        pw_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        pw_mgr.add_password(None, DEVICEAPI_ENDPOINT, accessToken, '')
        return sickbeard.helpers.getURL(req, password_mgr=pw_mgr)

    def _sendPushbullet(self, title, body, accessToken, device_iden):

        # build up the URL and parameters
        body = body.strip().encode('utf-8')

        data = urllib.urlencode({
            'type': 'note',
            'title': title,
            'body': body,
            'device_iden': device_iden
            })

        # send the request to pushbullet
        try:
            req = urllib2.Request(PUSHAPI_ENDPOINT, data)
            pw_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            pw_mgr.add_password(None, DEVICEAPI_ENDPOINT, accessToken, '')
            handle = sickbeard.helpers.getURLFileLike(req, password_mgr=pw_mgr, throw_exc=True)
            handle.close()
        except socket.timeout:
            return False
        except urllib2.URLError, e:
            # FIXME: Python 2.5 hack, it wrongly reports 201 as an error
            if hasattr(e, 'code') and e.code == 201:
                logger.log(u"PUSHBULLET: Notification successful.", logger.MESSAGE)
                return True

            # if we get an error back that doesn't have an error code then who knows what's really happening
            if not hasattr(e, 'code'):
                logger.log(u"PUSHBULLET: Notification failed." + ex(e), logger.ERROR)
            else:
                logger.log(u"PUSHBULLET: Notification failed. Error code: " + str(e.code), logger.ERROR)

            if e.code == 404:
                logger.log(u"PUSHBULLET: Access token is wrong/not associated to a device.", logger.ERROR)
            elif e.code == 401:
                logger.log(u"PUSHBULLET: Unauthorized, not a valid access token.", logger.ERROR)
            elif e.code == 400:
                logger.log(u"PUSHBULLET: Bad request, missing required parameter.", logger.ERROR)
            elif e.code == 503:
                logger.log(u"PUSHBULLET: Pushbullet server to busy to handle the request at this time.", logger.WARNING)
            return False

        logger.log(u"PUSHBULLET: Notification successful.", logger.MESSAGE)
        return True

    def _notify(self, title, body, accessToken=None, device_iden=None, force=False):
        """
        Sends a pushbullet notification based on the provided info or SB config

        title: The title of the notification to send
        body: The body string to send
        accessToken: The access token to grant access
        device_iden: The iden of a specific target, if none provided send to all devices
        force: If True then the notification will be sent even if Pushbullet is disabled in the config
        """

        # suppress notifications if the notifier is disabled but the notify options are checked
        if not sickbeard.USE_PUSHBULLET and not force:
            return False

        # fill in omitted parameters
        if not accessToken:
            accessToken = sickbeard.PUSHBULLET_ACCESS_TOKEN
        if not device_iden:
            device_iden = sickbeard.PUSHBULLET_DEVICE_IDEN

        logger.log(u"PUSHBULLET: Sending notice with details: title=\"%s\", body=\"%s\", device_iden=\"%s\"" % (title, body, device_iden), logger.DEBUG)

        return self._sendPushbullet(title, body, accessToken, device_iden)

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        if sickbeard.PUSHBULLET_NOTIFY_ONSNATCH:
            self._notify(notifyStrings[NOTIFY_SNATCH], ep_name)

    def notify_download(self, ep_name):
        if sickbeard.PUSHBULLET_NOTIFY_ONDOWNLOAD:
            self._notify(notifyStrings[NOTIFY_DOWNLOAD], ep_name)

    def test_notify(self, accessToken, device_iden):
        return self._notify("Test", "This is a test notification from Sick Beard", accessToken, device_iden, force=True)

    def update_library(self, ep_obj=None):
        pass

notifier = PushbulletNotifier
