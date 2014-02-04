#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import elementtree.ElementTree as etree

import sickbeard
import generic

from sickbeard import classes, logger, show_name_helpers, helpers
from sickbeard import tvcache
from sickbeard.exceptions import ex
from lib.dateutil.parser import parse as parseDate

class NZBClubProvider(generic.NZBProvider):

    def __init__(self):

        generic.NZBProvider.__init__(self, "NZBClub")

        self.supportsBacklog = True

        self.cache = NZBClubCache(self)

        self.url = 'http://nzbclub.com/'
        self.searchString = ''

    def isEnabled(self):
        return sickbeard.NZBCLUB

    def _get_season_search_strings(self, show, season):
        # sceneSearchStrings = set(show_name_helpers.makeSceneSeasonSearchString(show, season, "NZBIndex"))

        # # search for all show names and episode numbers like ("a","b","c") in a single search
        # return [' '.join(sceneSearchStrings)]
        return [x for x in show_name_helpers.makeSceneSeasonSearchString(show, season)]

    def _get_episode_search_strings(self, ep_obj):
        # # tvrname is better for most shows
        # if ep_obj.show.tvrname:
        #     searchStr = ep_obj.show.tvrname + " S%02dE%02d"%(ep_obj.season, ep_obj.episode)
        # else:
        #     searchStr = ep_obj.show.name + " S%02dE%02d"%(ep_obj.season, ep_obj.episode)
        # return [searchStr]
        return [x for x in show_name_helpers.makeSceneSearchString(ep_obj)]

    def _get_title_and_url(self, item):
        (title, url) = super(NZBClubProvider, self)._get_title_and_url(item)
        url = url.replace("_"," ").replace("/nzb view/","/nzb_get/") + ".nzb"
        logger.log( '_get_title_and_url(%s), returns (%s, %s)' %(item, title, url), logger.DEBUG)
        logger.log( 'self.searchString=%s' %(self.searchString), logger.DEBUG)

        # try to filter relevant parts from title
        stitle = filter( lambda x: x.lower().startswith( self.searchString.lower().strip().split()[0] ), re.sub( '\s+', ' ', re.sub('[\[\]\(\)\<\>]+', ' ', title) ).strip().split() )
        if len(stitle) > 1:
            logger.log( 'more than one result for the fixed title (%s), using first.' % stitle, logger.ERROR )
        if stitle:
            title = stitle[0]

        logger.log( 'fixed title: "%s"' % title, logger.DEBUG)
        return (title, url)

    def _doSearch(self, curString, quotes=False, show=None):

        term =  re.sub('[\.\-\:]', ' ', curString).encode('utf-8')
        self.searchString = term
        if quotes:
            term = "\""+term+"\""

        params = {"q": term,
                  "rpp": 50, #max 50
                  "ns": 1, #nospam
                  "szs":16, #min 100MB
                  "sp":1 #nopass
                  }

        searchURL = "http://nzbclub.com/nzbfeeds.aspx?" + urllib.urlencode(params)

        logger.log(u"Search string: " + searchURL)

        logger.log(u"Sleeping 10 seconds to respect NZBClub's rules")
        time.sleep(10)

        searchResult = self.getURL(searchURL,[("User-Agent","Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:5.0) Gecko/20100101 Firefox/5.0"),("Accept","text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),("Accept-Language","de-de,de;q=0.8,en-us;q=0.5,en;q=0.3"),("Accept-Charset","ISO-8859-1,utf-8;q=0.7,*;q=0.7"),("Connection","keep-alive"),("Cache-Control","max-age=0")])

        if not searchResult:
            return []

        try:
            parsedXML = etree.fromstring(searchResult)
            items = parsedXML.iter('item')
        except Exception, e:
            logger.log(u"Error trying to load NZBClub RSS feed: "+ex(e), logger.ERROR)
            return []

        results = []

        for curItem in items:
            (title, url) = self._get_title_and_url(curItem)

            if not title or not url:
                logger.log(u"The XML returned from the NZBClub RSS feed is incomplete, this result is unusable", logger.ERROR)
                continue
            if not title == 'Not_Valid':
                results.append(curItem)

        return results


    def findPropers(self, date=None):

        results = []

        for curResult in self._doSearch("(PROPER,REPACK)"):

            (title, url) = self._get_title_and_url(curResult)

            pubDate_node = curResult.find('pubDate')
            pubDate = helpers.get_xml_text(pubDate_node)
            dateStr = re.search('(\w{3}, \d{1,2} \w{3} \d{4} \d\d:\d\d:\d\d) [\+\-]\d{4}', pubDate)
            if not dateStr:
                logger.log(u"Unable to figure out the date for entry "+title+", skipping it")
                continue
            else:
                resultDate = parseDate(dateStr.group(1)).replace(tzinfo=None)

            if date == None or resultDate > date:
                results.append(classes.Proper(title, url, resultDate))

        return results


class NZBClubCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll NZBIndex every 25 minutes max
        self.minTime = 25


    def _getRSSData(self):
        # get all records since the last timestamp
        url = "http://nzbclub.com/nzbfeeds.aspx?"

        urlArgs = {'q': '',
                   "rpp": 50, #max 50
                  "ns": 1, #nospam
                  "szs":16, #min 100MB
                  "sp":1 #nopass
                  }

        url += urllib.urlencode(urlArgs)

        logger.log(u"NZBClub cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data


provider = NZBClubProvider()
