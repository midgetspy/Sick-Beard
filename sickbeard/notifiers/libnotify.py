import os
import sickbeard
import pynotify

from sickbeard import logger, common


class LibnotifyNotifier:
    def __init__(self):
        # This returns True, even when it should fail, so no useful information
        # to be had here...
        pynotify.init('Sick Beard')

    def notify_snatch(self, ep_name):
        if sickbeard.LIBNOTIFY_NOTIFY_ONSNATCH:
            self._notify(common.notifyStrings[common.NOTIFY_SNATCH], ep_name)

    def notify_download(self, ep_name):
        if sickbeard.LIBNOTIFY_NOTIFY_ONDOWNLOAD:
            self._notify(common.notifyStrings[common.NOTIFY_DOWNLOAD], ep_name)

    def test_notify(self):
        return self._notify('Test notification', "This is a test notification from Sick Beard", force=True)

    def _notify(self, title, message, force=False):
        if not sickbeard.USE_LIBNOTIFY and not force:
            return False

        # Can't make this a global constant because PROG_DIR isn't available
        # when the module is imported.
        icon_path = os.path.join(sickbeard.PROG_DIR, "data/images/sickbeard_touch_icon.png")
        icon_uri = 'file://' + os.path.abspath(icon_path)

        # If the session bus can't be acquired here a bunch of warning messages
        # will be printed but the call to show() will still return True.
        # pynotify doesn't seem to keen on error handling.
        n = pynotify.Notification(title, message, icon_uri)
        return n.show()


notifier = LibnotifyNotifier
