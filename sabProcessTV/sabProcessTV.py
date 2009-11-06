#!/usr/bin/python

import ConfigParser
import urllib
import sys
import os
import os.path

config = ConfigParser.ConfigParser()
configFilename = os.path.join(os.path.dirname(sys.argv[0]), "sabProcessTV.cfg")
print "Loading config from", configFilename
config.read(configFilename)

host = config.get("MidgetPVR", "host")
port = config.get("MidgetPVR", "port")
username = config.get("MidgetPVR", "username")
password = config.get("MidgetPVR", "password")

params = {}

if len(sys.argv) <= 1:
    print "ERROR: Insufficient arguments - expecting at least the download folder"
    sys.exit()
else:
    params['dir'] = sys.argv[1]
        
if config.get("MidgetPVR", "sourceDir") != "" and config.get("MidgetPVR", "pvrDir") != "":
        params['dir'] = params['dir'].replace(config.get("MidgetPVR", "sourceDir"), config.get("MidgetPVR", "pvrDir"))

if config.get("MidgetPVR", "sourceDir") != "" and config.get("MidgetPVR", "xbmcDir") != "":
    xbmcPath = params['dir'].replace(config.get("MidgetPVR", "sourceDir"), config.get("MidgetPVR", "xbmcDir"))
else:
    xbmcPath = None

class AuthURLOpener(urllib.FancyURLopener):
    def __init__(self, user, pw):
        self.username = user
        self.password = pw
        self.numTries = 0
        urllib.FancyURLopener.__init__(self)
    
    def prompt_user_passwd(self, host, realm):
        if self.numTries == 0:
            self.numTries = 1
            return (self.username, self.password)
        else:
            return ('', '')

    def openit(self, url):
        self.numTries = 0
        return urllib.FancyURLopener.open(self, url)


def blankHook(count, blockSize, totalSize):
    pass

myOpener = AuthURLOpener(username, password)

url = "http://" + host + ":" + port + "/processEpisode/?" + urllib.urlencode(params)

try:
    urlObj = myOpener.openit(url)
except IOError:
    print "Unable to open URL " + url
    sys.exit()

result = urlObj.readlines()
for line in result:
    print line
    
