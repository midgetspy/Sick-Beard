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

import sickbeard
from sickbeard.clients.generic import GenericClient

class uTorrentAPI(GenericClient):
    
    def __init__(self, host=None, username=None, password=None):
        
        super(uTorrentAPI, self).__init__('uTorrent', host, username, password)
      
        self.url = self.host + 'gui/'
            
    def _request(self, method='get', params={}, files=None):

        params.update({'token':self._get_auth()})
        return super(uTorrentAPI, self)._request(method=method, params=params, files=files)

    def _get_auth(self):

        response = self.session.get(self.url + 'token.html')
        if response.status_code == 404:
            return None
        
        try: 
            self.auth = re.findall("<div.*?>(.*?)</", response.text)[0]
        except:    
            return None
            
        return self.auth
      
    def _add_torrent_uri(self, result):

        params={'action':'add-url', 's': result.url}
        return self._request(params=params)

    def _add_torrent_file(self, result):

        params = {'action':'add-file'}
        files={'torrent_file': ('tv.torrent', result.content)}
        return  self._request(method='post', params=params, files=files)

    def _set_torrent_label(self, result):
        
        params = {'action':'setprops', 
                  'hash':result.hash, 
                  's':'label', 
                  'v':sickbeard.TORRENT_LABEL
                  }
        return self._request(params=params)
    
    def _set_torrent_pause(self, result):

        if sickbeard.TORRENT_PAUSED:
            params = {'action':'pause', 'hash':result.hash}
            return self._request(params=params)
        
        return True
        
api = uTorrentAPI()       