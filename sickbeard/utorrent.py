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
import socket
from sickbeard.name_parser.parser import NameParser, InvalidNameException


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

def _utorrent_api(host):
    try:
        response=urllib2.urlopen(host,timeout=1)

        return True
    except urllib2.HTTPError, e:
        if e.code == 400:
            return True
    except urllib2.URLError, e:
        return False
    return False

def _utorrent_credentials(host, username, password):
    try:
        auth = urllib2.HTTPBasicAuthHandler()
        auth.add_password(
            realm='uTorrent',
            uri=host,
            user='%s'%username,
            passwd=password
        )
        opener = urllib2.build_opener(auth)
        urllib2.install_opener(opener)

        urllib2.urlopen(host + 'gui/token.html')
        return True
    except urllib2.HTTPError, e:
        return False

def _get_token(opener):
    url = sickbeard.UTORRENT_HOST + 'gui/token.html'
    try:
        response = opener.open(url, timeout=5)

        token_re = "<div id='token' style='display:none;'>([^<>]+)</div>"
        match = re.search(token_re, response.read())
        return True, match.group(1)
    except urllib2.HTTPError, e:
        if e.code == 401:
            logger.log("uTorrent username & password are invalid.", logger.ERROR)
            return False, "uTorrent username & password are invalid."
        elif e.code == 404:
            logger.log("uTorrent is not running or the uTorrent API is not enabled.", logger.ERROR)
            return False, "uTorrent is not running or uTorrent API is not enabled."

        logger.log("An error occured while connecting to uTorrent.", logger.ERROR)
        return False, "An error occured while connecting to uTorrent."

def _action(url, host, username, password):
    if _utorrent_api(host):
        opener = _makeOpener(username, password)
        success, token = _get_token(opener)

        if success:
            url = host + 'gui/?token=' + token + url

            try:
                response = opener.open(url)

                return True, json.loads(response.read())
            except urllib2.HTTPError, e:
                if e.code == 401:
                    logger.log("uTorrent username & password are invalid.", logger.ERROR)
                    return False, "uTorrent username & password are invalid."
                elif e.code == 404:
                    logger.log("uTorrent is not running or the uTorrent API is not enabled.", logger.ERROR)
                    return False, "uTorrent is not running or uTorrent API is not enabled."

                logger.log("An error occured while connecting to uTorrent.", logger.ERROR)
                return False, "An error occured while connecting to uTorrent."
            except Exception as e:
                return False, e
        else:
            return False, token

    logger.log("uTorrent is not running or the uTorrent API is not enabled.", logger.ERROR)
    return False, "uTorrent is not running or the uTorrent API is not enabled."

def _findTorrentHash(url):
    i = 0
    while i < 15:
        try:
            if url.startswith('magnet'):
                token_re = "&dn=([^<>]+)&tr="
                match = re.search(token_re, url)
                name = match.group(1)[0:match.group(1).find('&tr=')].replace('_','.').replace('+','.')
            else:
                real_name = url[url.rfind('/') + 1:url.rfind('.torrent')]
                name = real_name.replace('_','.').replace('+','.')
        except:
            logger.log("Unable to retrieve episode name from " + url, logger.WARNING)
            return False

        try:
            myParser = NameParser()
            parse_result = myParser.parse(name)

            success, list = _action('&list=1', sickbeard.UTORRENT_HOST, sickbeard.UTORRENT_USERNAME, sickbeard.UTORRENT_PASSWORD)
        except:
            logger.log(u"Unable to parse the filename " + name + " into a valid episode", logger.WARNING)
            return False

        #Don't fail when a torrent name can't be parsed to a name
        try:
            for torrent in list['torrents']:
                torrent_result = myParser.parse(torrent[2])

                if torrent_result.series_name == parse_result.series_name and torrent_result.season_number == parse_result.season_number and torrent_result.episode_numbers == parse_result.episode_numbers:
                    return torrent[0]

        except InvalidNameException:
            pass

        i += 1
        time.sleep(1)

def testAuthentication(host=None, username=None, password=None):
    success, result = _action('&list=1', host, username, password)

    if not success:
        return False, result

    return True, result

def sendTorrent(result):
    url = '&action=add-url&s=' + quote(result.url).replace('/', '%2F') + '&t=' + str(int(time.time()))

    success, new_result = _action(url, sickbeard.UTORRENT_HOST, sickbeard.UTORRENT_USERNAME, sickbeard.UTORRENT_PASSWORD)

    hash = _findTorrentHash(result.url)

    if hash:
        url = '&action=setprops&s=label&hash=' + hash +'&v=' + quote(sickbeard.UTORRENT_LABEL) + '&t=' + str(int(time.time()))
        _action(url, sickbeard.UTORRENT_HOST, sickbeard.UTORRENT_USERNAME, sickbeard.UTORRENT_PASSWORD)

    return success, new_result