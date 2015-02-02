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
import time

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import elementtree.ElementTree as etree

import sickbeard
import generic

from sickbeard import helpers, classes, logger, db
from sickbeard import scene_exceptions

from sickbeard.common import Quality, MULTI_EP_RESULT, SEASON_RESULT
from sickbeard import tvcache
from sickbeard import encodingKludge as ek
from sickbeard.exceptions import ex, AuthException

from sickbeard.name_parser.parser import NameParser, InvalidNameException


class NewznabProvider(generic.NZBProvider):

    def __init__(self, name, url, key='', catIDs='5030,5040'):

        generic.NZBProvider.__init__(self, name)

        self.cache = NewznabCache(self)

        self.url = url

        self.key = key

        # a 0 in the key spot indicates that no key is needed
        if self.key == '0':
            self.needs_auth = False
        else:
            self.needs_auth = True

        if catIDs:
            self.catIDs = catIDs
        else:
            self.catIDs = '5030,5040'

        self.enabled = True
        self.supportsBacklog = True

        self.default = False

    def configStr(self):
        return self.name + '|' + self.url + '|' + self.key + '|' + self.catIDs + '|' + str(int(self.enabled))

    def imageName(self):
        if ek.ek(os.path.isfile, ek.ek(os.path.join, sickbeard.PROG_DIR, 'data', 'images', 'providers', self.getID() + '.png')):
            return self.getID() + '.png'
        return 'newznab.png'

    def isEnabled(self):
        return self.enabled

    def findEpisode(self, episode, manualSearch=False):

        logger.log(u"Searching " + self.name + " for " + episode.prettyName())

        self.cache.updateCache()
        results = self.cache.searchCache(episode, manualSearch)
        logger.log(u"Cache results: " + str(results), logger.DEBUG)

        # if we got some results then use them no matter what.
        # OR
        # return anyway unless we're doing a manual search
        if results or not manualSearch:
            return results

        itemList = []

        for cur_search_string in self._get_episode_search_strings(episode):
            itemList += self._doSearch(cur_search_string, show=episode.show)

        # check if shows that we have a tvrage id for returned 0 results
        # if so, fall back to just searching by query
        if itemList == [] and episode.show.tvrid != 0:
            logger.log(u"Unable to find a result on " + self.name + " using tvrage id (" + str(episode.show.tvrid) + "), trying to search by string...", logger.WARNING)
            for cur_search_string in self._get_episode_search_strings(episode, ignore_tvr=True):
                itemList += self._doSearch(cur_search_string, show=episode.show)

        for item in itemList:

            (title, url) = self._get_title_and_url(item)

            # parse the file name
            try:
                myParser = NameParser()
                parse_result = myParser.parse(title)
            except InvalidNameException:
                logger.log(u"Unable to parse the filename " + title + " into a valid episode", logger.WARNING)
                continue

            if episode.show.air_by_date:
                if parse_result.air_date != episode.airdate:

                    logger.log(u"Episode " + title + " didn't air on " + str(episode.airdate) + ", skipping it", logger.DEBUG)
                    continue

            elif parse_result.season_number != episode.season or episode.episode not in parse_result.episode_numbers:
                logger.log(u"Episode " + title + " isn't " + str(episode.season) + "x" + str(episode.episode) + ", skipping it", logger.DEBUG)
                continue

            quality = self.getQuality(item)

            if not episode.show.wantEpisode(episode.season, episode.episode, quality, manualSearch):
                logger.log(u"Ignoring result " + title + " because we don't want an episode that is " + Quality.qualityStrings[quality], logger.DEBUG)
                continue

            logger.log(u"Found result " + title + " at " + url, logger.DEBUG)

            result = self.getResult([episode])
            result.url = url
            result.name = title
            result.quality = quality

            results.append(result)

        return results

    def findSeasonResults(self, show, season):

        itemList = []
        results = {}

        for cur_string in self._get_season_search_strings(show, season):
            itemList += self._doSearch(cur_string)

        # check if shows that we have a tvrage id for returned 0 results
        # if so, fall back to just searching by query
        if itemList == [] and show.tvrid != 0:
            logger.log(u"Unable to find a result on " + self.name + " using tvrage id (" + str(show.tvrid) + "), trying to search by string...", logger.WARNING)
            for cur_string in self._get_season_search_strings(show, season, ignore_tvr=True):
                itemList += self._doSearch(cur_string)

        for item in itemList:

            (title, url) = self._get_title_and_url(item)

            quality = self.getQuality(item)

            # parse the file name
            try:
                myParser = NameParser(False)
                parse_result = myParser.parse(title)
            except InvalidNameException:
                logger.log(u"Unable to parse the filename " + title + " into a valid episode", logger.WARNING)
                continue

            if not show.air_by_date:
                # this check is meaningless for non-season searches
                if (parse_result.season_number != None and parse_result.season_number != season) or (parse_result.season_number == None and season != 1):
                    logger.log(u"The result " + title + " doesn't seem to be a valid episode for season " + str(season) + ", ignoring")
                    continue

                # we just use the existing info for normal searches
                actual_season = season
                actual_episodes = parse_result.episode_numbers

            else:
                if not parse_result.air_by_date:
                    logger.log(u"This is supposed to be an air-by-date search but the result " + title + " didn't parse as one, skipping it", logger.DEBUG)
                    continue

                myDB = db.DBConnection()
                sql_results = myDB.select("SELECT season, episode FROM tv_episodes WHERE showid = ? AND airdate = ?", [show.tvdbid, parse_result.air_date.toordinal()])

                if len(sql_results) != 1:
                    logger.log(u"Tried to look up the date for the episode " + title + " but the database didn't give proper results, skipping it", logger.WARNING)
                    continue

                actual_season = int(sql_results[0]["season"])
                actual_episodes = [int(sql_results[0]["episode"])]

            # make sure we want the episode
            wantEp = True
            for epNo in actual_episodes:
                if not show.wantEpisode(actual_season, epNo, quality):
                    wantEp = False
                    break

            if not wantEp:
                logger.log(u"Ignoring result " + title + " because we don't want an episode that is " + Quality.qualityStrings[quality], logger.DEBUG)
                continue

            logger.log(u"Found result " + title + " at " + url, logger.DEBUG)

            # make a result object
            epObj = []
            for curEp in actual_episodes:
                epObj.append(show.getEpisode(actual_season, curEp))

            result = self.getResult(epObj)
            result.url = url
            result.name = title
            result.quality = quality

            if len(epObj) == 1:
                epNum = epObj[0].episode
            elif len(epObj) > 1:
                epNum = MULTI_EP_RESULT
                logger.log(u"Separating multi-episode result to check for later - result contains episodes: " + str(parse_result.episode_numbers), logger.DEBUG)
            elif len(epObj) == 0:
                epNum = SEASON_RESULT
                result.extraInfo = [show]
                logger.log(u"Separating full season result to check for later", logger.DEBUG)

            if epNum in results:
                results[epNum].append(result)
            else:
                results[epNum] = [result]

        return results

    def _get_season_search_strings(self, show, season=None, ignore_tvr=False):

        if not show:
            return [{}]

        to_return = []

        # add new query strings for exceptions
        name_exceptions = scene_exceptions.get_scene_exceptions(show.tvdbid) + [show.name]
        for cur_exception in name_exceptions:

            cur_params = {}

            # search directly by tvrage id
            if not ignore_tvr and show.tvrid:
                cur_params['rid'] = show.tvrid
            # if we can't then fall back on a very basic name search
            else:
                cur_params['q'] = helpers.sanitizeSceneName(cur_exception)

            if season is not None:
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

    def _get_episode_search_strings(self, ep_obj, ignore_tvr=False):

        params = {}

        if not ep_obj:
            return [params]

        # search directly by tvrage id
        if not ignore_tvr and ep_obj.show.tvrid:
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
            elif code == '910':
                logger.log(u"" + self.name + " currently has their API disabled, probably maintenance?", logger.WARNING)
                return False
            else:
                logger.log(u"Unknown error given from " + self.name + ": " + parsedXML.attrib['description'], logger.ERROR)
                return False

        return True

    def _doSearch(self, search_params, show=None, max_age=0):

        self._checkAuth()

        params = {"t": "tvsearch",
                  "maxage": sickbeard.USENET_RETENTION,
                  "limit": 100,
                  "cat": self.catIDs}

        # if max_age is set, use it, don't allow it to be missing
        if max_age or not params['maxage']:
            params['maxage'] = max_age

        if search_params:
            params.update(search_params)

        if self.needs_auth and self.key:
            params['apikey'] = self.key

        results = []
        offset = total = hits = 0

        # hardcoded to stop after a max of 4 hits (400 items) per query
        while (hits < 4) and (offset == 0 or offset < total):
            if hits > 0:
                # sleep for a few seconds to not hammer the site and let cpu rest
                time.sleep(2)

            params['offset'] = offset

            search_url = self.url + 'api?' + urllib.urlencode(params)

            logger.log(u"Search url: " + search_url, logger.DEBUG)

            data = self.getURL(search_url)

            if not data:
                logger.log(u"No data returned from " + search_url, logger.ERROR)
                return results

            # hack this in until it's fixed server side
            if not data.startswith('<?xml'):
                data = '<?xml version="1.0" encoding="ISO-8859-1" ?>' + data

            parsedXML = helpers.parse_xml(data)

            if parsedXML is None:
                logger.log(u"Error trying to load " + self.name + " XML data", logger.ERROR)
                return results

            if self._checkAuthFromData(parsedXML):

                if parsedXML.tag == 'rss':
                    items = []
                    response_nodes = []
                    for node in parsedXML.getiterator():
                        # Collect all items for result parsing
                        if node.tag == "item":
                            items.append(node)
                        # Find response nodes but ignore XML namespacing to
                        # accomodate providers with alternative definitions
                        elif node.tag.split("}", 1)[-1] == "response":
                            response_nodes.append(node)
                    # Verify that one and only one node matches and use it,
                    # return otherwise
                    if len(response_nodes) != 1:
                        logger.log(u"No valid, unique response node was found in the API response",
                            logger.ERROR)
                        return results
                    response = response_nodes[0]

                else:
                    logger.log(u"Resulting XML from " + self.name + " isn't RSS, not parsing it", logger.ERROR)
                    return results

                # process the items that we have
                for curItem in items:
                    (title, url) = self._get_title_and_url(curItem)

                    if title and url:
                        # commenting this out for performance reasons, we see the results when they are added to cache anyways
                        # logger.log(u"Adding item from RSS to results: " + title, logger.DEBUG)
                        results.append(curItem)
                    else:
                        logger.log(u"The XML returned from the " + self.name + " RSS feed is incomplete, this result is unusable", logger.DEBUG)

                # check to see if our offset matches what was returned, otherwise dont trust their values and just use what we have
                if offset != int(response.get('offset') or 0):
                    logger.log(u"Newznab provider returned invalid api data, report this to your provider! Aborting fetching further results.", logger.WARNING)
                    return results

                try:
                    total = int(response.get('total') or 0)
                except AttributeError:
                    logger.log(u"Newznab provider provided invalid total.", logger.WARNING)
                    break

            # if we have 0 results, just break out otherwise increment and continue
            if total == 0:
                break
            else:
                offset += 100
                hits += 1

        return results

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
                  "cat": self.provider.catIDs}

        if self.provider.needs_auth and self.provider.key:
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
