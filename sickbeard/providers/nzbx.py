# Author: Ian Quick <ian.quick@gmail.com>
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

import urllib
import email.utils
import datetime
import re
import os
import json

from xml.dom.minidom import parseString

import sickbeard
import generic
from pprint import pprint
from sickbeard import classes
from sickbeard import helpers
from sickbeard import scene_exceptions
from sickbeard import encodingKludge as ek

from sickbeard import exceptions
from sickbeard import logger
from sickbeard import tvcache
from sickbeard.exceptions import ex

USE_TVRAGE = False

def parseDate(secs):
    if isinstance(secs, ( int , long ) ) :
        return str( datetime.date.fromtimestamp(secs))
    else:
        return secs

def jsonToRSS(json):
    xml = '<?xml version="1.0" encoding="ISO-8859-1" ?>\n'
    xml += '<rss version="2.0">\n'
    xml += '<channel>\n'
    xml += '<title>RSS Title</title>\n'
    xml += '<description>This is an example of an RSS feed</description>\n'
    xml += '<link>http://www.someexamplerssdomain.com/main.html</link>\n'
    xml += '<lastBuildDate>' + str(datetime.date.today()) + '</lastBuildDate>\n'
    xml += '<pubDate>' + str(datetime.date.today()) + '</pubDate>\n'
    xml += '<ttl>1800</ttl>\n'
    
    for entry in json:
        #pprint(entry)
        name = str(entry['name'] )
        logger.log('parsing ' + name )
        xml += '<item><title>' + urllib.quote_plus(name) + '</title>\n'
        xml += '<description>' + urllib.quote_plus(name) + '</description>\n'
        xml += '<link>http://nzbx.co/nzb?' + str(entry['guid']) + '*|*' + urllib.quote_plus(name) + '</link>\n'
        xml += '<pubDate>' + parseDate(entry['postdate']) + '</pubDate>\n'
        xml += '<guid>' + entry['guid'] + '</guid>\n'
        xml += '</item>\n'

    xml += '</channel>\n'
    xml += '</rss>\n'

    return xml

class NzbxProvider(generic.NZBProvider):

    def __init__(self):

        generic.NZBProvider.__init__(self, "nzbx")

        self.cache = NzbxCache(self)
        
        #self.cache.updateCache()

        self.url = "http://nzbx.co/"

        self.enabled = True
        self.needs_auth = False
        self.supportsBacklog = True

        self.default = False

    def configStr(self):
        return self.name + '|' + self.url + '|' + self.key + '|' + str(int(self.enabled))

    def imageName(self):
        if ek.ek(os.path.isfile, ek.ek(os.path.join, sickbeard.PROG_DIR, 'data', 'images', 'providers', self.getID() + '.png')):
            return self.getID() + '.png'
        return 'newznab.png'

    def isEnabled(self):
        return self.enabled

    def _get_season_search_strings(self, show, season=None):

        if not show:
            return [{}]

        to_return = []

        name_exceptions = scene_exceptions.get_scene_exceptions(show.tvdbid) + [show.name]
        for cur_exception in name_exceptions:

            cur_params = {}

            if show.tvrid and USE_TVRAGE:
                cur_params['q'] = show.tvrid
            else:
                cur_params['q'] = helpers.sanitizeSceneName(cur_exception)

            to_return.append(cur_params)
                
        return to_return
    


    def _get_episode_search_strings(self, ep_obj):

        params = {}

        if not ep_obj:
            return [params]

        logger.log(ep_obj.show.name)
        
        if ep_obj.show.tvrid and USE_TVRAGE:
            params['q'] = ep_obj.show.tvrid
        else:
            params['q'] = helpers.sanitizeSceneName(ep_obj.show.name)

        if ep_obj.show.air_by_date:
            date_str = str(ep_obj.airdate)
        else:
            logger.log('fooo')

        to_return = [params]

        if 'q' in params:
            name_exceptions = scene_exceptions.get_scene_exceptions(ep_obj.show.tvdbid)
            for cur_exception in name_exceptions:
                if cur_exception == ep_obj.show.name:
                    continue

                cur_return = params.copy()
                cur_return['q'] = helpers.sanitizeSceneName(cur_exception)
                to_return.append(cur_return)

        return to_return

    def _doGeneralSearch(self, search_string):
        return self._doSearch({'q': search_string})

    def _checkAuthFromData(self, data):
        return True

    def _doSearch(self, search_params, show=None, max_age=0):

        params = {
                  "limit": 250,
                  "index": 'releases',
                  "source": 'sickbeard',
                  }

        if search_params:
            params.update(search_params)

        searchURL = self.url + 'api/search?' + urllib.urlencode(params)

        logger.log(u"Search url: " + searchURL, logger.DEBUG)

        data = self.getURL(searchURL)
        parsedJSON = json.loads(data)
        
        if not data:
            return []

        data = jsonToRSS(parsedJSON )

        try:
            items = parseString(data).getElementsByTagName('item')
        except Exception, e:
            logger.log(u"Error trying to load " + self.name + " RSS feed: " + ex(e), logger.ERROR)
            logger.log(u"RSS data: " + data, logger.DEBUG)
            return []

        results = []

        for curItem in items:
            (title, url) = self._get_title_and_url(curItem)
            logger.log(u"title = " + title + " url = " + url )

            if not title or not url:
                logger.log(u"The XML returned from the " + self.name + " RSS feed is incomplete, this result is unusable: " + data, logger.ERROR)
                continue

            results.append(curItem)

        return results

    def findPropers(self, date=None):

        search_terms = ['.proper.', '.repack.']
        results = []

        cache_results = self.cache.listPropers(date)
        results = [classes.Proper(x['name'], x['url'], datetime.datetime.fromtimestamp(x['time'])) for x in cache_results]
        
        logger.log('in findPropers' )
        for term in search_terms:
            logger.log('for term in search_terms')
            for curResult in self._doSearch({'q': term}, max_age=4):
                
                (title, url) = self._get_title_and_url(curResult)

                description_node = curResult.getElementsByTagName('pubDate')[0]
                descriptionStr = helpers.get_xml_text(description_node)

                try:
                    dateStr = re.search('(\w{3}, \d{1,2} \w{3} \d{4} \d\d:\d\d:\d\d) [\+\-]\d{4}', descriptionStr).group(1)
                except:
                    dateStr = None

                if not dateStr:
                    logger.log(u"Unable to figure out the date for entry " + title + ", skipping it")
                    continue
                else:

                    resultDate = email.utils.parsedate(dateStr)
                    if resultDate:
                        resultDate = datetime.datetime(*resultDate[0:6])

                if date == None or resultDate > date:
                    search_result = classes.Proper(title, url, resultDate)
                    results.append(search_result)

        return results


class NzbxCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)
        self.minTime = 15

        
    def _getRSSData(self):
        url = 'https://nzbx.co/api/recent?category=tv'

        logger.log("NZBX.co cache update URL: " + url, logger.DEBUG )

        data = self.provider.getURL(url)
        data = json.loads(data)

        data = jsonToRSS(data)

        return data
    


    def _checkAuth(self, data):

        return self.provider._checkAuthFromData(data)

provider = NzbxProvider()
