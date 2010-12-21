import socket
import sys
from httplib import HTTPSConnection as Https
from urllib import urlencode


import sickbeard

from sickbeard import logger
    
def sendProwl(prowl_api, title="Sick Beard", event=None, message=None, priority=0):
	
	if not sickbeard.USE_PROWL:
		return False
	
	if not prowl_api:
		prowl_api = sickbeard.PROWL_API
    
	logger.log(u"Prowl title: " + title, logger.DEBUG)
	logger.log(u"Prowl event: " + event, logger.DEBUG)
	logger.log(u"Prowl message: " + message, logger.DEBUG)
	logger.log(u"Prowl api: " + prowl_api, logger.DEBUG)
	
	h = Https("prowl.weks.net")
        
    # Set User-Agent
	headers = {'User-Agent': "SickBeard",'Content-type': "application/x-www-form-urlencoded"}
                        
	# Perform the request and get the response headers and content
	data = {
		'apikey': prowl_api,
		'application': title,
		'event': event,
		'description': message,
		'priority': priority
	}

	h.request(	"POST",
				"/publicapi/add",
				headers = headers,
				body = urlencode(data))
	response = h.getresponse()
	request_status = response.status

	if request_status == 200:
		logger.log(u"Prowl notifications sent.", logger.DEBUG)
	elif request_status == 401: 
		logger.log(u"Prowl auth failed: %s" % response.reason, logger.ERROR)
	else:
		logger.log(u"Prowl notification failed.", logger.ERROR)