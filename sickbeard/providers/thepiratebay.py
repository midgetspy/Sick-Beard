# Author: Mr_Orange <mr_orange@hotmail.it>
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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import re
import urllib, urllib2
import sys
import os

import sickbeard
import generic
from sickbeard.common import Quality
from sickbeard.name_parser.parser import NameParser, InvalidNameException
from sickbeard import logger
from sickbeard import tvcache
from sickbeard import helpers
from sickbeard import show_name_helpers
from sickbeard.common import Overview 
from sickbeard.exceptions import ex
from sickbeard import encodingKludge as ek

proxy_dict = {
              'Getprivate.eu (NL)' : 'http://getprivate.eu/',
              '15bb51.info (US)' : 'http://15bb51.info/',
              'Hideme.nl (NL)' : 'http://hideme.nl/',
              'Rapidproxy.us (GB)' : 'http://rapidproxy.us/',
              'Proxite.eu (DE)' :'http://proxite.eu/',
              'Shieldmagic.com (GB)' : 'http://www.shieldmagic.com/',
              'Webproxy.cz (CZ)' : 'http://webproxy.cz/',
              'Freeproxy.cz (CZ)' : 'http://www.freeproxy.cz/',
             }

class ThePirateBayProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "ThePirateBay")
        
        self.supportsBacklog = True

        self.cache = ThePirateBayCache(self)
        
        self.proxy = ThePirateBayWebproxy() 
        
        self.url = 'http://thepiratebay.se/'

        self.searchurl = self.url+'search/%s/0/7/200'  # order by seed       

        self.re_title_url =  '/torrent/(?P<id>\d+)/(?P<title>.*?)//1".+?(?P<url>magnet.*?)//1".+?(?P<seeders>\d+)</td>.+?(?P<leechers>\d+)</td>'

    def isEnabled(self):
        return sickbeard.THEPIRATEBAY
        
    def imageName(self):
        return 'thepiratebay.png'
    
    def getQuality(self, item):
        
        quality = Quality.nameQuality(item[0])
        return quality    

    def _reverseQuality(self,quality):

        quality_string = ''

        if quality == Quality.SDTV:
            quality_string = 'HDTV x264'
        if quality == Quality.SDDVD:
            quality_string = 'DVDRIP'    
        elif quality == Quality.HDTV:    
            quality_string = '720p HDTV x264'
        elif quality == Quality.FULLHDTV:
            quality_string = '1080p HDTV x264'        
        elif quality == Quality.RAWHDTV:
            quality_string = '1080i HDTV mpeg2'
        elif quality == Quality.HDWEBDL:
            quality_string = '720p WEB-DL'
        elif quality == Quality.FULLHDWEBDL:
            quality_string = '1080p WEB-DL'            
        elif quality == Quality.HDBLURAY:
            quality_string = '720p Bluray x264'
        elif quality == Quality.FULLHDBLURAY:
            quality_string = '1080p Bluray x264'  
        
        return quality_string

    def _find_season_quality(self,title,torrent_id):
        """ Return the modified title of a Season Torrent with the quality found inspecting torrent file list """

        mediaExtensions = ['avi', 'mkv', 'wmv', 'divx',
                           'vob', 'dvr-ms', 'wtv', 'ts'
                           'ogv', 'rar', 'zip'] 
        
        quality = Quality.UNKNOWN        
        
        fileName = None
        
        fileURL = self.proxy._buildURL(self.url+'ajax_details_filelist.php?id='+str(torrent_id))
      
        data = self.getURL(fileURL)
        
        if not data:
            return None
        
        filesList = re.findall('<td.+>(.*?)</td>',data) 
        
        if not filesList: 
            logger.log(u"Unable to get the torrent file list for "+title, logger.ERROR)
            
        for fileName in filter(lambda x: x.rpartition(".")[2].lower() in mediaExtensions, filesList):
            quality = Quality.nameQuality(os.path.basename(fileName))
            if quality != Quality.UNKNOWN: break

        if fileName!=None and quality == Quality.UNKNOWN:
            quality = Quality.assumeQuality(os.path.basename(fileName))            

        if quality == Quality.UNKNOWN:
            logger.log(u"No Season quality for "+title, logger.DEBUG)
            return None

        try:
            myParser = NameParser()
            parse_result = myParser.parse(fileName)
        except InvalidNameException:
            return None
        
        logger.log(u"Season quality for "+title+" is "+Quality.qualityStrings[quality], logger.DEBUG)
        
        if parse_result.series_name and parse_result.season_number: 
            title = parse_result.series_name+' S%02d' % int(parse_result.season_number)+' '+self._reverseQuality(quality)
        
        return title

    def _get_season_search_strings(self, show, season=None):

        search_string = {'Episode': []}
    
        if not show:
            return []

        seasonEp = show.getAllEpisodes(season)

        wantedEp = [x for x in seasonEp if show.getOverview(x.status) in (Overview.WANTED, Overview.QUAL)]          

        #If Every episode in Season is a wanted Episode then search for Season first
        if wantedEp == seasonEp and not show.air_by_date:
            search_string = {'Season': [], 'Episode': []}
            for show_name in set(show_name_helpers.allPossibleShowNames(show)):
                ep_string = show_name +' S%02d' % int(season) #1) ShowName SXX   
                search_string['Season'].append(ep_string)
                      
                ep_string = show_name+' Season '+str(season)+' -Ep*' #2) ShowName Season X  
                search_string['Season'].append(ep_string)

        #Building the search string with the episodes we need         
        for ep_obj in wantedEp:
            search_string['Episode'] += self._get_episode_search_strings(ep_obj)[0]['Episode']
        
        #If no Episode is needed then return an empty list
        if not search_string['Episode']:
            return []
        
        return [search_string]

    def _get_episode_search_strings(self, ep_obj):
       
        search_string = {'Episode': []}
       
        if not ep_obj:
            return []
                
        if ep_obj.show.air_by_date:
            for show_name in set(show_name_helpers.allPossibleShowNames(ep_obj.show)):
                ep_string = show_name_helpers.sanitizeSceneName(show_name) +' '+ str(ep_obj.airdate)
                search_string['Episode'].append(ep_string)
        else:
            for show_name in set(show_name_helpers.allPossibleShowNames(ep_obj.show)):
                ep_string = show_name_helpers.sanitizeSceneName(show_name) +' '+ \
                sickbeard.config.naming_ep_type[2] % {'seasonnumber': ep_obj.season, 'episodenumber': ep_obj.episode} +'|'+\
                sickbeard.config.naming_ep_type[0] % {'seasonnumber': ep_obj.season, 'episodenumber': ep_obj.episode} +'|'+\
                sickbeard.config.naming_ep_type[3] % {'seasonnumber': ep_obj.season, 'episodenumber': ep_obj.episode} \

                search_string['Episode'].append(ep_string)
    
        return [search_string]

    def _doSearch(self, search_params, show=None):
    
        results = []
        items = {'Season': [], 'Episode': []}

        for mode in search_params.keys():
            for search_string in search_params[mode]:

                searchURL = self.proxy._buildURL(self.searchurl %(urllib.quote(search_string)))    
        
                logger.log(u"Search string: " + searchURL, logger.DEBUG)
        
                data = self.getURL(searchURL)
                if not data:
                    return []
        
                re_title_url = self.proxy._buildRE(self.re_title_url)
                
                #Extracting torrent information from data returned by searchURL                   
                match = re.compile(re_title_url, re.DOTALL ).finditer(urllib.unquote(data))
                for torrent in match:

                    title = torrent.group('title').replace('_','.')#Do not know why but SickBeard skip release with '_' in name
                    url = torrent.group('url')
                    id = int(torrent.group('id'))
                    seeders = int(torrent.group('seeders'))
                    leechers = int(torrent.group('leechers'))

                    #Filter unseeded torrent
                    if seeders == 0 or not title:
                        continue 
                   
                    #Accept Torrent only from Good People for every Episode Search
                    if sickbeard.THEPIRATEBAY_TRUSTED and re.search('(VIP|Trusted|Helper)',torrent.group(0))== None:
                        logger.log(u"ThePirateBay Provider found result "+torrent.group('title')+" but that doesn't seem like a trusted result so I'm ignoring it",logger.DEBUG)
                        continue

                    #Try to find the real Quality for full season torrent analyzing files in torrent 
                    if mode == 'Season' and Quality.nameQuality(title) == Quality.UNKNOWN:     
                        if not self._find_season_quality(title,id): continue
                        
                    item = title, url, id, seeders, leechers
                    
                    items[mode].append(item)    

            #For each search mode sort all the items by seeders
            items[mode].sort(key=lambda tup: tup[3], reverse=True)        

            results += items[mode]  
                
        return results

    def _get_title_and_url(self, item):
        
        title, url, id, seeders, leechers = item
        
        if url:
            url = url.replace('&amp;','&')

        return (title, url)

    def getURL(self, url, headers=None):

        if not headers:
            headers = []

        # Glype Proxies does not support Direct Linking.
        # We have to fake a search on the proxy site to get data
        if self.proxy.isEnabled():
            headers.append(('Referer', self.proxy.getProxyURL()))
            
        result = None

        try:
            result = helpers.getURL(url, headers)
        except (urllib2.HTTPError, IOError), e:
            logger.log(u"Error loading "+self.name+" URL: " + str(sys.exc_info()) + " - " + ex(e), logger.ERROR)
            return None

        return result

    def downloadResult(self, result):
        """
        Save the result to disk.
        """
        
        #Hack for rtorrent user (it will not work for other torrent client)
        if sickbeard.TORRENT_METHOD == "blackhole" and result.url.startswith('magnet'): 
            magnetFileName = ek.ek(os.path.join, sickbeard.TORRENT_DIR, helpers.sanitizeFileName(result.name) + '.' + self.providerType)
            magnetFileContent = 'd10:magnet-uri' + `len(result.url)` + ':' + result.url + 'e'

            try:
                fileOut = open(magnetFileName, 'wb')
                fileOut.write(magnetFileContent)
                fileOut.close()
                helpers.chmodAsParent(magnetFileName)
            except IOError, e:
                logger.log("Unable to save the file: "+ex(e), logger.ERROR)
                return False
            logger.log(u"Saved magnet link to "+magnetFileName+" ", logger.MESSAGE)
            return True

class ThePirateBayCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll ThePirateBay every 10 minutes max
        self.minTime = 20

    def updateCache(self):

        re_title_url = self.provider.proxy._buildRE(self.provider.re_title_url)
                
        if not self.shouldUpdate():
            return

        data = self._getData()

        # as long as the http request worked we count this as an update
        if data:
            self.setLastUpdate()
        else:
            return []

        # now that we've loaded the current RSS feed lets delete the old cache
        logger.log(u"Clearing "+self.provider.name+" cache and updating with new information")
        self._clearCache()

        match = re.compile(re_title_url, re.DOTALL).finditer(urllib.unquote(data))
        if not match:
            logger.log(u"The Data returned from the ThePirateBay is incomplete, this result is unusable", logger.ERROR)
            return []
                
        for torrent in match:

            title = torrent.group('title').replace('_','.')#Do not know why but SickBeard skip release with '_' in name
            url = torrent.group('url')
           
            if not title or not url:
                continue
           
            #accept torrent only from Trusted people
            if sickbeard.THEPIRATEBAY_TRUSTED and re.search('(VIP|Trusted|Helper)',torrent.group(0))== None:
                logger.log(u"ThePirateBay Provider found result "+torrent.group('title')+" but that doesn't seem like a trusted result so I'm ignoring it",logger.DEBUG)
                continue
           
            item = (title,url)

            self._parseItem(item)

    def _getData(self):
       
        #url for the last 50 tv-show
        url = self.provider.proxy._buildURL(self.provider.url+'tv/latest/')

        logger.log(u"ThePirateBay cache update URL: "+ url, logger.DEBUG)

        data = self.provider.getURL(url)

        return data

    def _parseItem(self, item):

        (title, url) = item

        if not title or not url:
            return

        logger.log(u"Adding item to cache: "+title, logger.DEBUG)

        self._addCacheEntry(title, url)

class ThePirateBayWebproxy:
    
    def __init__(self):
        self.Type   = 'GlypeProxy'
        self.param  = 'browse.php?u='
        self.option = '&b=32'
        
    def isEnabled(self):
        """ Return True if we Choose to call TPB via Proxy """ 
        return sickbeard.THEPIRATEBAY_PROXY
    
    def getProxyURL(self):
        """ Return the Proxy URL Choosen via Provider Setting """
        return str(sickbeard.THEPIRATEBAY_PROXY_URL)
    
    def _buildURL(self,url):
        """ Return the Proxyfied URL of the page """ 
        if self.isEnabled():
            url = self.getProxyURL() + self.param + url + self.option
        
        return url      

    def _buildRE(self,regx):
        """ Return the Proxyfied RE string """
        if self.isEnabled():
            regx = re.sub('//1',self.option,regx).replace('&','&amp;')
        else:
            regx = re.sub('//1','',regx)  

        return regx    
    
provider = ThePirateBayProvider()