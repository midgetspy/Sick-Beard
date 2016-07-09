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

import base64
import sickbeard

from lib import requests
from sickbeard import logger
from urlparse import urlparse
from lib import transmissionrpc

###################################################################################################

def sendTORRENT(torrent):    
    
    ###################################################################################################
    
    params = {}
    change_params = {}

    ###################################################################################################
    
    if sickbeard.TORRENT_PAUSED:
        params['paused'] = 1
    
    ###################################################################################################
    
    if not (sickbeard.TORRENT_PATH == ''):
        params['download_dir'] = sickbeard.TORRENT_PATH
    
    ###################################################################################################
    
    if not (sickbeard.TORRENT_RATIO == ''):
        change_params['seedRatioLimit'] = sickbeard.TORRENT_RATIO
    else:
        change_params['seedRatioMode'] = 1
        
    ###################################################################################################
    
    host = sickbeard.TORRENT_HOST
    if not host.startswith('http'):
        host = 'http://' + sickbeard.TORRENT_HOST
    host = urlparse(host)
    session = None
    if hasattr(torrent.provider, 'session'):
        session = torrent.provider.session
    else:
        session = requests.Session()

    ###################################################################################################
    
    if session:
        ###################################################################################################
        
        try:
            address = host.hostname
            if host.scheme:
                address = host.scheme + '://' + address
            if host.port:
                address += ':' + str(host.port)
            if host.path in ['','/']:
                address += '/transmission/rpc'
            else:
                address += host.path
            tc = transmissionrpc.Client(address, host.port, sickbeard.TORRENT_USERNAME, sickbeard.TORRENT_PASSWORD)
            logger.log("[Transmission] Login With Transmission, Successful.", logger.DEBUG)
        except transmissionrpc.TransmissionError, e:
            logger.log("[Transmission] Login With Transmission, Failed.",logger.ERROR)
            return False
            
        ###################################################################################################
        
        if not torrent.url.startswith("magnet:"):
            try:
                headers = {
                    'User-Agent': sickbeard.common.USER_AGENT,
                    'Referer': torrent.url
                }
                
                r = session.get(torrent.url, verify=False, headers=headers, timeout=60)
                logger.log("[Transmission] Succesfully Downloaded Torrent...", logger.DEBUG)
            except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
                logger.log("[Transmission] Download Error  - " + str(e), logger.ERROR)
                return False
        
        ###################################################################################################
        
        try:
            if torrent.url.startswith("magnet:"):
                tc.add_torrent(torrent.url,**params)
            else:
                tc.add_torrent(base64.b64encode(r.content),**params)    
            logger.log("[Transmission] Added Torrent To Transmission.",logger.DEBUG)
        except Exception, e:
            logger.log("[Transmission] Error Adding Torrent - " + str(e) + " - " + str(torrent.url), logger.ERROR)
            return False
        
        ###################################################################################################
        
        try:
            tc.set_session(**change_params)
            logger.log("[Transmission] Successfully Set Transmission Session Params.",logger.DEBUG)
        except Exception, e:
            logger.log("[Transmission] Error Setting Torrent Session.",logger.ERROR)
            return False
        
        ###################################################################################################
        
    else:
        logger.log("[Transmission] Error No Requests Session. For the url of " + torrent.url,logger.ERROR)
        return False
    logger.log("[Transmission] Completed Transaction.",logger.DEBUG)
    return True
    
###################################################################################################

def testAuthentication(host, username, password):

    try:
        if not host.startswith('http'):
            host = 'http://' + host
        host = urlparse(host)
    except Exception, e:
        return False, u"[Transmission] Host properties are not filled in correctly."

    try:
        address = host.hostname
        if host.scheme:
            address = host.scheme + '://' + address
        if host.port:
            address += ':' + str(host.port)
        if host.path in ['','/']:
            address += '/transmission/rpc'
        else:
            address += host.path
        tc = transmissionrpc.Client(address, host.port, sickbeard.TORRENT_USERNAME, sickbeard.TORRENT_PASSWORD)
        return True, u"[Transmission] Success: Connected and Authenticated. RPC version: " + str(tc.rpc_version)
    except Exception, e:
       return False, u"[Transmission] testAuthentication() Error: " + str(e)

###################################################################################################
