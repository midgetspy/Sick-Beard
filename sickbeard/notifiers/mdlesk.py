# Author: Michael Dlesk <michaeldlesk@gmail.com>
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
import urllib2
import socket
import base64

import sickbeard

from sickbeard import logger
from sickbeard.common import notifyStrings, NOTIFY_SNATCH, NOTIFY_DOWNLOAD
from sickbeard.exceptions import ex


class MdleskNotifier:

    def _sendMdlesk(self, title, body, server, username, apikey, source):
    	logger.log(u"Starting")
	requestParameters = ''
	requestParameters = requestParameters + '?'
	requestParameters = requestParameters + 'Username=%s' % urllib.quote_plus(username)
	requestParameters = requestParameters + '&ApiKey=%s' % urllib.quote_plus(apikey)
	requestParameters = requestParameters + '&Action=SendNotification'
	requestParameters = requestParameters + '&Source=%s' % urllib.quote_plus(source)
	requestParameters = requestParameters + '&Message=%s' % urllib.quote_plus(body)

	requestUrl = server + requestParameters

        # send the request to pushbullet
        try:
            logger.log(u"MDLESK: URL: " + requestUrl , logger.MESSAGE)
            req = urllib2.Request(requestUrl)
            handle = urllib2.urlopen(req)
            handle.close()
        except socket.timeout:
            return False
        except urllib2.URLError, e:
            # FIXME: Python 2.5 hack, it wrongly reports 201 as an error
            if hasattr(e, 'code') and e.code == 201:
                logger.log(u"MDLESK: Notification successful.", logger.MESSAGE)
                return True

            # if we get an error back that doesn't have an error code then who knows what's really happening
            if not hasattr(e, 'code'):
                logger.log(u"MDLESK: Notification failed." + ex(e), logger.ERROR)
            else:
                logger.log(u"MDLESK: Notification failed. Error code: " + str(e.code), logger.ERROR)
            return False

        logger.log(u"MDLESK: Notification successful.", logger.MESSAGE)
        return True

    def _notify(self, title, body, server=None, username=None, apikey=None, source=None, force=False):

        if not sickbeard.USE_MDLESK and not force:
            return False

        if not server:
            server = sickbeard.MDLESK_SERVER
        if not username:
            username = sickbeard.MDLESK_USERNAME
        if not apikey:
            apikey = sickbeard.MDLESK_APIKEY
        if not source:
            source = sickbeard.MDLESK_SOURCE    

        logger.log(u"MDLESK: Sending notification with details: source=\"%s\", title=\"%s\", body=\"%s\", server=\"%s\", username=\"%s\", api=\"%s\"" % (source, title, body, server, username, apikey), logger.DEBUG)

        return self._sendMdlesk(title, body, server, username, apikey, source)

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        if sickbeard.MDLESK_NOTIFY_ONSNATCH:
            self._notify(notifyStrings[NOTIFY_SNATCH], ep_name)

    def notify_download(self, ep_name):
        if sickbeard.MDLESK_NOTIFY_ONDOWNLOAD:
            self._notify(notifyStrings[NOTIFY_DOWNLOAD], ep_name)

    def test_notify(self, server, username, apikey, source):
        return self._notify("Test", "This is a test notification from Sick Beard", server, username, apikey, source, force=True)

    def update_library(self, ep_obj=None):
        pass

notifier = MdleskNotifier
