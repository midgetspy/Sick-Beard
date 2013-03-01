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

import urllib
import urllib2
from bs4 import BeautifulSoup
import re
import httplib
import gzip
from StringIO import StringIO
from nzbdownloader import NZBDownloader
from nzbdownloader import NZBSearchResult
import time

class BinSearch(NZBDownloader):
    
    def search(self, filename, minSize, newsgroup=None):

        if newsgroup != None:
            binSearchURLs = [  urllib.urlencode({'server' : 1, 'max': '250', 'adv_g' : newsgroup, 'q' : filename}), urllib.urlencode({'server' : 2, 'max': '250', 'adv_g' : newsgroup, 'q' : filename})]
        else:
            binSearchURLs = [  urllib.urlencode({'server' : 1, 'max': '250', 'q' : filename}), urllib.urlencode({'server' : 2, 'max': '250', 'q' : filename})]

        for suffixURL in binSearchURLs:
            binSearchURL = "http://binsearch.info/?adv_age=&" + suffixURL
        
            if self.lastRequestTime and self.lastRequestTime > ( time.mktime(time.localtime()) - 10):
                time.sleep( 10 )
            self.lastRequestTime = time.gmtime()            

            binSearchSoup =BeautifulSoup(urllib2.urlopen(binSearchURL))

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

                    return NZBSearchResult( nzbdata, sizeInMegs, binSearchURL )