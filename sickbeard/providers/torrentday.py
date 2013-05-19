

import sickbeard
import generic

from sickbeard import db
from sickbeard import helpers
from sickbeard import logger
from sickbeard import tvcache
from sickbeard import show_name_helpers

from httplib import BadStatusLine
from sickbeard.common import Quality
from sickbeard.common import Overview

import traceback


import urllib, urllib2, cookielib
import re, json, socket,datetime

class TorrentDayProvider(generic.TorrentProvider):

    def __init__(self):

        generic.TorrentProvider.__init__(self, "TorrentDay")
        
        self.supportsBacklog = True
        self.cache = TorrentDayCache(self)
        self.cj = cookielib.CookieJar()
        self.rssuid = ''
        self.rsshash = ''
        self.rsslink = ''
        self.url = 'http://www.torrentday.com/'
        self.downloadUrl = 'http://www.torrentday.com/download.php/'
        #self.token = None
                
        logger.log('Loading TorrentDay')
        
        self.cache = TorrentDayCache(self)
        
        
        
    def _checkAuth(self):
        if len(self.cj) >= 2:
            return True
        return False 

    def isEnabled(self):
        return sickbeard.TORRENTDAY
        
    def imageName(self):
        return 'torrentday.png'

    def getQuality(self, item):        
        quality = Quality.nameQuality(item[0])
        return quality 
    
    def _get_title_and_url(self, item):
        return item

    def _get_season_search_strings(self, show, season=None):
        
        search_string = []
    
        if not show:
            return []

        #Building the search string with the season we need
        #1) ShowName SXX 
        #2) ShowName Season X
        #for show_name in set(show_name_helpers.allPossibleShowNames(show)):
        #    ep_string = show_name + ' ' + 'S%02d' % int(season)   
        #    search_string.append(ep_string)
        #  
        #    ep_string = show_name + ' ' + 'Season' + ' ' + str(season)   
        #    search_string.append(ep_string)

        #Building the search string with the episodes we need         
        myDB = db.DBConnection()
        
        if show.air_by_date:
            (min_date, max_date) = self._get_airbydate_season_range(season)
            sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND airdate >= ? AND airdate <= ?", [show.tvdbid,  min_date.toordinal(), max_date.toordinal()])
        else:
            sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND season = ?", [show.tvdbid, season])
            
        for sqlEp in sqlResults:
            if show.getOverview(int(sqlEp["status"])) in (Overview.WANTED, Overview.QUAL):
                if show.air_by_date:
                    for show_name in set(show_name_helpers.allPossibleShowNames(show)):
                        ep_string = show_name_helpers.sanitizeSceneName(show_name) +' '+ str(datetime.date.fromordinal(sqlEp["airdate"])).replace('-', '.')
                        search_string.append(ep_string)
                else:
                    for show_name in set(show_name_helpers.allPossibleShowNames(show)):
                        ep_string = show_name_helpers.sanitizeSceneName(show_name) +' '+ sickbeard.config.naming_ep_type[2] % {'seasonnumber': season, 'episodenumber': int(sqlEp["episode"])}
                        search_string.append(ep_string)                       
        
        return search_string

    def _get_episode_search_strings(self, ep_obj):
        
        search_string = []
       
        if not ep_obj:
            return []
        if ep_obj.show.air_by_date:
            for show_name in set(show_name_helpers.allPossibleShowNames(ep_obj.show)):
                ep_string = show_name_helpers.sanitizeSceneName(show_name) +' '+ str(ep_obj.airdate).replace('-', '.')
                search_string.append(ep_string)
        else:
            for show_name in set(show_name_helpers.allPossibleShowNames(ep_obj.show)):
                ep_string = show_name_helpers.sanitizeSceneName(show_name) +' '+ sickbeard.config.naming_ep_type[2] % {'seasonnumber': ep_obj.season, 'episodenumber': ep_obj.episode}
                search_string.append(ep_string)
    
        return search_string    


    def doLogin(self):
        success = False
        if len(self.cj) < 2:
            '''Login function, returns True on success.'''
            
            username = sickbeard.TORRENTDAY_USERNAME
            password = sickbeard.TORRENTDAY_PASSWORD
            
            cookie = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
            login_data = urllib.urlencode({'username' : username, 'password' : password, 'submit.x': 0, 'submit.y': 0})
            res = opener.open('http://www.torrentday.com/torrents/', login_data)      
            
            headers = str(res.headers).splitlines()
            success = False
            for header in headers:
                if 'Expires' in header:
                    for cookies in cookie:
                        if cookies.name == 'uid':
                            uid = 'UID={0}; '.format(cookies.value)
                        elif cookies.name == 'pass':
                            passwd = 'PASS={0}; '.format(cookies.value)
                    self.cj = cookie
                    #self.token = ('{0}{1}'.format(uid,passwd))
                    success = True
                    logger.log("TorrentDay session: {0}".format(self.token), logger.DEBUG)
                    logger.log("TorrentDay successfully logged user '{0}' in.".format(sickbeard.TORRENTDAY_USERNAME))
                    logger.log("Detecting RSS Feed for user '{0}'.".format(sickbeard.TORRENTDAY_USERNAME))
                    rss_data = 'cat%5B%5D=24&cat%5B%5D=14&cat%5B%5D=7&cat%5B%5D=2&feed=direct&login=passkey'
                    rss_res = opener.open('http://www.torrentday.com/rss.php', rss_data).readlines()[-1]
                    reRSS = re.compile(r'u=(.*);tp=([0-9A-Fa-f]{32})', re.IGNORECASE|re.DOTALL)
                    uidhash = reRSS.findall(rss_res)
                    self.rssuid = uidhash[0][0]
                    self.rsshash = uidhash[0][1]
                    self.rsslink = 'http://www.torrentday.com/torrents/rss?download;l24;l14;l7;l2;u={0};tp={1}'.format(self.rssuid,self.rsshash)
                    logger.log('RSS Url: {0}'.format(self.rsslink), logger.DEBUG)
            if not success:
                logger.log("TorrentDay failed to log user '{0}' in. Incorrect Password?".format(sickbeard.TORRENTDAY_USERNAME), logger.ERROR)
                    
            res.close()
            
        else:
            success = True
            logger.log("Using TorrentDay session from cookie")
        return success
    
    def getURL(self, url, headers=[], data=None):
        html = ''
        if self.doLogin():
            result = None
            try:
                opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
                search_data = data
                result = opener.open(url, search_data)
                #result = opener.open('http://www.torrentday.com/V3/API/API.php', search_data)
                html = result.read()               
                
                
                logger.log('Got Results from Torrentday!')
                             
            except urllib2.HTTPError, e:
                logger.log(u"HTTP error " + str(e.code) + " while loading URL " + url, logger.WARNING)
                return None
            except urllib2.URLError, e:
                logger.log(u"URL error " + str(e.reason) + " while loading URL " + url, logger.WARNING)
                return None
            except BadStatusLine:
                logger.log(u"BadStatusLine error while loading URL " + url, logger.WARNING)
                return None
            except socket.timeout:
                logger.log(u"Timed out while loading URL " + url, logger.WARNING)
                return None
            except ValueError:
                logger.log(u"Unknown error while loading URL " + url, logger.WARNING)
                return None
            except Exception:
                logger.log(u"Unknown exception while loading URL " + url + ": " + traceback.format_exc(), logger.WARNING)
                return None
        return html
    
    
    def _doSearch(self, search_params, show=None):
        
        logger.log('Performing Search: {0}'.format(search_params))
        
        results = []
        
        searchTerm = '+'.join(search_params.split())
            
        data = {'/browse.php?' : None,'cata':'yes','jxt':8,'jxw':'b','search':searchTerm, 'c7':1, 'c26':1,'c2':1, 'c24':1}
        search_data = urllib.urlencode(data)
        html = self.getURL('http://www.torrentday.com/V3/API/API.php', data=search_data)
        logger.log('Post Data: {0}'.format(data), logger.DEBUG)
        res, pages = self.parseResults(html)
        
        results = results + res
        
        if pages > 1:
            for page in xrange(1,pages+1):
                data = {'/browse.php?' : None,'cata':'yes','page':page, 'jxt':8,'jxw':'b','search':searchTerm, 'c7':1, 'c26':1,'c2':1, 'c24':1}
                search_data = urllib.urlencode(data)
                html = self.getURL('http://www.torrentday.com/V3/API/API.php', search_data)
                logger.log('Post Data: {0}'.format(data), logger.DEBUG)
                res = self.parseResults(html)[0]
                results = results + res
        return results
        
            
            
    def parseResults(self, html):
        
        results = []
        numpages = 1
        
        try: 
            data = json.loads(html)
            torrents = data.get('Fs', [])[0].get('Cn', {}).get('torrents', [])
            rePager = re.compile(r'page=(\d*)',re.IGNORECASE|re.DOTALL)
            pager = rePager.findall(str(html))
            if pager:
                numpages = int(max(list(set(pager))))
                pass
            else:
                numpages = 1
                pass
            
            for tor in torrents:
                results.append(([tor['name'],self.downloadUrl + '{0}/{1}?torrent_pass={2}'.format(tor['id'],tor['fname'],self.rsshash)]))
                logger.log('Parser found: {0}'.format(tor['name']))   
        except AttributeError, e: 
            logger.log("No results found", logger.DEBUG)
            return [],0
        except ValueError, e:
            logger.log("No results found", logger.DEBUG)
            return [],0
        return results, numpages


class TorrentDayCache(tvcache.TVCache):
    def __init__(self, provider):
        
        tvcache.TVCache.__init__(self, provider)
        self.provider = provider
        self.minTime = 20

        
    def _getRSSData(self):
        self.url = self.provider.rsslink
        logger.log(u'RSS url:{0}'.format(self.url))
        xml = helpers.getURL(self.url)
        return xml
    
        
        
provider = TorrentDayProvider()   
