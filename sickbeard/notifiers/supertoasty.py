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

API_URL = "http://api.supertoasty.com/notify/{DEVICEID}?title={TITLE}&text={TEXT}&sender=SickBeard&image=https://github.com/midgetspy/Sick-Beard/raw/master/data/images/sickbeard_touch_icon.png"

class SuperToastyNotifier:

    def test_notify(self, deviceId, title="Test:"):
        return self._sendSuperToasty("This is a test notification from SickBeard", title, deviceId)

    def _sendSuperToasty(self, msg, title, deviceId):
        msg = msg.strip()
        apiurl = API_URL % {"DEVICEID": deviceId, "TITLE": title, "TEXT": msg}

        try:
            data = urllib.urlopen(apiurl)
        except IOError:
            return False
        
        logger.log(data)
        data.close()
        
        return True


    def notify_snatch(self, ep_name, title="Snatched:"):
        if sickbeard.SUPERTOASTY_NOTIFY_ONSNATCH:
            self._notifySuperToasty(title, ep_name)

    def notify_download(self, ep_name, title="Completed:"):
        if sickbeard.SUPERTOASTY_NOTIFY_ONDOWNLOAD:
            self._notifySuperToasty(title, ep_name)       

    def _notifySuperToasty(self, title, message=None, deviceId=None, force=False):
        if not sickbeard.USE_SUPERTOASTY and not force:
            logger.log("Notification for SuperToasty not enabled, skipping this notification", logger.DEBUG)
            return False

        if not deviceId:
            deviceId = sickbeard.SUPERTOASTY_DEVICEID

        logger.log(u"Sending notification through SuperToasty for " + message, logger.DEBUG)

        self._sendSuperToasty(message, title, deviceId)
        return True

notifier = SuperToastyNotifier