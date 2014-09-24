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

from httplib import HTTPSConnection
from urllib import urlencode

import sickbeard

from sickbeard.exceptions import ex
from sickbeard import common
from sickbeard import logger


class ProwlNotifier:

    def _notify(self, event, message, prowl_api=None, prowl_priority=None, force=False):

        # suppress notifications if the notifier is disabled but the notify options are checked
        if not sickbeard.USE_PROWL and not force:
            return False

        # fill in omitted parameters
        if not prowl_api:
            prowl_api = sickbeard.PROWL_API
        if not prowl_priority:
            prowl_priority = sickbeard.PROWL_PRIORITY

        logger.log("PROWL: Sending notice with details: event=\"%s\", message=\"%s\", priority=%s, api=%s" % (event, message, prowl_priority, prowl_api), logger.DEBUG)

        try:

            http_handler = HTTPSConnection("api.prowlapp.com")

            data = {'apikey': prowl_api,
                    'application': "SickBeard",
                    'event': event,
                    'description': message.encode('utf-8'),
                    'priority': prowl_priority
                    }

            http_handler.request("POST",
                                 "/publicapi/add",
                                 headers={'Content-type': "application/x-www-form-urlencoded"},
                                 body=urlencode(data)
                                 )

            response = http_handler.getresponse()
            request_status = response.status

        except Exception, e:
            logger.log(u"PROWL: Notification failed: " + ex(e), logger.ERROR)
            return False

        if request_status == 200:
            logger.log(u"PROWL: Notifications sent.", logger.MESSAGE)
            return True
        elif request_status == 401:
            logger.log(u"PROWL: Auth failed: %s" % response.reason, logger.ERROR)
            return False
        elif request_status == 406:
            logger.log(u"PROWL: Message throttle limit reached.", logger.WARNING)
            return False
        else:
            logger.log(u"PROWL: Notification failed.", logger.ERROR)
            return False

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        if sickbeard.PROWL_NOTIFY_ONSNATCH:
            self._notify(common.notifyStrings[common.NOTIFY_SNATCH], ep_name)

    def notify_download(self, ep_name):
        if sickbeard.PROWL_NOTIFY_ONDOWNLOAD:
            self._notify(common.notifyStrings[common.NOTIFY_DOWNLOAD], ep_name)

    def test_notify(self, prowl_api, prowl_priority):
        return self._notify("Test", "This is a test notification from Sick Beard", prowl_api, prowl_priority, force=True)

    def update_library(self, ep_obj=None):
        pass

notifier = ProwlNotifier
