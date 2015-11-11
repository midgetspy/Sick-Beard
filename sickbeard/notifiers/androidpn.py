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

class AndroidPNNotifier:

    def _sendAndroidPN(self, title, msg, url, username, broadcast):

        # build up the URL and parameters
        msg = msg.strip()

        data = urllib.urlencode({
            'action': "send",
            'broadcast': broadcast,
            'uri': "",
            'title': title,
            'username': username,
            'message': msg.encode('utf-8'),
            })

        # send the request to pushover
        try:
            req = urllib2.Request(url, data)
            handle = sickbeard.helpers.getURLFileLike(req, throw_exc=True)
            handle.close()

        except urllib2.URLError, e:
            # FIXME: Python 2.5 hack, it wrongly reports 201 as an error
            if hasattr(e, 'code') and e.code == 201:
                logger.log(u"ANDROIDPN: Notification successful.", logger.MESSAGE)
                return True

            # if we get an error back that doesn't have an error code then who knows what's really happening
            if not hasattr(e, 'code'):
                logger.log(u"ANDROIDPN: Notification failed." + ex(e), logger.ERROR)
                return False
            else:
                logger.log(u"ANDROIDPN: Notification failed. Error code: " + str(e.code), logger.ERROR)

            # HTTP status 404 if the provided email address isn't a AndroidPN user.
            if e.code == 404:
                logger.log(u"ANDROIDPN: Username is wrong/not a AndroidPN email. AndroidPN will send an email to it", logger.WARNING)
                return False

            # For HTTP status code 401's, it is because you are passing in either an invalid token, or the user has not added your service.
            elif e.code == 401:

                # HTTP status 401 if the user doesn't have the service added
                subscribeNote = self._sendAndroidPN(title, msg, username)
                if subscribeNote:
                    logger.log(u"ANDROIDPN: Subscription sent", logger.DEBUG)
                    return True
                else:
                    logger.log(u"ANDROIDPN: Subscription could not be sent", logger.ERROR)
                    return False

            # If you receive an HTTP status code of 400, it is because you failed to send the proper parameters
            elif e.code == 400:
                logger.log(u"ANDROIDPN: Wrong data sent to AndroidPN", logger.ERROR)
                return False

        logger.log(u"ANDROIDPN: Notification successful.", logger.MESSAGE)
        return True

    def _notify(self, title, message, url, username=None, broadcast=None, force=False):
        """
        Sends a pushover notification based on the provided info or SB config
        """

        # suppress notifications if the notifier is disabled but the notify options are checked
        if not sickbeard.USE_ANDROIDPN and not force:
            return False

        # fill in omitted parameters
        if not username:
            username = sickbeard.ANDROIDPN_USERNAME
        if not url:
            url = sickbeard.ANDROIDPN_URL
        if not broadcast:
            broadcast = sickbeard.ANDROIDPN_BROADCAST

        logger.log(u"ANDROIDPN: Sending notice with details: title=\"%s\", message=\"%s\", username=%s, url=%s, broadcast=%s" % (title, message, username, url, broadcast), logger.DEBUG)

        return self._sendAndroidPN(title, message, url, username, broadcast)

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        if sickbeard.ANDROIDPN_NOTIFY_ONSNATCH:
            self._notify(notifyStrings[NOTIFY_SNATCH], ep_name)

    def notify_download(self, ep_name):
        if sickbeard.ANDROIDPN_NOTIFY_ONDOWNLOAD:
            self._notify(notifyStrings[NOTIFY_DOWNLOAD], ep_name)

    def test_notify(self, userKey, priority, device, sound):
        return self._notify("Test", "This is a test notification from Sick Beard", url, username, broadcast, force=True)

    def update_library(self, ep_obj=None):
        pass

notifier = AndroidPNNotifier
