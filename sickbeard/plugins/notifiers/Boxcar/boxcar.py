# Author: Marvin Pinto <me@marvinp.ca>
# Author: Dennis Lutter <lad1337@gmail.com>
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
import time

import sickbeard

from sickbeard import logger
from sickbeard.common import notifyStrings, NOTIFY_SNATCH, NOTIFY_DOWNLOAD
from sickbeard.exceptions import ex

from sickbeard.INotifierPlugin import INotifierPlugin
from sickbeard.config import CheckSection, check_setting_int, check_setting_str, ConfigMigrator

from sickbeard.webserve import Home
import cherrypy
import os

API_URL = "https://boxcar.io/devices/providers/fWc4sgSmpcN6JujtBmR6/notifications"

class BoxcarNotifier(INotifierPlugin):

    def test_notify(self, email, title="Test"):
        return self._sendBoxcar("This is a test notification from SickBeard", title, email)

    def _sendBoxcar(self, msg, title, email, subscribe=False):
        """
        Sends a boxcar notification to the address provided
        
        msg: The message to send (unicode)
        title: The title of the message
        email: The email address to send the message to (or to subscribe with)
        subscribe: If true then instead of sending a message this function will send a subscription notification (optional, default is False)
        
        returns: True if the message succeeded, False otherwise
        """
        
        # build up the URL and parameters
        msg = msg.strip()
        curUrl = API_URL

        # if this is a subscription notification then act accordingly
        if subscribe:
            data = urllib.urlencode({'email': email})
            curUrl = curUrl + "/subscribe"
        
        # for normal requests we need all these parameters
        else:
            data = urllib.urlencode({
                'email': email,
                'notification[from_screen_name]': title,
                'notification[message]': msg.encode('utf-8'),
                'notification[from_remote_service_id]': int(time.time())
                })


        # send the request to boxcar
        try:
            req = urllib2.Request(curUrl)
            handle = urllib2.urlopen(req, data)
            handle.close()
            
        except urllib2.URLError, e:
            # if we get an error back that doesn't have an error code then who knows what's really happening
            if not hasattr(e, 'code'):
                logger.log("Boxcar notification failed." + ex(e), logger.ERROR)
                return False
            else:
                logger.log("Boxcar notification failed. Error code: " + str(e.code), logger.WARNING)

            # HTTP status 404 if the provided email address isn't a Boxcar user.
            if e.code == 404:
                logger.log("Username is wrong/not a boxcar email. Boxcar will send an email to it", logger.WARNING)
                return False
            
            # For HTTP status code 401's, it is because you are passing in either an invalid token, or the user has not added your service.
            elif e.code == 401:
                
                # If the user has already added your service, we'll return an HTTP status code of 401.
                if subscribe:
                    logger.log("Already subscribed to service", logger.ERROR)
                    # i dont know if this is true or false ... its neither but i also dont know how we got here in the first place
                    return False
                
                #HTTP status 401 if the user doesn't have the service added
                else:
                    subscribeNote = self._sendBoxcar(msg, title, email, True)
                    if subscribeNote:
                        logger.log("Subscription send", logger.DEBUG)
                        return True
                    else:
                        logger.log("Subscription could not be send", logger.ERROR)
                        return False
            
            # If you receive an HTTP status code of 400, it is because you failed to send the proper parameters
            elif e.code == 400:
                logger.log("Wrong data send to boxcar", logger.ERROR)
                return False

        logger.log("Boxcar notification successful.", logger.DEBUG)
        return True

    def notify_snatch(self, ep_name, title=notifyStrings[NOTIFY_SNATCH]):
        if self.BOXCAR_NOTIFY_ONSNATCH:
            self._notifyBoxcar(title, ep_name)
            

    def notify_download(self, ep_name, title=notifyStrings[NOTIFY_DOWNLOAD]):
        if self.BOXCAR_NOTIFY_ONDOWNLOAD:
            self._notifyBoxcar(title, ep_name)

    def _notifyBoxcar(self, title, message, username=None, force=False):
        """
        Sends a boxcar notification based on the provided info or SB config

        title: The title of the notification to send
        message: The message string to send
        username: The username to send the notification to (optional, defaults to the username in the config)
        force: If True then the notification will be sent even if Boxcar is disabled in the config
        """

        if not self.USE_BOXCAR and not force:
            logger.log("Notification for Boxcar not enabled, skipping this notification", logger.DEBUG)
            return False

        # if no username was given then use the one from the config
        if not username:
            username = self.BOXCAR_USERNAME

        logger.log("Sending notification for " + message, logger.DEBUG)

        self._sendBoxcar(message, title, username)
        return True

    def __init__(self):
        INotifierPlugin .__init__(self)
        
        self.USE_BOXCAR = False
        self.BOXCAR_NOTIFY_ONSNATCH = False
        self.BOXCAR_NOTIFY_ONDOWNLOAD = False
        self.BOXCAR_USERNAME = None
        self.BOXCAR_PASSWORD = None
        self.BOXCAR_PREFIX = None
        self.type = INotifierPlugin.NOTIFY_DEVICE
    
    def _addMethod(self):
        def testBoxcar(newself, username=None):
            cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

            result = self.test_notify(username)
            if result:
                return "Boxcar notification succeeded. Check your Boxcar clients to make sure it worked"
            else:
                return "Error sending Boxcar notification"
        
        testBoxcar.exposed = True
        Home.testBoxcar = testBoxcar

    def _addStatic(self):
        app = cherrypy.tree.apps[sickbeard.WEB_ROOT]
        app.merge({
             '/images/notifiers/boxcar.png': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/images/boxcar.png'),
             },
             '/js/configBoxcar.js': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/notification.js'),
             }
        })

    def _removeMethod(self):
        if hasattr(Home, 'testBoxcar'):
            del Home.testBoxcar

    def _removeStatic(self):
        pass

    def updateConfig(self, **kwargs):
        default = {
            'use_boxcar': 0,
            'boxcar_notify_onsnatch' : 0,
            'boxcar_notify_ondownload' : 0,
            'boxcar_username': None
            }
        
        for key, defval in default.items():
            value = kwargs.get(key, defval)
            val = 1 if value == "on" else value
            
            if hasattr(self, key.upper()):
                setattr(self, key.upper(), val)
            else:
                logger.log("Unknown notification setting: " + key, logger.ERROR)
    
    def readConfig(self, config):
        CheckSection(config, 'Boxcar')
        self.USE_BOXCAR = bool(check_setting_int(config, 'Boxcar', 'use_boxcar', 0))
        self.BOXCAR_NOTIFY_ONSNATCH = bool(check_setting_int(config, 'Boxcar', 'boxcar_notify_onsnatch', 0))
        self.BOXCAR_NOTIFY_ONDOWNLOAD = bool(check_setting_int(config, 'Boxcar', 'boxcar_notify_ondownload', 0))
        self.BOXCAR_USERNAME = check_setting_str(config, 'Boxcar', 'boxcar_username', '')
        
    def writeConfig(self, new_config):        
        new_config['Boxcar'] = {}
        new_config['Boxcar']['use_boxcar'] = int(self.USE_BOXCAR)
        new_config['Boxcar']['boxcar_notify_onsnatch'] = int(self.BOXCAR_NOTIFY_ONSNATCH)
        new_config['Boxcar']['boxcar_notify_ondownload'] = int(self.BOXCAR_NOTIFY_ONDOWNLOAD)
        new_config['Boxcar']['boxcar_username'] = self.BOXCAR_USERNAME
    
        return new_config
    
    def activateHook(self):
        self._addMethod()
        self._addStatic()

    def deactivateHook(self):
        self._removeMethod()
        self._removeStatic()
