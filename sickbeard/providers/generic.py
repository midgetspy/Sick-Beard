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

from __future__ import with_statement

import datetime
import os
import re

import sickbeard

from sickbeard import helpers, classes, logger, db

from sickbeard.common import Quality, MULTI_EP_RESULT, SEASON_RESULT
from sickbeard import tvcache
from sickbeard import encodingKludge as ek
from sickbeard.exceptions import ex

from lib.hachoir_parser import createParser

from sickbeard.name_parser.parser import NameParser, InvalidNameException


class GenericProvider:

    NZB = "nzb"
    TORRENT = "torrent"

    def __init__(self, name):

        # these need to be set in the subclass
        self.providerType = None
        self.name = name
        self.url = ''

        self.supportsBacklog = False

        self.cache = tvcache.TVCache(self)

    def getID(self):
        return GenericProvider.makeID(self.name)

    @staticmethod
    def makeID(name):
        return re.sub("[^\w\d_]", "_", name.strip().lower())

    def imageName(self):
        return self.getID() + '.png'

    def _checkAuth(self):
        return

    def isActive(self):
        if self.providerType == GenericProvider.NZB and sickbeard.USE_NZBS:
            return self.isEnabled()
        elif self.providerType == GenericProvider.TORRENT and sickbeard.USE_TORRENTS:
            return self.isEnabled()
        else:
            return False

    def isEnabled(self):
        """
        This should be overridden and should return the config setting eg. sickbeard.MYPROVIDER
        """
        return False

    def getResult(self, episodes):
        """
        Returns a result of the correct type for this provider
        """

        if self.providerType == GenericProvider.NZB:
            result = classes.NZBSearchResult(episodes)
        elif self.providerType == GenericProvider.TORRENT:
            result = classes.TorrentSearchResult(episodes)
        else:
            result = classes.SearchResult(episodes)

        result.provider = self

        return result

    def getURL(self, url, post_data=None, headers=None):
        """
        By default this is just a simple urlopen call but this method should be overridden
        for providers with special URL requirements (like cookies)
        """

        if not headers:
            headers = []

        data = helpers.getURL(url, post_data, headers)

        if not data:
            logger.log(u"Error loading " + self.name + " URL: " + url, logger.ERROR)
            return None

        return data

    def downloadResult(self, result):
        """
        Save the result to disk.
        """

        logger.log(u"Downloading a result from " + self.name + " at " + result.url)

        data = self.getURL(result.url)

        if not data:
            return False

        # use the appropriate watch folder
        if self.providerType == GenericProvider.NZB:
            saveDir = sickbeard.NZB_DIR
            writeMode = 'w'
        elif self.providerType == GenericProvider.TORRENT:
            saveDir = sickbeard.TORRENT_DIR
            writeMode = 'wb'
        else:
            return False

        # use the result name as the filename
        file_name = ek.ek(os.path.join, saveDir, helpers.sanitizeFileName(result.name) + '.' + self.providerType)

        logger.log(u"Saving to " + file_name, logger.DEBUG)

        try:
            with open(file_name, writeMode) as fileOut:
                fileOut.write(data)
            helpers.chmodAsParent(file_name)
        except EnvironmentError, e:
            logger.log(u"Unable to save the file: " + ex(e), logger.ERROR)
            return False

        # as long as it's a valid download then consider it a successful snatch
        return self._verify_download(file_name)

    def _verify_download(self, file_name=None):
        """
        Checks the saved file to see if it was actually valid, if not then consider the download a failure.
        """

        # primitive verification of torrents, just make sure we didn't get a text file or something
        if self.providerType == GenericProvider.TORRENT:
            parser = createParser(file_name)
            if parser:
                mime_type = parser._getMimeType()
                try:
                    parser.stream._input.close()
                except:
                    pass
                if mime_type != 'application/x-bittorrent':
                    logger.log(u"Result is not a valid torrent file", logger.WARNING)
                    return False

        return True

    def searchRSS(self):

        self._checkAuth()
        self.cache.updateCache()

        return self.cache.findNeededEpisodes()

    def getQuality(self, item):
        """
        Figures out the quality of the given RSS item node

        item: An elementtree.ElementTree element representing the <item> tag of the RSS feed

        Returns a Quality value obtained from the node's data

        """
        (title, url) = self._get_title_and_url(item)  # @UnusedVariable
        quality = Quality.nameQuality(title)
        return quality

    def _doSearch(self):
        return []

    def _get_season_search_strings(self, show, season, episode=None):
        return []

    def _get_episode_search_strings(self, ep_obj):
        return []

    def _get_title_and_url(self, item):
        """
        Retrieves the title and URL data from the item XML node

        item: An elementtree.ElementTree element representing the <item> tag of the RSS feed

        Returns: A tuple containing two strings representing title and URL respectively
        """
        title = helpers.get_xml_text(item.find('title'))
        if title:
            title = title.replace(' ', '.')

        url = helpers.get_xml_text(item.find('link'))
        if url:
            url = url.replace('&amp;', '&')

        return (title, url)

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

    def findPropers(self, search_date=None):

        results = self.cache.listPropers(search_date)

        return [classes.Proper(x['name'], x['url'], datetime.datetime.fromtimestamp(x['time'])) for x in results]


class NZBProvider(GenericProvider):

    def __init__(self, name):

        GenericProvider.__init__(self, name)

        self.providerType = GenericProvider.NZB


class TorrentProvider(GenericProvider):

    def __init__(self, name):

        GenericProvider.__init__(self, name)

        self.providerType = GenericProvider.TORRENT
