# coding=utf-8
# Author: Daniël Heimans
# URL: http://code.google.com/p/sickbeard
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

import sickbeard
import generic

from sickbeard import scene_exceptions
from sickbeard import logger
from sickbeard import tvcache
from sickbeard.helpers import sanitizeSceneName
from sickbeard.common import Quality
from sickbeard.exceptions import ex, AuthException

from lib import jsonrpclib
import datetime
import time
import socket
import math
import pprint

class BTNProvider(generic.TorrentProvider):
    
    def __init__(self):
        
        generic.TorrentProvider.__init__(self, "BTN")
        
        self.supportsBacklog = True
        self.cache = BTNCache(self)

        self.url = "http://broadcasthe.net"
    
    def isEnabled(self):
        return sickbeard.BTN
    
    def imageName(self):
        return 'btn.png'

    def checkAuthFromData(self, data):
        result = True
        if 'api-error' in data:
            logger.log("Error in sickbeard data retrieval: " + data['api-error'], logger.ERROR)
            result = False

        return result

    def _doSearch(self, search_params, show=None):
        params = {}
        apikey = sickbeard.BTN_API_KEY

        if search_params:
            params.update(search_params)

        search_results = self._api_call(apikey, params)
        
        if not search_results:
            return []

        if 'torrents' in search_results:
            found_torrents = search_results['torrents']
        else:
            found_torrents = {}

        # We got something, we know the API sends max 1000 results at a time. 
        # See if there are more than 1000 results for our query, if not we
        # keep requesting until we've got everything. 
        # max 150 requests per minute so limit at that
        max_pages = 150
        results_per_page = 1000.0

        if 'results' in search_results and search_results['results'] >= results_per_page:
            pages_needed = int(math.ceil(int(search_results['results']) / results_per_page))
            if pages_needed > max_pages:
                pages_needed = max_pages
            
            # +1 because range(1,4) = 1, 2, 3
            for page in range(1,pages_needed+1):
                search_results = self._api_call(apikey, params, results_per_page, page * results_per_page)
                # Note that this these are individual requests and might time out individually. This would result in 'gaps'
                # in the results. There is no way to fix this though.
                if 'torrents' in search_results:
                    found_torrents.update(search_results['torrents'])

        results = []

        for torrentid, torrent_info in found_torrents.iteritems():
            (title, url) = self._get_title_and_url(torrent_info)

            if not title or not url:
                logger.log(u"The BTN provider did not return both a valid title and URL for search parameters: " + str(params) + " but returned " + str(torrent_info), logger.WARNING)
            results.append(torrent_info)

