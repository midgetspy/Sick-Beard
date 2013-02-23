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

from sickbeard import helpers, logger, classes, show_name_helpers
from sickbeard.exceptions import ex

from bs4 import BeautifulSoup
import datetime
import generic
import httplib
from StringIO import StringIO
import gzip
import re
import sickbeard
import urllib
import urllib2
from sickbeard.common import Quality

class BinNewzProvider(generic.NZBProvider):

    def __init__(self):
        
        generic.NZBProvider.__init__(self, "BinnewZ")

        self.supportsBacklog = True
        
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

    def doBinSearch(self, filename, minSize, newsgroup=None):
        
        binsearch_results = []
        
        # now locate nzb with binsearch
        if newsgroup != None:
            binSearchURLs = [  urllib.urlencode({'server' : 1, 'max': '250', 'adv_g' : newsgroup, 'q' : filename}), urllib.urlencode({'server' : 2, 'max': '250', 'adv_g' : newsgroup, 'q' : filename})]
        else:
            binSearchURLs = [  urllib.urlencode({'server' : 1, 'max': '250', 'q' : filename}), urllib.urlencode({'server' : 2, 'max': '250', 'q' : filename})]

        for suffixURL in binSearchURLs:
            binSearchURL = "http://binsearch.info/?adv_age=&" + suffixURL

            binSearchResult = self.getURL(binSearchURL)
            binSearchSoup = BeautifulSoup( binSearchResult )

            foundName = None
            sizeInMegs = None
            for elem in binSearchSoup.findAll(lambda tag: tag.name=='tr' and tag.get('bgcolor') == '#FFFFFF' and 'size:' in tag.text):
                for checkbox in elem.findAll(lambda tag: tag.name=='input' and tag.get('type') == 'checkbox'):
                    sizeStr = re.search("size:\s+([^B]*)B", elem.text).group(1).strip()
                    
                    if "G" in sizeStr:
                        sizeInMegs = float( re.search("([0-9\\.]+)", sizeStr).group(1) ) * 1024
                    elif "K" in sizeStr:
                        sizeInMegs = 0
                    else:
                        sizeInMegs = float( re.search("([0-9\\.]+)", sizeStr).group(1) )
                    
                    if sizeInMegs > minSize:
                        foundName = checkbox.get('name')
                        break
                
            if foundName:
                params = urllib.urlencode({foundName: 'on', 'action': 'nzb'})
                headers = {"Referer":binSearchURL, "Content-type": "application/x-www-form-urlencoded","Accept-Encoding" : "gzip,deflate,sdch", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","User-Agent":"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.57 Safari/537.17"}
                conn = httplib.HTTPConnection( "binsearch.info" )
                conn.request("POST", "/fcgi/nzb.fcgi?adv_age=&" + suffixURL, params, headers)
                response = conn.getresponse()
                
                if response.status == 200:
                    rawData = response.read()      

                    if response.getheader('Content-Encoding') == 'gzip':
                        buf = StringIO( rawData )
                        f = gzip.GzipFile(fileobj=buf)
                        nzbdata = f.read()
                    else:
                        nzbdata = rawData

                    binsearch_results.append( BinSearchResult( nzbdata, sizeInMegs, binSearchURL ) )
                
                break
            
        return binsearch_results        
    
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
                    else:
                        logger.log(u"Unknown binnewz newsgroup: " + newsgroup, logger.ERROR)
                        continue
                    
                    if newsgroup in blacklist_groups:
                        logger.log(u"Ignoring result, newsgroup is blacklisted: " + newsgroup, logger.WARNING)
                        continue
   
                filename =  cells[5].contents[0]

                rawName = name
    
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
    
                m =  re.search("(.+)\s+S(\d{2})\s+E(\d{2})", name)
                if m:
                    name = m.group(1) + " S" + m.group(2) + "E" + m.group(3)                
    
                m =  re.search("(.+)\s+S(\d{2})\s+Ep(\d{2})", name)
                if m:
                    name = m.group(1) + " S" + m.group(2) + "E" + m.group(3)                

                if "720p" in qualityStr:
                    quality = Quality.HDBLURAY
                    minSize = 600
                elif "1080p" in qualityStr:
                    quality = Quality.FULLHDBLURAY
                    minSize = 600
                else:
                    quality = Quality.SDTV
                    minSize = 150
                
                if ( filename.find("*") != -1 ):
                    print "Range detected"
                    
                binsearch_results = self.doBinSearch( filename, minSize, newsgroup )
                # binsearch_results = self.doNZBClub( filename, minSize, newsgroup )
                
                for binsearch_result in binsearch_results:
                    results.append( BinNewzSearchResult( name, binsearch_result.nzbdata, binsearch_result.url, quality))

        return results
    
    def getResult(self, episodes):
        """
        Returns a result of the correct type for this provider
        """
        result = classes.NZBDataSearchResult(episodes)
        result.provider = self

        return result    
    
class BinSearchResult:
    
    def __init__(self, nzbdata, sizeInMegs, url):
        self.nzbdata = nzbdata
        self.sizeInMegs = sizeInMegs
        self.url = url
    
class BinNewzSearchResult:
    
    def __init__(self, title, nzbdata, url, quality):
        self.title = title
        self.url = url
        self.extraInfo = [nzbdata] 
        self.quality = quality
        
    def getQuality(self):
        return self.quality

provider = BinNewzProvider()   
