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


import urllib2

from hashlib import sha1

try:
    import json
except ImportError:
    from lib import simplejson as json

import sickbeard

from sickbeard import logger

class TraktNotifier:
    """
    A "notifier" for trakt.tv which keeps track of what has and hasn't been added to your library.
    """

    def notify_snatch(self, ep_name):
        pass

    def notify_download(self, ep_name):
        pass

    def update_library(self, ep_obj):
        """
        Sends a request to trakt indicating that the given episode is part of our library.
        
        ep_obj: The TVEpisode object to add to trakt
        """
        
        if sickbeard.USE_TRAKT:
            method = "show/episode/library/"
            method += "%API%"
            
            # URL parameters
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
        """
        Sends a test notification to trakt with the given authentication info and returns a boolean
        representing success.
        
        api: The api string to use
        username: The username to use
        password: The password to use
        
        Returns: True if the request succeeded, False otherwise
        """
        
        method = "account/test/"
        method += "%API%"
        return self._notifyTrakt(method, api, username, password, {})

    def _username(self):
        return sickbeard.TRAKT_USERNAME

    def _password(self):
        return sickbeard.TRAKT_PASSWORD

    def _api(self):
        return sickbeard.TRAKT_API

    def _use_me(self):
        return sickbeard.USE_TRAKT

    def _notifyTrakt(self, method, api, username, password, data = {}):
        """
        A generic method for communicating with trakt. Uses the method and data provided along
        with the auth info to send the command.
        
        method: The URL to use at trakt, relative, no leading slash.
        api: The API string to provide to trakt
        username: The username to use when logging in
        password: The unencrypted password to use when logging in
        
        Returns: A boolean representing success
        """
        logger.log("trakt_notifier: Call method " + method, logger.DEBUG)

        # if the API isn't given then use the config API
        if not api:
            api = self._api()

        # if the username isn't given then use the config username
        if not username:
            username = self._username()
        
        # if the password isn't given then use the config password
        if not password:
            password = self._password()
        password = sha1(password).hexdigest()

        # replace the API string with what we found
        method = method.replace("%API%", api)

        data["username"] = username
        data["password"] = password

        # take the URL params and make a json object out of them
        encoded_data = json.dumps(data);

        # request the URL from trakt and parse the result as json
        try:
            logger.log("trakt_notifier: Calling method http://api.trakt.tv/" + method + ", with data" + encoded_data, logger.DEBUG)
            stream = urllib2.urlopen("http://api.trakt.tv/" + method, encoded_data)
            resp = stream.read()

            resp = json.loads(resp)
            
            if ("error" in resp):
                raise Exception(resp["error"])

        except (IOError):
            logger.log("trakt_notifier: Failed calling method", logger.ERROR)
            return False

        if (resp["status"] == "success"):
            logger.log("trakt_notifier: Succeeded calling method. Result: " + resp["message"], logger.DEBUG)
            return True

        logger.log("trakt_notifier: Failed calling method", logger.ERROR)
        return False

notifier = TraktNotifier
