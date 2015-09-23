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

import socket
import sickbeard

from sickbeard import logger, common
from sickbeard.exceptions import ex

from lib.growl import gntp


class GrowlNotifier:

    def _send_growl(self, options, message=None):
        # send notification
        notice = gntp.GNTPNotice()

        #Required
        notice.add_header('Application-Name', options['app'])
        notice.add_header('Notification-Name', options['name'])
        notice.add_header('Notification-Title', options['title'])

        if options['password']:
            notice.set_password(options['password'])

        # optional
        if options['sticky']:
            notice.add_header('Notification-Sticky', options['sticky'])
        if options['priority']:
            notice.add_header('Notification-Priority', options['priority'])
        if options['icon']:
            notice.add_header('Notification-Icon', 'http://www.sickbeard.com/notify.png')

        if message:
            notice.add_header('Notification-Text', message)

        response = self._send(options['host'], options['port'], notice.encode(), options['debug'])
        if isinstance(response, gntp.GNTPOK):
            return True

        return False

    def _send(self, host, port, data, debug=False):
        if debug:
            print '<Sending>\n', data, '\n</Sending>'

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.send(data)
        response = gntp.parse_gntp(s.recv(1024))
        s.close()

        if debug:
            print '<Recieved>\n', response, '\n</Recieved>'

        return response

    def _notify(self, title="Sick Beard Notification", message=None, name=None, host=None, password=None, force=False):
        # suppress notifications if the notifier is disabled but the notify options are checked
        if not sickbeard.USE_GROWL and not force:
            return False

        # fill in omitted parameters
        if not name:
            name = title

        if not host:
            hostParts = sickbeard.GROWL_HOST.split(':')
        else:
            hostParts = host.split(':')

        if len(hostParts) != 2 or hostParts[1] == '':
            port = 23053
        else:
            port = int(hostParts[1])

        growlHosts = [(hostParts[0], port)]

        opts = {}

        opts['name'] = name

        opts['title'] = title
        opts['app'] = 'SickBeard'

        opts['sticky'] = None
        opts['priority'] = None
        opts['debug'] = False

        if not password:
            opts['password'] = sickbeard.GROWL_PASSWORD
        else:
            opts['password'] = password

        opts['icon'] = True

        # TODO: Multi hosts does not seem to work... registration only happens for the first
        for pc in growlHosts:
            print pc
            opts['host'] = pc[0]
            opts['port'] = pc[1]
            logger.log(u"GROWL: Sending message '" + message + "' to " + opts['host'] + ":" + str(opts['port']), logger.DEBUG)
            try:
                return self._send_growl(opts, message)
            except Exception, e:
                logger.log(u"GROWL: Unable to send growl to " + opts['host'] + ":" + str(opts['port']) + " - " + ex(e), logger.WARNING)
                return False

    def _sendRegistration(self, host=None, password=None, name="Sick Beard Notification"):
        opts = {}

        if not host:
            hostParts = sickbeard.GROWL_HOST.split(':')
        else:
            hostParts = host.split(':')

        if len(hostParts) != 2 or hostParts[1] == '':
            port = 23053
        else:
            port = int(hostParts[1])

        opts['host'] = hostParts[0]
        opts['port'] = port

        if not password:
            opts['password'] = sickbeard.GROWL_PASSWORD
        else:
            opts['password'] = password

        opts['app'] = 'SickBeard'
        opts['debug'] = False

        # send registration
        register = gntp.GNTPRegister()
        register.add_header('Application-Name', opts['app'])
        register.add_header('Application-Icon', 'http://www.sickbeard.com/notify.png')

        register.add_notification('Test', True)
        register.add_notification(common.notifyStrings[common.NOTIFY_SNATCH], True)
        register.add_notification(common.notifyStrings[common.NOTIFY_DOWNLOAD], True)

        if opts['password']:
            register.set_password(opts['password'])

        try:
            return self._send(opts['host'], opts['port'], register.encode(), opts['debug'])
        except Exception, e:
            logger.log(u"GROWL: Unable to send growl to " + opts['host'] + ":" + str(opts['port']) + " - " + ex(e), logger.WARNING)
            return False

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        if sickbeard.GROWL_NOTIFY_ONSNATCH:
            self._notify(common.notifyStrings[common.NOTIFY_SNATCH], ep_name)

    def notify_download(self, ep_name):
        if sickbeard.GROWL_NOTIFY_ONDOWNLOAD:
            self._notify(common.notifyStrings[common.NOTIFY_DOWNLOAD], ep_name)

    def test_notify(self, host, password):
        result = self._sendRegistration(host, password, "Test")
        if result:
            return self._notify("Test Growl", "This is a test notification from Sick Beard", "Test", host, password, force=True)
        else:
            return result

    def update_library(self, ep_obj=None):
        pass

notifier = GrowlNotifier
