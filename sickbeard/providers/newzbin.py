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

import re
import time
import urllib
import sys

import xml.etree.cElementTree as etree

import sickbeard
import generic

import sickbeard.encodingKludge as ek
from sickbeard import classes, logger, helpers, exceptions, sceneHelpers, db
from sickbeard import tvcache
from sickbeard.common import *

class NewzbinDownloader(urllib.FancyURLopener):

    def __init__(self):
        urllib.FancyURLopener.__init__(self)

    def http_error_default(self, url, fp, errcode, errmsg, headers):

        # if newzbin is throttling us, wait seconds and try again
        if errcode == 400:

            newzbinErrCode = int(headers.getheader('X-DNZB-RCode'))

            if newzbinErrCode == 450:
                rtext = str(headers.getheader('X-DNZB-RText'))
                result = re.search("wait (\d+) seconds", rtext)

            elif newzbinErrCode == 401:
                raise exceptions.AuthException("Newzbin username or password incorrect")

            elif newzbinErrCode == 402:
                raise exceptions.AuthException("Newzbin account not premium status, can't download NZBs")

            logger.log("Newzbin throttled our NZB downloading, pausing for " + result.group(1) + "seconds")

            time.sleep(int(result.group(1)))

            raise exceptions.NewzbinAPIThrottled()

