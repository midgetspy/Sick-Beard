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
import cookielib
import httplib
import re
import sys
import time
from lib import simplejson as json

import sickbeard
from sickbeard import logger
from sickbeard.exceptions import ex

def sendTORRENT(result):

    host = sickbeard.TORRENT_HOST+'gui/'
    
    username = sickbeard.TORRENT_USERNAME
    password = sickbeard.TORRENT_PASSWORD

    # this creates a password manager
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, host, username, password)
    
    # create the AuthHandler
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
      
    opener = urllib2.build_opener(authhandler)
    
    cj = cookielib.CookieJar()
    opener.add_handler(urllib2.HTTPCookieProcessor(cj))

    # All calls to urllib2.urlopen will now use our handler    
    f = urllib2.install_opener(opener)
    
    # authentication is now handled automatically for us
    try:
        open_request = urllib2.urlopen(host)
    except (EOFError, IOError), e:
        logger.log(u"Unable to connect to uTorrent "+ex(e), logger.ERROR)
        return False
    except httplib.InvalidURL, e:
        logger.log(u"Invalid uTorrent host, check your config "+ex(e), logger.ERROR)
        return False
    except urllib2.HTTPError, e:
        if e.code == 401:
            logger.log(u"Invalid uTorrent Username or Password, check your config", logger.ERROR)
            return False    
    except:    
        logger.log(u"Unable to connect to uTorrent, Please check your config", logger.ERROR)
        return False    
    
    try:
        open_request = urllib2.urlopen(host+"token.html")
        token = re.findall("<div.*?>(.*?)</", open_request.read())[0]
    except:
        logger.log(u"Unable to get uTorrent Token "+ex(e), logger.ERROR)
        return False            
    # obtained the token
    
    try:
        #get the list of current torrents
        list_url = "%s?list=1&token=%s" % (host, token)
        open_request = urllib2.urlopen(list_url)
        torrent_list = json.loads(open_request.read())["torrents"]

        add_url = "%s?action=add-url&token=%s&s=%s" % (host, token, urllib.quote_plus(result.url))
        if result.provider.token:
            add_url = add_url + ":COOKIE:" + result.provider.token
        
        logger.log(u"Calling uTorrent with url: "+add_url,logger.DEBUG)

        open_request = urllib2.urlopen(add_url)
        
        #add label and/or pause torrent
        if sickbeard.TORRENT_PATH or sickbeard.TORRENT_PAUSED:
            start_time = time.time()
            new_torrent_hash = ""
            while (True):
                time.sleep(1)
                elapsed_time = time.time() - start_time
                open_request = urllib2.urlopen(list_url)
                new_torrent_list = json.loads(open_request.read())["torrents"]
                for item in new_torrent_list:
                    if item[19] == result.url: 
                        #19 is the current order of the json result of the current version of utorrent.
                        #cannot figure out how to get it by name
                        new_torrent_hash = item[0]
                        break
                    
                if new_torrent_hash:
                    break
                
                if (len(new_torrent_list) - len(torrent_list) == 1):
                    #is this safe?
                    new_torrent_hash = new_torrent_list[len(new_torrent_list) - 1][0]
                    break;
                
                if (elapsed_time > 20): #20 seconds to wait?
                    raise Exception("Error")
            torrent_label = sickbeard.TORRENT_PATH.replace("/", "_").replace("\\", "_")
            if torrent_label:
                set_label_url = "%s?action=setprops&token=%s&hash=%s&s=label&v=%s" % (host, token, new_torrent_hash, torrent_label)
                open_request = urllib2.urlopen(set_label_url)
                
            if sickbeard.TORRENT_PAUSED:
                pause_url = "%s?action=pause&token=%s&hash=%s" % (host, token, new_torrent_hash)
                open_request = urllib2.urlopen(pause_url) 
            
        logger.log(u"Torrent sent to uTorrent successfully", logger.DEBUG)
        return True
    except Exception, e:
        logger.log(u"Unknown failure sending Torrent to uTorrent", logger.ERROR)
        return False 
    
def testAuthentication(host, username, password):
    
    if not host.endswith("/"):
        host = host + "/"
    host = host+'gui/'
    
    # this creates a password manager
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, host, username, password)
    
    # create the AuthHandler
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
      
    opener = urllib2.build_opener(authhandler)
    
    cj = cookielib.CookieJar()
    opener.add_handler(urllib2.HTTPCookieProcessor(cj))

    # All calls to urllib2.urlopen will now use our handler    
    f = urllib2.install_opener(opener)
    
    # authentication is now handled automatically for us
    try:
        open_request = urllib2.urlopen(host)
    except (EOFError, IOError), e:
        return False,"Error: Unable to connect to uTorrent" 
    except httplib.InvalidURL, e:
        return False,"Error: Invalid uTorrent host"
    except urllib2.HTTPError, e:
        if e.code == 401:
            return False,"Error: Invalid uTorrent Username or Password"    
    except:    
        return False,"Error: Unable to connect to uTorrent"    
         
    return True,"Success: Connected and Authenticated" 