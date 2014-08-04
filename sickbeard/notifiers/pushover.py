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
import time

import sickbeard

from sickbeard import logger
from sickbeard.common import notifyStrings, NOTIFY_SNATCH, NOTIFY_DOWNLOAD
from sickbeard.exceptions import ex

API_URL = "https://api.pushover.net/1/messages.json"
API_KEY = "OKCXmkvHN1syU2e8xvpefTnyvVWGv5"


class PushoverNotifier:

    def _sendPushover(self, title, msg, userKey=None):
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

        data = urllib.urlencode({
            'token': API_KEY,
            'title': title,
            'user': userKey,
            'message': msg.encode('utf-8'),
            'timestamp': int(time.time())
            })

        # send the request to pushover
        try:
            req = urllib2.Request(API_URL)
            handle = urllib2.urlopen(req, data)
            handle.close()

        except urllib2.URLError, e:
            # FIXME: Python 2.5 hack, it wrongly reports 201 as an error
            if hasattr(e, 'code') and e.code == 201:
                logger.log(u"PUSHOVER: Notification successful.", logger.MESSAGE)
                return True

            # if we get an error back that doesn't have an error code then who knows what's really happening
            if not hasattr(e, 'code'):
                logger.log(u"PUSHOVER: Notification failed." + ex(e), logger.ERROR)
                return False
            else:
                logger.log(u"PUSHOVER: Notification failed. Error code: " + str(e.code), logger.ERROR)

            # HTTP status 404 if the provided email address isn't a Pushover user.
            if e.code == 404:
                logger.log(u"PUSHOVER: Username is wrong/not a Pushover email. Pushover will send an email to it", logger.WARNING)
                return False

            # For HTTP status code 401's, it is because you are passing in either an invalid token, or the user has not added your service.
            elif e.code == 401:

                # HTTP status 401 if the user doesn't have the service added
                subscribeNote = self._sendPushover(title, msg, userKey)
                if subscribeNote:
                    logger.log(u"PUSHOVER: Subscription sent", logger.DEBUG)
                    return True
                else:
                    logger.log(u"PUSHOVER: Subscription could not be sent", logger.ERROR)
                    return False

            # If you receive an HTTP status code of 400, it is because you failed to send the proper parameters
            elif e.code == 400:
                logger.log(u"PUSHOVER: Wrong data sent to Pushover", logger.ERROR)
                return False

        logger.log(u"PUSHOVER: Notification successful.", logger.MESSAGE)
        return True

    def _notify(self, title, message, userKey=None, force=False):
        """
        Sends a pushover notification based on the provided info or SB config

        title: The title of the notification to send
        message: The message string to send
        userKey: The userKey to send the notification to
        """

        # suppress notifications if the notifier is disabled but the notify options are checked
        if not sickbeard.USE_PUSHOVER and not force:
            return False

        # fill in omitted parameters
        if not userKey:
            userKey = sickbeard.PUSHOVER_USERKEY

        logger.log(u"PUSHOVER: Sending notification for " + message, logger.DEBUG)

        return self._sendPushover(title, message, userKey)

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        if sickbeard.PUSHOVER_NOTIFY_ONSNATCH:
            self._notify(notifyStrings[NOTIFY_SNATCH], ep_name)

    def notify_download(self, ep_name):
        if sickbeard.PUSHOVER_NOTIFY_ONDOWNLOAD:
            self._notify(notifyStrings[NOTIFY_DOWNLOAD], ep_name)

    def test_notify(self, userKey):
        return self._notify("Test", "This is a test notification from Sick Beard", userKey, force=True)

    def update_library(self, ep_obj=None):
        pass

notifier = PushoverNotifier
