import sickbeard

import urllib
from common import *

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

class NZBSearchResult:

    def __init__(self, episode):
        self.provider = -1
        self.url = ""
        self.extraInfo = []
        self.episode = episode
        self.predownloaded = False

    def __str__(self):
        myString = providerNames[self.provider] + " @ " + self.url + "\n"
        myString += "Extra Info:\n"
        for extra in self.extraInfo:
            myString += "  " + extra + "\n"
        return myString

    def fileName(self):
        return self.episode.prettyName() + ".nzb"

class ShowListUI:
    def __init__(self, config, log):
        self.config = config
        self.log = log

    def selectSeries(self, allSeries):
        idList = [x.tvdbid for x in sickbeard.showList]

        # try to pick a show that's in my show list
        for curShow in allSeries:
            if int(curShow['sid']) in idList:
                return curShow
        
        # if nothing matches then just go with the first match I guess
        return allSeries[0]
