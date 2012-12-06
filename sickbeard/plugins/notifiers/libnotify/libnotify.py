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

import os
import cgi
import sickbeard

from sickbeard import logger, common

from sickbeard.INotifierPlugin import INotifierPlugin
from sickbeard.config import CheckSection, check_setting_int, check_setting_str, ConfigMigrator

from sickbeard.webserve import Home
import cherrypy
import os

class LibnotifyNotifier(INotifierPlugin):

    def diagnose():
        '''
        Check the environment for reasons libnotify isn't working.  Return a
        user-readable message indicating possible issues.
        '''
        try:
            import pynotify  #@UnusedImport
        except ImportError:
            return (u"<p>Error: pynotify isn't installed.  On Ubuntu/Debian, install the "
                    u"<a href=\"apt:python-notify\">python-notify</a> package.")
        if 'DISPLAY' not in os.environ and 'DBUS_SESSION_BUS_ADDRESS' not in os.environ:
            return (u"<p>Error: Environment variables DISPLAY and DBUS_SESSION_BUS_ADDRESS "
                    u"aren't set.  libnotify will only work when you run Sick Beard "
                    u"from a desktop login.")
        try:
            import dbus
        except ImportError:
            pass
        else:
            try:
                bus = dbus.SessionBus()
            except dbus.DBusException, e:
                return (u"<p>Error: unable to connect to D-Bus session bus: <code>%s</code>."
                        u"<p>Are you running Sick Beard in a desktop session?") % (cgi.escape(e),)
            try:
                bus.get_object('org.freedesktop.Notifications',
                               '/org/freedesktop/Notifications')
            except dbus.DBusException, e:
                return (u"<p>Error: there doesn't seem to be a notification daemon available: <code>%s</code> "
                        u"<p>Try installing notification-daemon or notify-osd.") % (cgi.escape(e),)
        return u"<p>Error: Unable to send notification."

    def init_pynotify(self):
        if self.pynotify is not None:
            return True
        try:
            import pynotify
        except ImportError:
            logger.log(u"Unable to import pynotify. libnotify notifications won't work.")
            return False
        try:
            import gobject
        except ImportError:
            logger.log(u"Unable to import gobject. We can't catch a GError in display.")
            return False
        if not pynotify.init('Sick Beard'):
            logger.log(u"Initialization of pynotify failed. libnotify notifications won't work.")
            return False
        self.pynotify = pynotify
        self.gobject = gobject
        return True

    def notify_snatch(self, ep_name):
        if self.LIBNOTIFY_NOTIFY_ONSNATCH:
            self._notify(common.notifyStrings[common.NOTIFY_SNATCH], ep_name)

    def notify_download(self, ep_name):
        if self.LIBNOTIFY_NOTIFY_ONDOWNLOAD:
            self._notify(common.notifyStrings[common.NOTIFY_DOWNLOAD], ep_name)

    def test_notify(self):
        return self._notify('Test notification', "This is a test notification from Sick Beard", force=True)

    def _notify(self, title, message, force=False):
        if not self.USE_LIBNOTIFY and not force:
            return False
        if not self.init_pynotify():
            return False

        # Can't make this a global constant because PROG_DIR isn't available
        # when the module is imported.
        icon_path = os.path.join(sickbeard.PROG_DIR, "data/images/sickbeard_touch_icon.png")
        icon_uri = 'file://' + os.path.abspath(icon_path)

        # If the session bus can't be acquired here a bunch of warning messages
        # will be printed but the call to show() will still return True.
        # pynotify doesn't seem too keen on error handling.
        n = self.pynotify.Notification(title, message, icon_uri)
        try:
            return n.show()
        except self.gobject.GError:
            return False

    def __init__(self):
        INotifierPlugin .__init__(self)
        
        self.USE_LIBNOTIFY = False
        self.LIBNOTIFY_NOTIFY_ONSNATCH = False
        self.LIBNOTIFY_NOTIFY_ONDOWNLOAD = False
        self.type = INotifierPlugin.NOTIFY_DEVICE
        
        self.pynotify = None
        self.gobject = None
    
    def _addMethod(self):
        def testLibnotify(newself):
            cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

            if self.test_notify():
                return "Tried sending desktop notification via libnotify"
            else:
                return self.diagnose()
        
        testLibnotify.exposed = True
        Home.testLibnotify = testLibnotify

    def _addStatic(self):
        app = cherrypy.tree.apps[sickbeard.WEB_ROOT]
        app.merge({
             '/images/notifiers/libnotify.png': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/images/libnotify.png'),
             },
             '/js/configLibnotify.js': {
                'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.join(os.path.dirname(__file__), 'data/notification.js'),
             }
        })

    def _removeMethod(self):
        if hasattr(Home, 'testLibnotify'):
            del Home.testLibnotify

    def _removeStatic(self):
        pass

    def updateConfig(self, **kwargs):
        default = {
            'use_libnotify': 0,
            'libnotify_notify_onsnatch': 0,
            'libnotify_notify_ondownload': 0
            }

        for key, defval in default.items():
            value = kwargs.get(key, defval)
            val = 1 if value == "on" else value
            
            if hasattr(self, key.upper()):
                setattr(self, key.upper(), val)
            else:
                logger.log("Unknown notification setting: " + key, logger.ERROR)
    
    def readConfig(self, config):
        CheckSection(config, 'Libnotify')
        self.USE_LIBNOTIFY = bool(check_setting_int(config, 'Libnotify', 'use_libnotify', 0))
        self.LIBNOTIFY_NOTIFY_ONSNATCH = bool(check_setting_int(config, 'Libnotify', 'libnotify_notify_onsnatch', 0))
        self.LIBNOTIFY_NOTIFY_ONDOWNLOAD = bool(check_setting_int(config, 'Libnotify', 'libnotify_notify_ondownload', 0))
        
    def writeConfig(self, new_config):        
        new_config['Libnotify'] = {}
        new_config['Libnotify']['use_libnotify'] = int(self.USE_LIBNOTIFY)
        new_config['Libnotify']['libnotify_notify_onsnatch'] = int(self.LIBNOTIFY_NOTIFY_ONSNATCH)
        new_config['Libnotify']['libnotify_notify_ondownload'] = int(self.LIBNOTIFY_NOTIFY_ONDOWNLOAD)
    
        return new_config
    
    def activateHook(self):
        self._addMethod()
        self._addStatic()

    def deactivateHook(self):
        self._removeMethod()
        self._removeStatic()