# -*- coding: latin-1 -*-
# Author: Guillaume Serre <guillaume.serre@gmail.com>
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

from bs4 import BeautifulSoup
from sickbeard import classes, show_name_helpers, logger
from sickbeard.common import Quality
import generic
import cookielib
import sickbeard
import urllib
import urllib2


class T411Provider(generic.TorrentProvider):

    def __init__(self):
        
        generic.TorrentProvider.__init__(self, "T411")

        self.supportsBacklog = True
        
        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
        
        self.url = "http://www.t411.me"
        
        self.login_done = False
        
    def isEnabled(self):
        return sickbeard.T411
    
    def getSearchParams(self, searchString, audio_lang, subcat):
        if audio_lang == "en":
            return urllib.urlencode( {'search': searchString, 'cat' : 210, 'submit' : 'Recherche', 'subcat': subcat } ) + "&term%5B17%5D%5B%5D=540&term%5B17%5D%5B%5D=721"
        elif audio_lang == "fr":
            return urllib.urlencode( {'search': searchString, 'cat' : 210, 'submit' : 'Recherche', 'subcat': subcat } ) + "&term%5B17%5D%5B%5D=541&term%5B17%5D%5B%5D=542"
        else:
            return urllib.urlencode( {'search': searchString, 'cat' : 210, 'submit' : 'Recherche', 'subcat': subcat } )

    def _get_season_search_strings(self, show, season):

        showNames = show_name_helpers.allPossibleShowNames(show)
        results = []
        for showName in showNames:
            results.append( self.getSearchParams(showName + " S%02d" % season, show.audio_lang, 433 ))
            results.append( self.getSearchParams(showName + " S%02d" % season, show.audio_lang, 637 ))
            results.append( self.getSearchParams(showName + " S%02d" % season, show.audio_lang, 634 ))
            results.append( self.getSearchParams(showName + " saison %02d" % season, show.audio_lang, 433 ))
            results.append( self.getSearchParams(showName + " saison %02d" % season, show.audio_lang, 637 ))
            results.append( self.getSearchParams(showName + " saison %02d" % season, show.audio_lang, 634 ))
        return results

    def _get_episode_search_strings(self, ep_obj):

        showNames = show_name_helpers.allPossibleShowNames(ep_obj.show)
        results = []
        for showName in showNames:
            results.append( self.getSearchParams( "%s S%02dE%02d" % ( showName, ep_obj.season, ep_obj.episode), ep_obj.show.audio_lang, 433 ))
            results.append( self.getSearchParams( "%s %dx%d" % ( showName, ep_obj.season, ep_obj.episode ), ep_obj.show.audio_lang , 433 ))
            results.append( self.getSearchParams( "%s %dx%02d" % ( showName, ep_obj.season, ep_obj.episode ), ep_obj.show.audio_lang, 433 ))
            results.append( self.getSearchParams( "%s S%02dE%02d" % ( showName, ep_obj.season, ep_obj.episode), ep_obj.show.audio_lang, 637 ))
            results.append( self.getSearchParams( "%s %dx%d" % ( showName, ep_obj.season, ep_obj.episode ), ep_obj.show.audio_lang, 637 ))
            results.append( self.getSearchParams( "%s %dx%02d" % ( showName, ep_obj.season, ep_obj.episode ), ep_obj.show.audio_lang, 637 ))
            results.append( self.getSearchParams( "%s S%02dE%02d" % ( showName, ep_obj.season, ep_obj.episode), ep_obj.show.audio_lang, 634))
            results.append( self.getSearchParams( "%s %dx%d" % ( showName, ep_obj.season, ep_obj.episode ), ep_obj.show.audio_lang, 634 ))
            results.append( self.getSearchParams( "%s %dx%02d" % ( showName, ep_obj.season, ep_obj.episode ), ep_obj.show.audio_lang, 634 ))
        return results
    
    def _get_title_and_url(self, item):
        return (item.title, item.url)
    
    def getQuality(self, item):
        return item.getQuality()
    
    def _doLogin(self, login, password):

        data = urllib.urlencode({'login': login, 'password' : password, 'submit' : 'Connexion', 'remember': 1, 'url' : '/'})
        self.opener.open(self.url + '/users/login', data)
    
    def _doSearch(self, searchString, show=None, season=None):
        
        if not self.login_done:
            self._doLogin( sickbeard.T411_USERNAME, sickbeard.T411_PASSWORD )

        results = []
        searchUrl = self.url + '/torrents/search/?' + searchString
        logger.log(u"Search string: " + searchUrl, logger.DEBUG)
        
        r = self.opener.open( searchUrl )
        soup = BeautifulSoup( r )
        resultsTable = soup.find("table", { "class" : "results" })
        if resultsTable:
            rows = resultsTable.find("tbody").findAll("tr")
    
            for row in rows:
                link = row.find("a", title=True)
                title = link['title']
                
                pageURL = link['href']
                if pageURL.startswith("//"):
                    pageURL = "http:" + pageURL
                
                torrentPage = self.opener.open( pageURL )
                torrentSoup = BeautifulSoup( torrentPage )
               
                downloadTorrentLink = torrentSoup.find("a", text=u"Télécharger")
                if downloadTorrentLink:
                    
                    downloadURL = self.url + downloadTorrentLink['href']
                    
                    quality = Quality.nameQuality( title )

                    if show:
                        results.append( T411SearchResult( self.opener, link['title'], downloadURL, quality, str(show.audio_lang) ) )
                    else:
                        results.append( T411SearchResult( self.opener, link['title'], downloadURL, quality ) )

        return results
    
    def getResult(self, episodes):
        """
        Returns a result of the correct type for this provider
        """
        result = classes.TorrentDataSearchResult(episodes)
        result.provider = self

        return result    
    
class T411SearchResult:
    
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

provider = T411Provider()
