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
from sickbeard import logger, classes, show_name_helpers
from sickbeard.common import Quality
from sickbeard.exceptions import ex
import cookielib
import generic
import sickbeard
import urllib
import urllib2


class CpasbienProvider(generic.TorrentProvider):

    def __init__(self):
        
        generic.TorrentProvider.__init__(self, "Cpasbien")

        self.supportsBacklog = True
        
        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
        
        self.url = "http://www.cpasbien.me"
        
        
    def isEnabled(self):
        return sickbeard.Cpasbien

    def _get_season_search_strings(self, show, season):

        showNames = show_name_helpers.allPossibleShowNames(show)
        result = []
        for showName in showNames:
            result.append( showName + " S%02d" % season )
        return result

    def _get_episode_search_strings(self, ep_obj):

        strings = []

        showNames = show_name_helpers.allPossibleShowNames(ep_obj.show)
        for showName in showNames:
            strings.append("%s S%02dE%02d" % ( showName, ep_obj.season, ep_obj.episode) )
            strings.append("%s %dx%d" % ( showName, ep_obj.season, ep_obj.episode ) )

        return strings
    
    def _get_title_and_url(self, item):
        return (item.title, item.url)
    
    def getQuality(self, item):
        return item.getQuality()
        
    def _doSearch(self, searchString, show=None, season=None):

        results = []
        searchUrl = self.url + '/recherche/'

        data = urllib.urlencode({'champ_recherche': searchString})

        try:
            soup = BeautifulSoup( urllib2.urlopen(searchUrl, data) )
        except Exception, e:
            logger.log(u"Error trying to load cpasbien response: "+ex(e), logger.ERROR)
            return []

        rows = soup.findAll(attrs = {'class' : ["color0", "color1"]})

        for row in rows:
            link = row.find("a", title=True)
            title = str(link.text).lower().strip()  
            pageURL = link['href']

            if "vostfr" in title and (not show.subtitles) and show.audio_lang == "fr":
                continue

            torrentPage = self.opener.open( pageURL )
            torrentSoup = BeautifulSoup( torrentPage )

            downloadTorrentLink = torrentSoup.find("a", title=u"Cliquer ici pour télécharger ce torrent")
            if downloadTorrentLink:
                
                downloadURL = downloadTorrentLink['href']

                if "720p" in title:
                    if "bluray" in title:
                        quality = Quality.HDBLURAY
                    elif "web-dl" in title.lower() or "web.dl" in title.lower():
                        quality = Quality.HDWEBDL
                    else:
                        quality = Quality.HDTV
                elif "1080p" in title:
                    quality = Quality.FULLHDBLURAY
                elif "hdtv" in title:
                    if "720p" in title:
                        quality = Quality.HDTV
                    elif "1080p" in title:
                        quality = Quality.FULLHDTV
                    else:
                        quality = Quality.SDTV
                else:
                    quality = Quality.SDTV

                if show:
                    results.append( CpasbienSearchResult( self.opener, title, downloadURL, quality, str(show.audio_lang) ) )
                else:
                    results.append( CpasbienSearchResult( self.opener, title, downloadURL, quality ) )

        return results
    
    def getResult(self, episodes):
        """
        Returns a result of the correct type for this provider
        """
        result = classes.TorrentDataSearchResult(episodes)
        result.provider = self

        return result    
    
class CpasbienSearchResult:
    
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

provider = CpasbienProvider()