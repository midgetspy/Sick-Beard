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
import urllib2, cookielib, base64
try:
    import json
except ImportError:
    from lib import simplejson as json

from sickbeard.common import USER_AGENT
from sickbeard import logger
from sickbeard.exceptions import ex
from urllib import quote
import cookielib
import re
import time



def _makeOpener(username, password):
    auth_handler = urllib2.HTTPBasicAuthHandler()
    auth_handler.add_password(realm='uTorrent',
                              uri=sickbeard.UTORRENT_HOST,
                              user=username,
                              passwd=password)
    opener = urllib2.build_opener(auth_handler)
    urllib2.install_opener(opener)

    cookie_jar = cookielib.CookieJar()
    cookie_handler = urllib2.HTTPCookieProcessor(cookie_jar)

    handlers = [auth_handler, cookie_handler]
    return urllib2.build_opener(*handlers)

def _get_token(opener):
    url = sickbeard.UTORRENT_HOST + 'gui/token.html'
    response = opener.open(url)
    token_re = "<div id='token' style='display:none;'>([^<>]+)</div>"
    match = re.search(token_re, response.read())
    return match.group(1)

def _action(url, host, username, password):
    opener = _makeOpener(username, password)
    url = host + 'gui/?token=' + _get_token(opener) + url

    request = urllib2.Request(url)

    try:
        response = opener.open(request)
        return True, json.loads(response.read())
    except Exception as e:
        return False, e

def _findTorrentHash(list, new_list):
    for torrent in new_list['torrents']:
        found = False

        for old_torrent in list['torrents']:
            if old_torrent[0] == torrent[0]:
                found = True

        if not found:
            return torrent[0]

    return False

def testAuthentication(host=None, username=None, password=None):
    success, result = _action('&list=1', host, username, password)

    if not success:
        return False, "Unable to connect"

    return True, "Success"

def sendTorrent(result):
    success, list = _action('&list=1', sickbeard.UTORRENT_HOST, sickbeard.UTORRENT_USERNAME, sickbeard.UTORRENT_PASSWORD)

    url = '&action=add-url&s=' + quote(result.url).replace('/', '%2F') + '&t=' + str(int(time.time()))

    success, new_result = _action(url, sickbeard.UTORRENT_HOST, sickbeard.UTORRENT_USERNAME, sickbeard.UTORRENT_PASSWORD)

    #We need to sleep 10 seconds to make sure that the torrent is downloaded.
    #Still need to find a better solution for this.
    time.sleep(10)
    success, new_list = _action('&list=1', sickbeard.UTORRENT_HOST, sickbeard.UTORRENT_USERNAME, sickbeard.UTORRENT_PASSWORD)

    hash = _findTorrentHash(list, new_list)

    if hash:
        url = '&action=setprops&s=label&hash=' + hash +'&v=' + quote(sickbeard.UTORRENT_LABEL) + '&t=' + str(int(time.time()))
        _action(url, sickbeard.UTORRENT_HOST, sickbeard.UTORRENT_USERNAME, sickbeard.UTORRENT_PASSWORD)

    return success, new_result