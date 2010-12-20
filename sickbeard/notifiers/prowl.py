import socket
import sys

import sickbeard

from sickbeard import logger

from lib.pyrowl import Pyrowl
    
def sendProwl(title="Sick Beard", event=None, message=None, api_key=None):

	if not sickbeard.USE_PROWL:
		return False

	logger.log(u"Prowl title: " + title, logger.DEBUG)
	logger.log(u"Prowl event: " + event, logger.DEBUG)
	logger.log(u"Prowl message: " + message, logger.DEBUG)
	logger.log(u"Prowl api: " + api_key, logger.DEBUG)

	#if name == None:
	#	name = title

	#Send Notification
	global p
	pkey = None
    
	p = Pyrowl()
	p.addkey(api_key)
	res = p.push(title, event, message, batch_mode=False)
