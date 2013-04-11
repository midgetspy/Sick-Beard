# Authors: 
# Pedro Jose Pereira Vieito <pvieito@gmail.com> (Twitter: @pvieito)
# Jens Timmerman <jens.timmerman@gmail.com> & Mr_Orange
#
# URL: https://github.com/mr-orange/Sick-Beard
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard. If not, see <http://www.gnu.org/licenses/>.
#
# Uses the Synology Download Station API v1: http://download.synology.com/download/other/Synology_Download_Station_Official_API_V3.pdf.

import json
import requests

import re
import time
from hashlib import sha1

import sickbeard
from sickbeard import logger
from sickbeard.exceptions import ex
from sickbeard.clients import http_error_code
from lib.bencode import bencode, bdecode
from sickbeard.clients.generic import GenericClient

class DownloadStationAPI(GenericClient):
    
    def __init__(self, host=None, username=None, password=None):
                
        self.name = 'DownloadStation'
        self.username = sickbeard.TORRENT_USERNAME if username is None else username
        self.password = sickbeard.TORRENT_PASSWORD if password is None else password
        self.host = sickbeard.TORRENT_HOST if host is None else host
        
        self.url = None
        self.response = None
        self.auth = None
        self.last_time = time.time()
        self.session = requests.session()
        
        self.url = self.host + 'webapi/DownloadStation/task.cgi'
    
    def _get_auth(self):
        
        auth_url = self.host + 'webapi/auth.cgi?api=SYNO.API.Auth&version=2&method=login&account=' + self.username + '&passwd=' + self.password + '&session=DownloadStation&format=sid'
        
        try:
            self.response = self.session.get(auth_url)
            self.auth = json.loads(self.response.text)['data']['sid']
        except:
            return None
        
        return self.auth
            
    def _add_torrent_uri(self, result):
        
        data = {'api':'SYNO.DownloadStation.Task', 'version':'1', 'method':'create', 'session':'DownloadStation', '_sid':self.auth, 'uri':result.url}
        self._request(method='post', data=data)
        
        return json.loads(self.response.text)['success']
    
    def _add_torrent_file(self, result):
    
        # This should work, but it doesn't
        data = {'api':'SYNO.DownloadStation.Task', 'version':'1', 'method':'create', 'session':'DownloadStation', '_sid':self.auth}
        files = {'file':('tv.torrent', result.hash)}
        self._request(method='post', data=data, files=files)
        
        return json.loads(self.response.text)['success']

api = DownloadStationAPI()
