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
    
    try:
        opener = urllib2.build_opener(authhandler)
        opener.add_handler(urllib2.HTTPCookieProcessor(cj))
        
        # All calls to urllib2.urlopen will now use our handler
        urllib2.install_opener(opener)  
        
    except (EOFError, IOError), e:
        logger.log(u"Unable to connect to Transmission: "+ex(e), logger.ERROR)
        return False

    #Finding the Session id required for connection    
    try:
        open_request = urllib2.urlopen(host)    
    except urllib2.HTTPError, e:
        msg = str(e.read())
    except httplib.InvalidURL, e:
        logger.log(u"Invalid Transmission host, check your config: "+ex(e), logger.ERROR)
        return False
    except urllib2.URLError, e:
        logger.log(u"Unable to connect to Transmission: "+ex(e), logger.ERROR)
        return False
    
    try:
        session_id = re.search('X-Transmission-Session-Id:\s*(\w+)', msg).group(1)
    except:
        logger.log(u"Unable to get Transmission Session-Id: "+ex(e), logger.ERROR)
        return False             
        
       
    post_data = json.dumps({ 'arguments': { 'filename': result.url,
                                            'pause' : 0    
                                          }, 
                              'method': 'torrent-add',      
                            })
        
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
        