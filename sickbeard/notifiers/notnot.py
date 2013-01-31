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

import urllib2

import sickbeard

from sickbeard import logger
from sickbeard.common import notifyStrings, NOTIFY_SNATCH, NOTIFY_DOWNLOAD
from sickbeard.exceptions import ex

try:
    import json
except ImportError:
    from lib import simplejson as json


class NotNotNotifier:
    def test_notify(self, api_id=None, api_key=None, api_type=None):
        return self._sendNotNot("This is a test notification from SickBeard", api_id, api_key, api_type)

    def _sendNotNot(self, msg, api_id=None, api_key=None, api_type=None):
        """
        Sends a Message to NotNot

        msg: Message to send
        """
        if not api_id:
            api_id = sickbeard.NOTNOT_API_ID
        if not api_key:
            api_key = sickbeard.NOTNOT_API_KEY

        API_TYPE = sickbeard.NOTNOT_API_TYPE if not api_type else api_type
        API_URL = "https://notnot.sejo-it.be/send/%s" % ("user" if API_TYPE == 0 else "group")
        msg = msg.strip()

        if API_TYPE == 0:
            data = {"request": {"msg": msg, "api_key": api_key, "email": api_id}}
        else:
            data = {"request": {"msg": msg, "api_key": api_key, "group_name": api_id}}

        headers = {"Content-Type": "application/json"}

        try:
            request = urllib2.Request(API_URL, data=json.dumps(data), headers=headers)
            stream = urllib2.urlopen(request)
            response = stream.read()
            stream.close()
            resp = json.loads(response)
            if "result" in resp:
                logger.log(u"NotNot notification successful.", logger.DEBUG)
                return True
            else:
                return False
        except urllib2.URLError, e:
            logger.log(u"NotNot notification failed." + ex(e), logger.ERROR)
            return False

    def notify_snatch(self, ep_name, title=notifyStrings[NOTIFY_SNATCH]):
        if sickbeard.NOTNOT_NOTIFY_ONSNATCH:
            self._notifyNotNot(title, ep_name)

    def notify_download(self, ep_name, title=notifyStrings[NOTIFY_DOWNLOAD]):
        if sickbeard.NOTNOT_NOTIFY_ONDOWNLOAD:
            self._notifyNotNot(title, ep_name)

    def _notifyNotNot(self, title, message, api_id=None, api_key=None, api_type=None):
        """
        Sends a NotNot notification based on the provided info or SB config

        title: The title of the notification to send
        message: The message string to send
        userKey: The userKey to send the notification to
        """

        if not sickbeard.USE_NOTNOT:
            logger.log(u"Notification for NotNot not enabled, skipping this notification", logger.DEBUG)
            return False

        logger.log(u"Sending notification for " + message, logger.DEBUG)

        self._sendNotNot("%s: %s" % (message, title), api_id, api_key, api_type)
        return True


notifier = NotNotNotifier
