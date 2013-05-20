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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import urllib, urllib2
import StringIO, zlib, gzip
import re, socket
from xml.dom.minidom import parseString
from httplib import BadStatusLine
import traceback

import sickbeard
import generic

from sickbeard.common import Quality, USER_AGENT
from sickbeard import logger
from sickbeard import tvcache
from sickbeard import helpers
from sickbeard.exceptions import ex
from sickbeard import scene_exceptions

class KATProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "KAT")
        
        self.supportsBacklog = True

        self.cache = KATCache(self)

        self.url = 'http://kat.ph/'

    def isEnabled(self):
        return sickbeard.kat
        
    def imageName(self):
        return 'kat.png'
      
    def getQuality(self, item):
        
        #torrent_node = item.getElementsByTagName('torrent')[0]
        #filename_node = torrent_node.getElementsByTagName('title')[0]
        #filename = get_xml_text(filename_node)
        
        # I think the only place we can get anything resembing the filename is in 
        # the title
        filename = helpers.get_xml_text(item.getElementsByTagName('title')[0])

        quality = Quality.nameQuality(filename)
        
        return quality

    def findSeasonResults(self, show, season):
        
        results = {}
        
        if show.air_by_date:
            logger.log(u"KAT doesn't support air-by-date backlog because of limitations on their RSS search.", logger.WARNING)
            return results
        
        results = generic.TorrentProvider.findSeasonResults(self, show, season)
        
        return results
    def _get_season_search_strings(self, show, season=None):
    
        params = {}
    
        if not show:
            return params
        global lang
        lang = show.audio_lang
        params['show_name'] = helpers.sanitizeSceneName(show.name).replace('.',' ').encode('utf-8')
          
        if season != None:
            params['season'] = season
    
        return [params]

    def _get_episode_search_strings(self, ep_obj):
    
        params = {}
        
        global lang
        
        if not ep_obj:
            return [params]

        params['show_name'] = helpers.sanitizeSceneName(ep_obj.show.name).replace('.',' ').encode('utf-8')
        
        if ep_obj.show.air_by_date:
            params['date'] = str(ep_obj.airdate)
        else:
            params['season'] = ep_obj.season
            params['episode'] = ep_obj.episode

        to_return = [params]

        # add new query strings for exceptions
        name_exceptions = scene_exceptions.get_scene_exceptions(ep_obj.show.tvdbid)
        for name_exception in name_exceptions:
            # don't add duplicates
            if name_exception != ep_obj.show.name:
                # only change show name
                cur_return = params.copy()
                cur_return['show_name'] = helpers.sanitizeSceneName(name_exception)
                to_return.append(cur_return)

        logger.log(u"KAT _get_episode_search_strings for %s is returning %s" % (repr(ep_obj), repr(params)), logger.DEBUG)
        lang = ep_obj.show.audio_lang
        return to_return

    def getURL(self, url, headers=None):
        """
        Overriding here to capture a 404 (which literally means episode-not-found in KAT).
        """

        if not headers:
            headers = []

        opener = urllib2.build_opener()
        opener.addheaders = [('User-Agent', USER_AGENT), ('Accept-Encoding', 'gzip,deflate')]
        for cur_header in headers:
            opener.addheaders.append(cur_header)

        try:
            usock = opener.open(url)
            url = usock.geturl()
            encoding = usock.info().get("Content-Encoding")
    
            if encoding in ('gzip', 'x-gzip', 'deflate'):
                content = usock.read()
                if encoding == 'deflate':
                    data = StringIO.StringIO(zlib.decompress(content))
                else:
                    data = gzip.GzipFile(fileobj=StringIO.StringIO(content))
                result = data.read()
    
            else:
                result = usock.read()
    
            usock.close()
            
            return result
    
        except urllib2.HTTPError, e:
            if e.code == 404:
                # for a 404, we fake an empty result
                return '<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel></channel></rss>'
            
            logger.log(u"HTTP error " + str(e.code) + " while loading URL " + url, logger.ERROR)
            return None
        except urllib2.URLError, e:
            logger.log(u"URL error " + str(e.reason) + " while loading URL " + url, logger.ERROR)
            return None
        except BadStatusLine:
            logger.log(u"BadStatusLine error while loading URL " + url, logger.ERROR)
            return None
        except socket.timeout:
            logger.log(u"Timed out while loading URL " + url, logger.ERROR)
            return None
        except ValueError:
            logger.log(u"Unknown error while loading URL " + url, logger.ERROR)
            return None
        except Exception:
            logger.log(u"Unknown exception while loading URL " + url + ": " + traceback.format_exc(), logger.ERROR)
            return None

    def _doSearch(self, search_params, show=None, season=None):
        # First run a search using the advanced format -- results are probably more reliable, but often not available for several weeks
        # http://kat.ph/usearch/%22james%20may%22%20season:1%20episode:1%20verified:1/?rss=1
        def advancedEpisodeParamBuilder(params):
            episodeParam = ''
            if 'show_name' in params:
                episodeParam = episodeParam + urllib.quote('"' + params.pop('show_name') + '"') +"%20"
            if 'season' in params:
                episodeParam = episodeParam + 'season:' + str(params.pop('season')) +"%20"
            if 'episode' in params:
                episodeParam = episodeParam + 'episode:' + str(params.pop('episode')) +"%20"
            if str(lang)=="fr":
                episodeParam = episodeParam + ' french'
            return episodeParam
        searchURL = self._buildSearchURL(advancedEpisodeParamBuilder, search_params);
        logger.log(u"Advanced-style search string: " + searchURL, logger.DEBUG)
        data = self.getURL(searchURL)
            
        # First run a search using the advanced format -- results are probably more reliable, but often not available for several weeks
        # http://kat.ph/usearch/%22james%20may%22%20season:1%20episode:1%20verified:1/?rss=1
        if not data or data == '<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel></channel></rss>':
            def fuzzyEpisodeParamBuilder(params):
                episodeParam = ''
                if not 'show_name' in params or not 'season' in params:
                    return ''
                episodeParam = episodeParam + urllib.quote('"' + params.pop('show_name') +'"') + "%20"
                episodeParam = episodeParam + 'S' + str(params.pop('season')).zfill(2)
                if 'episode' in params:
                    episodeParam += 'E' + str(params.pop('episode')).zfill(2)
                if str(lang)=="fr":
                    episodeParam = episodeParam + ' french'
                return episodeParam
            searchURL = self._buildSearchURL(fuzzyEpisodeParamBuilder, search_params);
            logger.log(u"Fuzzy-style search string: " + searchURL, logger.DEBUG)
            data = self.getURL(searchURL)

        if not data:
            return []
        
        return self._parseKatRSS(data)

    def _buildSearchURL(self, episodeParamBuilder, search_params):

        params = {"rss": "1", "field": "seeders", "sorder": "desc" }

        if search_params:
            params.update(search_params)

        searchURL = self.url + 'usearch/'

        # Build the episode search parameter via a delegate
        # Many of the 'params' here actually belong in the path as name:value pairs.
        # so we remove the ones we know about (adding them to the path as we do so)
        # NOTE: episodeParamBuilder is expected to modify the passed 'params' variable by popping params it uses
        searchURL = searchURL + episodeParamBuilder(params)

        if 'date' in params:
            logger.log(u"Sorry, air by date not supported by kat.  Removing: " + params.pop('date'), logger.WARNING)

        # we probably have an extra %20 at the end of the url.  Not likely to
        # cause problems, but it is uneeded, so trim it
        if searchURL.endswith('%20'):
            searchURL = searchURL[:-3]

        searchURL = searchURL + '%20verified:1/?' + urllib.urlencode(params) # this will likely only append the rss=1 part

        return searchURL

    def _parseKatRSS(self, data):

        try:
            parsedXML = parseString(data)
            items = parsedXML.getElementsByTagName('item')
        except Exception, e:
            logger.log(u"Error trying to load KAT RSS feed: "+ex(e), logger.ERROR)
            logger.log(u"RSS data: "+data, logger.DEBUG)
            return []

        results = []

        for curItem in items:

            (title, url) = self._get_title_and_url(curItem)
            if not title or not url:
                logger.log(u"The XML returned from the KAT RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
                continue

            if self._get_seeders(curItem) <= 0:
                logger.log(u"Discarded result with no seeders: " + title, logger.DEBUG)
                continue
            curItem.audio_langs=lang
            
            results.append(curItem)

        return results

    def _get_title_and_url(self, item):
        #(title, url) = generic.TorrentProvider._get_title_and_url(self, item)

        title = helpers.get_xml_text(item.getElementsByTagName('title')[0])
        
        url = None
            # if we have a preference for magnets, go straight for the throat...
        try:
            url = helpers.get_xml_text(item.getElementsByTagName('magnetURI')[0])
        except Exception:
            pass
                
        if url is None:
            url = item.getElementsByTagName('enclosure')[0].getAttribute('url').replace('&amp;','&')

        return (title, url)

    def _get_seeders(self, item):
        return int(helpers.get_xml_text(item.getElementsByTagName('torrent:seeds')[0]))

    def _extract_name_from_filename(self, filename):
        name_regex = '(.*?)\.?(\[.*]|\d+\.TPB)\.torrent$'
        logger.log(u"Comparing "+name_regex+" against "+filename, logger.DEBUG)
        match = re.match(name_regex, filename, re.I)
        if match:
            return match.group(1)
        return None
    
#    <item>
#        <title>James Mays Things You Need To Know S02E06 HDTV XviD-AFG</title>
#        <description>random text in here</description>        
#        <category>Tv</category>
#        <link>http://kat.ph/james-mays-things-you-need-to-know-s02e06-hdtv-xvid-afg-t6666685.html</link>
#        <guid>http://kat.ph/james-mays-things-you-need-to-know-s02e06-hdtv-xvid-afg-t6666685.html</guid>
#        <pubDate>Mon, 17 Sep 2012 22:48:02 +0000</pubDate>
#        <torrentLink>http://kat.ph/james-mays-things-you-need-to-know-s02e06-hdtv-xvid-afg-t6666685.html</torrentLink>
#        <hash>556022412DE29EE0B0AC1ED83EF610AA3081CDA4</hash>
#        <peers>0</peers>
#        <seeds>0</seeds>
#        <leechs>0</leechs>
#        <size>255009149</size>
#        <verified>1</verified>
#        <enclosure url="https://torcache.net/torrent/556022412DE29EE0B0AC1ED83EF610AA3081CDA4.torrent?title=[kat.ph]james.mays.things.you.need.to.know.s02e06.hdtv.xvid.afg" length="255009149" type="application/x-bittorrent" />
#    </item>


class KATCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll KAT every 15 minutes max
        self.minTime = 15


    def _getRSSData(self):
        url = self.provider.url + 'tv/?rss=1'

        logger.log(u"KAT cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data

    def _parseItem(self, item):

        (title, url) = self.provider._get_title_and_url(item)

        if not title or not url:
            logger.log(u"The XML returned from the KAT RSS feed is incomplete, this result is unusable", logger.ERROR)
            return
            
        logger.log(u"Adding item from RSS to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = KATProvider()