# Author: Mr_Orange <mr_orange@hotmail.it>
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

import urllib2
import httplib
import re

try:
    import json
except ImportError:
    from lib import simplejson as json

import sickbeard
from sickbeard import logger
from sickbeard.exceptions import ex
from urlparse import urlparse

class TransmissionRPC(object):
    """TransmissionRPC lite library"""
    def __init__(self, host="localhost", port=9091, username=None, password=None):
        super(TransmissionRPC, self).__init__()
        self.url = 'http://' + host + ':' + str(port) + '/transmission/rpc'
        self.tag = 0
        self.session_id = 0
        self.session = {}
        if username and password:
            password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
            password_manager.add_password(realm=None, uri=self.url, user=username, passwd=password)
            opener = urllib2.build_opener(urllib2.HTTPBasicAuthHandler(password_manager), urllib2.HTTPDigestAuthHandler(password_manager))
            opener.addheaders = [('User-agent', 'sick-beard-transmission-client/1.0')]
            urllib2.install_opener(opener)
        elif username or password:
            logger.log('Either user or password missing, not using authentication.', logger.DEBUG)
        self.session = self.get_session()

    def _request(self, ojson):
        self.tag += 1
        headers = {'x-transmission-session-id': str(self.session_id)}
        request = urllib2.Request(self.url, json.dumps(ojson).encode('utf-8'), headers)
        try:
            open_request = urllib2.urlopen(request)
            response = json.loads(open_request.read())
            logger.log('response: ' + str(json.dumps(response).encode('utf-8')), logger.DEBUG)
            if response['result'] == 'success':
                logger.log(u"Torrent sent to Transmission successfully", logger.DEBUG)
                return response["arguments"]
            else:
                logger.log("Unknown failure sending Torrent to Transmission. Return text is: " + response['result'], logger.ERROR)
                return False
        except httplib.InvalidURL, e:
            logger.log(u"Invalid Transmission host, check your config " + ex(e), logger.ERROR)
            return False
        except urllib2.HTTPError, e:
            if e.code == 401:
                logger.log(u"Invalid Transmission Username or Password, check your config", logger.ERROR)
                return False
            elif e.code == 409:
                msg = str(e.read())
                try:
                    self.session_id = re.search('X-Transmission-Session-Id:\s*(\w+)', msg).group(1)
                    logger.log('X-Transmission-Session-Id: ' + self.session_id, logger.DEBUG)
                    ##resend request with the updated header
                    return self._request(ojson)
                except:
                    logger.log(u"Unable to get Transmission Session-Id " + ex(e), logger.ERROR)
            else:
                logger.log(u"TransmissionRPC HTTPError: " + ex(e), logger.ERROR)
        except urllib2.URLError, e:
            logger.log(u"Unable to connect to Transmission " + ex(e), logger.ERROR)

    def get_session(self):
        post_data = {
            'method': 'session-get',
            'tag': self.tag
        }
        return self._request(post_data)

    def add_torrent(self, torrent, arguments={}):
        arguments["filename"] = torrent
        post_data = {
            'arguments': arguments,
            'method': 'torrent-add',
            'tag': self.tag
        }
        return self._request(post_data)

    def set_torrent(self, id, arguments={}):
        arguments["ids"] = id
        post_data = {
            'arguments': arguments,
            'method': 'torrent-set',
            'tag': self.tag
        }
        logger.log("Trying to set_torrent", logger.DEBUG)
        return self._request(post_data)

def sendTORRENT(torrent):

    path = sickbeard.TORRENT_PATH
    ratio = sickbeard.TORRENT_RATIO
    paused = sickbeard.TORRENT_PAUSED
    log = "Torrent will be added with path:" + path + ", ratio: " + ratio + "and paused = " +  str(paused)
    logger.log(log, logger.DEBUG)
    try:
        host = urlparse(sickbeard.TORRENT_HOST)
    except Exception, e:
        logger.log(u"Host properties are not filled in correctly, port is missing.", logger.ERROR)
        return False

    # Set parameters for Transmission
    params = {}
    change_params = {}

    if not (ratio == ''):
        change_params['seedRatioLimit'] = ratio
    else:
        change_params['seedRatioMode'] = 1

    if paused == '':
        params['paused'] = 0
    else:
        params['paused'] = paused

    if not (path == ''):
        params['download-dir'] = path
    
    #check for cookies
    if torrent.provider.token:
        params['cookies'] = torrent.provider.token
        
    try:
        tc = TransmissionRPC(host.hostname, host.port, sickbeard.TORRENT_USERNAME, sickbeard.TORRENT_PASSWORD)
        torrent = tc.add_torrent(torrent.url, arguments=params)
        tc.set_torrent(torrent["torrent-added"]["hashString"], change_params)
        
        return True
    except Exception, e:
        logger.log("Unknown failure sending Torrent to Transmission. Return text is: " + str(e), logger.ERROR)
        return False

def testAuthentication(host, username, password):

    try:
        host = urlparse(host)
    except Exception, e:
        return False, u"Host properties are not filled in correctly, port is missing."

    try:
        tc = TransmissionRPC(host.hostname, host.port, username, password)
        return True, u"Success: Connected and Authenticated. RPC version: " + str(tc.session["rpc-version"])
    except Exception, e:
       return False, u"Error: Unable to connect to Transmission" 