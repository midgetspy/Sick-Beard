import urllib

import xml.etree.cElementTree as etree

import sickbeard
import generic

from sickbeard.common import *
from sickbeard import logger
from sickbeard import tvcache

class TvTorrentsProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "TvTorrents")
        
        self.supportsBacklog = False

        self.cache = TvTorrentsCache(self)

        self.url = 'http://www.tvtorrents.com/'

    def isEnabled(self):
        return sickbeard.TVTORRENTS
        
    def imageName(self):
        return 'tvtorrents.gif'

class TvTorrentsCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll TvTorrents every 15 minutes max
        self.minTime = 15


    def _getRSSData(self):
        # These will be ignored on the serverside.
        RegEx = "all.month|month.of|season[\s\d]*complete"
    
        url = 'http://www.tvtorrents.com/RssServlet?digest='+ sickbeard.TVTORRENTS_DIGEST +'&hash='+ sickbeard.TVTORRENTS_HASH +'&fname=true&exclude=(' + RegEx + ')'
        logger.log(u"TvTorrents cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)
        
        xml_content = etree.fromstring(data)
        description = xml_content.findtext('channel/description')
		
        if "User can't be found" in description:
            logger.log(u"TvTorrents invalid digest, check your config", logger.ERROR)
			
        if "Invalid Hash" in description:
            logger.log(u"TvTorrents invalid hash, check your config", logger.ERROR)

        return data

    def _parseItem(self, item):

        title = item.findtext('title')
        url = item.findtext('link')

        if not title or not url:
            logger.log(u"The XML returned from the TvTorrents RSS feed is incomplete, this result is unusable", logger.ERROR)
            return

        logger.log(u"Adding item from RSS to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = TvTorrentsProvider()