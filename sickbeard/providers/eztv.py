import urllib
import sys
import os.path

from lib.BeautifulSoup import BeautifulStoneSoup
from sickbeard.common import *
from sickbeard.logging import *

providerType = "torrent"
providerName = "EZTV"

def isActive():
    return sickbeard.USE_TORRENT

def _getEZTVURL (url):

    result = None

    try:
        f = urllib.urlopen(url)
        result = "".join(f.readlines())
    except (urllib.ContentTooShortError, IOError) as e:
        Logger().log("Error loading EZTV URL: " + sys.exc_info() + " - " + str(e), ERROR)
        return None

    return result


def downloadTorrent (torrent):
    
    Logger().log("Downloading a torrent from EZTV at " + torrent.url)

    data = _getEZTVURL(torrent.url)
    
    if data == None:
        return False
    
    fileName = os.path.join(sickbeard.TORRENT_DIR, torrent.fileName())
    #fileName = os.path.join(sickbeard.TORRENT_DIR, os.path.basename(torrent.url))
    
    Logger().log("Saving to " + fileName, DEBUG)
    
    fileOut = open(fileName, "wb")
    fileOut.write(data)
    fileOut.close()

    return True



def findEpisode(episode, forceQuality=None):

    if episode.status in (BACKLOG, DISCBACKLOG):
        Logger().log("Skipping "+episode.prettyName()+" because it'll probably be too old", DEBUG)
        return []

    Logger().log("Searching EZTV for " + episode.prettyName())

    if forceQuality != None:
        epQuality = forceQuality
    elif episode.show.quality == BEST:
        epQuality = HD
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

    Logger().log("Search string: "+searchURL, DEBUG)

    data = _getEZTVURL(searchURL)

    if data == None:
        return []

    results = []
    
    try:
        responseSoup = BeautifulStoneSoup(data, convertEntities=BeautifulStoneSoup.XML_ENTITIES)
        items = responseSoup.findAll('item')
    except Exception as e:
        Logger().log("Error trying to load EZTV RSS feed: "+str(e), ERROR)
        return []

    for item in items:
        
        if item.title == None or item.link == None:
            Logger().log("The XML returned from the EZTV RSS feed is incomplete, this result is unusable: "+data, ERROR)
            continue
        
        if epQuality == SD and '720p' in item.title or '720p' in item.link:
            continue
        
        title = item.title.string
        url = item.link.string
        
        Logger().log("Found result " + title + " at " + url, DEBUG)

        result = sickbeard.classes.TorrentSearchResult(episode)
        result.provider = sickbeard.common.EZTV
        result.url = url 
        result.extraInfo = [title]
        
        results.append(result)
        
    return results
