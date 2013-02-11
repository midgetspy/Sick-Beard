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
        """
        Sends a message to notify using the given authentication information
        
        msg: The string to send to notifo
        title: The title of the message
        username: The username to send it to
        apisecret: The API key for the username
        label: The label to use for the message (optional)
        
        Returns: True if the message was delivered, False otherwise
        """

        # tidy up the message
        msg = msg.strip()
        
        # build up the URL and parameters
        apiurl = API_URL % {"username": username, "secret": apisecret}
        data = urllib.urlencode({
            "title": title,
            "label": label,
            "msg": msg.encode(sickbeard.SYS_ENCODING)
        })

        # send the request to notifo
        try:
            data = urllib.urlopen(apiurl, data)    
            result = json.load(data)

        except ValueError, e:
            logger.log(u"Unable to decode JSON: " + repr(data), logger.ERROR)
            return False
        
        except IOError, e:
            logger.log(u"Error trying to communicate with notifo: "+ex(e), logger.ERROR)
            return False
        
        data.close()

        # see if it worked
        if result["status"] != "success" or result["response_message"] != "OK":
            return False
        else:
            return True


    def notify_snatch(self, ep_name, title="Snatched:"):
        """
        Send a notification that an episode was snatched
        
        ep_name: The name of the episode that was snatched
        title: The title of the notification (optional)
        """
        if sickbeard.NOTIFO_NOTIFY_ONSNATCH:
            self._notifyNotifo(title, ep_name)

    def notify_download(self, ep_name, title="Completed:"):
        """
        Send a notification that an episode was downloaded
        
        ep_name: The name of the episode that was downloaded
        title: The title of the notification (optional)
        """
        if sickbeard.NOTIFO_NOTIFY_ONDOWNLOAD:
            self._notifyNotifo(title, ep_name)

    def notify_subtitle_download(self, ep_name, lang, title="Completed:"):
        """
        Send a notification that a subtitle was downloaded
        
        ep_name: The name of the episode
        lang: The language of subtitle that was downloaded
        title: The title of the notification (optional)
        """
        if sickbeard.NOTIFO_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._notifyNotifo(title, ep_name + ": " + lang)

    def _notifyNotifo(self, title, message, username=None, apisecret=None, force=False):
        """
        Send a notifo notification based on the SB settings.
        
        title: The title to send
        message: The message to send
        username: The username to send it to (optional, default to the username in the config)
        apisecret: The API key to use (optional, defaults to the api key in the config)
        force: If true then the notification will be sent even if it is disabled in the config (optional)
        
        Returns: True if the message succeeded, false otherwise
        """
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