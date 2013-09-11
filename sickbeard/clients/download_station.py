# Authors: 
# Pedro Jose Pereira Vieito <pvieito@gmail.com> (Twitter: @pvieito)
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
# Uses the Synology Download Station API: http://download.synology.com/download/other/Synology_Download_Station_Official_API_V3.pdf.

import sickbeard
from sickbeard.clients.generic import GenericClient

class DownloadStationAPI(GenericClient):
    
    def __init__(self, host=None, username=None, password=None):
                
        super(DownloadStationAPI, self).__init__('DownloadStation', host, username, password)

        self.url = self.host + 'webapi/DownloadStation/task.cgi'
    
    def _get_auth(self):
        
        auth_url = self.host + 'webapi/auth.cgi?api=SYNO.API.Auth&version=2&method=login&account=' + self.username + '&passwd=' + self.password + '&session=DownloadStation&format=sid'
        
        try:
            self.response = self.session.get(auth_url)
            self.auth = self.response.json()['data']['sid']
        except:
            return None
        
        return self.auth
            
    def _add_torrent_uri(self, result):
        
        data = {'api':'SYNO.DownloadStation.Task', 
                'version':'1', 'method':'create', 
                'session':'DownloadStation', 
                '_sid':self.auth, 
                'uri':result.url
                }
        self._request(method='post', data=data)
        
        return self.response.json()['success']
    
    def _add_torrent_file(self, result):

        data = {'api':'SYNO.DownloadStation.Task',
                'version':'1',
                'method':'create',
                'session':'DownloadStation',
                '_sid':self.auth
                }
        files = {'file':(result.name + '.torrent', result.content)}
        self._request(method='post', data=data, files=files)
        
        return self.response.json()['success']

api = DownloadStationAPI()
