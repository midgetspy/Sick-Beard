# Author: Jodi Jones <venom@gen-x.co.nz>
# URL: https://github.com/VeNoMouS/Sick-Beard
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

import sickbeard
from lib import requests
from base64 import b64encode
from sickbeard import logger

try:
    import json
except ImportError:
    from lib import simplejson as json

###################################################################################################

class Deluge:
    
    ###################################################################################################
    
    def __init__(self):
        self.seq_id = 1
        self.jdata = None
        self.session = None
        self.deluge_host = None
        self.label_created = False
        self.name = "Deluge"
        
        logger.log("[" + self.name + "] initializing...", logger.DEBUG)
        
    ###################################################################################################
    
    def _authenicate(self,host,password):
        try:
            if not host.startswith('http'):
                host = 'http://' + host
            
            if host.endswith('/'):
                host = host.rstrip('/')
                        
            if not host.endswith("/json"):
                host = host + "/json"
                
            self.deluge_host = host
        except Exception:
            logger.log("[" + self.name + "] _authenicate() Host properties are not filled in correctly.",logger.ERROR)
            return False, u"[" + self.name + "] Host properties are not filled in correctly."
        
        if self._sendRequest({'method': 'auth.login','params': [password],'id': self.seq_id }):
            logger.log("[" + self.name + "] _authenicate() Success: Connected and Authenticated.",logger.DEBUG)
            return True,u"[" + self.name + "] _authenicate() Success: Connected and Authenticated."
        else:
            logger.log("[" + self.name + "] _authenicate() Authenication Failure...",logger.ERROR)
            return False,u"[" + self.name + "] _authenicate() Authenication Failure..."
        
    ###################################################################################################

    def _sendRequest(self,post_data):    
        if self.session:
            try:
                self.jdata = None
                self.seq_id+=1
                r = self.session.post(self.deluge_host, data=json.dumps(post_data), timeout=30, verify=False) 
                if not r.json()['error']:
                    self.jdata = r.json()
                    return True
                else:
                    logger.log("[" + self.name + "] _sendRequest() request failed..  ", logger.DEBUG)
                    return False
            except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
                logger.log("[" + self.name + "]  _sendRequest() Error  - " + str(e), logger.ERROR)
                return False
        logger.log("[" + self.name + "] _sendRequest() ... no session??",logger.ERROR)
        return False
    
    ###################################################################################################
    
    def _sendTORRENT(self,torrent):
        ###################################################################################################
        try:
            if hasattr(torrent.provider, 'session'):
                self.session = torrent.provider.session
            else:
                self.session = requests.Session()
        except Exception:
            self.session = requests.Session()
            
        if not torrent.url.startswith("magnet:"):
            ###################################################################################################
            # Attempt to download torrent file.
            try:
                r =  self.session.get(torrent.url, verify=False)
            except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
               logger.log("[" + self.name + "] _sendTORRENT() Error grabbing torrent " + torrent.url + " - " + ex(e), logger.ERROR)
               return False
            if r.content:
                logger.log("[" + self.name + "] _sendTORRENT() Succesfully downloaded torrent from " + torrent.url, logger.DEBUG)
            else:
                logger.log("[" + self.name + "] _sendTORRENT() Error no content data found for torrent file.",logger.ERROR)
                return False
        
        ###################################################################################################
        
        if not self._authenicate(sickbeard.TORRENT_HOST,sickbeard.TORRENT_PASSWORD)[0]:
                    return False

        ###################################################################################################
        
        options = {} 
        if sickbeard.TORRENT_PATH:
            options['download_location'] = sickbeard.TORRENT_PATH
        if sickbeard.TV_DOWNLOAD_DIR:
            options['move_completed'] = "true"
            options['move_completed_path'] = sickbeard.TV_DOWNLOAD_DIR
        
        ###################################################################################################
        
        if torrent.url.startswith("magnet:"):
            if not self._sendRequest({'method': 'core.add_torrent_magnet', 'params': [torrent.url, options], 'id': self.seq_id}):
                    logger.log("[" + self.name + "] _sendTORRENT() Error grabbing torrent from " + torrent.url,logger.ERROR)
                    return False
            else:
                logger.log("[" + self.name + "] _sendTORRENT() Downloaded torrent from " + torrent.url, logger.DEBUG)
        else:
            if not self._sendRequest({'method': 'core.add_torrent_file', 'params': ['',b64encode(r.content), options], 'id': self.seq_id}):
                logger.log("[" + self.name + "] _sendTORRENT() Error Adding torrent to deluge.",logger.ERROR)
                return False
        ###################################################################################################
        
        torrentHash = self.jdata['result']
        
        ###################################################################################################
        
        if torrentHash and self.jdata['id'] == (self.seq_id-1):
            
            ###################################################################################################
            
            if sickbeard.TORRENT_PAUSED:
                if not self._sendRequest({'method': 'core.pause_torrent', 'params': [[torrenthash]], 'id': self.seq_id}):
                    logger.log("[" + self.name + "] _sendTORRENT() Error setting Pause on torrent hash " + torrentHash,logger.ERROR)
            
            ###################################################################################################
            
            if  sickbeard.TORRENT_RATIO:
                if not self._sendRequest({'method': 'core.set_torrent_stop_at_ratio', 'params': [torrentHash, True], 'id': self.seq_id}):
                    logger.log("[" + self.name + "] _sendTORRENT() Error setting Stop At Ratio on torrent hash " + torrentHash,logger.ERROR)
                
                if not self._sendRequest({'method': 'core.set_torrent_stop_ratio','params': [torrentHash,float(sickbeard.TORRENT_RATIO)],'id': self.seq_id}):
                    logger.log("[" + self.name + "] _sendTORRENT() Error setting Stop Ration On torrent hash " + torrentHash,logger.ERROR)
                    
            ###################################################################################################
            
            if sickbeard.TORRENT_LABEL:
                sickbeard.TORRENT_LABEL = sickbeard.TORRENT_LABEL.replace("/", "_").replace("\\", "_")
                if not self._sendRequest({'method': 'label.get_labels', 'params': [], 'id': self.seq_id}):
                    logger.log("[" + self.name + "] _sendTORRENT() Error requesting Labels.",logger.ERROR)
                else:
                    if sickbeard.TORRENT_LABEL not in self.jdata['result']:
                        logger.log("[" + self.name + "] _sendTORRENT() " + sickbeard.TORRENT_LABEL + " label does not exist, Attempting to add it.",logger.DEBUG)
                        if not self._sendRequest({'method': 'label.add', 'params': [sickbeard.TORRENT_LABEL], 'id': self.seq_id}):
                            logger.log("[" + self.name + "] _sendTORRENT() Could not create label " + sickbeard.TORRENT_LABEL,logger.ERROR)
                        
                    ###################################################################################################
                    # Recheck & Set Label on hash.
                    
                    if self._sendRequest({'method': 'label.get_labels', 'params': [], 'id': self.seq_id}):
                        if sickbeard.TORRENT_LABEL in self.jdata['result']:
                            if not self._sendRequest({'method': 'label.set_torrent', 'params': [torrentHash, sickbeard.TORRENT_LABEL], 'id': self.seq_id}):
                                logger.log("[" + self.name + "] _sendTORRENT() Error setting label " + sickbeard.TORRENT_LABEL + " on Torrent Hash " + torrentHash,logger.ERROR)
                        else:
                            logger.log("[" + self.name + "] _sendTORRENT() Could not find label " + sickbeard.TORRENT_LABEL + ", giving up", logger.ERROR)
                    else:
                        logger.log("[" + self.name + "] _sendTORRENT() Error requesting Labels.",logger.ERROR)
                
            ###################################################################################################
            
            logger.log("[" + self.name + "] _sendTORRENT() Torrent added successfully.", logger.DEBUG)
            return True
        logger.log("[" + self.name + "] _sendTORRENT() Failed, no hash returned.",logger.ERROR)
        return False

###################################################################################################

def testAuthentication(host, username, password):
    deluge = Deluge()
    deluge.session = requests.Session()
    return deluge._authenicate(host,password)

###################################################################################################

def sendTORRENT(torrent):
    deluge = Deluge()
    return deluge._sendTORRENT(torrent)

###################################################################################################