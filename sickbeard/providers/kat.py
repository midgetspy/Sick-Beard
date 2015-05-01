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
#
# @author: Dermot Buckley <dermot@buckley.ie>
# Extensive changes/improvments by Ash Eldritch <ash.eldritch@gmail.com>
# Changes/improvements by Fabio Nisci <fabionisci@gmail.com>

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

        self.url = 'http://katproxy.com/'

    def isEnabled(self):
        return sickbeard.KAT
        
    def imageName(self):
        return 'kat.png'
      
    def getQuality(self, item):
        
        #torrent_node = item.getElementsByTagName('torrent')[0]
        #filename_node = torrent_node.getElementsByTagName('title')[0]
        #filename = get_xml_text(filename_node)
        
        # I think the only place we can get anything resembing the filename is in 
        # the title
        filename = helpers.get_xml_text(item.find('title'))

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
        
        params['show_name'] = helpers.sanitizeSceneName(show.name).replace('.',' ').encode('utf-8')
          
        if season != None:
            params['season'] = season
    
        return [params]

    def _get_episode_search_strings(self, ep_obj):
    
        params = {}
        
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

    def _doSearch(self, search_params, show=None):

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
            return episodeParam
        searchURL = self._buildSearchURL(advancedEpisodeParamBuilder, search_params);
        logger.log(u"Advanced-style search string: " + searchURL, logger.DEBUG)
        data = self.getURL(searchURL)

        # Run a fuzzier search if no results came back from the "advanced" style search
        # http://kat.ph/usearch/%22james%20may%22%20S01E01%20verified:1/?rss=1
        if not data or data == '<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel></channel></rss>':
            def fuzzyEpisodeParamBuilder(params):
                episodeParam = ''
                if not 'show_name' in params or not 'season' in params:
                    return ''
                episodeParam = episodeParam + urllib.quote('"' + params.pop('show_name') + '"') + "%20"
                episodeParam = episodeParam + 'S' + str(params.pop('season')).zfill(2)
                if 'episode' in params:
                    episodeParam += 'E' + str(params.pop('episode')).zfill(2)
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

        searchURL = searchURL + '%20verified:1/?' + urllib.urlencode(params)  # this will likely only append the rss=1 part

        return searchURL

    def _parseKatRSS(self, data):

        parsedXML = helpers.parse_xml(data)
        if parsedXML is None:
            logger.log(u"Error trying to load " + self.name + " RSS feed", logger.ERROR)
            return []

        items = parsedXML.findall('.//item')

        results = []

        for curItem in items:

            (title, url) = self._get_title_and_url(curItem)

            if not title or not url:
                logger.log(u"The XML returned from the KAT RSS feed is incomplete, this result is unusable: "+data, logger.ERROR)
                continue

            if self._get_seeders(curItem) <= 0:
                logger.log(u"Discarded result with no seeders: " + title, logger.DEBUG)
                continue

            #if self.urlIsBlacklisted(url):
            #    logger.log(u'URL "%s" for "%s" is blacklisted, ignoring.' % (url, title), logger.DEBUG)
            #    continue

            results.append(curItem)

        return results

    def _get_title_and_url(self, item):
        #     <item>
        #         <title>The Dealership S01E03 HDTV x264 C4TV</title>
        #         <category>TV</category>
        #         <link>http://katproxy.com/the-dealership-s01e03-hdtv-x264-c4tv-t7739376.html</link>
        #         <guid>http://katproxy.com/the-dealership-s01e03-hdtv-x264-c4tv-t7739376.html</guid>
        #         <pubDate>Thu, 15 Aug 2013 20:54:03 +0000</pubDate>
        #         <torrent:contentLength>311302749</torrent:contentLength>
        #         <torrent:infoHash>F94F9B44A03DDA439E5818E2C2F18342103522EF</torrent:infoHash>
        #         <torrent:magnetURI><![CDATA[magnet:?xt=urn:btih:F94F9B44A03DDA439E5818E2C2F18342103522EF&dn=the+dealership+s01e03+hdtv+x264+c4tv&tr=udp%3A%2F%2Ftracker.publicbt.com%3A80&tr=udp%3A%2F%2Fopen.demonii.com%3A1337]]></torrent:magnetURI>
        #         <torrent:seeds>0</torrent:seeds>
        #         <torrent:peers>0</torrent:peers>
        #         <torrent:verified>0</torrent:verified>
        #         <torrent:fileName>the.dealership.s01e03.hdtv.x264.c4tv.torrent</torrent:fileName>
        #         <enclosure url="http://torcache.net/torrent/F94F9B44A03DDA439E5818E2C2F18342103522EF.torrent?title=[katproxy.com]the.dealership.s01e03.hdtv.x264.c4tv" length="311302749" type="application/x-bittorrent" />
        #     </item>

        title = helpers.get_xml_text(item.find('title'))

        url = None
        if sickbeard.PREFER_MAGNETS:
            # if we have a preference for magnets, go straight for the throat...
            url = helpers.get_xml_text(item.find('{http://xmlns.ezrss.it/0.1/}torrent/{http://xmlns.ezrss.it/0.1/}magnetURI'))
            if not url:
                # The above, although standard, is unlikely in kat.  They kinda screw up their namespaces, so we get
                # this instead...
                url = helpers.get_xml_text(item.find('{http://xmlns.ezrss.it/0.1/}magnetURI'))

        if not url:
            enclos = item.find('enclosure')
            if enclos is not None:
                url = enclos.get('url')
                if url:
                    url = url.replace('&amp;', '&')

        if not url:
            url = None  # this should stop us returning empty strings as urls

        return (title, url)

    def _get_seeders(self, item):
        try:
            return int(helpers.get_xml_text(item.find('{http://xmlns.ezrss.it/0.1/}seeds')))
        except ValueError:
            return 1  # safer to return 1 than 0, otherwise if this breaks all torrents would be ignored!

    def _extract_name_from_filename(self, filename):
        name_regex = '(.*?)\.?(\[.*]|\d+\.TPB)\.torrent$'
        logger.log(u"Comparing " + name_regex + " against " + filename, logger.DEBUG)
        match = re.match(name_regex, filename, re.I)
        if match:
            return match.group(1)
        return None


class KATCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll KAT every 15 minutes max
        self.minTime = 15


    def _getRSSData(self):
        # url = self.provider.url + 'tv/?rss=1'
        url = self.provider.url + 'usearch/category%3Atv%20verified%3A1/?rss=1'  # better maybe? - verified only

        logger.log(u"KAT cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data

    def _parseItem(self, item):

        (title, url) = self.provider._get_title_and_url(item)

        if not title or not url:
            logger.log(u"The XML returned from the KAT RSS feed is incomplete, this result is unusable", logger.ERROR)
            return
            
        #if url and self.provider.urlIsBlacklisted(url):
        #    logger.log(u"url %s is blacklisted, skipping..." % url, logger.DEBUG)
        #    return

        logger.log(u"Adding item from RSS to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

provider = KATProvider()
