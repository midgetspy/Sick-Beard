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

from httplib import HTTPSConnection, HTTPException
from urllib import urlencode

try:
    # this only exists in 2.6
    from ssl import SSLError
except ImportError:
    # make a fake one since I don't know what it is supposed to be in 2.5
    class SSLError(Exception):
        pass

import sickbeard

from sickbeard import logger, common

class ProwlNotifier:

    def test_notify(self, prowl_api, prowl_priority):
        return self._sendProwl(prowl_api, prowl_priority, event="Test", message="Testing Prowl settings from Sick Beard", force=True)

    def notify_snatch(self, ep_name):
        if sickbeard.PROWL_NOTIFY_ONSNATCH:
            self._sendProwl(prowl_api=None, prowl_priority=None, event=common.notifyStrings[common.NOTIFY_SNATCH], message=ep_name)

    def notify_download(self, ep_name):
        if sickbeard.PROWL_NOTIFY_ONDOWNLOAD:
            self._sendProwl(prowl_api=None, prowl_priority=None, event=common.notifyStrings[common.NOTIFY_DOWNLOAD], message=ep_name)
        
    def _sendProwl(self, prowl_api=None, prowl_priority=None, event=None, message=None, force=False):
        
        if not sickbeard.USE_PROWL and not force:
                return False
        
        if prowl_api == None:
            prowl_api = sickbeard.PROWL_API
            
        if prowl_priority == None:
            prowl_priority = sickbeard.PROWL_PRIORITY
        
            
        title = "Sick Beard"
        
        logger.log(u"Prowl title: " + title, logger.DEBUG)
        logger.log(u"Prowl event: " + event, logger.DEBUG)
        logger.log(u"Prowl message: " + message, logger.DEBUG)
        logger.log(u"Prowl api: " + prowl_api, logger.DEBUG)
        logger.log(u"Prowl priority: " + prowl_priority, logger.DEBUG)
        
        http_handler = HTTPSConnection("api.prowlapp.com")
                                                
        data = {'apikey': prowl_api,
                'application': title,
                'event': event,
                'description': message.encode('utf-8'),
                'priority': prowl_priority }

        try:
            http_handler.request("POST",
                                    "/publicapi/add",
                                    headers = {'Content-type': "application/x-www-form-urlencoded"},
                                    body = urlencode(data))
        except (SSLError, HTTPException):
            logger.log(u"Prowl notification failed.", logger.ERROR)
            return False
        response = http_handler.getresponse()
        request_status = response.status

        if request_status == 200:
                logger.log(u"Prowl notifications sent.", logger.DEBUG)
                return True
        elif request_status == 401: 
                logger.log(u"Prowl auth failed: %s" % response.reason, logger.ERROR)
                return False
        else:
                logger.log(u"Prowl notification failed.", logger.ERROR)
                return False
                
notifier = ProwlNotifier
