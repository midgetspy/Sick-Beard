# Author: Nic Wolfe <nic@wolfeden.ca>
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
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import re
import time
import urllib
import datetime

from xml.dom.minidom import parseString
from xml.etree import ElementTree

import generic
import sickbeard

from sickbeard import classes, logger, show_name_helpers, helpers
from sickbeard import tvcache
from sickbeard import exceptions


import requests
from bs4 import BeautifulSoup

class NZBto(generic.NZBProvider):

    def __init__(self):

        generic.NZBProvider.__init__(self, "NZBto")

        self.supportsBacklog = True

        self.cache = NNZBtoCache(self)

        self.url = 'http://nzb.to/'
        self.searchString = ''

        self.session = requests.Session()
        self.session.get("http://nzb.to")
        self.session.headers["Referer"] = "http://nzb.to/login"
        self.session.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:20.0) Gecko/20100101 Firefox/20.0"


    def isEnabled(self):
        self.proxy = sickbeard.NZBTO_PROXY
        return sickbeard.NZBTO

    def _checkAuth(self):
        if not sickbeard.NZBTO_USER or not sickbeard.NZBTO_PASS:
            raise exceptions.AuthException("nzb.to authentication details are empty, check your config")
        else:
            self.proxy = sickbeard.NZBTO_PROXY

    def _get_season_search_strings(self, show, season):
        return [x for x in show_name_helpers.makeSceneSeasonSearchString(show, season)]

    def _get_episode_search_strings(self, ep_obj):
        return [x for x in show_name_helpers.makeSceneSearchString(ep_obj)]

    def _get_title_and_url(self, item):
        cur_el = item.tr.find("td", attrs={"class": "title"}).find("a")
        tmp_title = cur_el.text
        dl = item.find("a", attrs={"title": "NZB erstellen"})
        dl = cur_el
        tmp_url = "http://nzb.to/inc/ajax/popupdetails.php?n=" + cur_el["href"].split("nid=")[1]
        x = self.session.get(tmp_url)
        tro = BeautifulSoup(x.text)
        pw = tro.find('span', attrs={"style": "color:#ff0000"}).strong.next.next
        if not pw or pw.strip() == "-":
            title = tmp_title
        else:
            title = "%s{{%s}}" % (tmp_title, pw.strip())

        params = {"nid": dl["href"].split("nid=")[1], "user": sickbeard.NZBTO_USER, "pass": sickbeard.NZBTO_PASS, "rel": title}
        url = self.proxy + urllib.urlencode(params)

        logger.log( '_get_title_and_url(), returns (%s, %s)' %(title, url), logger.DEBUG)
        logger.log( 'self.searchString=%s' %(self.searchString), logger.DEBUG)

        return (title, url)

    def _doSearch(self, curString, quotes=False, show=None):
        self.session.post("http://nzb.to/login.php", data={"action": "login", "username": sickbeard.NZBTO_USER, "password": sickbeard.NZBTO_PASS, "bind_ip": "on", "Submit": ".%3AEinloggen%3A.", "ret_url": ""})
        logger.log( 'sending login to nzb.to returned Cookie: {0}'.format(self.session.cookies.get_dict()), logger.DEBUG)

        term =  re.sub('[\.\-\:]', ' ', curString).encode('utf-8')
        self.searchString = term
        if quotes:
            term = "\""+term+"\""

        #http://nzb.to/?p=list&q=Shameless+S03E12+german&cat=13&sort=post_date&order=desc&amount=50
        params = {"q": term,
                  "sort": "post_date", #max 50
                  "order": "desc", #nospam
                  "amount": 50, #min 100MB
                  }

        searchURL = "http://nzb.to/?p=list&" + urllib.urlencode(params)

        logger.log(u"Search string: " + searchURL)

        logger.log(u"Sleeping 10 seconds to respect NZBto's rules")
        time.sleep(10)

        #logger.log(u"CURRENT COOKIE: {0}".format(self.session.cookies.get_dict()))

        cookie_test = re.compile(r"[0-9]*-\d{1}-.*")
        if re.match(cookie_test, self.session.cookies.get("NZB_SID") ):
            logger.log("ERROR... COOKIE SEEMS NOT TO BE VALID", logger.ERROR)

        #searchResult = self.getURL(searchURL,[("User-Agent","Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:5.0) Gecko/20100101 Firefox/5.0"),("Accept","text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),("Accept-Language","de-de,de;q=0.8,en-us;q=0.5,en;q=0.3"),("Accept-Charset","ISO-8859-1,utf-8;q=0.7,*;q=0.7"),("Connection","keep-alive"),("Cache-Control","max-age=0")])
        if curString == "cache":
            url = "http://nzb.to/?p=list&cat=13&sa_Video-Genre=3221225407&sort=post_date&order=desc&amount=100"
            logger.log(url)
            searchResult = self.session.get(url)
            #logger.log(u"{0}".format(searchResult))
        else:
            searchResult = self.session.post("http://nzb.to/?p=list", data=params)

        if not searchResult:
            logger.log("Search gave no results...")
            return []

        try:
            parsedXML = BeautifulSoup(searchResult.text)
            table_regex = re.compile(r'tbody-.*')
            items = parsedXML.findAll("tbody", attrs={"id": table_regex})
        except Exception, e:
            logger.log(u"Error trying to load NZBto HTML feed: "+exceptions.ex(e), logger.ERROR)
            return []

        results = []

        for curItem in items:
            (title, url) = self._get_title_and_url(curItem)

            if not title or not url:
                logger.log(u"The XML returned from the NZBto HTML feed is incomplete, this result is unusable", logger.ERROR)
                continue
            if not title == 'Not_Valid':
                results.append(curItem)

        return results


    def findPropers(self, date=None):

        results = []

        for curResult in self._doSearch("REPACK"):

            (title, url) = self._get_title_and_url(curResult)

            pubDate_node = curResult.find('td', attrs={'class':'final'}).span
            if not pubDate_node:
                logger.log(u"Unable to figure out the date for entry "+title+", skipping it")
                continue
            pubDate = pubDate_node['title']
            #Genaues Datum/Zeit: 09-09-2013 10:41:47
            dateStr = re.search('.*:\s(\d{2}-\d{2}-\d{4}\s\d{2}:\d{2}:\d{2})', pubDate)
            if not dateStr:
                logger.log(u"Unable to figure out the date for entry "+title+", skipping it")
                continue
            else:
                #logger.log(u"Proper date for %s is %s" % (title, dateStr.group(1)))
                resultDate = datetime.datetime.strptime(dateStr.group(1), "%d-%m-%Y %H:%M:%S")

            if date == None or resultDate > date:
                results.append(classes.Proper(title, url, resultDate))

        return results


