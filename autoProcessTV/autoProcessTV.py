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
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.


import ConfigParser
import urllib
import sys
import os
import os.path

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


def processEpisode(dirName, nzbName=None):

    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessTV.cfg")
    print "Loading config from", configFilename
    config.read(configFilename)
    
    host = config.get("SickBeard", "host")
    port = config.get("SickBeard", "port")
    username = config.get("SickBeard", "username")
    password = config.get("SickBeard", "password")
    
    params = {}
    
    params['quiet'] = 1

    params['dir'] = dirName
    if nzbName != None:
        params['nzbName'] = nzbName
        
    if config.get("SickBeard", "sourceDir") != "" and config.get("SickBeard", "pvrDir") != "":
            params['dir'] = params['dir'].replace(config.get("SickBeard", "sourceDir"), config.get("SickBeard", "pvrDir"))
    
    if config.get("SickBeard", "sourceDir") != "" and config.get("SickBeard", "xbmcDir") != "":
        xbmcPath = params['dir'].replace(config.get("SickBeard", "sourceDir"), config.get("SickBeard", "    Dir"))
    else:
        xbmcPath = None
    
    
    myOpener = AuthURLOpener(username, password)
    
    url = "http://" + host + ":" + port + "/home/postprocess/processEpisode?" + urllib.urlencode(params)
    
    try:
        urlObj = myOpener.openit(url)
    except IOError:
        print "Unable to open URL " + url
        sys.exit()
    
    result = urlObj.readlines()
    for line in result:
        print line
        
