# Author: Jordon Smith <smith@jordon.me.uk>
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard. If not, see <http://www.gnu.org/licenses/>.

import urllib
import generic
import sickbeard

from sickbeard import tvcache
from sickbeard import classes
from sickbeard import logger
from sickbeard import exceptions
from sickbeard import show_name_helpers
from datetime import datetime

try:
    import json
except ImportError:
    from lib import simplejson as json


class OmgwtfnzbsProvider(generic.NZBProvider):

    def __init__(self):
        generic.NZBProvider.__init__(self, "omgwtfnzbs")
        self.cache = OmgwtfnzbsCache(self)
        self.url = 'https://api.omgwtfnzbs.org/'
        self.supportsBacklog = True

    def isEnabled(self):
        return sickbeard.OMGWTFNZBS

    def _checkAuth(self):
        if not sickbeard.OMGWTFNZBS_UID or not sickbeard.OMGWTFNZBS_KEY:
            raise exceptions.AuthException("omgwtfnzbs authentication details are empty, check your config")
        
    def _get_season_search_strings(self, show, season):
        return [x for x in show_name_helpers.makeSceneSeasonSearchString(show, season)]

    def _get_episode_search_strings(self, ep_obj):
        return [x for x in show_name_helpers.makeSceneSearchString(ep_obj)]

    def _get_title_and_url(self, item):
        return (item['release'], item['getnzb'])

    def _doSearch(self, search, show=None, retention=0):
        params = {'user': sickbeard.OMGWTFNZBS_UID,
                  'api': sickbeard.OMGWTFNZBS_KEY,
                  'eng': 1,
                  'catid': '19,20', # SD,HD
                  'retention': sickbeard.USENET_RETENTION,
                  'search': search}
               
        if retention or not params['retention']:
            params['retention'] = retention
            
        url = self.url + 'json?' + urllib.urlencode(params)
        logger.log(u"omgwtfnzbs search url: " + url, logger.DEBUG)
        data = self.getURL(url)
        try:
            items = json.loads(data)
        except ValueError:
            logger.log(u"Error trying to decode omgwtfnzbs json response", logger.ERROR)
            return []
            
        results = []
        if 'notice' in items:
            if 'api information is incorrect' in items.get('notice'):
                raise exceptions.AuthException("omgwtfnzbs authentication details are incorrect")
            else:
                logger.log(u"omgwtfnzbs notice: " + items.get('notice'), logger.DEBUG)
        else:
            for item in items:
                if 'release' in item and 'getnzb' in item:
                    results.append(item)
        return results

    def findPropers(self, date=None):
        search_terms = ['.PROPER.', '.REPACK.']
        results = []
        
        for term in search_terms:
            for item in self._doSearch(term, retention=4):
                if 'usenetage' in item:
                    name, url = self._get_title_and_url(item)
                    results.append(classes.Proper(name, url, datetime.fromtimestamp(item['usenetage'])))
        return results
        

class OmgwtfnzbsCache(tvcache.TVCache):

    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        self.minTime = 20

    def _getRSSData(self):
        params = {'user': sickbeard.OMGWTFNZBS_UID,
                  'api': sickbeard.OMGWTFNZBS_KEY,
                  'eng': 1,
                  'catid': '19,20'} # SD,HD

        url = 'http://rss.omgwtfnzbs.org/rss-download.php?' + urllib.urlencode(params)
        logger.log(u"omgwtfnzbs cache update URL: " + url, logger.DEBUG)
        return self.provider.getURL(url)

provider = OmgwtfnzbsProvider()

