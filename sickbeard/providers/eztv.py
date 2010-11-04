import urllib

import sickbeard
import generic

from sickbeard.common import *
from sickbeard import logger
from sickbeard import tvcache

class EZTVProvider(generic.TorrentProvider):
    
    def __init__(self):
        
        generic.TorrentProvider.__init__(self, "EZTV@BT-Chat")
        
        self.cache = EZTVCache(self)
        
        self.url = 'http://www.eztv.it/'

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
        
        logger.log(u"EZTV@BT-Chat cache update URL: "+ url, logger.DEBUG)
        
        data = self.provider.getURL(url)
        
        return data
    
    def _parseItem(self, item):

        title = item.findtext('title')
        url = item.findtext('link')

        if not title or not url:
            logger.log(u"The XML returned from the EZTV@BT-Chat RSS feed is incomplete, this result is unusable", logger.ERROR)
            return
        
        # hack off the .[eztv].torrent stuff
        titleMatch = re.search("(.*)\.\[[\w_\.\-]+?\]\.torrent", title)
        
        if not titleMatch:
            logger.log(u"Unable to parse the result "+title+" into a valid EZTV torrent result, ignoring it", logger.ERROR)
            return
        
        title = titleMatch.group(1)
        
        logger.log(u"Adding item from RSS to cache: "+title, logger.DEBUG)            

        self._addCacheEntry(title, url)

provider = EZTVProvider()