class NewzbinProvider(generic.NZBProvider):

    def __init__(self):

        generic.NZBProvider.__init__(self, "Newzbin")

        self.supportsBacklog = True

        self.cache = NewzbinCache(self)

        self.url = 'https://www.newzbin.com/'

        self.NEWZBIN_NS = 'http://www.newzbin.com/DTD/2007/feeds/report/'

    def _report(self, name):
        return '{'+self.NEWZBIN_NS+'}'+name

    def isEnabled(self):
        return sickbeard.NEWZBIN

    def getQuality(self, item):
        attributes = item.find(self._report('attributes'))
        attr_dict = {}

        for attribute in attributes.getiterator(self._report('attribute')):
            cur_attr = attribute.attrib['type']
            if cur_attr not in attr_dict:
                attr_dict[cur_attr] = [attribute.text]
            else:
                attr_dict[cur_attr].append(attribute.text)

        logger.log("Finding quality of item based on attributes "+str(attr_dict), logger.DEBUG)

        if self._is_SDTV(attr_dict):
            quality = Quality.SDTV
        elif self._is_SDDVD(attr_dict):
            quality = Quality.SDDVD
        elif self._is_HDTV(attr_dict):
            quality = Quality.HDTV
        elif self._is_WEBDL(attr_dict):
            quality = Quality.HDWEBDL
        elif self._is_720pBluRay(attr_dict):
            quality = Quality.HDBLURAY
        elif self._is_1080pBluRay(attr_dict):
            quality = Quality.FULLHDBLURAY
        else:
            quality = Quality.UNKNOWN

        logger.log("Resulting quality: "+str(quality), logger.DEBUG)

        return quality

    def _is_SDTV(self, attrs):

        # Video Fmt: (XviD or DivX), NOT 720p, NOT 1080p
        video_fmt = 'Video Fmt' in attrs and ('XviD' in attrs['Video Fmt'] or 'DivX' in attrs['Video Fmt']) \
                            and ('720p' not in attrs['Video Fmt']) \
                            and ('1080p' not in attrs['Video Fmt'])

        # Source: TV Cap or HDTV or (None)
        source = 'Source' not in attrs or 'TV Cap' in attrs['Source'] or 'HDTV' in attrs['Source']

        # Subtitles: (None)
        subs = 'Subtitles' not in attrs

        return video_fmt and source and subs

    def _is_SDDVD(self, attrs):

        # Video Fmt: (XviD or DivX), NOT 720p, NOT 1080p
        video_fmt = 'Video Fmt' in attrs and ('XviD' in attrs['Video Fmt'] or 'DivX' in attrs['Video Fmt']) \
                            and ('720p' not in attrs['Video Fmt']) \
                            and ('1080p' not in attrs['Video Fmt'])

        # Source: DVD
        source = 'Source' in attrs and 'DVD' in attrs['Source']

        # Subtitles: (None)
        subs = 'Subtitles' not in attrs

        return video_fmt and source and subs

    def _is_HDTV(self, attrs):
        # Video Fmt: x264, 720p
        video_fmt = 'Video Fmt' in attrs and ('x264' in attrs['Video Fmt']) \
                            and ('720p' in attrs['Video Fmt'])

        # Source: TV Cap or HDTV or (None)
        source = 'Source' not in attrs or 'TV Cap' in attrs['Source'] or 'HDTV' in attrs['Source']

        # Subtitles: (None)
        subs = 'Subtitles' not in attrs

        return video_fmt and source and subs

    def _is_WEBDL(self, attrs):

        # Video Fmt: H.264, 720p
        video_fmt = 'Video Fmt' in attrs and ('H.264' in attrs['Video Fmt']) \
                            and ('720p' in attrs['Video Fmt'])

        # Subtitles: (None)
        subs = 'Subtitles' not in attrs

        return video_fmt and subs

    def _is_720pBluRay(self, attrs):

        # Video Fmt: x264, 720p
        video_fmt = 'Video Fmt' in attrs and ('x264' in attrs['Video Fmt']) \
                            and ('720p' in attrs['Video Fmt'])

        # Source: Blu-ray or HD-DVD
        source = 'Source' in attrs and ('Blu-ray' in attrs['Source'] or 'HD-DVD' in attrs['Source'])

        return video_fmt and source

    def _is_1080pBluRay(self, attrs):

        # Video Fmt: x264, 1080p
        video_fmt = 'Video Fmt' in attrs and ('x264' in attrs['Video Fmt']) \
                            and ('1080p' in attrs['Video Fmt'])

        # Source: Blu-ray or HD-DVD
        source = 'Source' in attrs and ('Blu-ray' in attrs['Source'] or 'HD-DVD' in attrs['Source'])

        return video_fmt and source


    def getIDFromURL(self, url):
        id_regex = re.escape(self.url) + 'browse/post/(\d+)/'
        id_match = re.match(id_regex, url)
        if not id_match:
            return None
        else:
            return id_match.group(1)

    def downloadResult(self, nzb):

        id = self.getIDFromURL(nzb.url)
        if not id:
            logger.log("Unable to get an ID from "+str(nzb.url)+", can't download from Newzbin's API", logger.ERROR)
            return False

        logger.log("Downloading an NZB from newzbin with id "+id)

        fileName = ek.ek(os.path.join, sickbeard.NZB_DIR, helpers.sanitizeFileName(nzb.name)+'.nzb')
        logger.log("Saving to " + fileName)

        urllib._urlopener = NewzbinDownloader()

        params = urllib.urlencode({"username": sickbeard.NEWZBIN_USERNAME, "password": sickbeard.NEWZBIN_PASSWORD, "reportid": id})
        try:
            urllib.urlretrieve(self.url+"api/dnzb/", fileName, data=params)
        except exceptions.NewzbinAPIThrottled:
            logger.log("Done waiting for Newzbin API throttle limit, starting downloads again")
            self.downloadResult(nzb)
        except (urllib.ContentTooShortError, IOError), e:
            logger.log("Error downloading NZB: " + str(sys.exc_info()) + " - " + str(e), logger.ERROR)
            return False

        return True

    def getURL(self, url):

        myOpener = classes.AuthURLOpener(sickbeard.NEWZBIN_USERNAME, sickbeard.NEWZBIN_PASSWORD)
        try:
            f = myOpener.openit(url)
        except (urllib.ContentTooShortError, IOError), e:
            logger.log("Error loading search results: " + str(sys.exc_info()) + " - " + str(e), logger.ERROR)
            return None

        data = f.read()
        f.close()

        return data

    def _get_season_search_strings(self, show, season):

        nameList = set(sceneHelpers.allPossibleShowNames(show))

        if show.is_air_by_date:
            suffix = ''
        else:
            suffix = 'x'
        searchTerms = ['^"'+x+' - '+str(season)+suffix+'"' for x in nameList]
        #searchTerms += ['^"'+x+' - Season '+str(season)+'"' for x in nameList]
        searchStr = " OR ".join(searchTerms)

        searchStr += " -subpack -extras"

        logger.log("Searching newzbin for string "+searchStr, logger.DEBUG)
        
        return [searchStr]

    def _get_episode_search_strings(self, ep_obj):

        nameList = set(sceneHelpers.allPossibleShowNames(ep_obj.show))
        if not ep_obj.show.is_air_by_date:
            searchStr = " OR ".join(['^"'+x+' - %dx%02d"'%(ep_obj.season, ep_obj.episode) for x in nameList])
        else:
            searchStr = " OR ".join(['^"'+x+' - '+str(ep_obj.airdate)+'"' for x in nameList])
        return [searchStr]

    def _doSearch(self, searchStr):

        data = self._getRSSData(searchStr.encode('utf-8'))
        
        item_list = []

        try:
            responseSoup = etree.ElementTree(etree.XML(data))
            items = responseSoup.getiterator('item')
        except Exception, e:
            logger.log("Error trying to load Newzbin RSS feed: "+str(e), logger.ERROR)
            return []

        for cur_item in items:
            title = cur_item.findtext('title')
            if title == 'Feed Error':
                raise exceptions.AuthException("The feed wouldn't load, probably because of invalid auth info")

            item_list.append(cur_item)

        return item_list


    def _getRSSData(self, search=None):

        params = {
                'searchaction': 'Search',
                'fpn': 'p',
                'category': 8,
                'u_nfo_posts_only': 0,
                'u_url_posts_only': 0,
                'u_comment_posts_only': 0,
                'u_show_passworded': 0,
                'u_v3_retention': 0,
                'ps_rb_source': 3008,
                'ps_rb_video_format': 3082257,
                'ps_rb_language': 4096,
                'sort': 'date',
                'order': 'desc',
                'u_post_results_amt': 50,
                'feed': 'rss',
                'hauth': 1,
        }

        if search:
            params['q'] = search + " AND "
        else:
            params['q'] = ''

        params['q'] += 'Attr:Lang~Eng AND NOT Attr:VideoF=DVD'

        url = self.url + "search/?%s" % urllib.urlencode(params)
        logger.log("Newzbin search URL: " + url, logger.DEBUG)

        data = self.getURL(url)

        return data

class NewzbinCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll Newzbin every 10 mins max
        self.minTime = 10

    def _getRSSData(self):

        data = self.provider._getRSSData()

        return data

    def _parseItem(self, item):

        title = item.findtext('title')
        url = item.findtext('link')

        if title == 'Feeds Error':
            logger.log("There's an error in the feed, probably bad auth info", logger.DEBUG)
            raise exceptions.AuthException("Invalid Newzbin username/password")

        if not title or not url:
            logger.log("The XML returned from the "+self.provider.name+" feed is incomplete, this result is unusable", logger.ERROR)
            return

        quality = self.provider.getQuality(item)

        logger.log("Found quality "+str(quality), logger.DEBUG)

        logger.log("Adding item from RSS to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url, quality=quality)


provider = NewzbinProvider()
