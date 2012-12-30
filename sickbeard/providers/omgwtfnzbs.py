# Author: James Cox <james@imaj.es>
# Based on nzbsrus.py by Nic Wolfe <nic@wolfeden.ca>
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

import os
import re
import sys
import time
import urllib

from xml.dom.minidom import parseString
from datetime import datetime, timedelta

import sickbeard
import generic

import sickbeard.encodingKludge as ek
from sickbeard import classes, logger, helpers, exceptions, show_name_helpers
from sickbeard import tvcache
from sickbeard.common import Quality
from sickbeard.exceptions import ex
from lib.dateutil.parser import parse as parseDate

class OMGWTFNZBSProvider(generic.NZBProvider):

  def __init__(self):
    generic.NZBProvider.__init__(self, "omgwtfnzbs")

    self.supportsBacklog = True
    self.cache = OmgWtfNzbsCache(self)

    self.url = 'http://rss.omgwtfnzbs.org/'

  def isEnabled(self):
    return sickbeard.OMGWTFNZBS

  def _checkAuth(self):
    if sickbeard.OMGWTFNZBS_UID in (None, "") or sickbeard.OMGWTFNZBS_HASH in (None, ""):
      raise exceptions.AuthException("omgwtfnzbs authentication details are empty, check your config")

  def _get_season_search_strings(self, show, season):
    sceneSearchStrings = set(show_name_helpers.makeSceneSeasonSearchString(show, season, "omgwtfnzbs"))

    # search for all show names and episode numbers like ("a","b","c") in a single search
    return [' '.join(sceneSearchStrings)]

  def _get_episode_search_strings(self, ep_obj):
    sceneSearchStrings = set(show_name_helpers.makeSceneSearchString(ep_obj))

    # search for all show names and episode numbers like ("a","b","c") in a single search
    return ['("' + '","'.join(sceneSearchStrings) + '")']

  def _doSearch(self, curString, quotes=False, show=None):
    term =  re.sub('[\.\-\"]', ' ', curString).encode('utf-8')
    if quotes:
      term = "\""+term+"\""

    params = {"search": term,
               'catid': '19,20,21',
                'user': sickbeard.OMGWTFNZBS_UID,
                 'api': sickbeard.OMGWTFNZBS_HASH,
                 "eng": 1}

    searchURL = "http://api.omgwtfnzbs.org/xml/?" + urllib.urlencode(params)

    logger.log(u"Sleeping 10 seconds to respect omgwtfnzb's rules")
    time.sleep(10)

    logger.log(u"Search string: " + searchURL, logger.DEBUG)
    searchResult = self.getURL(searchURL)

    if not searchResult:
      return []

    try:
      parsedXML = parseString(searchResult)
      items = parsedXML.getElementsByTagName('post')
    except Exception, e:
      logger.log(u"Error trying to load omgwtfnzbs RSS feed: " + ex(e), logger.ERROR)
      return []

    results = []

    for curItem in items:
      (title, url) = self._get_title_and_url(curItem)

      if title == 'Error: No Results Found For Your Search':
        continue

      if not title or not url:
        logger.log(u"The XML returned from the omgwtfnzbs RSS feed is incomplete, this result is unusable", logger.ERROR)
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

  def _get_title_and_url(self, item):
    """
    Retrieves the title and URL data from the item XML node

    item: An xml.dom.minidom.Node representing the <item> tag of the RSS feed

    Returns: A tuple containing two strings representing title and URL respectively
    """
    title = helpers.get_xml_text(item.getElementsByTagName('release')[0])
    try:
      url = helpers.get_xml_text(item.getElementsByTagName('getnzb')[0])
      if url:
        url = url.replace('&amp;','&')
    except IndexError:
      url = None

    return (title, url)


class OmgWtfNzbsCache(tvcache.TVCache):

  def __init__(self, provider):
    tvcache.TVCache.__init__(self, provider)
    # only poll omgwtfnzbs every 15 minutes max
    self.minTime = 15


  def _getRSSData(self):
    url = self.provider.url + 'rss-download.php?'
    urlArgs = { 'catid': '19,20,21', "eng": 1, 
                'user': sickbeard.OMGWTFNZBS_UID, 'api': sickbeard.OMGWTFNZBS_HASH}

    logger.log(u"Sleeping 10 seconds to respect omgwtfnzb's rules")
    time.sleep(10)

    url += urllib.urlencode(urlArgs)

    logger.log(u"omgwtfnzbs cache update URL: "+ url, logger.DEBUG)

    data = self.provider.getURL(url)

    return data

  def _checkAuth(self, data):
    return data != 'Invalid Link'

provider = OMGWTFNZBSProvider()

# vim: set et ts=2 sw=2 tw=0 ft=python :
