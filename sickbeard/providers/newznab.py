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

import urllib
import email.utils
import datetime
import re
import os

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import elementtree.ElementTree as etree

import sickbeard
import generic

from sickbeard import classes
from sickbeard import helpers
from sickbeard import scene_exceptions
from sickbeard import encodingKludge as ek

from sickbeard import logger
from sickbeard import tvcache
from sickbeard.exceptions import ex, AuthException


class NewznabProvider(generic.NZBProvider):

    def __init__(self, name, url, key=''):

        generic.NZBProvider.__init__(self, name)

        self.cache = NewznabCache(self)

        self.url = url
        self.key = key

        # if a provider doesn't need an api key then this can be false
        self.needs_auth = True

        self.enabled = True
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

        # add new query strings for exceptions
        name_exceptions = scene_exceptions.get_scene_exceptions(show.tvdbid) + [show.name]
        for cur_exception in name_exceptions:

            cur_params = {}

            # search directly by tvrage id
            if show.tvrid:
                cur_params['rid'] = show.tvrid
            # if we can't then fall back on a very basic name search
            else:
                cur_params['q'] = helpers.sanitizeSceneName(cur_exception)

            if season != None:
                # air-by-date means &season=2010&q=2010.03, no other way to do it atm
                if show.air_by_date:
                    cur_params['season'] = season.split('-')[0]
                    if 'q' in cur_params:
                        cur_params['q'] += '.' + season.replace('-', '.')
                    else:
                        cur_params['q'] = season.replace('-', '.')
                else:
                    cur_params['season'] = season

            # hack to only add a single result if it's a rageid search
            if not ('rid' in cur_params and to_return):
                to_return.append(cur_params)

        return to_return

    def _get_episode_search_strings(self, ep_obj):

        params = {}

        if not ep_obj:
            return [params]

        # search directly by tvrage id
        if ep_obj.show.tvrid:
            params['rid'] = ep_obj.show.tvrid
        # if we can't then fall back on a very basic name search
        else:
            params['q'] = helpers.sanitizeSceneName(ep_obj.show.name)

        if ep_obj.show.air_by_date:
            date_str = str(ep_obj.airdate)

            params['season'] = date_str.partition('-')[0]
            params['ep'] = date_str.partition('-')[2].replace('-', '/')
        else:
            params['season'] = ep_obj.season
            params['ep'] = ep_obj.episode

        to_return = [params]

        # only do exceptions if we are searching by name
        if 'q' in params:

            # add new query strings for exceptions
            name_exceptions = scene_exceptions.get_scene_exceptions(ep_obj.show.tvdbid)
            for cur_exception in name_exceptions:

                # don't add duplicates
                if cur_exception == ep_obj.show.name:
                    continue

                cur_return = params.copy()
                cur_return['q'] = helpers.sanitizeSceneName(cur_exception)
                to_return.append(cur_return)

        return to_return

    def _doGeneralSearch(self, search_string):
        return self._doSearch({'q': search_string})

    def _checkAuth(self):

        if self.needs_auth and not self.key:
            logger.log(u"Incorrect authentication credentials for " + self.name + " : " + "API key is missing", logger.DEBUG)
            raise AuthException("Your authentication credentials for " + self.name + " are missing, check your config.")

        return True

    def _checkAuthFromData(self, parsedXML):

        if parsedXML is None:
            return self._checkAuth()

        if parsedXML.tag == 'error':
            code = parsedXML.attrib['code']

            if code == '100':
                raise AuthException("Your API key for " + self.name + " is incorrect, check your config.")
            elif code == '101':
                raise AuthException("Your account on " + self.name + " has been suspended, contact the administrator.")
            elif code == '102':
                raise AuthException("Your account isn't allowed to use the API on " + self.name + ", contact the administrator")
            else:
                logger.log(u"Unknown error given from " + self.name + ": " + parsedXML.attrib['description'], logger.ERROR)
                return False

        return True

    def _doSearch(self, search_params, show=None, max_age=0):

        self._checkAuth()

        params = {"t": "tvsearch",
                  "maxage": sickbeard.USENET_RETENTION,
                  "limit": 100,
                  "cat": '5030,5040'}

        # if max_age is set, use it, don't allow it to be missing
        if max_age or not params['maxage']:
            params['maxage'] = max_age

        # hack this in for now
        if self.getID() == 'nzbs_org':
            params['cat'] += ',5070,5090'

        if search_params:
            params.update(search_params)

        if self.key:
            params['apikey'] = self.key

        search_url = self.url + 'api?' + urllib.urlencode(params)

        logger.log(u"Search url: " + search_url, logger.DEBUG)

        data = self.getURL(search_url)

        if not data:
            logger.log(u"No data returned from " + search_url, logger.ERROR)
            return []

        # hack this in until it's fixed server side
        if not data.startswith('<?xml'):
            data = '<?xml version="1.0" encoding="ISO-8859-1" ?>' + data

        parsedXML = helpers.parse_xml(data)

        if parsedXML is None:
            logger.log(u"Error trying to load " + self.name + " XML data", logger.ERROR)
            return []

        if self._checkAuthFromData(parsedXML):

            if parsedXML.tag == 'rss':
                items = parsedXML.findall('.//item')

            else:
                logger.log(u"Resulting XML from " + self.name + " isn't RSS, not parsing it", logger.ERROR)
                return []

            results = []

            for curItem in items:
                (title, url) = self._get_title_and_url(curItem)

                if title and url:
                    logger.log(u"Adding item from RSS to results: " + title, logger.DEBUG)
                    results.append(curItem)
                else:
                    logger.log(u"The XML returned from the " + self.name + " RSS feed is incomplete, this result is unusable", logger.DEBUG)

            return results

        return []

    def findPropers(self, search_date=None):

        search_terms = ['.proper.', '.repack.']

        cache_results = self.cache.listPropers(search_date)
        results = [classes.Proper(x['name'], x['url'], datetime.datetime.fromtimestamp(x['time'])) for x in cache_results]

        for term in search_terms:
            for item in self._doSearch({'q': term}, max_age=4):

                (title, url) = self._get_title_and_url(item)

                description_node = item.find('pubDate')
                description_text = helpers.get_xml_text(description_node)

                try:
                    # we could probably do dateStr = descriptionStr but we want date in this format
                    date_text = re.search('(\w{3}, \d{1,2} \w{3} \d{4} \d\d:\d\d:\d\d) [\+\-]\d{4}', description_text).group(1)
                except:
                    date_text = None

                if not date_text:
                    logger.log(u"Unable to figure out the date for entry " + title + ", skipping it")
                    continue
                else:

                    result_date = email.utils.parsedate(date_text)
                    if result_date:
                        result_date = datetime.datetime(*result_date[0:6])

                if not search_date or result_date > search_date:
                    search_result = classes.Proper(title, url, result_date)
                    results.append(search_result)

        return results


class NewznabCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll newznab providers every 15 minutes max
        self.minTime = 15

    def _getRSSData(self):

        params = {"t": "tvsearch",
                  "cat": '5040,5030'}

        # hack this in for now
        if self.provider.getID() == 'nzbs_org':
            params['cat'] += ',5070,5090'

        if self.provider.key:
            params['apikey'] = self.provider.key

        rss_url = self.provider.url + 'api?' + urllib.urlencode(params)

        logger.log(self.provider.name + " cache update URL: " + rss_url, logger.DEBUG)

        data = self.provider.getURL(rss_url)

        if not data:
            logger.log(u"No data returned from " + rss_url, logger.ERROR)
            return None

        # hack this in until it's fixed server side
        if data and not data.startswith('<?xml'):
            data = '<?xml version="1.0" encoding="ISO-8859-1" ?>' + data

        return data

    def _checkAuth(self, parsedXML):
            return self.provider._checkAuthFromData(parsedXML)
