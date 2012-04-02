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

import urllib, urllib2
import httplib
import cookielib
import re

try:
    import json
except ImportError:
    from lib import simplejson as json

import sickbeard
from sickbeard import logger
from sickbeard.exceptions import ex

def sendTORRENT(result):

    host = sickbeard.TORRENT_HOST+'transmission/rpc'
    username = sickbeard.TORRENT_USERNAME
    password = sickbeard.TORRENT_PASSWORD

    cj = cookielib.CookieJar()

    #password manager
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, host, username, password)
        
    # create the AuthHandler
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
        
    opener = urllib2.build_opener(authhandler)
    opener.add_handler(urllib2.HTTPCookieProcessor(cj))
            
    # All calls to urllib2.urlopen will now use our handler
    urllib2.install_opener(opener)  

    #Finding the Session id required for connection    
    try:
        open_request = urllib2.urlopen(host)    
    except httplib.InvalidURL, e:
        logger.log(u"Invalid Transmission host, check your config "+ex(e), logger.ERROR)
        return False
    except urllib2.HTTPError, e:
        if e.code == 401:
            logger.log(u"Invalid Transmission Username or Password, check your config", logger.ERROR)
            return False
        else:
             msg = str(e.read())
    except urllib2.URLError, e:
        logger.log(u"Unable to connect to Transmission "+ex(e), logger.ERROR)
        return False
    
    try:
        session_id = re.search('X-Transmission-Session-Id:\s*(\w+)', msg).group(1)
    except:
        logger.log(u"Unable to get Transmission Session-Id "+ex(e), logger.ERROR)
        return False             
        
    post_data = { 'arguments': { 'filename': result.url,
                                            'pause' : 0, 
                                          }, 
                              'method': 'torrent-add',      
                            }
    if not (sickbeard.TORRENT_PATH == ''):
        post_data['arguments']['download_dir'] = sickbeard.TORRENT_PATH

    post_data = json.dumps(post_data)
        
    request = urllib2.Request(url=host, data=post_data.encode('utf-8'))
    request.add_header('X-Transmission-Session-Id', session_id)

    try:
        open_request = urllib2.urlopen(request)
        response = json.loads(open_request.read())
    except:
        return False
    
    if response['result'] == 'success':
        logger.log(u"Torrent sent to Transmission successfully", logger.DEBUG)
        return True
    else:
        logger.log("Unknown failure sending Torrent to Transmission. Return text is: " + response['result'], logger.ERROR)
        return False
    
def testAuthentication(host, username, password):
        
    host = host+'transmission/rpc'

    cj = cookielib.CookieJar()

    #password manager
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, host, username, password)
        
    # create the AuthHandler
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
        
    opener = urllib2.build_opener(authhandler)
    opener.add_handler(urllib2.HTTPCookieProcessor(cj))
            
    # All calls to urllib2.urlopen will now use our handler
    urllib2.install_opener(opener)  

    #Finding the Session id required for connection    
    try:
        open_request = urllib2.urlopen(host)    
    except httplib.InvalidURL, e:
        return False,"Error: Invalid Transmission host"
    except urllib2.HTTPError, e:
        if e.code == 401:
            return False,"Error: Invalid Transmission Username or Password"
        else:
            msg = str(e.read())
    except urllib2.URLError, e:
        return False,"Error: Invalid Transmission Username or Password"

    try:
        session_id = re.search('X-Transmission-Session-Id:\s*(\w+)', msg).group(1)         
        return True,"Success: Connected and Authenticated"
    except:    
        return False,"Error: Unable to get Transmission Session-Id" 
