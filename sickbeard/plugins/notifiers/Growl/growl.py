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

import socket

import sickbeard

from sickbeard import logger, common
from sickbeard.exceptions import ex

from lib.growl import gntp

from sickbeard.INotifierPlugin import INotifierPlugin
from sickbeard.config import CheckSection, check_setting_int, check_setting_str, ConfigMigrator

from sickbeard.webserve import Home
import cherrypy
import os

import urllib

class GrowlPlugin(INotifierPlugin):

    def test_notify(self, host, password):
        self._sendRegistration(host, password, 'Test')
        return self._sendGrowl("Test Growl", "Testing Growl settings from Sick Beard", "Test", host, password, force=True)

    def notify_snatch(self, ep_name):
        if self.GROWL_NOTIFY_ONSNATCH:
            self._sendGrowl(common.notifyStrings[common.NOTIFY_SNATCH], ep_name)

    def notify_download(self, ep_name):
        if self.GROWL_NOTIFY_ONDOWNLOAD:
            self._sendGrowl(common.notifyStrings[common.NOTIFY_DOWNLOAD], ep_name)

    def _send_growl(self, options,message=None):
                
        #Send Notification
        notice = gntp.GNTPNotice()
    
        #Required
        notice.add_header('Application-Name',options['app'])
        notice.add_header('Notification-Name',options['name'])
        notice.add_header('Notification-Title',options['title'])
    
        if options['password']:
            notice.set_password(options['password'])
    
        #Optional
        if options['sticky']:
            notice.add_header('Notification-Sticky',options['sticky'])
        if options['priority']:
            notice.add_header('Notification-Priority',options['priority'])
        if options['icon']:
            notice.add_header('Notification-Icon', 'https://raw.github.com/midgetspy/Sick-Beard/master/data/images/sickbeard.png')
    
        if message:
            notice.add_header('Notification-Text',message)

        response = self._send(options['host'],options['port'],notice.encode(),options['debug'])
        if isinstance(response,gntp.GNTPOK): return True
        return False

    def _send(self, host,port,data,debug=False):
        if debug: print '<Sending>\n',data,'\n</Sending>'
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host,port))
        s.send(data)
        response = gntp.parse_gntp(s.recv(1024))
        s.close()
    
        if debug: print '<Recieved>\n',response,'\n</Recieved>'

        return response

    def _sendGrowl(self, title="Sick Beard Notification", message=None, name=None, host=None, password=None, force=False):
        if not self.USE_GROWL and not force:
            return False
    
        if name == None:
            name = title
    
        if host == None:
            hostParts = self.GROWL_HOST.split(':')
        else:
            hostParts = host.split(':')
    
        if len(hostParts) != 2 or hostParts[1] == '':
            port = 23053
        else:
            port = int(hostParts[1])
    
        growlHosts = [(hostParts[0],port)]
    
        opts = {}
    
        opts['name'] = name
    
        opts['title'] = title
        opts['app'] = 'SickBeard'
    
        opts['sticky'] = None
        opts['priority'] = None
        opts['debug'] = False
    
        if password == None:
            opts['password'] = self.GROWL_PASSWORD
        else:
            opts['password'] = password
    
        opts['icon'] = True
    
    
        for pc in growlHosts:
            opts['host'] = pc[0]
            opts['port'] = pc[1]
            logger.log(u"Sending growl to "+opts['host']+":"+str(opts['port'])+": "+message)
            try:
                return self._send_growl(opts, message)
            except socket.error, e:
                logger.log(u"Unable to send growl to "+opts['host']+":"+str(opts['port'])+": "+ex(e))
                return False

    def _sendRegistration(self, host=None, password=None, name='Sick Beard Notification'):
        opts = {}
    
        if host == None:
            hostParts = self.GROWL_HOST.split(':')
        else:
            hostParts = host.split(':')
    
        if len(hostParts) != 2 or hostParts[1] == '':
            port = 23053
        else:
            port = int(hostParts[1])
            
        opts['host'] = hostParts[0]
        opts['port'] = port
        
            
        if password == None:
            opts['password'] = self.GROWL_PASSWORD
        else:
            opts['password'] = password
    
        
        opts['app'] = 'SickBeard'
        opts['debug'] = False
        
        #Send Registration
        register = gntp.GNTPRegister()
        register.add_header('Application-Name', opts['app'])
        register.add_header('Application-Icon', 'https://raw.github.com/midgetspy/Sick-Beard/master/data/images/sickbeard.png')
        
        register.add_notification('Test', True)
        register.add_notification(common.notifyStrings[common.NOTIFY_SNATCH], True)
        register.add_notification(common.notifyStrings[common.NOTIFY_DOWNLOAD], True)

        if opts['password']:
            register.set_password(opts['password'])
        
        try:
            return self._send(opts['host'],opts['port'],register.encode(),opts['debug'])
        except socket.error, e:
            logger.log(u"Unable to send growl to "+opts['host']+":"+str(opts['port'])+": "+str(e).decode('utf-8'))
            return False
    
    def __init__(self):
        INotifierPlugin .__init__(self)
        
        self.USE_GROWL = False
        self.GROWL_NOTIFY_ONSNATCH = False
        self.GROWL_NOTIFY_ONDOWNLOAD = False
        self.GROWL_HOST = ''
        self.GROWL_PASSWORD = None
        self.type = INotifierPlugin.NOTIFY_DEVICE
    
    def _addMethod(self):
        def testGrowl(newself, host=None, password=None):
            cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
            
            result = self.test_notify(host, password)
            if password==None or password=='':
                pw_append = ''
            else:
                pw_append = " with password: " + password

            if result:
                return "Registered and Tested growl successfully "+urllib.unquote_plus(host)+pw_append
            else:
                return "Registration and Testing of growl failed "+urllib.unquote_plus(host)+pw_append
            
        testGrowl.exposed = True
        Home.testGrowl = testGrowl

    def _addStatic(self):
        app = cherrypy.tree.apps[sickbeard.WEB_ROOT]
        app.merge({
             '/images/notifiers/growl.png': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/images/growl.png'),
             },
             '/js/configGrowl.js': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/notification.js'),
             }
        })

    def _removeMethod(self):
        if hasattr(Home, 'testGrowl'):
            del Home.testGrowl

    def _removeStatic(self):
        pass

    def updateConfig(self, **kwargs):
        default = {
            'use_growl': 0,
            'growl_notify_onsnatch': 0,
            'growl_notify_ondownload' : 0,
            'growl_host' : '',
            'growl_password' : None
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
        CheckSection(config, 'Growl')
        self.USE_GROWL = bool(check_setting_int(config, 'Growl', 'use_growl', 0))
        self.GROWL_NOTIFY_ONSNATCH = bool(check_setting_int(config, 'Growl', 'growl_notify_onsnatch', 0))
        self.GROWL_NOTIFY_ONDOWNLOAD = bool(check_setting_int(config, 'Growl', 'growl_notify_ondownload', 0))
        self.GROWL_HOST = check_setting_str(config, 'Growl', 'growl_host', '')
        self.GROWL_PASSWORD = check_setting_str(config, 'Growl', 'growl_password', '')
        
    def writeConfig(self, new_config):        
        new_config['Growl'] = {}
        new_config['Growl']['use_growl'] = int(self.USE_GROWL)
        new_config['Growl']['growl_notify_onsnatch'] = int(self.GROWL_NOTIFY_ONSNATCH)
        new_config['Growl']['growl_notify_ondownload'] = int(self.GROWL_NOTIFY_ONDOWNLOAD)
        new_config['Growl']['growl_host'] = self.GROWL_HOST
        new_config['Growl']['growl_password'] = self.GROWL_PASSWORD
    
        return new_config
    
    def activateHook(self):
        self._addMethod()
        self._addStatic()

    def deactivateHook(self):
        self._removeMethod()
        self._removeStatic()
