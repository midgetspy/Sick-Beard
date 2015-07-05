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

    def _sendBoxcar2(self, title, msg, accessToken, sound):
        """
        Sends a boxcar2 notification to the address provided

        msg: The message to send (unicode)
        title: The title of the message
        accessToken: The access token to send notification to

        returns: True if the message succeeded, False otherwise
        """

        # build up the URL and parameters
        msg = msg.strip().encode('utf-8')

        data = urllib.urlencode({
            'user_credentials': accessToken,
            'notification[title]': title + " - " + msg,
            'notification[long_message]': msg,
            'notification[sound]': sound,
            'notification[source_name]': "SickBeard"
            })

        # send the request to boxcar2
        try:
            req = urllib2.Request(API_URL)
            handle = urllib2.urlopen(req, data)
            handle.close()

        except urllib2.URLError, e:
            # FIXME: Python 2.5 hack, it wrongly reports 201 as an error
            if hasattr(e, 'code') and e.code == 201:
                logger.log(u"BOXCAR2: Notification successful.", logger.MESSAGE)
                return True

            # if we get an error back that doesn't have an error code then who knows what's really happening
            if not hasattr(e, 'code'):
                logger.log(u"BOXCAR2: Notification failed." + ex(e), logger.ERROR)
            else:
                logger.log(u"BOXCAR2: Notification failed. Error code: " + str(e.code), logger.ERROR)

            if e.code == 404:
                logger.log(u"BOXCAR2: Access token is wrong/not associated to a device.", logger.ERROR)
            elif e.code == 401:
                logger.log(u"BOXCAR2: Access token not recognized.", logger.ERROR)
            elif e.code == 400:
                logger.log(u"BOXCAR2: Wrong data sent to boxcar.", logger.ERROR)
            elif e.code == 503:
                logger.log(u"BOXCAR2: Boxcar server to busy to handle the request at this time.", logger.WARNING)
            return False

        logger.log(u"BOXCAR2: Notification successful.", logger.MESSAGE)
        return True

    def _notify(self, title, message, accessToken=None, sound=None, force=False):
        """
        Sends a boxcar2 notification based on the provided info or SB config

        title: The title of the notification to send
        message: The message string to send
        accessToken: The access token to send the notification to (optional, defaults to the access token in the config)
        force: If True then the notification will be sent even if Boxcar is disabled in the config
        """

        # suppress notifications if the notifier is disabled but the notify options are checked
        if not sickbeard.USE_BOXCAR2 and not force:
            return False

        # fill in omitted parameters
        if not accessToken:
            accessToken = sickbeard.BOXCAR2_ACCESS_TOKEN
        if not sound:
            sound = sickbeard.BOXCAR2_SOUND

        logger.log(u"BOXCAR2: Sending notification for " + message, logger.DEBUG)

        return self._sendBoxcar2(title, message, accessToken, sound)

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        if sickbeard.BOXCAR2_NOTIFY_ONSNATCH:
            self._notify(notifyStrings[NOTIFY_SNATCH], ep_name)

    def notify_download(self, ep_name):
        if sickbeard.BOXCAR2_NOTIFY_ONDOWNLOAD:
            self._notify(notifyStrings[NOTIFY_DOWNLOAD], ep_name)

    def test_notify(self, accessToken, sound):
        return self._notify("Test", "This is a test notification from Sick Beard", accessToken, sound, force=True)

    def update_library(self, ep_obj=None):
        pass

notifier = Boxcar2Notifier
