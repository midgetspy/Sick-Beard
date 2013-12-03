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
from sickbeard.exceptions import ex

###################################################################################################

def sendTORRENT(torrent):    
    
    ###################################################################################################
    
    magnet = 0    
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
    
    host = urlparse(sickbeard.TORRENT_HOST)
    session = torrent.provider.session
    
    if torrent.url.startswith("magnet:"):
        magnet=1
        
    ###################################################################################################
    
    if session:
        ###################################################################################################
        
        try:
            tc = transmissionrpc.Client(host.hostname, host.port, sickbeard.TORRENT_USERNAME, sickbeard.TORRENT_PASSWORD)
            logger.log("[Transmission] Login With Transmission, Successful.", logger.DEBUG)
        except transmissionrpc.TransmissionError, e:
            logger.log("[Transmission] Login With Transmission, Failed - " + transmissionrpc.TransmissionError.message, logger.ERROR)    
            return False,u"[Transmission] Login With Transmission, Failed."
            
        ###################################################################################################
        
        if not magnet:
            try:    
                r = session.get(torrent.url, verify=False)
                logger.log("[Transmission] Succesfully Downloaded Torrent...", logger.DEBUG)
            except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
                logger.log("[Transmission] Download Error  - " + ex(e), logger.ERROR)
                return False,u"[Transmission] Download Error - " + ex(e)
        
        ###################################################################################################
        
        try:
            if magnet:
                tc.add_torrent(torrent.url,**params)
            else:
                tc.add_torrent(base64.b64encode(r.content),**params)    
            logger.log("[Transmission] Added Torrent To Transmission.",logger.DEBUG)
        except Exception, e:
            logger.log("[Transmission] Error Adding Torrent - " + ex(e), logger.ERROR)
            return False,u"[Transmission] Error Adding Torrent."
        
        ###################################################################################################
        
        try:
            tc.set_session(**change_params)
            logger.log("[Transmission] Successfully Set Transmission Session Params.",logger.DEBUG)
        except Exception, e:
            logger.log("[Transmission] Error Setting Torrent Session.",logger.ERROR)
            return False,u"[Transmission] Error Setting Torrent Session."
        
        ###################################################################################################
        
    else:
        logger.log("[Transmission] Error No Requests Session.",logger.ERROR)
        return False, u"[Transmission] Error No Requests Session."
    logger.log("[Transmission] Completed Transaction.",logger.DEBUG)
    return True,u"[Transmission] Completed Transction."
    
###################################################################################################

def testAuthentication(host, username, password):

    try:
        host = urlparse(host)
    except Exception, e:
        return False, u"[Transmission] Host properties are not filled in correctly."

    try:
        tc = transmissionrpc.Client(host.hostname, host.port, sickbeard.TORRENT_USERNAME, sickbeard.TORRENT_PASSWORD)
        return True, u"[Transmission] Success: Connected and Authenticated. RPC version: " + str(tc.rpc_version)
    except Exception, e:
       return False, u"[Transmission] testAuthentication() Error: " + ex(e)

###################################################################################################