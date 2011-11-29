# Author: Marvin Pinto <me@marvinp.ca>
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

import base64
import urllib
import urllib2
import time
import json

import sickbeard

from sickbeard import logger

try:
    import lib.simplejson as json #@UnusedImport
except:
    import json #@Reimport

API_URL = "https://boxcar.io/notifications"

class BoxcarNotifier:

    def test_notify(self, username, password, title="Test:"):
        return self._sendBoxcar("This is a test notification from SickBeard", title, username, password)

    def _sendBoxcar(self, msg, title, username, password, label="SickBeard"):
        msg = msg.strip()
        data = urllib.urlencode({
                'notification[from_screen_name]': username,
                'notification[message]': msg.encode('utf-8'),
                'notification[from_remote_service_id]': int(time.time())
                })

        req = urllib2.Request(API_URL)
        base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
        req.add_header("Authorization", "Basic %s" % base64string)

        try:
            handle = urllib2.urlopen(req, data)

        except Exception, e:
            logger.log(e, logger.DEBUG)
            logger.log("Boxcar notification failed.", logger.DEBUG)
            return False

	logger.log("Boxcar notification successful.", logger.DEBUG)
	handle.close()
	return True

    def notify_snatch(self, ep_name, title="Snatched:"):
        if sickbeard.BOXCAR_NOTIFY_ONSNATCH:
            self._notifyBoxcar(title, ep_name)

    def notify_download(self, ep_name, title="Completed:"):
        if sickbeard.BOXCAR_NOTIFY_ONDOWNLOAD:
            self._notifyBoxcar(title, ep_name)       

    def _notifyBoxcar(self, title, message=None, username=None, password=None, force=False):
        if not sickbeard.USE_BOXCAR and not force:
            logger.log("Notification for Boxcar not enabled, skipping this notification", logger.DEBUG)
            return False

        if not username:
            username = sickbeard.BOXCAR_USERNAME
        if not password:
            password = sickbeard.BOXCAR_PASSWORD

        logger.log("Sending notification for " + message, logger.DEBUG)

        self._sendBoxcar(message, title, username, password)
        return True

notifier = BoxcarNotifier
