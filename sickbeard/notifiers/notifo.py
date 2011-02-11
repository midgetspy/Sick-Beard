import urllib

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
        apiurl = API_URL % self.get_credentials(username, apisecret)
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
        return true

    def notify_downloade(self, ep_name):
        return true

    def _notifyNotifo(self, message):
        return true

    def get_credentials(self, username = None, secret = None):
        if username is not None and secret is not None:
            return {"username": username, "secret": secret}
        return {"username": "jeroen94704", "secret": ""}
    
notifier = NotifoNotifier
