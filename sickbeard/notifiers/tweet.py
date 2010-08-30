import socket
import sys

from os import popen

import sickbeard

from sickbeard import logger

def send_tweet(options,message=None):
	#temporary curl code

        if len(message) > 140:
                print "Message too long"
		return False

	url = 'http://twitter.com/statuses/update.xml'
	curl = 'curl -s -u %s:%s -d status="%s" %s' % (options['tname'],options['password'],prefix+message,url)

	pipe = popen(curl, 'r')
	#message = "DVR has recorded " + sname + " - " + sys.argv[4] + "x" + sys.argv[5] + " - " + stitle


def notifyTwitter(message=None, username=None, password=None):

	if not sickbeard.USE_TWITTER:
		return False

	opts = {}

	if password == None:
		opts['password'] = sickbeard.TWITTER_PASSWORD
	else:
		opts['password'] = password

        if username == None:
                opts['tname'] = sickbeard.TWITTER_USERNAME
        else:
                opts['tname'] = username

        if message == "This is a test notification from Sick Beard":
                prefix = ""
        else:
                prefix = "DVR has recorded: "

	logger.log("Sending tweet from "+opts['tname']+" Password "+str(opts['password'])+": "+prefix+message)
	try:
		send_tweet(opts, prefix+message)
	except e:
		logger.log("Unable to send tweet")
