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

import urllib
import urllib2

import sickbeard

from sickbeard import logger
from sickbeard.common import notifyStrings, NOTIFY_SNATCH, NOTIFY_DOWNLOAD
from sickbeard.exceptions import ex

API_URL = "https://api.pushbullet.com/api/pushes"

class PushbulletNotifier:

    def _sendPushbullet(self, msg, title, apiKey=None):
        """
        Sends a pushbullet notification to all devices for now.

        msg: The message to send (unicode)
        title: The title of the message
        apiKey: The pushbullet api key to send the message to

        returns: True if the message succeeded, False otherwise
        """

        if not apiKey:
            apiKey = sickbeard.PUSHBULLET_apiKey

        # build up the URL and parameters
        msg = msg.strip()

        data = urllib.urlencode({
            'type': 'note',
            'title': title,
            'body': msg.encode('utf-8')
            })
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, API_URL, apiKey, "")
        handler = urllib2.HTTPBasicAuthHandler(password_mgr)
        opener = urllib2.build_opener(handler)
        urllib2.install_opener(opener)

        # send the request to pushbullet
        try:
			response = urllib2.urlopen(API_URL, data)
		
        except urllib2.HTTPError, e:
            # if we get an error back that doesn't have an error code then who knows what's really happening
            if not hasattr(e, 'code'):
                logger.log(u"PUSHBULLET: Notification failed." + ex(e), logger.ERROR)
                return False
            else:
                logger.log(u"PUSHBULLET: Notification failed. Error code: " + str(e.code), logger.WARNING)

            # HTTP status 404 if the provided email address isn't a Pushbullet user.
            if e.code == 401:
                logger.log(u"PUSHBULLET: Username is wrong/not a Pushbullet email. Pushbullet will send an email to it", logger.WARNING)
                return False

            # If you receive an HTTP status code of 400, it is because you failed to send the proper parameters
            elif e.code == 400:
                logger.log(u"PUSHBULLET: Wrong data sent to Pushbullet", logger.ERROR)
                return False

        logger.log(u"PUSHBULLET: Notification successful.", logger.DEBUG)
        return True

    def _notify(self, title, message, apiKey=None ):
        """
        Sends a pushbullet notification based on the provided info or SB config

        title: The title of the notification to send
        message: The message string to send
        apiKey: The apiKey to send the notification to
        """

        # suppress notifications if the notifier is disabled but the notify options are checked
        if not sickbeard.USE_PUSHBULLET:
            return False

        # fill in omitted parameters
        if not apiKey:
            apiKey = sickbeard.PUSHBULLET_apiKey

        logger.log(u"PUSHBULLET: Sending notification for " + message, logger.DEBUG)

        self._sendPushbullet(message, title)
        return True

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        if sickbeard.PUSHBULLET_NOTIFY_ONSNATCH:
            self._notify(notifyStrings[NOTIFY_SNATCH], ep_name)

    def notify_download(self, ep_name):
        if sickbeard.PUSHBULLET_NOTIFY_ONDOWNLOAD:
            self._notify(notifyStrings[NOTIFY_DOWNLOAD], ep_name)

    def test_notify(self, apiKey=None):
        return self._sendPushbullet("This is a test notification from SickBeard", 'Test', apiKey)

    def update_library(self, showName=None):
        pass

notifier = PushbulletNotifier
