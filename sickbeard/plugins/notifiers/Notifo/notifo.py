# Author: Nic Wolfe <nic@wolfeden.ca>
# Revised by: Shawn Conroyd - 4/12/2011
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

import urllib

import sickbeard

from sickbeard import logger
from sickbeard.exceptions import ex

try:
    import lib.simplejson as json #@UnusedImport
except:
    import json #@Reimport
    
from sickbeard.INotifierPlugin import INotifierPlugin
from sickbeard.config import CheckSection, check_setting_int, check_setting_str, ConfigMigrator

from sickbeard.webserve import Home
import cherrypy
import os

API_URL = "https://%(username)s:%(secret)s@api.notifo.com/v1/send_notification"

class NotifoNotifier(INotifierPlugin):

    def test_notify(self, username, apisecret, title="Test:"):
        return self._sendNotifo("This is a test notification from SickBeard", title, username, apisecret)

    def _sendNotifo(self, msg, title, username, apisecret, label="SickBeard"):
        """
        Sends a message to notify using the given authentication information
        
        msg: The string to send to notifo
        title: The title of the message
        username: The username to send it to
        apisecret: The API key for the username
        label: The label to use for the message (optional)
        
        Returns: True if the message was delivered, False otherwise
        """

        # tidy up the message
        msg = msg.strip()
        
        # build up the URL and parameters
        apiurl = API_URL % {"username": username, "secret": apisecret}
        data = urllib.urlencode({
            "title": title,
            "label": label,
            "msg": msg.encode(sickbeard.SYS_ENCODING)
        })

        # send the request to notifo
        try:
            data = urllib.urlopen(apiurl, data)    
            result = json.load(data)

        except ValueError, e:
            logger.log(u"Unable to decode JSON: "+data, logger.ERROR)
            return False
        
        except IOError, e:
            logger.log(u"Error trying to communicate with notifo: "+ex(e), logger.ERROR)
            return False
        
        data.close()

        # see if it worked
        if result["status"] != "success" or result["response_message"] != "OK":
            return False
        else:
            return True


    def notify_snatch(self, ep_name, title="Snatched:"):
        """
        Send a notification that an episode was snatched
        
        ep_name: The name of the episode that was snatched
        title: The title of the notification (optional)
        """
        if self.NOTIFO_NOTIFY_ONSNATCH:
            self._notifyNotifo(title, ep_name)

    def notify_download(self, ep_name, title="Completed:"):
        """
        Send a notification that an episode was downloaded
        
        ep_name: The name of the episode that was downloaded
        title: The title of the notification (optional)
        """
        if self.NOTIFO_NOTIFY_ONDOWNLOAD:
            self._notifyNotifo(title, ep_name)       

    def _notifyNotifo(self, title, message, username=None, apisecret=None, force=False):
        """
        Send a notifo notification based on the SB settings.
        
        title: The title to send
        message: The message to send
        username: The username to send it to (optional, default to the username in the config)
        apisecret: The API key to use (optional, defaults to the api key in the config)
        force: If true then the notification will be sent even if it is disabled in the config (optional)
        
        Returns: True if the message succeeded, false otherwise
        """
        if not self.USE_NOTIFO and not force:
            logger.log("Notification for Notifo not enabled, skipping this notification", logger.DEBUG)
            return False

        if not username:
            username = self.NOTIFO_USERNAME
        if not apisecret:
            apisecret = self.NOTIFO_APISECRET

        logger.log(u"Sending notification for " + message, logger.DEBUG)

        self._sendNotifo(message, title, username, apisecret)
        return True

    def __init__(self):
        INotifierPlugin .__init__(self)
        
        self.USE_NOTIFO = False
        self.NOTIFO_NOTIFY_ONSNATCH = False
        self.NOTIFO_NOTIFY_ONDOWNLOAD = False
        self.NOTIFO_USERNAME = None
        self.NOTIFO_APISECRET = None
        self.NOTIFO_PREFIX = None
        self.type = INotifierPlugin.NOTIFY_DEVICE
    
    def _addMethod(self):
        def testNotifo(newself, username=None, apisecret=None):
            cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

            result = self.test_notify(username, apisecret)
            if result:
                return "Notifo notification succeeded. Check your Notifo clients to make sure it worked"
            else:
                return "Error sending Notifo notification"
        
        testNotifo.exposed = True
        Home.testNotifo = testNotifo

    def _addStatic(self):
        app = cherrypy.tree.apps[sickbeard.WEB_ROOT]
        app.merge({
             '/images/notifiers/notifo.png': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/images/notifo.png'),
             },
             '/js/configNotifo.js': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/notification.js'),
             }
        })

    def _removeMethod(self):
        if hasattr(Home, 'testNotifo'):
            del Home.testNotifo

    def _removeStatic(self):
        pass

    def updateConfig(self, **kwargs):
        default = {
            'use_notifo': 0,
            'notifo_notify_onsnatch': 0,
            'notifo_notify_ondownload': 0,
            'notifo_username': '',
            'notifo_apisecret': ''
            }

        for key, defval in default.items():
            value = kwargs.get(key, defval)
            val = 1 if value == "on" else value
            
            if hasattr(self, key.upper()):
                setattr(self, key.upper(), val)
            else:
                logger.log("Unknown notification setting: " + key, logger.ERROR)
    
    def readConfig(self, config):
        CheckSection(config, 'Notifo')
        self.USE_NOTIFO = bool(check_setting_int(config, 'Notifo', 'use_notifo', 0))
        self.NOTIFO_NOTIFY_ONSNATCH = bool(check_setting_int(config, 'Notifo', 'notifo_notify_onsnatch', 0))
        self.NOTIFO_NOTIFY_ONDOWNLOAD = bool(check_setting_int(config, 'Notifo', 'notifo_notify_ondownload', 0))
        self.NOTIFO_USERNAME = check_setting_str(config, 'Notifo', 'notifo_username', '')
        self.NOTIFO_APISECRET = check_setting_str(config, 'Notifo', 'notifo_apisecret', '')
        
    def writeConfig(self, new_config):        
        new_config['Notifo'] = {}
        new_config['Notifo']['use_notifo'] = int(self.USE_NOTIFO)
        new_config['Notifo']['notifo_notify_onsnatch'] = int(self.NOTIFO_NOTIFY_ONSNATCH)
        new_config['Notifo']['notifo_notify_ondownload'] = int(self.NOTIFO_NOTIFY_ONDOWNLOAD)
        new_config['Notifo']['notifo_username'] = self.NOTIFO_USERNAME
        new_config['Notifo']['notifo_apisecret'] = self.NOTIFO_APISECRET
    
        return new_config
    
    def activateHook(self):
        self._addMethod()
        self._addStatic()

    def deactivateHook(self):
        self._removeMethod()
        self._removeStatic()