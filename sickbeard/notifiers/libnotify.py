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


def diagnose():
    '''
    Check the environment for reasons libnotify isn't working.  Return a
    user-readable message indicating possible issues.
    '''
    try:
        import pynotify  # @UnusedImport
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


class LibnotifyNotifier:
    def __init__(self):
        self.pynotify = None
        self.gobject = None

    def init_pynotify(self):
        if self.pynotify is not None:
            return True
        try:
            import pynotify
        except ImportError:
            logger.log(u"LIBNOTIFY: Unable to import pynotify. libnotify notifications won't work.", logger.ERROR)
            return False
        try:
            import gobject
        except ImportError:
            logger.log(u"LIBNOTIFY: Unable to import gobject. We can't catch a GError in display.", logger.ERROR)
            return False
        if not pynotify.init('Sick Beard'):
            logger.log(u"LIBNOTIFY: Initialization of pynotify failed. libnotify notifications won't work.", logger.ERROR)
            return False
        self.pynotify = pynotify
        self.gobject = gobject
        return True

    def _notify(self, title, message, force=False):
        # suppress notifications if the notifier is disabled but the notify options are checked
        if not sickbeard.USE_LIBNOTIFY and not force:
            return False

        # detect if we can use pynotify
        if not self.init_pynotify():
            return False

        # Can't make this a global constant because PROG_DIR isn't available
        # when the module is imported.
        icon_path = os.path.join(sickbeard.PROG_DIR, "data/images/sickbeard_touch_icon.png")
        icon_uri = "file://" + os.path.abspath(icon_path)

        # If the session bus can't be acquired here a bunch of warning messages
        # will be printed but the call to show() will still return True.
        # pynotify doesn't seem too keen on error handling.
        n = self.pynotify.Notification(title, message, icon_uri)
        try:
            return n.show()
        except self.gobject.GError:
            return False

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        if sickbeard.LIBNOTIFY_NOTIFY_ONSNATCH:
            self._notify(common.notifyStrings[common.NOTIFY_SNATCH], ep_name)

    def notify_download(self, ep_name):
        if sickbeard.LIBNOTIFY_NOTIFY_ONDOWNLOAD:
            self._notify(common.notifyStrings[common.NOTIFY_DOWNLOAD], ep_name)

    def test_notify(self):
        return self._notify("Test", "This is a test notification from Sick Beard", force=True)

    def update_library(self, ep_obj=None):
        pass

notifier = LibnotifyNotifier
