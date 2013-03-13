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

from binsearch import BinSearch
from nzbclub import NZBClub
from nzbindex import NZBIndex

from bs4 import BeautifulSoup
from sickbeard import logger, classes, show_name_helpers
from sickbeard.providers import generic
from sickbeard.common import Quality
from sickbeard.exceptions import ex

import sickbeard
import re
import urllib
import urllib2

class BinNewzProvider(generic.NZBProvider):

    def __init__(self):
        
        generic.NZBProvider.__init__(self, "BinnewZ")

        self.supportsBacklog = True
        
        self.nzbDownloaders = [ NZBIndex(), NZBClub(), BinSearch() ]
        
        self.url = "http://www.binnews.in/"
        
    def isEnabled(self):
        return sickbeard.BINNEWZ

    def _get_season_search_strings(self, show, season):
        
        showNames = show_name_helpers.allPossibleShowNames(show)
        result = []
        for showName in showNames:
            result.append( showName + ".S%02d" % season )
        return result

    def _get_episode_search_strings(self, ep_obj):
        strings = []

        showNames = show_name_helpers.allPossibleShowNames(ep_obj.show)
        for showName in showNames:
            strings.append("%s S%02dE%02d" % ( showName, ep_obj.season, ep_obj.episode) )
            strings.append("%s %dx%d" % ( showName, ep_obj.season, ep_obj.episode ) )

        return strings
    
    def _get_title_and_url(self, item):
        return (item.title, item.refererURL)
    
    def getQuality(self, item):
        return item.quality
    
    def _doSearch(self, searchString, show=None, season=None):
        
        logger.log("BinNewz : Searching for " + searchString)
        
        data = urllib.urlencode({'b_submit': 'BinnewZ', 'cats[]' : 'all', 'edSearchAll' : searchString, 'sections[]': 'all'})
        
        try:
            soup = BeautifulSoup( urllib2.urlopen("http://www.binnews.in/_bin/search2.php", data) )
        except Exception, e:
            logger.log(u"Error trying to load BinNewz response: "+ex(e), logger.ERROR)
            return []
        
        results = []

        tables = soup.findAll("table", id="tabliste")
        for table in tables:

            rows = table.findAll("tr")
            for row in rows:
                
                cells = row.select("> td")
                if (len(cells) < 11):
                    continue

                name = cells[2].text.strip()
                language = cells[3].find("img").get("src")

                if show:
                    if show.audio_lang == "fr":
                        if not "_fr" in language:
                            continue
                    elif show.audio_lang == "en":
                        if "_fr" in language:
                            continue                
  
                # blacklist_groups = [ "alt.binaries.multimedia" ]
                blacklist_groups = []                
                
                newgroupLink = cells[4].find("a")
                newsgroup = None
                if newgroupLink.contents:
                    newsgroup = newgroupLink.contents[0]
                    if newsgroup == "abmulti":
                        newsgroup = "alt.binaries.multimedia"
                    elif newsgroup == "abtvseries":
                        newsgroup = "alt.binaries.tvseries"
                    elif newsgroup == "abtv":
                        newsgroup = "alt.binaries.tv"
                    elif newsgroup == "a.b.teevee":
                        newsgroup = "alt.binaries.teevee"
                    elif newsgroup == "abstvdivxf":
                        newsgroup = "alt.binaries.series.tv.divx.french"
                    elif newsgroup == "abhdtvx264fr":
                        newsgroup = "alt.binaries.hdtv.x264.french"
                    elif newsgroup == "abmom":
                        newsgroup = "alt.binaries.mom"  
                    elif newsgroup == "abhdtv":
                        newsgroup = "alt.binaries.hdtv"
                    elif newsgroup == "abboneless":
                        newsgroup = "alt.binaries.boneless"
                    elif newsgroup == "abhdtvf":
                        newsgroup = "alt.binaries.hdtv.french"
                    elif newsgroup == "abhdtvx264":
                        newsgroup = "alt.binaries.hdtv.x264"
                    elif newsgroup == "absuperman":
                        newsgroup = "alt.binaries.superman"
                    elif newsgroup == "abechangeweb":
                        newsgroup = "alt.binaries.echange-web"
                    elif newsgroup == "abmdfvost":
                        newsgroup = "alt.binaries.movies.divx.french.vost"
                    elif newsgroup == "abdvdr":
                        newsgroup = "alt.binaries.dvdr"
                    elif newsgroup == "abmzeromov":
                        newsgroup = "alt.binaries.movies.zeromovies"
                    elif newsgroup == "abcfaf":
                        newsgroup = "alt.binaries.cartoons.french.animes-fansub"
                    elif newsgroup == "abcfrench":
                        newsgroup = "alt.binaries.cartoons.french"
                    elif newsgroup == "abgougouland":
                        newsgroup = "alt.binaries.gougouland"
                    elif newsgroup == "abroger":
                        newsgroup = "alt.binaries.roger"
                    elif newsgroup == "abtatu":
                        newsgroup = "alt.binaries.tatu"
                    elif newsgroup =="abstvf":
                        newsgroup = "alt.binaries.series.tv.french"
                    elif newsgroup =="abmdfreposts":
                        newsgroup="alt.binaries.movies.divx.french.reposts"
                    elif newsgroup =="abmdf":
                        newsgroup="alt.binaries.movies.french"
                    else:
                        logger.log(u"Unknown binnewz newsgroup: " + newsgroup, logger.ERROR)
                        continue
                    
                    if newsgroup in blacklist_groups:
                        logger.log(u"Ignoring result, newsgroup is blacklisted: " + newsgroup, logger.WARNING)
                        continue
   
                filename =  cells[5].contents[0]
    
                m =  re.search("^(.+)\s+{(.*)}$", name)
                qualityStr = ""
                if m:
                    name = m.group(1)
                    qualityStr = m.group(2)
    
                m =  re.search("^(.+)\s+\[(.*)\]$", name)
                source = None
                if m:
                    name = m.group(1)
                    source = m.group(2)

                m =  re.search("(.+)\(([0-9]{4})\)", name)
                year = ""
                if m:
                    name = m.group(1)
                    year = m.group(2)
    
                m =  re.search("(.+)\((\d{2}/\d{2}/\d{4})\)", name)
                dateStr = ""
                if m:
                    name = m.group(1)
                    dateStr = m.group(2)
    
                m =  re.search("(.+)\s+S(\d{2})\s+E(\d{2})(.*)", name)
                if m:
                    name = m.group(1) + " S" + m.group(2) + "E" + m.group(3) + m.group(4)
    
                m =  re.search("(.+)\s+S(\d{2})\s+Ep(\d{2})(.*)", name)
                if m:
                    name = m.group(1) + " S" + m.group(2) + "E" + m.group(3) + m.group(4)
                    
                        
                filenameLower = filename.lower()
                if "720p" in qualityStr:
                    if "HDTV" in name or "hdtv" in filenameLower:
                        quality = Quality.HDTV
                    else:
                        quality = Quality.HDBLURAY
                    minSize = 600
                elif "1080p" in qualityStr:
                    if "web-dl" in name or "web-dl" in filenameLower:
                        quality = Quality.FULLHDWEBDL
                    elif "bluray" in filenameLower or "blu-ray" in filenameLower:
                        quality = Quality.FULLHDBLURAY
                    else:
                        quality = Quality.FULLHDTV
                    minSize = 600
                else:
                    quality = Quality.SDTV
                    minSize = 150
                
                # FIXME
                if show and show.quality == 28 and quality == Quality.SDTV:
                    continue
                
                searchItems = []
                multiEpisodes = False
                
                rangeMatcher = re.search(".*S\d{2}\s*E(\d{2})\s+[.|Et]\s+E(\d{2}).*", name)
                if not rangeMatcher:
                    rangeMatcher = re.search(".*S\d{2}\s*E(\d{2}),(\d{2}).*", name)
                if rangeMatcher:
                    rangeStart = int( rangeMatcher.group(1))
                    rangeEnd = int( rangeMatcher.group(2))
                    if ( filename.find("*") != -1 ):
                        for i in range(rangeStart, rangeEnd + 1):
                            searchItem = filename.replace("**", str(i) )
                            searchItem = searchItem.replace("*", str(i) )
                            searchItems.append( searchItem )
                    else:
                        multiEpisodes = True

                if len(searchItems) == 0:
                    searchItems.append( filename )

                for searchItem in searchItems:
                    for downloader in self.nzbDownloaders:
                        logger.log("Searching for download : " + name + ", search string = "+ searchItem + " on " + downloader.__class__.__name__)
                        try:
                            binsearch_result =  downloader.search(searchItem, minSize, newsgroup )
                            if binsearch_result:
                                binsearch_result.audio_langs = show.audio_lang
                                binsearch_result.title = name
                                binsearch_result.quality = quality
                                results.append( binsearch_result )
                                logger.log("Found : " + searchItem + " on " + downloader.__class__.__name__)
                                break
                        except Exception, e:
                            logger.log("Searching from " + downloader.__class__.__name__ + " failed : " + ex(e), logger.ERROR)

        return results
    
    def getResult(self, episodes):
        """
        Returns a result of the correct type for this provider
        """
        result = classes.NZBDataSearchResult(episodes)
        result.provider = self

        return result    

provider = BinNewzProvider()
