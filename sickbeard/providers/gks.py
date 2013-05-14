# Author: Julien Goret <jgoret@gmail.com>
# URL: https://github.com/Kyah/Sick-Beard
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

from bs4 import BeautifulSoup
from sickbeard import classes, show_name_helpers, logger
from sickbeard.common import Quality
from sickbeard import helpers
from sickbeard import logger
from sickbeard import tvcache

import generic
import cookielib
import sickbeard
import urllib
import urllib2


class GksProvider(generic.TorrentProvider):

    def __init__(self): 
        generic.TorrentProvider.__init__(self, "gks")
        self.supportsBacklog = True
        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
        self.url = "https://gks.gs/"
    
    def isEnabled(self):
        return sickbeard.GKS

    def imageName(self):
        return 'gks.png'
    
    def getSearchParams(self, searchString, audio_lang):
        results = []
        if audio_lang == "en":
            results.append( urllib.urlencode( {'q': searchString, 'category' : 22, 'ak' : sickbeard.GKS_KEY} ) + "&order=desc&sort=normal&exact" )
        elif audio_lang == "fr":
            results.append( urllib.urlencode( {'q': searchString, 'category' : 12, 'ak' : sickbeard.GKS_KEY} ) + "&order=desc&sort=normal&exact" )
            results.append( urllib.urlencode( {'q': searchString, 'category' : 14, 'ak' : sickbeard.GKS_KEY} ) + "&order=desc&sort=normal&exact" )
        else:
            results.append( urllib.urlencode( {'q': searchString, 'ak' : sickbeard.GKS_KEY} ) + "&order=desc&sort=normal&exact" )
        return results

    def _get_season_search_strings(self, show, season):

        showNames = show_name_helpers.allPossibleShowNames(show)
        results = []
        for showName in showNames:
            for result in self.getSearchParams(showName + "+S%02d" % season, show.audio_lang) :
                results.append(result)
            for result in self.getSearchParams(showName + "+saison+%02d" % season, show.audio_lang):
                results.append(result)
        return results

    def _get_episode_search_strings(self, ep_obj):

        showNames = show_name_helpers.allPossibleShowNames(ep_obj.show)
        results = []
        for showName in showNames:
            for result in self.getSearchParams( "%s S%02dE%02d" % ( showName, ep_obj.season, ep_obj.episode), ep_obj.show.audio_lang) :
                results.append(result)
        return results
        
    def _doSearch(self, searchString, show=None, season=None):
        results = []
        searchUrl = self.url+'rdirect.php?type=search&'+searchString
        logger.log(u"Search URL: " + searchUrl, logger.DEBUG)
		
        data = self.opener.open( searchUrl )
        soup = BeautifulSoup(data)
        resultsTable = soup.find("channel")
        if resultsTable:
            items = resultsTable.findAll("item")
            for item in items:
                title = item.title.string
                if "vostfr" in title.lower() or "aucun resultat" in title.lower():
                    continue
                else :
                    downloadURL = item.link.string
                    quality = Quality.nameQuality(title)
                    if show:
                        results.append( GksSearchResult( self.opener, title, downloadURL, quality, str(show.audio_lang) ) )
                    else:
                        results.append( GksSearchResult( self.opener, title, downloadURL, quality ) )
        else :
            logger.log(u"Please check your GKS.GS provider configuration", logger.ERROR)
        return results
    
    def getResult(self, episodes):
        """
        Returns a result of the correct type for this provider
        """
        result = classes.TorrentDataSearchResult(episodes)
        result.provider = self
        return result
    
    def _get_title_and_url(self, item):
        return (item.title, item.url)
        
class GksSearchResult:
    
    def __init__(self, opener, title, url, quality, audio_langs=None):
        self.opener = opener
        self.title = title
        self.url = url
        self.quality = quality
        self.audio_langs=[audio_langs]

    def getNZB(self):
        return self.opener.open( self.url , 'wb').read()
        
    def getQuality(self):
        return self.quality


provider = GksProvider()