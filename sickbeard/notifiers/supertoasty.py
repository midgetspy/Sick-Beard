# Author: Nic Wolfe <nic@wolfeden.ca>
# Modified by: Travis La Marr <exiva@exiva.net>
#
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

from httplib import HTTPConnection
from urllib import urlencode

import sickbeard

from sickbeard import logger, common

class ToastyNotifier:

    def test_notify(self, toasty_api):
        return self._sendToasty(toasty_api, event="Test", message="Testing supertoasty settings from Sick Beard", force=True)

    def notify_snatch(self, ep_name):
        if sickbeard.TOASTY_NOTIFY_ONSNATCH:
            self._sendToasty(toasty_api=None, event=common.notifyStrings[common.NOTIFY_SNATCH], message=ep_name)

    def notify_download(self, ep_name):
        if sickbeard.TOASTY_NOTIFY_ONDOWNLOAD:
            self._sendToasty(toasty_api=None, event=common.notifyStrings[common.NOTIFY_DOWNLOAD], message=ep_name)
        
    def _sendToasty(self, toasty_api=None, event=None, message=None, force=False):

        logger.log(u"SuperToasty: init", logger.DEBUG)

        if not sickbeard.USE_TOASTY and not force:
                return False
        
        if toasty_api == None:
            toasty_api = sickbeard.TOASTY_API

        title = "Sick Beard"
        image = "http://f.cl.ly/items/1H2M2s35230G3N252X0M/sickbeard_touch_icon.png"
        
        logger.log(u"SuperToasty title: " + title, logger.DEBUG)
        logger.log(u"SuperToasty event: " + event, logger.DEBUG)
        logger.log(u"SuperToasty message: " + message, logger.DEBUG)
        logger.log(u"SuperToasty device id: " + toasty_api, logger.DEBUG)
        
        http_handler = HTTPConnection("api.supertoasty.com")
                                                
        data = { 'title': event,
                'text': message.encode('utf-8'),
                'sender': title,
                'image': image }

        http_handler.request("POST",
                                "/notify/"+toasty_api,
                                headers = {'Content-type': "application/x-www-form-urlencoded"},
                                body = urlencode(data))
        response = http_handler.getresponse()
        request_status = response.status

        if request_status == 200:
                logger.log(u"SuperToasty notifications sent.", logger.DEBUG)
                return True
        elif request_status == 401: 
                logger.log(u"SuperToasty auth failed: %s" % response.reason, logger.ERROR)
                return False
        else:
                logger.log(u"SuperToasty notification failed.", logger.ERROR)
                return False
                
notifier = ToastyNotifier