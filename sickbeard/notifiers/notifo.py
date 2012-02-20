# Author: Nic Wolfe <nic@wolfeden.ca>
# Revised by: Shawn Conroyd - 4/12/2011
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
from sickbeard.exceptions import ex

try:
    import lib.simplejson as json #@UnusedImport
except:
    import json #@Reimport

API_URL = "https://%(username)s:%(secret)s@api.notifo.com/v1/send_notification"

class NotifoNotifier:

    def test_notify(self, username, apisecret, title="Test:"):
        return self._sendNotifo("This is a test notification from SickBeard", title, username, apisecret)

    def _sendNotifo(self, msg, title, username, apisecret, label="SickBeard"):
        msg = msg.strip()
        apiurl = API_URL % {"username": username, "secret": apisecret}
        data = urllib.urlencode({
            "title": title,
            "label": label,
            "msg": msg.encode(sickbeard.SYS_ENCODING)
        })

        try:
            data = urllib.urlopen(apiurl, data)    
            result = json.load(data)
        except ValueError, e:
            logger.log(u"Unable to decode JSON: "+data, logger.ERROR)
            return False
        except IOError, e:
            logger.log(u"Error trying to communicate with notifo: "+ex(e), logger.ERROR)
            return False
        
        data.close()

        if result["status"] != "success" or result["response_message"] != "OK":
            return False
        else:
            return True


    def notify_snatch(self, ep_name, title="Snatched:"):
        if sickbeard.NOTIFO_NOTIFY_ONSNATCH:
            self._notifyNotifo(title, ep_name)

    def notify_download(self, ep_name, title="Completed:"):
        if sickbeard.NOTIFO_NOTIFY_ONDOWNLOAD:
            self._notifyNotifo(title, ep_name)       

    def _notifyNotifo(self, title, message=None, username=None, apisecret=None, force=False):
        if not sickbeard.USE_NOTIFO and not force:
            logger.log("Notification for Notifo not enabled, skipping this notification", logger.DEBUG)
            return False

        if not username:
            username = sickbeard.NOTIFO_USERNAME
        if not apisecret:
            apisecret = sickbeard.NOTIFO_APISECRET

        logger.log(u"Sending notification for " + message, logger.DEBUG)

        self._sendNotifo(message, title, username, apisecret)
        return True

notifier = NotifoNotifier