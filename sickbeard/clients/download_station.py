# Authors: Mr_Orange & Jens Timmerman <jens.timmerman@gmail.com>
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

import sickbeard
from sickbeard import logger
from sickbeard.clients.generic import GenericClient


class DownloadStationAPI(GenericClient):
    
    def __init__(self, host=None, username=None, password=None):
        
        super(DownloadStationAPI, self).__init__('DownloadStation', host, username, password)
      
        self.url = self.host + 'webapi/DownloadStation/task.cgi'

    def _get_auth(self):
        
        params = {'api': 'SYNO.API.Auth',
                  'version': '2',
                  'method': 'login',
                  'account': self.username,
                  'passwd': self.password,
                  'session': 'DownloadStation',
                  'format': 'sid',
                  }

        self.response = self.session.get(self.host + 'auth.cgi', params=params)
        
        if not self.response.json["success"]:
            return None

        self.auth = self.response.json["data"]["sid"]
        
        return self.auth

    def _add_torrent_uri(self, result):

        params = {'api': 'SYNO.DownloadStation.Task',
                  'version': '1',
                  'method': 'create',
                  '_sid': self.auth,
                  'uri': result.url,
                  'session': 'DownloadStation',
                  }
        
        self._request(method='post', params=params)
        
        return self.response.json["success"]
            
    def _add_torrent_file(self, result):

        params = {'api': 'SYNO.DownloadStation.Task',
                  'version': '1',
                  'method': 'create',
                  '_sid': self.auth,
                  'file': 'tv.torrent',
                  'session': 'DownloadStation',
                  }
        
        self._request(method='post', params=params, files={'file': result.content})
    
        return self.response.json["success"]
    
api = DownloadStationAPI()    
    