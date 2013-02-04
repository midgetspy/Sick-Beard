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

import re
import time

import sickbeard
from sickbeard import logger, helpers
from sickbeard.exceptions import ex
from sickbeard.encodingKludge import fixStupidEncodings
from lib import requests
from sickbeard.clients.generic import GenericClient

class uTorrentAPI(GenericClient):
    
    def __init__(self, host=None, username=None, password=None):
        
        super(uTorrentAPI, self).__init__('uTorrent', host, username, password)
      
        self.url = sickbeard.TORRENT_HOST + 'gui/' if host is None else host + 'gui/'
            
    def _request(self, method='get', params={}, files=None):

        params.update({'token':self._get_auth()})
        return super(uTorrentAPI, self)._request(method=method, params=params, files=files)

    def _get_auth(self):

        response = self.session.get(self.url + 'token.html')
        if response.status_code == 404:
            return None
        self.auth = re.findall("<div.*?>(.*?)</", response.text)[0]
        return self.auth
      
    def _add_torrent_uri(self, result):

        params={'action':'add-url', 's': result.url}
        return self._request(params=params)

    def _add_torrent_file(self, result):

        params = {'action':'add-file'}
        files={'torrent_file': ('tv.torrent', result.content)}
        return  self._request(method='post', params=params, files=files)

    def _set_torrent_label(self, result):
        
        params = {'action':'setsetting', 
                  'hash':self._get_torrent_hash(result), 
                  's':'label', 
                  'v':sickbeard.TORRENT_LABEL
                  }
        return self._request(params=params)
    
    def set_torrent_pause(self, result):
        if sickbeard.TORRENT_PAUSED:
            params = {'action':'pause', 'hash':self._get_torrent_hash(result)}
            return self._request(params=params)
        
api = uTorrentAPI()       