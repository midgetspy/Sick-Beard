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

from sickbeard.INotifierPlugin import INotifierPlugin
from sickbeard.config import CheckSection, check_setting_int, check_setting_str, ConfigMigrator

from sickbeard.webserve import Home
import cherrypy
import os

class TraktNotifier(INotifierPlugin):
    """
    A "notifier" for trakt.tv which keeps track of what has and hasn't been added to your library.
    """

    def update_library(self, ep_obj, add = True):
        """
        Sends a request to trakt indicating that the given episode is part of our library.
        
        ep_obj: The TVEpisode object to add to trakt
        """
        if add:
            if self.USE_TRAKT:
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
        return self.TRAKT_USERNAME

    def _password(self):
        return self.TRAKT_PASSWORD

    def _api(self):
        return self.TRAKT_API

    def _use_me(self):
        return self.USE_TRAKT

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

    def __init__(self):
        INotifierPlugin .__init__(self)
        
        self.USE_TRAKT = False
        self.TRAKT_USERNAME = None
        self.TRAKT_PASSWORD = None
        self.TRAKT_API = ''
        self.type = INotifierPlugin.NOTIFY_ONLINE
    
    def _addMethod(self):
        def testTrakt(newself, api=None, username=None, password=None):
            cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

            result = self.test_notify(api, username, password)
            if result:
                return "Test notice sent successfully to Trakt"
            else:
                return "Test notice failed to Trakt"
        
        testTrakt.exposed = True
        Home.testTrakt = testTrakt

    def _addStatic(self):
        app = cherrypy.tree.apps[sickbeard.WEB_ROOT]
        app.merge({
             '/images/notifiers/trakt.png': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/images/trakt.png'),
             },
             '/js/configTrakt.js': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/notification.js'),
             }
        })

    def _removeMethod(self):
        if hasattr(Home, 'testTrakt'):
            del Home.testTrakt

    def _removeStatic(self):
        pass

    def updateConfig(self, **kwargs):
        default = {
            'use_trakt': 0,
            'trakt_username': None,
            'trakt_password' : None,
            'trakt_api' : None
            }
        
        for key, defval in default.items():
            value = kwargs.get(key, defval)
            val = 1 if value == "on" else value
            
            if hasattr(self, key.upper()):
                setattr(self, key.upper(), val)
            else:
                logger.log("Unknown notification setting: " + key, logger.ERROR)
    
    def readConfig(self, config):
        CheckSection(config, 'Trakt')
        self.USE_TRAKT = bool(check_setting_int(config, 'Trakt', 'use_trakt', 0))
        self.TRAKT_USERNAME = check_setting_str(config, 'Trakt', 'trakt_username', '')
        self.TRAKT_PASSWORD = check_setting_str(config, 'Trakt', 'trakt_password', '')
        self.TRAKT_API = check_setting_str(config, 'Trakt', 'trakt_api', '')
        
    def writeConfig(self, new_config):        
        new_config['Trakt'] = {}
        new_config['Trakt']['use_trakt'] = int(self.USE_TRAKT)
        new_config['Trakt']['trakt_username'] = self.TRAKT_USERNAME
        new_config['Trakt']['trakt_password'] = self.TRAKT_PASSWORD
        new_config['Trakt']['trakt_api'] = self.TRAKT_API
    
        return new_config
    
    def activateHook(self):
        self._addMethod()
        self._addStatic()

    def deactivateHook(self):
        self._removeMethod()
        self._removeStatic()
