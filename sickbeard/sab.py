# Author: Nic Wolfe <nic@wolfeden.ca>
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
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.



import urllib, httplib
import datetime

import sickbeard

from lib import MultipartPostHandler
import urllib2, cookielib
try:
    import json
except ImportError:
    from lib import simplejson as json

from sickbeard.common import USER_AGENT
from sickbeard import logger
from sickbeard.exceptions import ex

def sendNZB(nzb):
    """
    Sends an NZB to SABnzbd via the API.
    
    nzb: The NZBSearchResult object to send to SAB
    """

    # set up a dict with the URL params in it
    params = {}
    if sickbeard.SAB_USERNAME != None:
        params['ma_username'] = sickbeard.SAB_USERNAME
    if sickbeard.SAB_PASSWORD != None:
        params['ma_password'] = sickbeard.SAB_PASSWORD
    if sickbeard.SAB_APIKEY != None:
        params['apikey'] = sickbeard.SAB_APIKEY
    if sickbeard.SAB_CATEGORY != None:
        params['cat'] = sickbeard.SAB_CATEGORY

    # if it aired recently make it high priority
    for curEp in nzb.episodes:
        if datetime.date.today() - curEp.airdate <= datetime.timedelta(days=7):
            params['priority'] = 1

    # if it's a normal result we just pass SAB the URL
    if nzb.resultType == "nzb":
        params['mode'] = 'addurl'
        params['name'] = nzb.url

    # if we get a raw data result we want to upload it to SAB
    elif nzb.resultType == "nzbdata":
        params['mode'] = 'addfile'
        multiPartParams = {"nzbfile": (nzb.name + ".nzb", nzb.extraInfo[0])}

    url = sickbeard.SAB_HOST + "api?" + urllib.urlencode(params)

    logger.log(u"Sending NZB to SABnzbd")
    logger.log(u"URL: " + url, logger.DEBUG)

    try:
        # if we have the URL to an NZB then we've built up the SAB API URL already so just call it 
        if nzb.resultType == "nzb":
            f = urllib.urlopen(url)
        
        # if we are uploading the NZB data to SAB then we need to build a little POST form and send it
        elif nzb.resultType == "nzbdata":
            cookies = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies),
                                          MultipartPostHandler.MultipartPostHandler)
            req = urllib2.Request(url,
                                  multiPartParams,
                                  headers={'User-Agent': USER_AGENT})

            f = opener.open(req)

    except (EOFError, IOError), e:
        logger.log(u"Unable to connect to SAB: " + ex(e), logger.ERROR)
        return False

    except httplib.InvalidURL, e:
        logger.log(u"Invalid SAB host, check your config: " + ex(e), logger.ERROR)
        return False

    # this means we couldn't open the connection or something just as bad
    if f == None:
        logger.log(u"No data returned from SABnzbd, NZB not sent", logger.ERROR)
        return False

    # if we opened the URL connection then read the result from SAB
    try:
        result = f.readlines()
    except Exception, e:
        logger.log(u"Error trying to get result from SAB, NZB not sent: " + ex(e), logger.ERROR)
        return False

    # SAB shouldn't return a blank result, this most likely (but not always) means that it timed out and didn't recieve the NZB
    if len(result) == 0:
        logger.log(u"No data returned from SABnzbd, NZB not sent", logger.ERROR)
        return False

    # massage the result a little bit
    sabText = result[0].strip()

    logger.log(u"Result text from SAB: " + sabText, logger.DEBUG)

    # do some crude parsing of the result text to determine what SAB said
    if sabText == "ok":
        logger.log(u"NZB sent to SAB successfully", logger.DEBUG)
        return True
    elif sabText == "Missing authentication":
        logger.log(u"Incorrect username/password sent to SAB, NZB not sent", logger.ERROR)
        return False
    else:
        logger.log(u"Unknown failure sending NZB to sab. Return text is: " + sabText, logger.ERROR)
        return False

def _checkSabResponse(f):
    try:
        result = f.readlines()
    except Exception, e:
        logger.log(u"Error trying to get result from SAB" + ex(e), logger.ERROR)
        return False, "Error from SAB"

    if len(result) == 0:
        logger.log(u"No data returned from SABnzbd, NZB not sent", logger.ERROR)
        return False, "No data from SAB"

    sabText = result[0].strip()
    sabJson = {}
    try:
        sabJson = json.loads(sabText)
    except ValueError, e:
        pass

    if sabText == "Missing authentication":
        logger.log(u"Incorrect username/password sent to SAB", logger.ERROR)
        return False, "Incorrect username/password sent to SAB"
    elif 'error' in sabJson:
        logger.log(sabJson['error'], logger.ERROR)
        return False, sabJson['error']
    else:
        return True, sabText

def _sabURLOpenSimple(url):
    try:
        f = urllib.urlopen(url)
    except (EOFError, IOError), e:
        logger.log(u"Unable to connect to SAB: " + ex(e), logger.ERROR)
        return False, "Unable to connect"
    except httplib.InvalidURL, e:
        logger.log(u"Invalid SAB host, check your config: " + ex(e), logger.ERROR)
        return False, "Invalid SAB host"
    if f == None:
        logger.log(u"No data returned from SABnzbd", logger.ERROR)
        return False, "No data returned from SABnzbd"
    else:
        return True, f

def getSabAccesMethod(host=None, username=None, password=None, apikey=None):
    url = host + "api?mode=auth"
    
    result, f = _sabURLOpenSimple(url)
    if not result:
        return False, f

    result, sabText = _checkSabResponse(f)
    if not result:
        return False, sabText

    return True, sabText

def testAuthentication(host=None, username=None, password=None, apikey=None):
    """
    Sends a simple API request to SAB to determine if the given connection information is connect
    
    host: The host where SAB is running (incl port)
    username: The username to use for the HTTP request
    password: The password to use for the HTTP request
    apikey: The API key to provide to SAB
    
    Returns: A tuple containing the success boolean and a message
    """
    
    # build up the URL parameters
    params = {}
    params['mode'] = 'queue'
    params['output'] = 'json'
    params['ma_username'] = username
    params['ma_password'] = password
    params['apikey'] = apikey
    url = host + "api?" + urllib.urlencode(params)
    
    # send the test request
    logger.log(u"SABnzbd test URL: " + url, logger.DEBUG)
    result, f = _sabURLOpenSimple(url)
    if not result:
        return False, f

    # check the result and determine if it's good or not
    result, sabText = _checkSabResponse(f)
    if not result:
        return False, sabText
    
    return True, "Success"
    
