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

from binsearch_downloader import BinSearch
from bs4 import BeautifulSoup
from nzbclub_downloader import NZBClub
from sickbeard import logger, classes, show_name_helpers
from sickbeard.common import Quality
from sickbeard.exceptions import ex
from sickbeard.providers.nzbclub_downloader import NZBClub
import generic
import httplib
import re
import sickbeard
import urllib


class BinNewzProvider(generic.NZBProvider):

    def __init__(self):
        
        generic.NZBProvider.__init__(self, "BinnewZ")

        self.supportsBacklog = True
        
        self.nzbDownloaders = [ NZBClub(), BinSearch() ]
        # self.nzbDownloaders = [ NZBClub() ]
        
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
        return (item.title, item.url)
    
    def getQuality(self, item):
        return item.getQuality()
    
    def _doSearch(self, searchString, show=None, season=None):
        
        data = urllib.urlencode({'b_submit': 'BinnewZ', 'cats[]' : all, 'edSearchAll' : searchString, 'sections[]': 'all'})
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        h = httplib.HTTPConnection('www.binnews.in:80')
        h.request('POST', '/_bin/search2.php', data, headers)

        r = h.getresponse()
        contents = r.read()
        
        try:
            soup = BeautifulSoup( contents )
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
    
                encoderSpan = cells[1].find("span")
                if encoderSpan:
                    encoder = encoderSpan.contents[0]
                name = cells[2].text.strip()
                language = cells[3].find("img").get("src")

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

                if "720p" in qualityStr:
                    if "HDTV" in name or "HDTV" in filename:
                        quality = Quality.HDTV
                    else:
                        quality = Quality.HDBLURAY
                    minSize = 600
                elif "1080p" in qualityStr:
                    quality = Quality.FULLHDBLURAY
                    minSize = 600
                else:
                    quality = Quality.SDTV
                    minSize = 150
                
                # FIXME
                if show.quality == 28 and quality == Quality.SDTV:
                    continue
                
                if ( filename.find("*") != -1 ):
                    print "TODO: Range detected"

                for downloader in self.nzbDownloaders:
                    binsearch_result =  downloader.search(filename, minSize, newsgroup )
                    if binsearch_result:
                        results.append( BinNewzSearchResult( name, binsearch_result.nzbdata, binsearch_result.url, quality))
                        break

        return results
    
    def getResult(self, episodes):
        """
        Returns a result of the correct type for this provider
        """
        result = classes.NZBDataSearchResult(episodes)
        result.provider = self

        return result    

class BinNewzSearchResult:
    
    def __init__(self, title, nzbdata, url, quality):
        self.title = title
        self.url = url
        self.extraInfo = [nzbdata] 
        self.quality = quality
        
    def getQuality(self):
        return self.quality

provider = BinNewzProvider()   
