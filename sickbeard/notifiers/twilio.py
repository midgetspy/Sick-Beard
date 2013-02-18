# Author: Mathieu Fenniak <biziqe@mathieu.fenniak.net>
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
import base64

import sickbeard

from sickbeard import logger
from sickbeard.common import notifyStrings, NOTIFY_SNATCH, NOTIFY_DOWNLOAD
from sickbeard.exceptions import ex

API_URL = "https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/SMS/Messages"

class TwilioNotifier:

    def test_notify(self, from_number, to_number, account_sid, auth_token):
        return self._sendTwilio("This is a test notification from SickBeard", from_number, to_number, account_sid, auth_token)

    def _sendTwilio(self, msg, from_number, to_number, account_sid, auth_token):
        """
        Sends an SMS message with the Twilio web API
        
        msg: The message to send (unicode)
        from_number: source phone number of the SMS; E.164 format (eg. +14031234567)
        to_number: target phone number of the SMS; E.164 format (eg. +14031234567)
        account_sid: a 34 character string, starting with the letters AC
        auth_token: account auth token
        
        returns: True if the message succeeded, False otherwise
        """
        
        # build up the URL and parameters
        msg = msg.strip()
        curUrl = API_URL
        curUrl = curUrl.replace("{AccountSid}", urllib.quote_plus(account_sid))

        data = urllib.urlencode({
            'From': from_number,
            'To': to_number,
            'Body': msg,
        })
        authHeader = base64.encodestring('%s:%s' % (account_sid, auth_token)).replace('\n', '')

        # send the request to Twilio
        try:
            req = urllib2.Request(curUrl)
            req.add_header("Authorization", "Basic %s" % authHeader)
            handle = urllib2.urlopen(req, data)
            handle.close()
        except urllib2.URLError, e:
            # Success, SMS queued.
            if e.code == 201:
                return True

            # if we get an error back that doesn't have an error code then who knows what's really happening
            if not hasattr(e, 'code'):
                logger.log("Twilio notification failed." + ex(e), logger.ERROR)
            else:
                logger.log("Twilio notification failed. Error code: " + str(e.code), logger.WARNING)

            # HTTP status 404 might be provided if the account sid doesn't exist.
            if e.code == 404:
                logger.log("AccountSid is wrong/not vald.", logger.WARNING)
            # Supplied credentials are not sufficient.
            elif e.code == 401:
                logger.log("AccountSid and AuthToken have resulted in an unauthorized error.", logger.WARNING)
            return False

        logger.log("Twilio SMS notification successful.", logger.DEBUG)
        return True

    def notify_snatch(self, ep_name, title=notifyStrings[NOTIFY_SNATCH]):
        if sickbeard.TWILIO_NOTIFY_ONSNATCH:
            self._notifyTwilio(title, ep_name)
            
    def notify_download(self, ep_name, title=notifyStrings[NOTIFY_DOWNLOAD]):
        if sickbeard.TWILIO_NOTIFY_ONDOWNLOAD:
            self._notifyTwilio(title, ep_name)

    def _notifyTwilio(self, title, message, from_number=None, to_number=None, account_sid=None, auth_token=None):
        """
        Sends an SMS via Twilio based on the provided info or SB config

        title: The title of the notification to send
        message: The message string to send
        from_number: source phone number of the SMS; E.164 format (eg. +14031234567)
        to_number: target phone number of the SMS; E.164 format (eg. +14031234567)
        account_sid: a 34 character string, starting with the letters AC
        auth_token: account auth token
        """

        if not sickbeard.USE_TWILIO:
            logger.log("Notification for Twilio not enabled, skipping this notification", logger.DEBUG)
            return False

        # if no params were given then use the config
        if not from_number:
            from_number = sickbeard.TWILIO_FROM_NUMBER
        if not to_number:
            to_number = sickbeard.TWILIO_TO_NUMBER
        if not account_sid:
            account_sid = sickbeard.TWILIO_ACCOUNT_SID
        if not auth_token:
            auth_token = sickbeard.TWILIO_AUTH_TOKEN

        logger.log("Sending notification for " + message, logger.DEBUG)
        self._sendTwilio("%s: %s" % (title, message), from_number, to_number, account_sid, auth_token)

notifier = TwilioNotifier

