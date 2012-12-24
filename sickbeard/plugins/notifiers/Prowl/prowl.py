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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

from httplib import HTTPSConnection, HTTPException
from urllib import urlencode

try:
    # this only exists in 2.6
    from ssl import SSLError
except ImportError:
    # make a fake one since I don't know what it is supposed to be in 2.5
    class SSLError(Exception):
        pass

import sickbeard

from sickbeard import logger, common

from sickbeard.INotifierPlugin import INotifierPlugin
from sickbeard.config import CheckSection, check_setting_int, check_setting_str, ConfigMigrator

from sickbeard.webserve import Home
import cherrypy
import os

class ProwlNotifier(INotifierPlugin):

    def test_notify(self, prowl_api, prowl_priority):
        return self._sendProwl(prowl_api, prowl_priority, event="Test", message="Testing Prowl settings from Sick Beard", force=True)

    def notify_snatch(self, ep_name):
        if self.PROWL_NOTIFY_ONSNATCH:
            self._sendProwl(prowl_api=None, prowl_priority=None, event=common.notifyStrings[common.NOTIFY_SNATCH], message=ep_name)

    def notify_download(self, ep_name):
        if self.PROWL_NOTIFY_ONDOWNLOAD:
            self._sendProwl(prowl_api=None, prowl_priority=None, event=common.notifyStrings[common.NOTIFY_DOWNLOAD], message=ep_name)
        
    def _sendProwl(self, prowl_api=None, prowl_priority=None, event=None, message=None, force=False):
        
        if not self.USE_PROWL and not force:
                return False
        
        if prowl_api == None:
            prowl_api = self.PROWL_API
            
        if prowl_priority == None:
            prowl_priority = self.PROWL_PRIORITY
        
            
        title = "Sick Beard"
        
        logger.log(u"Prowl title: " + title, logger.DEBUG)
        logger.log(u"Prowl event: " + event, logger.DEBUG)
        logger.log(u"Prowl message: " + message, logger.DEBUG)
        logger.log(u"Prowl api: " + prowl_api, logger.DEBUG)
        logger.log(u"Prowl priority: " + prowl_priority, logger.DEBUG)
        
        http_handler = HTTPSConnection("api.prowlapp.com")
                                                
        data = {'apikey': prowl_api,
                'application': title,
                'event': event,
                'description': message.encode('utf-8'),
                'priority': prowl_priority }

        try:
            http_handler.request("POST",
                                    "/publicapi/add",
                                    headers = {'Content-type': "application/x-www-form-urlencoded"},
                                    body = urlencode(data))
        except (SSLError, HTTPException):
            logger.log(u"Prowl notification failed.", logger.ERROR)
            return False
        response = http_handler.getresponse()
        request_status = response.status

        if request_status == 200:
                logger.log(u"Prowl notifications sent.", logger.DEBUG)
                return True
        elif request_status == 401: 
                logger.log(u"Prowl auth failed: %s" % response.reason, logger.ERROR)
                return False
        else:
                logger.log(u"Prowl notification failed.", logger.ERROR)
                return False
                
    def __init__(self):
        INotifierPlugin .__init__(self)
        
        self.USE_PROWL = False
        self.PROWL_NOTIFY_ONSNATCH = False
        self.PROWL_NOTIFY_ONDOWNLOAD = False
        self.PROWL_API = None
        self.PROWL_PRIORITY = 0
        self.type = INotifierPlugin.NOTIFY_DEVICE
    
    def _addMethod(self):
        def testProwl(newself, prowl_api=None, prowl_priority=0):
            cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

            result = self.test_notify(prowl_api, prowl_priority)
            if result:
                return "Test prowl notice sent successfully"
            else:
                return "Test prowl notice failed"
        
        testProwl.exposed = True
        Home.testProwl = testProwl

    def _addStatic(self):
        app = cherrypy.tree.apps[sickbeard.WEB_ROOT]
        app.merge({
             '/images/notifiers/prowl.png': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/images/prowl.png'),
             },
             '/js/configProwl.js': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/notification.js'),
             }
        })

    def _removeMethod(self):
        if hasattr(Home, 'testProwl'):
            del Home.testProwl

    def _removeStatic(self):
        pass

    def updateConfig(self, **kwargs):
        default = {
            'use_prowl': 0,
            'prowl_notify_onsnatch': 0,
            'prowl_notify_ondownload' : 0,
            'prowl_api' : None,
            'prowl_priority' : 0
            }
        
        #extract keys that are in default and combine with default where missing
        
        for key, defval in default.items():
            value = kwargs.get(key, defval)
            val = 1 if value == "on" else value
            
            if hasattr(self, key.upper()):
                setattr(self, key.upper(), val)
            else:
                logger.log("Unknown notification setting: " + key, logger.ERROR)
    
    def readConfig(self, config):
        CheckSection(config, 'Prowl')
        self.USE_PROWL = bool(check_setting_int(config, 'Prowl', 'use_prowl', 0))
        self.PROWL_NOTIFY_ONSNATCH = bool(check_setting_int(config, 'Prowl', 'prowl_notify_onsnatch', 0))
        self.PROWL_NOTIFY_ONDOWNLOAD = bool(check_setting_int(config, 'Prowl', 'prowl_notify_ondownload', 0))
        self.PROWL_API = check_setting_str(config, 'Prowl', 'prowl_api', '')
        self.PROWL_PRIORITY = check_setting_str(config, 'Prowl', 'prowl_priority', "0")
        
    def writeConfig(self, new_config):        
        new_config['Prowl'] = {}
        new_config['Prowl']['use_prowl'] = int(self.USE_PROWL)
        new_config['Prowl']['prowl_notify_onsnatch'] = int(self.PROWL_NOTIFY_ONSNATCH)
        new_config['Prowl']['prowl_notify_ondownload'] = int(self.PROWL_NOTIFY_ONDOWNLOAD)
        new_config['Prowl']['prowl_api'] = self.PROWL_API
        new_config['Prowl']['prowl_priority'] = self.PROWL_PRIORITY
    
        return new_config
    
    def activateHook(self):
        self._addMethod()
        self._addStatic()

    def deactivateHook(self):
        self._removeMethod()
        self._removeStatic()

