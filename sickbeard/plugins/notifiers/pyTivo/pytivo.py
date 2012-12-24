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

import os
import sickbeard

from urllib import urlencode
from urllib2 import Request, urlopen, URLError

from sickbeard import logger
from sickbeard import encodingKludge as ek

from sickbeard.INotifierPlugin import INotifierPlugin
from sickbeard.config import CheckSection, check_setting_int, check_setting_str, ConfigMigrator

import cherrypy

class pyTivoNotifier(INotifierPlugin):

    def update_library(self, ep_obj, add=True):

        # Values from config
        
        if not self.USE_PYTIVO:
            return False
        
        host = self.PYTIVO_HOST
        shareName = self.PYTIVO_SHARE_NAME
        tsn = self.PYTIVO_TIVO_NAME
        
        # There are two more values required, the container and file.
        # 
        # container: The share name, show name and season
        #
        # file: The file name
        # 
        # Some slicing and dicing of variables is required to get at these values.
        #
        # There might be better ways to arrive at the values, but this is the best I have been able to 
        # come up with.
        #
        
        
        # Calculated values
        
        showPath = ep_obj.show.location
        showName = ep_obj.show.name
        rootShowAndSeason = ek.ek(os.path.dirname, ep_obj.location)      
        absPath = ep_obj.location
        
        # Some show names have colons in them which are illegal in a path location, so strip them out.
        # (Are there other characters?)
        showName = showName.replace(":","")
        
        root = showPath.replace(showName, "")
        showAndSeason = rootShowAndSeason.replace(root, "")
        
        container = shareName + "/" + showAndSeason
        file = "/" + absPath.replace(root, "")
        
        # Finally create the url and make request
        requestUrl = "http://" + host + "/TiVoConnect?" + urlencode( {'Command':'Push', 'Container':container, 'File':file, 'tsn':tsn} )
               
        logger.log(u"pyTivo notification: Requesting " + requestUrl)
        
        request = Request( requestUrl )

        try:
            response = urlopen(request) #@UnusedVariable   
        except URLError, e:
            if hasattr(e, 'reason'):
                logger.log(u"pyTivo notification: Error, failed to reach a server")
                logger.log(u"'Error reason: " + e.reason)
                return False
            elif hasattr(e, 'code'):
                logger.log(u"pyTivo notification: Error, the server couldn't fulfill the request")
                logger.log(u"Error code: " + e.code)
                return False
        else:
            logger.log(u"pyTivo notification: Successfully requested transfer of file")
            return True

    def __init__(self):
        INotifierPlugin .__init__(self)
        
        self.USE_PYTIVO = False
        self.PYTIVO_NOTIFY_ONSNATCH = False
        self.PYTIVO_NOTIFY_ONDOWNLOAD = False
        self.PYTIVO_UPDATE_LIBRARY = False
        self.PYTIVO_HOST = ''
        self.PYTIVO_SHARE_NAME = ''
        self.PYTIVO_TIVO_NAME = ''
        self.has_javascript = False
        self.type = INotifierPlugin.NOTIFY_HOMETHEATER

    def _addStatic(self):
        app = cherrypy.tree.apps[sickbeard.WEB_ROOT]
        app.merge({
             '/images/notifiers/pytivo.png': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/images/pytivo.png'),
             }
        })

    def _removeStatic(self):
        pass

    def updateConfig(self, **kwargs):
        default = {
            'use_pytivo': 0,
            'pytivo_notify_onsnatch': 0,
            'pytivo_notify_ondownload': 0,
            'pytivo_update_library': 0,

            'pytivo_host': '',
            'pytivo_share_name': '',
            'pytivo_tivo_name' : ''
            }
        
        for key, defval in default.items():
            value = kwargs.get(key, defval)
            val = 1 if value == "on" else value
            
            if hasattr(self, key.upper()):
                setattr(self, key.upper(), val)
            else:
                logger.log("Unknown notification setting: " + key, logger.ERROR)
    
    def readConfig(self, config):
        CheckSection(config, 'pyTivo')
        self.USE_PYTIVO = bool(check_setting_int(config, 'pyTivo', 'use_pytivo', 0))
        self.PYTIVO_NOTIFY_ONSNATCH = bool(check_setting_int(config, 'pyTivo', 'pytivo_notify_onsnatch', 0))
        self.PYTIVO_NOTIFY_ONDOWNLOAD = bool(check_setting_int(config, 'pyTivo', 'pytivo_notify_ondownload', 0))
        self.PYTIVO_UPDATE_LIBRARY = bool(check_setting_int(config, 'pyTivo', 'pyTivo_update_library', 0))
        self.PYTIVO_HOST = check_setting_str(config, 'pyTivo', 'pytivo_host', '')
        self.PYTIVO_SHARE_NAME = check_setting_str(config, 'pyTivo', 'pytivo_share_name', '')
        self.PYTIVO_TIVO_NAME = check_setting_str(config, 'pyTivo', 'pytivo_tivo_name', '')
        
    def writeConfig(self, new_config):        
        new_config['pyTivo'] = {}
        new_config['pyTivo']['use_pytivo'] = int(self.USE_PYTIVO)
        new_config['pyTivo']['pytivo_notify_onsnatch'] = int(self.PYTIVO_NOTIFY_ONSNATCH)
        new_config['pyTivo']['pytivo_notify_ondownload'] = int(self.PYTIVO_NOTIFY_ONDOWNLOAD)
        new_config['pyTivo']['pyTivo_update_library'] = int(self.PYTIVO_UPDATE_LIBRARY)
        new_config['pyTivo']['pytivo_host'] = self.PYTIVO_HOST
        new_config['pyTivo']['pytivo_share_name'] = self.PYTIVO_SHARE_NAME
        new_config['pyTivo']['pytivo_tivo_name'] = self.PYTIVO_TIVO_NAME
    
        return new_config
    
    def activateHook(self):
        self._addStatic()

    def deactivateHook(self):
        self._removeStatic()

