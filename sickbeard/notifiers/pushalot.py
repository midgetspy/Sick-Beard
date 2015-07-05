# Author: Maciej Olesinski (https://github.com/molesinski/)
# Based on prowl.py by Nic Wolfe <nic@wolfeden.ca>
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

from httplib import HTTPSConnection
from urllib import urlencode

import sickbeard

from sickbeard.exceptions import ex
from sickbeard import common
from sickbeard import logger


class PushalotNotifier:

    def _notify(self, title, message, authtoken=None, silent=None, important=None, force=False):

        # suppress notifications if the notifier is disabled but the notify options are checked
        if not sickbeard.USE_PUSHALOT and not force:
            return False

        # fill in omitted parameters
        if not authtoken:
            authtoken = sickbeard.PUSHALOT_AUTHORIZATIONTOKEN
        if not important:
            important = bool(sickbeard.PUSHALOT_IMPORTANT)
        if not silent:
            silent = bool(sickbeard.PUSHALOT_SILENT)

        logger.log(u"PUSHALOT: Sending notice with details: title=\"%s\", message=\"%s\", silent=%s, important=%s, authtoken=%s" % (title, message, silent, important, authtoken), logger.DEBUG)

        try:

            http_handler = HTTPSConnection("pushalot.com")

            data = {'AuthorizationToken': authtoken,
                    'Title': title.encode('utf-8'),
                    'Body': message.encode('utf-8'),
                    'IsImportant': important,
                    'IsSilent': silent,
                    'Source': 'SickBeard'
                    }

            http_handler.request("POST", "/api/sendmessage",
                                 headers={'Content-type': "application/x-www-form-urlencoded"},
                                 body=urlencode(data)
                                 )

            response = http_handler.getresponse()
            request_status = response.status

        except Exception, e:
            logger.log(u"PUSHALOT: Notification failed: " + ex(e), logger.ERROR)
            return False

        if request_status == 200:
            logger.log(u"PUSHALOT: Notifications sent.", logger.MESSAGE)
            return True
        elif request_status == 400:
            logger.log(u"PUSHALOT: Auth failed: %s" % response.reason, logger.ERROR)
            return False
        elif request_status == 406:
            logger.log(u"PUSHALOT: Message throttle limit reached.", logger.WARNING)
            return False
        elif request_status == 410:
            logger.log(u"PUSHALOT: The AuthorizationToken is invalid.", logger.ERROR)
            return False
        elif request_status == 503:
            logger.log(u"PUSHALOT: Notification servers are currently overloaded with requests. Try again later.", logger.ERROR)
            return False
        else:
            logger.log(u"PUSHALOT: Notification failed.", logger.ERROR)
            return False

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        if sickbeard.PUSHALOT_NOTIFY_ONSNATCH:
            self._notify(common.notifyStrings[common.NOTIFY_SNATCH], ep_name)

    def notify_download(self, ep_name):
        if sickbeard.PUSHALOT_NOTIFY_ONDOWNLOAD:
            self._notify(common.notifyStrings[common.NOTIFY_DOWNLOAD], ep_name)

    def test_notify(self, authtoken, silent, important):
        return self._notify("Test", "This is a test notification from Sick Beard", authtoken, silent, important, force=True)

    def update_library(self, ep_obj=None):
        pass

notifier = PushalotNotifier
