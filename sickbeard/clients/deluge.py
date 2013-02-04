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
import time
import json
from base64 import b64encode

import sickbeard
from sickbeard import logger
from sickbeard.exceptions import ex
from lib import requests
from sickbeard.clients.generic import GenericClient

class DelugeAPI(GenericClient): 

    def __init__(self, host=None, username=None, password=None):

        super(DelugeAPI, self).__init__('Deluge', host, username, password)
                
        self.url = sickbeard.TORRENT_HOST + 'json' if host is None else host + 'json'
           
    def _get_auth(self):

        post_data = json.dumps({ "method": "auth.login",
                                 "params": [self.password],
                                 "id": 1
                                 })
        response = self.session.post(self.url, data=post_data.encode('utf-8'))
        self.auth = response.json['result']
        return self.auth
     
    def _add_torrent_uri(self, result):

        post_data = json.dumps({ "method": "core.add_torrent_magnet",
                                 "params": [result.url,{}],
                                 "id": 2
                                 })
        return self._request(method='post', data=post_data)
            
    def _add_torrent_file(self, result):

        post_data = json.dumps({ "method": "core.add_torrent_file",
                                 "params": ['tv.torrent', b64encode(result.content),{}],
                                 "id": 2
                                 })           
        return self._request(method='post', data=post_data)
    
    def _set_torrent_label(self, result):
        # First add the label
        post_data = json.dumps({ "method": "label.add",
                                 "params": [sickbeard.TORRENT_LABEL],
                                 "id": 3
                                 })
        self._request(method='post', data=post_data)

        # Then set the label to torrent    
        post_data = json.dumps({ "method": "label.set_torrent",
                                 "params": [self._get_torrent_hash(result), sickbeard.TORRENT_LABEL],
                                 "id": 4
                                 })             
        return self._request(method='post', data=post_data)
    
    def _set_torrent_ratio(self, result):

        if sickbeard.TORRENT_RATIO != '':
            post_data = json.dumps({"method": "core.set_torrent_stop_at_ratio",
                                    "params": [self._get_torrent_hash(result), True],
                                    "id": 5
                                    })        
            self._request(method='post', data=post_data)
            
            post_data = json.dumps({"method": "core.set_torrent_stop_ratio",
                                    "params": [self._get_torrent_hash(result),float(sickbeard.TORRENT_RATIO)],
                                    "id": 6
                                    })        
            return self._request(method='post', data=post_data)

    def _set_torrent_path(self, result):

        if sickbeard.TORRENT_PATH != '':
            post_data = json.dumps({ "method": "core.set_torrent_move_on_completed",
                                   "params": [self._get_torrent_hash(result), True],
                                   "id": 7
                                   })        
            self._request(method='post', data=post_data)
            
            post_data = json.dumps({ "method": "core.set_torrent_move_on_completed_path",
                                   "params": [self._get_torrent_hash(result), sickbeard.TORRENT_PATH],
                                   "id": 8
                                   })        
            return self._request(method='post', data=post_data)
        
    def _set_torrent_pause(self, result):
        
        if sickbeard.TORRENT_PAUSED:
            post_data = json.dumps({ "method": "core.pause_torrent",
                                   "params": [self._get_torrent_hash(result)],
                                   "id": 8
                                   })
            return self._request(method='post', data=post_data)

api = DelugeAPI()