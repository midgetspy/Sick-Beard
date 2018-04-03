###################################################################################################
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
###################################################################################################

import re
import sickbeard

from hashlib import sha1

from lib import requests
from lib.bencode import bencode, bdecode

from sickbeard import logger
from sickbeard.exceptions import ex

###################################################################################################

def _authToken(session=None,host=None, username=None, password=None):
    auth = None

    if not session:
        session = requests.Session()
    
    response = session.get(host + "gui/token.html",auth=(username, password), verify=False,timeout=30)
    if response.status_code == 200:
        auth = re.search("<div.*?>(\S+)<\/div>", response.text).group(1)
    else:
        logger.log("[uTorrent] Authenication Failed.",logger.ERROR)
        
    return auth,session

###################################################################################################

def _TorrentHash(url=None,torrent=None):
    hash=None
    if url.startswith('magnet'):
        hash = re.search('urn:btih:([\w]{32,40})', url).group(1)
        if len(hash) == 32:
            hash = b16encode(b32decode(hash)).upper()
    else:
        info = bdecode(torrent)["info"]
        hash = sha1(bencode(info)).hexdigest().upper()
    return hash

###################################################################################################

def testAuthentication(host=None, username=None, password=None):
    auth,session = _authToken(None,host,username,password)
    if auth:
        return True,u"[uTorrent] Authenication Successful."
    return False,u"[uTorrent] Authenication Failed."

###################################################################################################

def _sendRequest(session,params=None,files=None,fnct=None,):
    try:
        response = session.post(sickbeard.TORRENT_HOST + "gui/",auth=(sickbeard.TORRENT_USERNAME, sickbeard.TORRENT_PASSWORD), params=params, files=files,timeout=30)
    except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
        logger.log("[uTorrent] Problem sending command " + fnct +  " - " + ex(e), logger.ERROR)
        return False
    
    if response.status_code == 200:
        return True
    
    logger.log("[uTorrent] Problem sending command " + fnct + ", return code = " + str(response.status_code))
    return False

###################################################################################################

def sendTORRENT(torrent):
    
    ###################################################################################################
    
    session = None
    torrent_hash = None
    params = {}
    files = {}
    
    ###################################################################################################
        
    session = torrent.provider.session if hasattr(torrent.provider, 'session') else requests.Session()
    
    ###################################################################################################
    
    if session:
        
        ###################################################################################################
        
        auth,session = _authToken(session,sickbeard.TORRENT_HOST,sickbeard.TORRENT_USERNAME, sickbeard.TORRENT_PASSWORD)
        if not auth:
            return False

        ###################################################################################################
        
        if torrent.url.startswith("magnet:"):
            params = {'token': auth, 'action': 'add-url', 's': torrent.url }
            if not _sendRequest(session,params,None,"Add-URL"):
                return False
            torrent_hash = _TorrentHash(torrent.url)
        else:
            try:
                headers = {
                    'Referer': torrent.url
                }
                
                tsession = session.get(torrent.url, verify=False, headers=headers, timeout=60)
                logger.log("[uTorrent] Succesfully downloaded torrent from provider...", logger.DEBUG)
            except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
                logger.log("[uTorrent] Torrent download Error  - " + ex(e), logger.ERROR)
                return False
            
            params = {'token': auth, 'action': 'add-file'}
            files = {'torrent_file': ("", tsession.content)}
            if not _sendRequest(session,params,files,"Add-File"):
                return False
            torrent_hash = _TorrentHash(torrent.url,tsession.content)
        
        ###################################################################################################
        
        if not torrent_hash:
            logger.log("[uTorrent] Could not find torrent's hash to associate with, addtional functions now disabled.",logger.DEBUG)
            return True
        
        ###################################################################################################
        
        if torrent_hash and sickbeard.TORRENT_PAUSED:
            params = {'token': auth, 'action': 'pause', 'hash': torrent_hash}
            _sendRequest(session,params,None,"Pause")
            logger.log("[uTorrent] Paused torrent with hash " + torrent_hash,logger.DEBUG)
        
        ###################################################################################################
        
        if torrent_hash and sickbeard.TORRENT_PATH:
            torrent_label = sickbeard.TORRENT_PATH.replace("/", "_").replace("\\", "_")
            params = {'token': auth, 'action': 'setprops', 'hash': torrent_hash, 's': 'label', 'v': torrent_label}
            _sendRequest(session,params,None,"Label")
            logger.log("[uTorrent] Label set to " + torrent_label + " for torrent with hash " + torrent_hash,logger.DEBUG)
        
        ###################################################################################################
        
        if torrent_hash and sickbeard.TORRENT_RATIO:
            params = {'token': auth, 'action': 'setprops', 'hash': torrent_hash, 's': 'seed_override', 'v': '1'}
            _sendRequest(session,params,None,"SetRatio(seed_override)")
            
            params = {'token': auth, 'action': 'setprops', 'hash': torrent_hash, 's': 'seed_ratio', 'v': float(sickbeard.TORRENT_RATIO)*10}
            _sendRequest(session,params,None,"SetRatio(ratio)")
            logger.log("[uTorrent] Ratio set to " + str(sickbeard.TORRENT_RATIO) + " for torrent with hash " + torrent_hash,logger.DEBUG)
        return True