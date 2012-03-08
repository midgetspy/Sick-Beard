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
import datetime

from xml.dom.minidom import parseString

import sickbeard
import generic

from sickbeard import classes, logger, show_name_helpers, helpers
from sickbeard import tvcache
from sickbeard.exceptions import ex

class NZBMatrixProvider(generic.NZBProvider):

    def __init__(self):

        generic.NZBProvider.__init__(self, "NZBMatrix")

        self.supportsBacklog = True

        self.cache = NZBMatrixCache(self)

        self.url = 'http://www.nzbmatrix.com/'

    def isEnabled(self):
        return sickbeard.NZBMATRIX

    def _get_season_search_strings(self, show, season):
        sceneSearchStrings = set(show_name_helpers.makeSceneSeasonSearchString(show, season, "nzbmatrix"))

        # search for all show names and episode numbers like ("a","b","c") in a single search
        return [' '.join(sceneSearchStrings)]

    def _get_episode_search_strings(self, ep_obj):

        sceneSearchStrings = set(show_name_helpers.makeSceneSearchString(ep_obj))

        # search for all show names and episode numbers like ("a","b","c") in a single search
        return ['("' + '","'.join(sceneSearchStrings) + '")']

    def _doSearch(self, curString, quotes=False, show=None):

        term =  re.sub('[\.\-]', ' ', curString).encode('utf-8')
        if quotes:
            term = "\""+term+"\""

        params = {"term": term,
                  "maxage": sickbeard.USENET_RETENTION,
                  "page": "download",
                  "username": sickbeard.NZBMATRIX_USERNAME,
                  "apikey": sickbeard.NZBMATRIX_APIKEY,
                  "subcat": "6,41",
                  "english": 1,
                  "ssl": 1,
                  "scenename": 1}

        # don't allow it to be missing
        if not params['maxage']:
            params['maxage'] = '0'

        # if the show is a documentary use those cats on nzbmatrix
        if show and show.genre and 'documentary' in show.genre.lower():
            params['subcat'] = params['subcat'] + ',53,9' 

        searchURL = "https://rss.nzbmatrix.com/rss.php?" + urllib.urlencode(params)

        logger.log(u"Search string: " + searchURL, logger.DEBUG)

        logger.log(u"Sleeping 10 seconds to respect NZBMatrix's rules")
        time.sleep(10)

        searchResult = self.getURL(searchURL)

        if not searchResult:
            return []

        try:
            parsedXML = parseString(searchResult)
            items = parsedXML.getElementsByTagName('item')
        except Exception, e:
            logger.log(u"Error trying to load NZBMatrix RSS feed: "+ex(e), logger.ERROR)
            return []

        results = []

        for curItem in items:
            (title, url) = self._get_title_and_url(curItem)

            if title == 'Error: No Results Found For Your Search':
                continue

            if not title or not url:
                logger.log(u"The XML returned from the NZBMatrix RSS feed is incomplete, this result is unusable", logger.ERROR)
                continue

            results.append(curItem)

        return results


    def findPropers(self, date=None):

        results = []

        for curResult in self._doSearch("(PROPER,REPACK)"):

            (title, url) = self._get_title_and_url(curResult)

            description_node = curResult.getElementsByTagName('description')[0]
            descriptionStr = helpers.get_xml_text(description_node)

            dateStr = re.search('<b>Added:</b> (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)', descriptionStr).group(1)
            if not dateStr:
                logger.log(u"Unable to figure out the date for entry "+title+", skipping it")
                continue
            else:
                resultDate = datetime.datetime.strptime(dateStr, "%Y-%m-%d %H:%M:%S")

            if date == None or resultDate > date:
                results.append(classes.Proper(title, url, resultDate))

        return results


class NZBMatrixCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll NZBMatrix every 25 minutes max
        self.minTime = 25


    def _getRSSData(self):
        # get all records since the last timestamp
        url = "https://rss.nzbmatrix.com/rss.php?"

        urlArgs = {'page': 'download',
                   'username': sickbeard.NZBMATRIX_USERNAME,
                   'apikey': sickbeard.NZBMATRIX_APIKEY,
                   'maxage': sickbeard.USENET_RETENTION,
                   'english': 1,
                   'ssl': 1,
                   'scenename': 1,
                   'subcat': '6,41'}

        # don't allow it to be missing
        if not urlArgs['maxage']:
            urlArgs['maxage'] = '0'

        url += urllib.urlencode(urlArgs)

        logger.log(u"NZBMatrix cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data


provider = NZBMatrixProvider()
