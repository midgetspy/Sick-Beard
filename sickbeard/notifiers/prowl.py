import socket
import sys
from httplib import HTTPSConnection
from urllib import urlencode


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
                'description': message,
                'priority': prowl_priority }

        http_handler.request("POST",
                                "/publicapi/add",
                                headers = {'Content-type': "application/x-www-form-urlencoded"},
                                body = urlencode(data))
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