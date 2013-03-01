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

import re
import json
from base64 import b64encode

import sickbeard
from sickbeard.clients.generic import GenericClient

class TransmissionAPI(GenericClient):
    
    def __init__(self, host=None, username=None, password=None):
        
        super(TransmissionAPI, self).__init__('Transmission', host, username, password)
      
        self.url = self.host + 'transmission/rpc'

    def _get_auth(self):

        post_data = json.dumps({'method': 'session-get',})
        self.response = self.session.post(self.url, data=post_data.encode('utf-8'))

        try: 
            self.auth = re.search('X-Transmission-Session-Id:\s*(\w+)', self.response.text).group(1)
        except:
            return None     
        
        self.session.headers.update({'x-transmission-session-id': self.auth})
        
        #Validating Transmission authorization
        post_data = json.dumps({'arguments': {},
                                'method': 'session-get',
                                })       
        self._request(method='post', data=post_data)            
        
        return self.auth     

    def _add_torrent_uri(self, result):

        arguments = { 'filename': result.url,
                      'paused': 1 if sickbeard.TORRENT_PAUSED else 0,
                      'download-dir': sickbeard.TORRENT_PATH
                      }
        post_data = json.dumps({ 'arguments': arguments,
                                 'method': 'torrent-add',
                                 })        
        self._request(method='post', data=post_data)

        return self.response.json['result'] == "success"

    def _add_torrent_file(self, result):

        arguments = { 'arguments': b64encode(result.content),
                      'method': 'session-get',
                      'download-dir': sickbeard.TORRENT_PATH
                      }        
        post_data = json.dumps({'arguments': arguments,
                                'method': 'torrent-add',
                                })
        self._request(method='post', data=post_data)
        
        return self.response.json['result'] == "success"

    def _set_torrent_ratio(self, result):
        
        torrent_id = self.response.json["arguments"]["torrent-added"]["id"]
        
        if sickbeard.TORRENT_RATIO == '':
            # Use global settings
            ratio = None
            mode = 0
        elif float(sickbeard.TORRENT_RATIO) == 0:
            ratio = 0
            mode  = 2    
        elif float(sickbeard.TORRENT_RATIO) > 0:
            ratio = float(sickbeard.TORRENT_RATIO)
            mode = 1 # Stop seeding at seedRatioLimit

        arguments = { 'ids': [torrent_id],
                      'seedRatioLimit': ratio,
                      'seedRatioMode': mode
                      } 
        post_data = json.dumps({'arguments': arguments,
                                'method': 'torrent-set',
                                })       
        self._request(method='post', data=post_data)            
        
        return self.response.json['result'] == "success"    

api = TransmissionAPI()