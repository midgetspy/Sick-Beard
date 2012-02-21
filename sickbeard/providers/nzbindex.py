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

import xml.etree.cElementTree as etree

import sickbeard
import generic

from sickbeard import classes, logger, show_name_helpers
from sickbeard import tvcache
from sickbeard.exceptions import ex

class NZBIndexProvider(generic.NZBProvider):

    def __init__(self):

        generic.NZBProvider.__init__(self, "NZBIndex")

        self.supportsBacklog = True

        self.cache = NZBIndexCache(self)

        self.url = 'http://www.NZBIndex.nl/'

    def isEnabled(self):
        return sickbeard.NZBINDEX

    def _get_season_search_strings(self, show, season):
        sceneSearchStrings = set(show_name_helpers.makeSceneSeasonSearchString(show, season, "NZBIndex"))

        # search for all show names and episode numbers like ("a","b","c") in a single search
        return [' '.join(sceneSearchStrings)]

    def _get_episode_search_strings(self, ep_obj):
        # tvrname is better for most shows
        if ep_obj.show.tvrname:
            searchStr = ep_obj.show.tvrname + " S%02dE%02d"%(ep_obj.season, ep_obj.episode)
        else:
            searchStr = ep_obj.show.name + " S%02dE%02d"%(ep_obj.season, ep_obj.episode)
        return [searchStr]

    def _doSearch(self, curString, quotes=False, show=None):

        term =  re.sub('[\.\-]', ' ', curString).encode('utf-8')
        if quotes:
            term = "\""+term+"\""

        params = {"q": term,
                  "max": 50,
                  "hidespam": 1,
                  "minsize":100,
                  "nzblink":1}

        searchURL = "http://nzbindex.nl/rss/?" + urllib.urlencode(params)

        logger.log(u"Search string: " + searchURL, logger.DEBUG)

        logger.log(u"Sleeping 10 seconds to respect NZBIndex's rules")
        time.sleep(10)
        
        searchResult = self.getURL(searchURL,[("User-Agent","Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:5.0) Gecko/20100101 Firefox/5.0"),("Accept","text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),("Accept-Language","de-de,de;q=0.8,en-us;q=0.5,en;q=0.3"),("Accept-Charset","ISO-8859-1,utf-8;q=0.7,*;q=0.7"),("Connection","keep-alive"),("Cache-Control","max-age=0")])

        if not searchResult:
            return []

        try:
            responseSoup = etree.ElementTree(etree.XML(searchResult))
            items = responseSoup.getiterator('item')
        except Exception, e:
            logger.log(u"Error trying to load NZBIndex RSS feed: "+ex(e), logger.ERROR)
            return []

        results = []

        for curItem in items:
            title = curItem.findtext('title')
            url = curItem.findtext('link')

            if not title or not url:
                logger.log(u"The XML returned from the NZBIndex RSS feed is incomplete, this result is unusable", logger.ERROR)
                continue

            results.append(curItem)

        return results


    def findPropers(self, date=None):

        results = []

        for curResult in self._doSearch("(PROPER,REPACK)"):

            title = curResult.findtext('title')
            url = curResult.findtext('link').replace('&amp;','&')

            descriptionStr = curResult.findtext('description')
            dateStr = re.search('<b>Added:</b> (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)', descriptionStr).group(1)
            if not dateStr:
                logger.log(u"Unable to figure out the date for entry "+title+", skipping it")
                continue
            else:
                resultDate = datetime.datetime.strptime(dateStr, "%Y-%m-%d %H:%M:%S")

            if date == None or resultDate > date:
                results.append(classes.Proper(title, url, resultDate))

        return results


class NZBIndexCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll NZBIndex every 25 minutes max
        self.minTime = 25


    def _getRSSData(self):
        # get all records since the last timestamp
        url = "http://nzbindex.nl/rss/?"

        urlArgs = {'q': '',
                   'max': 500,
                   'sort': 'agedesc',
                   'hidespam': 1,
                   'minsize':100,
                   'nzblink':1}

        url += urllib.urlencode(urlArgs)

        logger.log(u"NZBIndex cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data


provider = NZBIndexProvider()
