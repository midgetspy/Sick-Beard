# Author: Dlesk Development <mdlesk@my.devry.edu>
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

API_URL = "https://boxcar.io/devices/providers/fWc4sgSmpcN6JujtBmR6/notifications"

class DleskDevNotifier:

    def test_notify(self):
        return self._sendNotif("SickBeard Test", "This is a test notification from SickBeard", sickbeard.DLESKDEVNOTIF_USERNAME, sickbeard.DLESKDEVNOTIF_PASSWORD)

    def _sendNotif(self, title, message, username, password):
        """
        Sends a Dlesk Dev notification to the address provided
        
        msg: The message to send
        title: The title (subject) of the message
        username: User name to send the notification to
        password: Password authentication for the user
        
        returns: True if the message succeeded, False otherwise
        """
        
        # send the request to the Dlesk Dev Notif Server
        try:
	    pushmessage = urllib.quote_plus(message)
	    pushurl = 'http://notifications.dleskdevelopment.com/Api.aspx?username=' + username + '&password=' + password + '&message=' + pushmessage + '&subject=' + title + '&cmd=send_notification'
	    urllib.urlopen(pushurl)
        except urllib2.URLError, e:
            logger.log("Dlesk Dev Notification failed", logger.ERROR)
            return False
            
        logger.log("Dlesk Development notification successful.", logger.DEBUG)
        return True

    def notify_snatch(self, ep_name, title=notifyStrings[NOTIFY_SNATCH]):
        if sickbeard.DLESKDEVNOTIF_NOTIFY_ONSNATCH:
            self._sendNotif(title, ep_name, sickbeard.DLESKDEVNOTIF_USERNAME, sickbeard.DLESKDEVNOTIF_PASSWORD)
            
    def notify_download(self, ep_name, title=notifyStrings[NOTIFY_DOWNLOAD]):
        if sickbeard.DLESKDEVNOTIF_NOTIFY_ONDOWNLOAD:
            self._sendNotif(title, ep_name, sickbeard.DLESKDEVNOTIF_USERNAME, sickbeard.DLESKDEVNOTIF_PASSWORD)

notifier = DleskDevNotifier
