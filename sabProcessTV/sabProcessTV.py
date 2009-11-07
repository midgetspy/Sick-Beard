#!/usr/bin/python

# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of SickBeard.
#
# SickBeard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickBeard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with SickBeard.  If not, see <http://www.gnu.org/licenses/>.


import ConfigParser
import urllib
import sys
import os
import os.path

config = ConfigParser.ConfigParser()
configFilename = os.path.join(os.path.dirname(sys.argv[0]), "sabProcessTV.cfg")
print "Loading config from", configFilename
config.read(configFilename)

host = config.get("SickBeard", "host")
port = config.get("SickBeard", "port")
username = config.get("SickBeard", "username")
password = config.get("SickBeard", "password")

params = {}

if len(sys.argv) <= 1:
    print "ERROR: Insufficient arguments - expecting at least the download folder"
    sys.exit()
else:
    params['dir'] = sys.argv[1]
        
if config.get("SickBeard", "sourceDir") != "" and config.get("SickBeard", "pvrDir") != "":
        params['dir'] = params['dir'].replace(config.get("SickBeard", "sourceDir"), config.get("SickBeard", "pvrDir"))

if config.get("SickBeard", "sourceDir") != "" and config.get("SickBeard", "xbmcDir") != "":
    xbmcPath = params['dir'].replace(config.get("SickBeard", "sourceDir"), config.get("SickBeard", "xbmcDir"))
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
    
