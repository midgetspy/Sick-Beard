try:
    from hashlib import md5
except:
    from md5 import md5
from random import randint
import time
from urllib import unquote, quote
import os
from hashlib import sha1

import sickbeard
from sickbeard import versionChecker
from lib import requests

def GA():

    visitor_filepath = os.path.join(sickbeard.PROG_DIR, 'visitors.txt')
    if not os.path.exists(visitor_filepath):
        visitor_file = open(visitor_filepath,"w") 
        visitor_file.write(str(randint(0, 0x7fffffff)))
        visitor_file.close()

    try:                    
        visitor_file = open(visitor_filepath,"r")
        VISITOR = visitor_file.read()
        visitor_file.close()
    
        versionCheck = versionChecker.CheckVersion().updater
        versionCheck._find_installed_version()

        VERSION = str(versionCheck._cur_commit_hash)
        NAME = sickbeard.version.SICKBEARD_VERSION
        PATH = quote(NAME + '/' + VERSION)
        UATRACK="UA-44367770-1"
        utm_gif_location = "http://www.google-analytics.com/__utm.gif"
        utm_url = utm_gif_location + "?" + \
            "utmwv=" + VERSION + \
            "&utmn=" + str(randint(0, 0x7fffffff)) + \
            "&utmp=" + quote(PATH+"/") + \
            "&utmac=" + UATRACK + \
            "&utmcc=__utma=%s" % ".".join(["1", "1", VISITOR, "1", "1","2"])
 
        send_request_to_ga(utm_url)
        
    except Exceptions, e:
        logger.log("GA Error: " + ex(e), logger.ERROR)
        
def send_request_to_ga(url):
    try:
        response = requests.get(url)
    except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError), e:
        pass
