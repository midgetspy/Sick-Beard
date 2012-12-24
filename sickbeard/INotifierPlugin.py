# Author: Cyrill Bannwart <bcyrill@twinsquared.ch>
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

from lib.yapsy.IPlugin import IPlugin

class INotifierPlugin(IPlugin):

    NOTIFY_UNKNOWN = -1
    NOTIFY_HOMETHEATER = 0
    NOTIFY_DEVICE = 1
    NOTIFY_ONLINE = 2

    def __init__(self):
        """
        Set the basic variables.
        """
        self.type = INotifierPlugin.NOTIFY_UNKNOWN
        self.has_javascript = True
        self.is_activated = False

    def notify_snatch(self, ep_name):
        pass

    def notify_download(self, ep_name):
        pass
    
    def update_library(self, ep_obj, add = True):
        pass

    def updateConfig(self, **kwargs):
        pass

    def readConfig(self, conf):
        pass
    
    def writeConfig(self, conf):
        pass

    def activate(self):
        """
        Called at plugin activation.
        """
        if not self.is_activated:
            self.activateHook()
        self.is_activated = True
        
        return

    def activateHook(self):
        """
        Called when an inactive plugin is about to be activated.
        """
        pass

    def deactivate(self):
        """
        Called when the plugin is disabled.
        """
        if self.is_activated:
            self.deactivateHook()
        self.is_activated = False

    def deactivateHook(self):
        """
        Called when an active plugin is about to be deactivated.
        """
        pass
        