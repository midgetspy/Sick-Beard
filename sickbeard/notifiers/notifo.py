import urllib
import sickbeard

from sickbeard import logger, common

try:
    import simplejson as json
except:
    import json


API_URL = "https://%(username)s:%(secret)s@api.notifo.com/v1/send_notification"

class NotifoNotifier:

    def test_notify(self, username, apisecret):
        return self._sendNotifo("This is a test notification from Sick Beard", username, apisecret)

    def _sendNotifo(self, msg, username, apisecret):
        msg = msg.strip()
        apiurl = API_URL % {"username": username, "secret": apisecret}
        data = urllib.urlencode({
            "msg": msg,
        })

        data = urllib.urlopen(apiurl, data)
        try:
            try:
                result = json.load(data)
            except IOError:
                return False
        finally:
            data.close()

        if result["status"] != "success" or result["response_message"] != "OK":
            return False
        else:
            return True


    def notify_snatch(self, ep_name):
        if sickbeard.NOTIFO_NOTIFY_ONSNATCH:
            self._notifyNotifo(common.notifyStrings[common.NOTIFY_SNATCH]+': '+ep_name)

    def notify_downloade(self, ep_name):
        if sickbeard.NOTIFO_NOTIFY_ONDOWNLOAD:
            self._notifyNotifo(common.notifyStrings[common.NOTIFY_DOWNLOAD]+': '+ep_name)       

    def _notifyNotifo(self, message=None, username=None, apisecret=None):
        if not sickbeard.USE_NOTIFO and not force:
            logger.log("Notification for Notifo not enabled, skipping this notification", logger.DEBUG)
            return False

        if not username:
            username = sickbeard.NOTIFO_USERNAME
        if not apisecret:
            apisecret = sickbeard.NOTIFO_APISECRET

        logger.log(u"Sending notification for " + message, logger.DEBUG)

        self._sendNotifo(message, username, apisecret)
        return True

notifier = NotifoNotifier
