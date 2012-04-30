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

import urllib2
import httplib
import cookielib
import re
from StringIO import StringIO
import gzip

try:
    import json
except ImportError:
    from lib import simplejson as json

import sickbeard
from sickbeard import logger
from sickbeard.exceptions import ex
from urlparse import urlparse

def sendTORRENT(result):

    host = sickbeard.TORRENT_HOST+'json'
    password = sickbeard.TORRENT_PASSWORD

    # this creates a password manager
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, host, "admin", password)
    
    # create the AuthHandler
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
      
    opener = urllib2.build_opener(authhandler)
    
    cj = cookielib.CookieJar()
    opener.add_handler(urllib2.HTTPCookieProcessor(cj))

    # All calls to urllib2.urlopen will now use our handler    
    urllib2.install_opener(opener)
    
    post_data = json.dumps({ "method": "auth.login",
                             "params": [password],
                             "id": 1
                           })
    request = urllib2.Request(url=host, data=post_data.encode('utf-8'))

    try:
        response = urllib2.urlopen(request)
    except (EOFError, IOError), e:
        logger.log(u"Unable to connect to Deluge "+ex(e), logger.ERROR)
        return False
    except httplib.InvalidURL, e:
        logger.log(u"Invalid Deluge host, check your config "+ex(e), logger.ERROR)
        return False
    except urllib2.HTTPError, e:
        if e.code == 401:
            logger.log(u"Invalid Deluge Username or Password, check your config", logger.ERROR)
            return False    
    except:    
        logger.log(u"Unable to connect to Deluge, Please check your config", logger.ERROR)
        return False    

    try:            
        session_id = re.search('_session_id=\s*(\w+)', response.info().get('Set-Cookie'))
    except:
        logger.log(u"Unable to get Deluge Authorization ID "+ex(e), logger.ERROR)
        return False    
   
    if result.url.startswith('magnet'):
        post_data = json.dumps({ "method": 'core.add_torrent_magnet',
                                 "params": [result.url,{}],
                                 "id": 2
                              })
    else:    
        post_data = json.dumps({ "method": 'core.add_torrent_url',
                                 "params": [result.url,{}],
                                 "id": 2
                              })
    
    logger.log(u"Sending Torrent to Deluge Client", logger.DEBUG)
                
    try:
        request = urllib2.Request(url=host, data=post_data.encode('utf-8'))
        response = urllib2.urlopen(request)
        file_obj = StringIO(response.read())
        buffer = gzip.GzipFile(fileobj=file_obj)
        data = json.loads(buffer.read())
        if data["error"] == None:
            logger.log(u"Torrent sent to Deluge successfully", logger.DEBUG)
            return True
        else:
            logger.log(u"Unknown failure sending Torrent to Deluge. Return text is: " + data["error"], logger.ERROR)            
    except:
        logger.log(u"Unknown failure sending Torrent to Deluge", logger.ERROR)
        return False    
  
def testAuthentication(host, username, password):
    
    host = host+'json'
    
    # this creates a password manager
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, host, username, password)
    
    # create the AuthHandler
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
      
    opener = urllib2.build_opener(authhandler)
    
    cj = cookielib.CookieJar()
    opener.add_handler(urllib2.HTTPCookieProcessor(cj))

    # All calls to urllib2.urlopen will now use our handler    
    urllib2.install_opener(opener)
    
    # authentication is now handled automatically for us
    post_data = json.dumps({ "method": "auth.login",
                             "params": [password],
                             "id": 1
                           })
    
    request = urllib2.Request(url=host, data=post_data.encode('utf-8'))

    try:    
        response = urllib2.urlopen(request)
    except (EOFError, IOError), e:
        return False,"Error: Unable to connect to Deluge" 
    except httplib.InvalidURL, e:
        return False,"Error: Invalid Deluge host"
    except:    
        return False,"Error: Unable to connect to Deluge"    
         
    try:            
        session_id = re.search('_session_id=\s*(\w+)', response.info().get('Set-Cookie'))
    except:
        return False,"Error: Invalid Deluge Password"    
         
    return True,"Success: Connected and Authenticated" 