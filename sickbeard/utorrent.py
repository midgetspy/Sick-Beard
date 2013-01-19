# Authors: Mr_Orange <mr_orange@hotmail.it>, EchelonFour
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

import urllib, urllib2
import cookielib
import httplib
import re
import time
from hashlib import sha1

import sickbeard
from sickbeard import logger, helpers
from sickbeard.exceptions import ex
from sickbeard.encodingKludge import fixStupidEncodings
from lib import MultipartPostHandler
from lib.bencode import bencode, bdecode


def testAuthentication(host, username, password):

    try: 
        utorrent = uTorrentAPI(host, username, password) 
        utorrent.opener.open(host + 'gui/' + "token.html")
    except httplib.InvalidURL, err:
        return False,"Error: Invalid uTorrent host"
    except urllib2.HTTPError, err:
        if err.code == 401:
            return False,"Error: Invalid uTorrent Username or Password"
    except:    
        return False,"Error: Unable to connect to uTorrent"    
         
    return True,"Success: Connected and Authenticated"   

class uTorrentAPI(object):
    
    def __init__(self, host=None, username=None, password=None):

        super(uTorrentAPI, self).__init__()

        self.url = sickbeard.TORRENT_HOST + 'gui/' if host is None else host + 'gui/'
        self.username = sickbeard.TORRENT_USERNAME if username is None else username
        self.password = sickbeard.TORRENT_PASSWORD if password is None else password

        self.token = ''
        self.last_time = time.time()

        cookies = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies), MultipartPostHandler.MultipartPostHandler)
#        self.opener.addheaders = [('User-agent', 'sickbeard-utorrent-client/1.0')]
        password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_manager.add_password(None, self.url, self.username, self.password)
        self.opener.add_handler(urllib2.HTTPBasicAuthHandler(password_manager))
#        self.opener.add_handler(urllib2.HTTPDigestAuthHandler(password_manager))
        urllib2.install_opener(self.opener)
        self.token = self.get_token()

    def _request(self, action, data = None):
        if time.time() > self.last_time + 1800:
            self.last_time = time.time()
            self.token = self.get_token()
        
        request = urllib2.Request(self.url + "?token=" + self.token + "&" + action, data)
        
        try:
            open_request = self.opener.open(request)
            response = open_request.read()
            if response:
                return response
            else:
                logger.log(u'Unknown failure sending command to uTorrent. Return text is: ' + response, logger.DEBUG)
                return False
                
        except httplib.InvalidURL, err:
            logger.log(u'Invalid uTorrent host, check your config', logger.ERROR)
        except urllib2.HTTPError, err:
            if err.code == 401:
                logger.log(u'Invalid uTorrent Username or Password, check your config', logger.ERROR)
            else:
                logger.log(u'uTorrent HTTPError: ' + ex(err), logger.ERROR)
        except urllib2.URLError, err:
            logger.log(u'Unable to connect to uTorrent '+ ex(err), logger.ERROR)
        return False

    def get_token(self):
        request = urllib2.urlopen(self.url+"token.html")
        token = re.findall("<div.*?>(.*?)</", request.read())[0]
        return token

    def add_torrent_uri(self, torrent):
        action = "action=add-url&s=%s" % torrent
        return self._request(action)

    def add_torrent_file(self, filename, filedata):
        action = "action=add-file"
        return self._request(action, {"torrent_file": (filename, filedata)})

    def set_torrent(self, hash, params):
        action = "action=setprops&hash=%s" % hash
        for k, v in params.iteritems():
            action += "&s=%s&v=%s" % (k, v)
        return self._request(action)

    def pause_torrent(self, hash):
        action = "action=pause&hash=%s" % hash
        return self._request(action)
        
    def sendTORRENT(self, result):
        
        logger.log(u"Calling uTorrent with url: " + result.url, logger.DEBUG)
        
        try:
            if result.url.startswith('magnet'):
                torrent_hash = re.findall('urn:btih:([\w]{32,40})', result.url)[0]
                self.add_torrent_uri(urllib.quote_plus(result.url))
            else:
                filedata = helpers.getURL(result.url)
                info = bdecode(filedata)["info"]
                torrent_hash = sha1(bencode(info)).hexdigest().upper()            
                self.add_torrent_file('file', filedata)

            #Change settings of added torrents
            self.set_torrent(torrent_hash, {'label' : sickbeard.TORRENT_LABEL})

            return True
        except Exception, err:
            logger.log('Failed to send torrent to uTorrent: ' + ex(err), logger.ERROR)
            return False