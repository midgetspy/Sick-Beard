import socket
import sys
from httplib import HTTPSConnection
from urllib import urlencode


import sickbeard

from sickbeard import logger
    
def sendProwl(prowl_api, title="Sick Beard", event=None, message=None):
    
    if not sickbeard.USE_PROWL:
        return False
    
    if not prowl_api:
        prowl_api = sickbeard.PROWL_API
    
    logger.log(u"Prowl title: " + title, logger.DEBUG)
    logger.log(u"Prowl event: " + event, logger.DEBUG)
    logger.log(u"Prowl message: " + message, logger.DEBUG)
    logger.log(u"Prowl api: " + prowl_api, logger.DEBUG)
    
    priority = sickbeard.PROWL_PRIORITY
    http_handler = HTTPSConnection("prowl.weks.net")
                        
    data = {'apikey': prowl_api,
        'application': title,
        'event': event,
        'description': message,
        'priority': priority }

    http_handler.request("POST",
                "/publicapi/add",
                headers = {'Content-type': "application/x-www-form-urlencoded"},
                body = urlencode(data))
    response = http_handler.getresponse()
    request_status = response.status

    if request_status == 200:
        logger.log(u"Prowl notifications sent.", logger.DEBUG)
    elif request_status == 401: 
        logger.log(u"Prowl auth failed: %s" % response.reason, logger.ERROR)
    else:
        logger.log(u"Prowl notification failed.", logger.ERROR)