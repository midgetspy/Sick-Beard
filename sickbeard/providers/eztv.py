import urllib

import sickbeard
import generic

from sickbeard.common import *
from sickbeard import logger
from sickbeard import tvcache

providerType = "torrent"
providerName = "EZTV"

class EZTVProvider(generic.TorrentProvider):
    
    def __init__(self):
        
        generic.NZBProvider.__init__(self, "NZBsRUS")
        
        self.cache = EZTVCache(self)

    def isEnabled(self):
        return sickbeard.USE_TORRENT


class EZTVCache(tvcache.TVCache):
    
    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll EZTV every 15 minutes max
        self.minTime = 15
        

    def _getRSSData(self):
        url = 'http://rss.bt-chat.com/?group=3&cat=9'
        urlArgs = {'group': 3,
                   'cat': 9}

        url += urllib.urlencode(urlArgs)
        
        logger.log("EZTV@BT-Chat cache update URL: "+ url, logger.DEBUG)
        
        data = self.provider.getURL(url)
        
        return data
    
    def _parseItem(self, item):

        title = item.findtext('title')
        url = item.findtext('link')

        if not title or not url:
            logger.log("The XML returned from the EZTV@BT-Chat RSS feed is incomplete, this result is unusable", logger.ERROR)
            continue
        
        # hack off the .[eztv].torrent stuff
        titleMatch = re.search("(.*)\.\[[\w_\.\-]+?\]\.torrent", title)
        
        if not titleMatch:
            logger.log("Unable to parse the result "+title+" into a valid EZTV torrent result, ignoring it", logger.ERROR)
            continue
        
        title = titleMatch.group(1)
        
        logger.log("Adding item from RSS to cache: "+title, logger.DEBUG)            

        self._addCacheEntry(title, url)