#        Disabled this because it overspammed the debug log a bit too much
#        logger.log(u'BTN provider returning the following results for search parameters: ' + str(params), logger.DEBUG)
#        for result in results:
#            (title, result) = self._get_title_and_url(result)
#            logger.log(title, logger.DEBUG)
            
        return results

    def _api_call(self, apikey, params={}, results_per_page=1000, offset=0):
        server = jsonrpclib.Server('http://api.btnapps.net')
        
        search_results ={} 
        try:
            search_results = server.getTorrentsSearch(apikey, params, int(results_per_page), int(offset))
        except jsonrpclib.jsonrpc.ProtocolError, error:
            logger.log(u"JSON-RPC protocol error while accessing BTN API: " + ex(error), logger.ERROR)
            search_results = {'api-error': ex(error)}
            return search_results
        except socket.timeout:
            logger.log(u"Timeout while accessing BTN API", logger.WARNING)
        except socket.error, error:
            # Note that sometimes timeouts are thrown as socket errors
            logger.log(u"Socket error while accessing BTN API: " + error[1], logger.ERROR)
        except Exception, error:
            errorstring = str(error)
            if(errorstring.startswith('<') and errorstring.endswith('>')):
                errorstring = errorstring[1:-1]
            logger.log(u"Unknown error while accessing BTN API: " + errorstring, logger.ERROR)

        return search_results

    def _get_title_and_url(self, search_result):
        
        # The BTN API gives a lot of information in response, 
        # however Sick Beard is built mostly around Scene or 
        # release names, which is why we are using them here. 
        if 'ReleaseName' in search_result and search_result['ReleaseName']:
            title = search_result['ReleaseName']
        else:
            # If we don't have a release name we need to get creative
            title = u''
            if 'Series' in search_result:
                title += search_result['Series'] 
            if 'GroupName' in search_result:
                title += '.' + search_result['GroupName'] if title else search_result['GroupName']
            if 'Resolution' in search_result:
                title += '.' + search_result['Resolution'] if title else search_result['Resolution']
            if 'Source' in search_result:
                title += '.' + search_result['Source'] if title else search_result['Source']
            if 'Codec' in search_result:
                title += '.' + search_result['Codec'] if title else search_result['Codec']
        
        if 'DownloadURL' in search_result:
            url = search_result['DownloadURL']
        else:
            url = None

        return (title, url)

    def _get_season_search_strings(self, show, season=None):
        if not show:
            return [{}]

        search_params = []

        name_exceptions = scene_exceptions.get_scene_exceptions(show.tvdbid) + [show.name]
        for name in name_exceptions:

            current_params = {}

            if show.tvdbid:
                current_params['tvdb'] = show.tvdbid
            elif show.tvrid:
                current_params['tvrage'] = show.tvrid
            else:
                # Search by name if we don't have tvdb or tvrage id
                current_params['series'] = sanitizeSceneName(name)

            if season != None:
                whole_season_params = current_params.copy()
                partial_season_params = current_params.copy()
                # Search for entire seasons: no need to do special things for air by date shows
                whole_season_params['category'] = 'Season'
                whole_season_params['name'] = 'Season ' + str(season)

                search_params.append(whole_season_params)

                # Search for episodes in the season
                partial_season_params['category'] = 'Episode'
                
                if show.air_by_date:
                    # Search for the year of the air by date show
                    partial_season_params['name'] = str(season.split('-')[0])
                else:
                    # Search for any result which has Sxx in the name
                    partial_season_params['name'] = 'S%02d' % int(season)

                search_params.append(partial_season_params)

            else:
                search_params.append(current_params)
        
        return search_params

    def _get_episode_search_strings(self, ep_obj):
        
        if not ep_obj:
            return [{}]

        search_params = {'category':'Episode'}

        if ep_obj.show.tvdbid:
            search_params['tvdb'] = ep_obj.show.tvdbid
        elif ep_obj.show.tvrid:
            search_params['tvrage'] = ep_obj.show.rid
        else:
            search_params['series'] = sanitizeSceneName(ep_obj.show_name)

        if ep_obj.show.air_by_date:
            date_str = str(ep_obj.airdate)
            
            # BTN uses dots in dates, we just search for the date since that 
            # combined with the series identifier should result in just one episode
            search_params['name'] = date_str.replace('-','.')

        else:
            # Do a general name search for the episode, formatted like SXXEYY
            search_params['name'] = "S%02dE%02d" % (ep_obj.season,ep_obj.episode)

        to_return = [search_params]

        # only do scene exceptions if we are searching by name
        if 'series' in search_params:
            
            # add new query string for every exception
            name_exceptions = scene_exceptions.get_scene_exceptions(ep_obj.show.tvdbid)
            for cur_exception in name_exceptions:
                
                # don't add duplicates
                if cur_exception == ep_obj.show.name:
                    continue

                # copy all other parameters before setting the show name for this exception
                cur_return = search_params.copy()
                cur_return['series'] = sanitizeSceneName(cur_exception)
                to_return.append(cur_return)

        return to_return

    def getQuality(self, item):
        quality = None 
        (title,url) = self._get_title_and_url(item)
        quality = Quality.nameQuality(title)

        return quality

    def _doGeneralSearch(self, search_string):
        # 'search' looks as broad is it can find. Can contain episode overview and title for example, 
        # use with caution!
        return self._doSearch({'search': search_string})

class BTNCache(tvcache.TVCache):
    
    def __init__(self, provider):
        tvcache.TVCache.__init__(self, provider)
        
        # At least 15 minutes between queries
        self.minTime = 15

    def updateCache(self):
        if not self.shouldUpdate():
            return
        
        data = self._getRSSData()

        # As long as we got something from the provider we count it as an update 
        if data:
            self.setLastUpdate()
        else:
            return []
        
        logger.log(u"Clearing "+self.provider.name+" cache and updating with new information")
        self._clearCache()

        if not self._checkAuth(data):
            raise AuthException("Your authentication info for "+self.provider.name+" is incorrect, check your config")

        # By now we know we've got data and no auth errors, all we need to do is put it in the database
        for item in data:
            self._parseItem(item)

    def _getRSSData(self):
        # Get the torrents uploaded since last check.
        seconds_since_last_update = math.ceil(time.time() - time.mktime(self._getLastUpdate().timetuple()))

        
        # default to 15 minutes
        if seconds_since_last_update < 15*60:
            seconds_since_last_update = 15*60

        # Set maximum to 24 hours of "RSS" data search, older things will need to be done through backlog
        if seconds_since_last_update > 24*60*60:
            logger.log(u"The last known successful \"RSS\" update on the BTN API was more than 24 hours ago (%i hours to be precise), only trying to fetch the last 24 hours!" %(int(seconds_since_last_update)//(60*60)), logger.WARNING)
            seconds_since_last_update = 24*60*60

        age_string = "<=%i" % seconds_since_last_update  
        search_params={'age': age_string}

        data = self.provider._doSearch(search_params)
       
        return data

    def _parseItem(self, item):
        (title, url) = self.provider._get_title_and_url(item)
        
        if not title or not url:
            logger.log(u"The result returned from the BTN regular search is incomplete, this result is unusable", logger.ERROR)
            return
        logger.log(u"Adding item from regular BTN search to cache: " + title, logger.DEBUG)

        self._addCacheEntry(title, url)

    def _checkAuth(self, data):
        return self.provider.checkAuthFromData(data)

provider = BTNProvider()