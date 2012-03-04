import urllib, urllib2
import cookielib
import httplib
import re
import sys

import sickbeard
from sickbeard import logger
from sickbeard.exceptions import ex

def sendTORRENT(result):

    REMOTE_DBG = False
    
    if REMOTE_DBG:
                # Make pydev debugger works for auto reload.
                # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
        try:
            import pysrc.pydevd as pydevd
            # stdoutToServer and stderrToServer redirect stdout and stderr to eclipse console
            pydevd.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True)
        except ImportError:
            sys.stderr.write("Error: " + "You must add org.python.pydev.debug.pysrc to your PYTHONPATH.")
            sys.exit(1) 

    host = sickbeard.TORRENT_HOST+'gui/'
    username = sickbeard.TORRENT_USERNAME
    password = sickbeard.TORRENT_PASSWORD

    # this creates a password manager
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, host, username, password)

    # create the AuthHandler
    authhandler = urllib2.HTTPBasicAuthHandler(passman)
    
    try:    
        opener = urllib2.build_opener(authhandler)
    
        cj = cookielib.CookieJar()
        opener.add_handler(urllib2.HTTPCookieProcessor(cj))

        # All calls to urllib2.urlopen will now use our handler    
        f = urllib2.install_opener(opener)
   
    except (EOFError, IOError), e:
        logger.log(u"Unable to connect to uTorrent: "+ex(e), logger.ERROR)
        return False
    
    except httplib.InvalidURL, e:
        logger.log(u"Invalid uTorrent host, check your config: "+ex(e), logger.ERROR)
        return False
    
    # authentication is now handled automatically for us
    try:
        pagehandle = urllib2.urlopen(host)
    except:    
        logger.log(u"Unable to connect to uTorrent WebUI, Please check activation of your uTorrent WebUI", logger.ERROR)
        return False    
    
    try:
        pagehandle = urllib2.urlopen(host+"token.html")
        token = re.findall("<div.*?>(.*?)</", pagehandle.read())[0]
    except:
        logger.log(u"Unable to get uTorrent Token: "+ex(e), logger.ERROR)
        return False            
    # obtained the token
    
    add_url = "%s?action=add-url&token=%s&s=%s" % (host, token, urllib.quote_plus(result.url))
    logger.log(u"Sending Episode to uTorrent url: "+add_url,logger.DEBUG)

    try:
        pagehandle = urllib2.urlopen(add_url)
        return pagehandle.read()
    except:
        return False   