# Author: David Rothera <david.rothera@gmail.com>
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
import base64

import sickbeard

from sickbeard import logger
from sickbeard.common import notifyStrings, NOTIFY_SNATCH, NOTIFY_DOWNLOAD
from sickbeard.exceptions import ex

PUSHAPI_ENDPOINT = 'https://api.pushbullet.com/v2/pushes'
DEVICEAPI_ENDPOINT = 'https://api.pushbullet.com/v2/devices'


class PushbulletNotifier:

    def test_notify(self, api_key=None):
        return self._sendPushbullet(
            "Test Push",
            "This is a test notification from Sickbeard",
            api_key
        )


    def _sendPushbullet(self, title='', body='', api_key=None):
        # if no api_key was given then use the one from the config
        if not api_key:
            api_key = sickbeard.PUSHBULLET_APIKEY

        request = urllib2.Request(PUSHAPI_ENDPOINT)
        base64string = base64.encodestring('%s:%s' % (api_key, '')).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)
        params = urllib.urlencode({
            'type': 'note',
            'title': title,
            'body': body
        })

        try:
            urllib2.urlopen(request, params).read()
        except urllib2.URLError, e:
            logger.log("Issue with request. Received code %s" % e.code)
            return False

        return True


    def notify_snatch(self, ep_name, title=notifyStrings[NOTIFY_SNATCH]):
        if sickbeard.PUSHBULLET_NOTIFY_ONSNATCH:
            self._sendPushbullet(title, ep_name)


    def notify_download(self, ep_name, title=notifyStrings[NOTIFY_DOWNLOAD]):
        if sickbeard.PUSHBULLET_NOTIFY_ONDOWNLOAD:
            self._sendPushbullet(title, ep_name)

notifier = PushbulletNotifier
