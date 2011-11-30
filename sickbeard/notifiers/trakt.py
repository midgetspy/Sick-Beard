# Author: Dieter Blomme <dieterblomme@gmail.com>
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


import urllib, urllib2
import socket
import base64
import time, struct
import pprint

from hashlib import sha1

from lib import simplejson as json

import sickbeard

from sickbeard import db
from sickbeard import logger
from sickbeard import common
from sickbeard.exceptions import ex
from sickbeard.encodingKludge import fixStupidEncodings

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

class TraktNotifier:

    def notify_snatch(self, ep_name):
        pass

    def notify_download(self, ep_name):
        pass

    def update_library(self, ep_obj):
        if sickbeard.USE_TRAKT:
            method = "show/episode/library/"
            method += "%API%"
            
            data = {
                'tvdb_id': ep_obj.show.tvdbid,
                'title': ep_obj.show.name,
                'year': ep_obj.show.startyear,
                'episodes': [ {
                    'season': ep_obj.season,
                    'episode': ep_obj.episode
                    } ]
                }
            
            if data is not None:
                self._notifyTrakt(method, None, None, None, data)

    def test_notify(self, api, username, password):
        method = "account/test/"
        method += "%API%"
        return self._notifyTrakt(method, api, username, password, {}, 1)

    def _username(self):
        return sickbeard.TRAKT_USERNAME

    def _password(self):
        return sickbeard.TRAKT_PASSWORD

    def _api(self):
        return sickbeard.TRAKT_API

    def _use_me(self):
        return sickbeard.USE_TRAKT

    def _notifyTrakt(self, method, api, username, password, data = {}, tries=3):
        logger.log("trakt_notifier: Call method " + method, logger.DEBUG)
        logger.log("trakt_notifier: tries " + repr(tries), logger.DEBUG)
        if (tries <= 0):
            logger.log("trakt_notifier: Failed to call method " + method + " completely", logger.ERROR)
            return

        if not api:
            api = self._api()
        if not username:
            username = self._username()
        if not password:
            password = self._password()
        password = sha1(password).hexdigest()

        method = method.replace("%API%", api)

        data["username"] = username
        data["password"] = password

        encoded_data = json.dumps(data);

        try:
            logger.log("trakt_notifier: Calling method http://api.trakt.tv/" + method + ", with data" + encoded_data, logger.DEBUG)
            stream = urllib.urlopen("http://api.trakt.tv/" + method, encoded_data)
            resp = stream.read()

            resp = json.loads(resp)
            
            if ("error" in resp):
                raise Exception(resp["error"])
        except (IOError, json.JSONDecodeError):
            logger.log("trakt_notifier: Failed calling method", logger.ERROR)
            if (tries > 1):
                logger.log("trakt_notifier: Retrying, attempts left: " + str(retry), logger.DEBUG)
                time.sleep(5)
                self._notifyTrakt(method, api, username, password, data, post, tries -  1)
            else:
                return False

        if (resp["status"] == "success"):
            logger.log("trakt_notifier: Succeeded calling method. Result: " + resp["message"], logger.DEBUG)
            return True

        return False

notifier = TraktNotifier
