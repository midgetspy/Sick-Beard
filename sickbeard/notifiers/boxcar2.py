# Author: Marvin Pinto <me@marvinp.ca>
# Author: Dennis Lutter <lad1337@gmail.com>
# Author: Shawn Conroyd <mongo527@gmail.com>
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

API_URL = "https://new.boxcar.io/api/notifications"


class Boxcar2Notifier:

    def test_notify(self, accessToken, title="Test"):
        return self._sendBoxcar2("This is a test notification from SickBeard", title, accessToken)

    def _sendBoxcar2(self, msg, title, accessToken):
        """
        Sends a boxcar notification to the address provided

        msg: The message to send (unicode)
        title: The title of the message
        accessToken: The access token to send notification to

        returns: True if the message succeeded, False otherwise
        """

        # build up the URL and parameters
        msg = msg.strip()
        curUrl = API_URL

        data = urllib.urlencode({
            'user_credentials': accessToken,
            'notification[title]': "SickBeard - " + title + " - " + msg.encode('utf-8'),
            'notification[long_message]': msg.encode('utf-8'),
            'notification[sound]': "done"
            })

        # send the request to boxcar
        try:
            req = urllib2.Request(curUrl)
            handle = urllib2.urlopen(req, data)
            handle.close()

        except urllib2.URLError, e:
            # if we get an error back that doesn't have an error code then who knows what's really happening
            if not hasattr(e, 'code'):
                logger.log("Boxcar2 notification failed." + ex(e), logger.ERROR)
                return False
            else:
                logger.log("Boxcar2 notification failed. Error code: " + str(e.code), logger.WARNING)

            # HTTP status 404 if the provided access token isn't a Boxcar token.
            if e.code == 404:
                logger.log("Access Token is wrong/not a boxcar2 token.", logger.WARNING)
                return False

            # For HTTP status code 401's, it is because you are passing in either an invalid token, or the user has not added your service.
            elif e.code == 401:

                # Return an HTTP status code of 401.
                logger.log("Already subscribed to service", logger.ERROR)
                # i dont know if this is true or false ... its neither but i also dont know how we got here in the first place
                return False

            # If you receive an HTTP status code of 400, it is because you failed to send the proper parameters
            elif e.code == 400:
                logger.log("Wrong data send to boxcar2", logger.ERROR)
                return False

        logger.log("Boxcar2 notification successful.", logger.DEBUG)
        return True

    def notify_snatch(self, ep_name, title=notifyStrings[NOTIFY_SNATCH]):
        if sickbeard.BOXCAR2_NOTIFY_ONSNATCH:
            self._notifyBoxcar2(title, ep_name)

    def notify_download(self, ep_name, title=notifyStrings[NOTIFY_DOWNLOAD]):
        if sickbeard.BOXCAR2_NOTIFY_ONDOWNLOAD:
            self._notifyBoxcar2(title, ep_name)

    def _notifyBoxcar2(self, title, message, accessToken=None, force=False):
        """
        Sends a boxcar notification based on the provided info or SB config

        title: The title of the notification to send
        message: The message string to send
        accessToken: The access token to send the notification to (optional, defaults to the access token in the config)
        force: If True then the notification will be sent even if Boxcar is disabled in the config
        """

        if not sickbeard.USE_BOXCAR2 and not force:
            logger.log("Notification for Boxcar2 not enabled, skipping this notification", logger.DEBUG)
            return False

        # if no accessToken was given then use the one from the config
        if not accessToken:
            accessToken = sickbeard.BOXCAR2_ACCESS_TOKEN

        logger.log("Sending notification for " + message, logger.DEBUG)

        self._sendBoxcar2(message, title, accessToken)
        return True

notifier = Boxcar2Notifier
