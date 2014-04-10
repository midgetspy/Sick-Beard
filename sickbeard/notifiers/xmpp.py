# Author: Dieter Blomme <dieterblomme@gmail.com>
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
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.
import sickbeard
try:
    from sleekxmpp import ClientXMPP
except ImportError:
    class ClientXMPP(object):
        def __init__(self, *args, **kwargs):
            pass


class XmppNotifier:
    """
    A xmpp notifier.
    """
    def __init__(self):
        self.xmpp = None

    def init_xmpp(self):
        if self.xmpp is not None:
            return self.xmpp
        try:
            from sleekxmpp import ClientXMPP
        except ImportError:
            sickbeard.logger.log(u"Error: sleekxmpp package isn't installed. XMPP notifications will not work.")
            return False
        self.xmpp = True
        return self.xmpp

    def notify_snatch(self, ep_name):
        if self._notify_onsnatch():
            return self._notify(sickbeard.common.notifyStrings[sickbeard.common.NOTIFY_SNATCH]+': '+ep_name)
        return True

    def notify_download(self, ep_name):
        if self._notify_ondownload():
            return self._notify(sickbeard.common.notifyStrings[sickbeard.common.NOTIFY_DOWNLOAD]+': '+ep_name)
        return True

    def test_notify(self, username, password, target, force=False):
        return self._notify(u"Testing XMPP settings from Sick Beard", username=username,
                            password=password, target=target, force=force)

    def _notify(self, message, username=None, password=None, target=None, force=False):
        if not self._use_me() and not force:
            return False
        if not self.init_xmpp():
            return False

        if username is None:
            username = self._username()
        if password is None:
            password = self._password()
        if target is None:
            target = self._target()

        client = xmppClient(username, password, target, message)
        try:
            if client.connect(reattempt=False):
                client.process(block=True)
                if not client.authenticated:
                    sickbeard.logger.log(u"Failed to authenticate with xmpp server")
                    return False
                return True
        except:
            pass
        return False

    def _username(self):
        return sickbeard.XMPP_USERNAME

    def _password(self):
        return sickbeard.XMPP_PASSWORD

    def _target(self):
        return sickbeard.XMPP_TARGET

    def _use_me(self):
        return bool(sickbeard.USE_XMPP)

    def _notify_ondownload(self):
        return bool(sickbeard.XMPP_NOTIFY_ONDOWNLOAD)

    def _notify_onsnatch(self):
        return bool(sickbeard.XMPP_NOTIFY_ONSNATCH)


class xmppClient(ClientXMPP):
    def __init__(self, jid, password, recipient, message):
        super(xmppClient, self).__init__(jid, password)
        self.recipient = recipient
        self.msg = message
        self.add_event_handler("session_start", self.start)

    def start(self, event):
        self.send_presence()
        self.get_roster()
        self.send_message(mto=self.recipient,
                          mbody=self.msg,
                          mtype="chat")
        self.disconnect(wait=True)

notifier = XmppNotifier