class NNZBtoCache(tvcache.TVCache):

    def __init__(self, provider):

        tvcache.TVCache.__init__(self, provider)

        # only poll nzb.to every 40 minutes max
        self.minTime = 40

        self.session = requests.Session()
        self.session.get("http://nzb.to")
        self.session.headers["Referer"] = "http://nzb.to/login"
        self.session.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:20.0) Gecko/20100101 Firefox/20.0"

    def _parseItem(self, item):
        title, url = self.provider._get_title_and_url(item)
        logger.log(u"Adding item from RSS to cache: " + title, logger.DEBUG)
        self._addCacheEntry(title, url)


    def updateCache(self):
        if not self.shouldUpdate():
            return
        # get all records since the last timestamp
        #
        if not sickbeard.NZBTO_USER or not sickbeard.NZBTO_PASS:
            raise exceptions.AuthException("nzb.to authentication details are empty, check your config")
        else:
            #if user and pass are ok, log us in
            self.provider.proxy = sickbeard.NZBTO_PROXY
            self.provider.session.post("http://nzb.to/login.php", data={"action": "login", "username": sickbeard.NZBTO_USER, "password": sickbeard.NZBTO_PASS, "bind_ip": "on", "Submit": ".%3AEinloggen%3A.", "ret_url": ""})

        url = "http://nzb.to/?p=list&cat=13&sa_Video-Genre=3221225407&sort=post_date&order=desc&amount=100"

        urlArgs = {'q': '',
                   "rpp": 50, #max 50
                  "ns": 1, #nospam
                  "szs":16, #min 100MB
                  "sp":1 #nopass
                  }

        #url += urllib.urlencode(urlArgs)

        logger.log(u"NZBto cache update URL: "+ url, logger.DEBUG)

        data = self.provider._doSearch("cache")
        if not data:
            return

        #logger.log(u"{0}".format(data))
        self.setLastUpdate()

        # now that we've got the latest releases lets delete the old cache
        logger.log(u"Clearing nzb.to cache and updating with new information")
        self._clearCache()

        for item in data:
            self._parseItem(item)


provider = NZBto()
