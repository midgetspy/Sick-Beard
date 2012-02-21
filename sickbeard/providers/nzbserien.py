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
from sickbeard.common import Quality

class NZBSerienProvider(generic.NZBProvider):

    def __init__(self):

        generic.NZBProvider.__init__(self, "NZBSerien")

        self.supportsBacklog = True

        self.cache = NZBSerienCache(self)

        self.url = 'http://nzbserien.org'

    def isEnabled(self):
        return sickbeard.NZBSERIEN

    def _get_season_search_strings(self, show, season):
        return [x for x in show_name_helpers.makeSceneSeasonSearchString(show, season)]

    def _get_episode_search_strings(self, ep_obj):
        return [x for x in show_name_helpers.makeSceneSearchString(ep_obj)]

    def _doSearch(self, curString, quotes=False, show=None):

        term =  re.sub('[\.\-\:]', '%', curString).encode('utf-8')
        term = term.replace(' ', '%')
        if quotes:
            term = "\""+term+"\""

        params = {"page": "search",
                  "s": term}

        searchURL = "http://nzbserien.org/?" + urllib.urlencode(params)

        logger.log(u"Search string: " + searchURL, logger.DEBUG)

        logger.log(u"Sleeping 10 seconds to respect NZBSerien's rules")
        time.sleep(10)
        
        searchResult = self.getURL(searchURL,[("User-Agent","Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:5.0) Gecko/20100101 Firefox/5.0"),("Accept","text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),("Accept-Language","de-de,de;q=0.8,en-us;q=0.5,en;q=0.3"),("Accept-Charset","ISO-8859-1,utf-8;q=0.7,*;q=0.7"),("Connection","keep-alive"),("Cache-Control","max-age=0")])

        if not searchResult:
            return []

        results = []
        lines = []
        
        #####################################################
        # be aware that this is just a very very dirty hack !
        
        p = re.compile('<td class="tablecontent"><a href([\w. <="?>:/&;/-])*</a></td>')
        rest = searchResult
        found = True
        while found:
            found = False
            match = p.search(rest)
            if not match == None:
                found = True
                #print rest[match.start():match.end()]
                lines.append(rest[match.start():match.end()])
                rest = rest[match.end():]
        
        urlre = re.compile('download.php\?[\w=]*')
        titlere = re.compile('">[\w./-]*</a>')
        for line in lines:
            u = urlre.search(line)
            t = titlere.search(line)
            #print line[t.start()+2:t.end()-4] + " == " + line[u.start():u.end()]
            if not u == None:
                if not t == None:
                    results.append((line[t.start()+2:t.end()-4],"http://nzbserien.org/"+line[u.start():u.end()]))   #(title,url)

        return results

    def getQuality(self, item):
        (title,url) = item
        quality = Quality.nameQuality(title)
        return quality

    def _get_title_and_url(self, item):
        (title,url) = item
        if url:
            url = url.replace('&amp;','&')  #not shure if we really need this
        return (title, url)

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


class NZBSerienCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)
        self.minTime = 25


    def _getRSSData(self):
    
        url = "http://nzbserien.org/serien.xml"

        logger.log(u"NZBSerien cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data


provider = NZBSerienProvider()
