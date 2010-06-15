import urllib
import sys
import os.path
import re
import datetime

import xml.etree.cElementTree as etree

from sickbeard.common import *
from sickbeard import logger, helpers, classes
from sickbeard import tvcache

providerType = "torrent"
providerName = "EZTV"

def isActive():
    return sickbeard.USE_TORRENT

def _getEZTVURL (url):

    result = None

    try:
        f = urllib.urlopen(url)
        result = "".join(f.readlines())
    except (urllib.ContentTooShortError, IOError), e:
        logger.log("Error loading EZTV@BT-Chat URL: " + sys.exc_info() + " - " + str(e), logger.ERROR)
        return None

    return result


def downloadTorrent (torrent):
    
    logger.log("Downloading a torrent from EZTV@BT-Chat at " + torrent.url)

    data = _getEZTVURL(torrent.url)
    
    if data == None:
        return False
    
    fileName = os.path.join(sickbeard.TORRENT_DIR, helpers.sanitizeFileName(torrent.name)+".torrent")
    
    logger.log("Saving to " + fileName, logger.DEBUG)
    
    fileOut = open(fileName, "wb")
    fileOut.write(data)
    fileOut.close()

    return True


def searchRSS():
    myCache = EZTVCache()
    myCache.updateCache()
    return myCache.findNeededEpisodes()
    
def findEpisode (episode, manualSearch=False):

    logger.log("Searching EZTV@BT-Chat for " + episode.prettyName(True))

    myCache = EZTVCache()
    myCache.updateCache()
    
    torrentResults = myCache.searchCache(episode, manualSearch)
    logger.log("Cache results: "+str(torrentResults), logger.DEBUG)

    return torrentResults

def findSeasonResults(show, season):
    
    return {}        

def findPropers(date=None):

    results = EZTVCache().listPropers(date)
    
    return [classes.Proper(x['name'], x['url'], datetime.datetime.fromtimestamp(x['time'])) for x in results]

class EZTVCache(tvcache.TVCache):
    
    def __init__(self):

        tvcache.TVCache.__init__(self, providerName.lower())

        # only poll NZBs'R'US every 15 minutes max
        self.minTime = 15
        
    
    def updateCache(self):

        if not self.shouldUpdate():
            return
        
        url = 'http://rss.bt-chat.com/?group=3&cat=9'
        urlArgs = {'group': 3,
                   'cat': 9}

        url += urllib.urlencode(urlArgs)
        
        logger.log("EZTV@BT-Chat cache update URL: "+ url, logger.DEBUG)
        
        data = _getEZTVURL(url)
        
        # as long as the http request worked we count this as an update
        if data:
            self.setLastUpdate()
        
        # now that we've loaded the current RSS feed lets delete the old cache
        logger.log("Clearing cache and updating with new information")
        self._clearCache()
        
        try:
            responseSoup = etree.ElementTree(etree.XML(data))
            items = responseSoup.getiterator('item')
        except Exception, e:
            logger.log("Error trying to load EZTV@BT-Chat RSS feed: "+str(e), logger.ERROR)
            return []
            
        for item in items:

            title = item.findtext('title')
            url = item.findtext('link')

            if not title or not url:
                logger.log("The XML returned from the EZTV@BT-Chat RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
                continue
            
            # hack off the .[eztv].torrent stuff
            titleMatch = re.search("(.*)\.\[[\w_\.\-]+?\]\.torrent", title)
            
            if not titleMatch:
                logger.log("Unable to parse the result "+title+" into a valid EZTV torrent result, ignoring it", logger.ERROR)
                continue
            
            title = titleMatch.group(1)
            
            logger.log("Adding item from RSS to cache: "+title, logger.DEBUG)            

            self._addCacheEntry(title, url)

