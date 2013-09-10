# Author: Marcos Junior <junalmeida@gmail.com>
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

import urllib, urllib2, cookielib, StringIO, gzip
import httplib
import re

try:
    import json
except ImportError:
    from lib import simplejson as json

import sickbeard
from sickbeard import logger
from sickbeard.exceptions import ex
from urlparse import urlparse

RPC_URL = "json"

def _makeOpener(host, username, password):  
    auth_handler = urllib2.HTTPBasicAuthHandler()
    auth_handler.add_password(realm='deluge',
                              uri=host,
                              user=username,
                              passwd=password)
    opener = urllib2.build_opener(auth_handler)
    urllib2.install_opener(opener)

    cookie_jar = cookielib.CookieJar()
    cookie_handler = urllib2.HTTPCookieProcessor(cookie_jar)

    handlers = [auth_handler, cookie_handler]
    deluge_request = urllib2.build_opener(*handlers)
    
    headers = {'X-Requested-With': 'XMLHttpRequest', 'Content-type': 'application/json', 'Accept-encoding': 'gzip'}    
    post_data = json.dumps({"method": "auth.login",
                            "params": [password],
                            "id": 1
                           })
    request = urllib2.Request(host, post_data, headers)
    response = deluge_request.open(request)
    auth_data = gzip.GzipFile(fileobj=StringIO.StringIO(response.read()))
    jsonObject = json.loads(auth_data.read())
    if jsonObject["error"]:
        deluge_request = None
        raise Exception("Deluge unknown Error." + str(jsonObject["error"]))
    if jsonObject["result"] == False:
        deluge_request = None
        raise Exception("Deluge unauthorized. Check your password.")

    return deluge_request
    
def _request(data):
    host = sickbeard.TORRENT_HOST
    if not host.endswith("/"):
        host += "/"
    host += RPC_URL
    password = sickbeard.TORRENT_PASSWORD
    
    opener = _makeOpener(host, None, password)

    post_data = json.dumps(data)
    request = urllib2.Request(host, post_data, {})
    response = opener.open(request)
    result_data = gzip.GzipFile(fileobj=StringIO.StringIO(response.read()))
    jsonObject = json.loads(result_data.read())
    return jsonObject

    
def sendTORRENT(torrent):    
    result = None
    try:
        ratio = sickbeard.TORRENT_RATIO
        paused = sickbeard.TORRENT_PAUSED
        download_dir = sickbeard.TV_DOWNLOAD_DIR
        cookie = torrent.provider.token
        
        options = {}
        headers = {}
        if cookie:
            headers['Cookie'] = cookie
            
       
        post_data = {"method": "core.add_torrent_url",
                     "params": [torrent.url,
                                options,
                                headers],
                     
                     "id": 2
                    }
        
        result = _request(post_data)
        if result and not result["error"]:
            hash = result["result"]
            if paused:
                post_data = {"method": "core.pause_torrent",
                             "params": [[hash]],
                             "id": 5
                            }
                result = _request(post_data)
            if not (download_dir == ''):
                post_data = {"method": "core.set_torrent_move_completed",
                             "params": [hash, True],
                             "id": 3
                            }        
                result = _request(post_data)
                post_data = {"method": "core.set_torrent_move_completed_path",
                             "params": [hash, download_dir],
                             "id": 4
                            }
                result = _request(post_data)
            if ratio:
                post_data = {"method": "core.set_torrent_stop_at_ratio",
                             "params": [hash, True],
                             "id": 6
                            }        
                result = _request(post_data)
                post_data = {"method": "core.set_torrent_stop_ratio",
                             "params": [hash,float(ratio)],
                             "id": 7
                            }     
                result = _request(post_data)
            logger.log('Torrent added to deluge successfully.', logger.DEBUG)
            return True
        else:
            logger.log("Deluge error: " + str(result["error"]), logger.ERROR)
            return False
    except Exception, e:
        logger.log("Deluge error: " + str(e) + "\r\n" + str(result), logger.ERROR)
        return False
        
    
def testAuthentication(host, username, password):
    if not host.endswith("/"):
        host += "/"
    host += RPC_URL
    try:    
        opener = _makeOpener(host, username, password)
        
        headers = {'X-Requested-With': 'XMLHttpRequest', 'Content-type': 'application/json', 'Accept-encoding': 'gzip'}
        post_data = json.dumps({"method": "auth.login",
                                "params": [password],
                                "id": 1
                                })
        request = urllib2.Request(host, post_data, headers)
    

        response = opener.open(request)
        data = gzip.GzipFile(fileobj=StringIO.StringIO(response.read()))
        jsonObject = json.loads(data.read())
        return True, u"Connected and authenticated."
    except Exception, e:
        return False, u"Cannot connect to Deluge: " + str(e)