import urllib
import sys
import os.path

import xml.etree.cElementTree as etree
from sickbeard.common import *
from sickbeard import logger, helpers

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
        logger.log("Error loading EZTV URL: " + sys.exc_info() + " - " + str(e), logger.ERROR)
        return None

    return result


def downloadTorrent (torrent):
    
    logger.log("Downloading a torrent from EZTV at " + torrent.url)

    data = _getEZTVURL(torrent.url)
    
    if data == None:
        return False
    
    fileName = os.path.join(sickbeard.TORRENT_DIR, helpers.sanitizeFileName(torrent.fileName()))
    #fileName = os.path.join(sickbeard.TORRENT_DIR, os.path.basename(torrent.url))
    
    logger.log("Saving to " + fileName, logger.DEBUG)
    
    fileOut = open(fileName, "wb")
    fileOut.write(data)
    fileOut.close()

    return True



def findEpisode(episode, forceQuality=None, manualSearch=False):

    if episode.status == DISCBACKLOG:
        logger.log("EZTV doesn't support disc backlog. Download it manually.")
        return []

    logger.log("Searching EZTV for " + episode.prettyName(True))

    if forceQuality != None:
        epQuality = forceQuality
    elif episode.show.quality == BEST:
        epQuality = ANY
    else:
        epQuality = episode.show.quality
    
    if epQuality == HD:
        quality = '720p'
    else:
        quality = ''

    params = {'show_name': episode.show.name,
              'quality': quality,
              'season': episode.season,
              'episode': episode.episode,
              'mode': 'rss'}
    
    searchURL = "http://ezrss.it/search/index.php?" + urllib.urlencode(params)

    logger.log("Search string: "+searchURL, logger.DEBUG)

    data = _getEZTVURL(searchURL)

    if data == None:
        return []

    results = []
    
    try:
        responseSoup = etree.ElementTree(element = etree.XML(data))
        items = responseSoup.getiterator('item')
    except Exception, e:
        logger.log("Error trying to load EZTV RSS feed: "+str(e), logger.ERROR)
        return []

    for item in items:
        
        title = item.findtext('title')
        url = item.findtext('link')
        filesize = item.find('enclosure').attrib['length']
        
        if title == None or url == None:
            logger.log("The XML returned from the EZTV RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
            continue
        
        # if we are looking for an SD episode pass on anything with 720p in it
        if epQuality == SD and ('720p' in title.lower() or '720p' in url.lower()):
            logger.log("Looking for SD episode on EZTV but found HD. Title: " + title + " URL: " + url)
            continue
        
        try:
            filesize = int(filesize)
        except ValueError:
            logger.log("The file size from EZTV is invalid. Filesize" + filesize +  " Title: " + title + " URL: " + url)
            filesize = 0
        
        logger.log("Found result " + title + " at " + url, logger.DEBUG)

        result = sickbeard.classes.TorrentSearchResult(episode)
        result.provider = 'eztv'
        result.url = url 
        result.extraInfo = [title, filesize]
        
        results.append(result)
        
    # this shouldn't be necessary but can't hurt
    results.sort(lambda x,y: cmp(y.extraInfo[1], x.extraInfo[1]))
        
    return results

def findPropers(date=None):
    return []