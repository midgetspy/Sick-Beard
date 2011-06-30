# Author: Jeffrey Ness <jness@flip-edesign.com>
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

import sickbeard

from sickbeard import logger, common
from sickbeard.exceptions import ex

try:
    from googlevoice import Voice
    loaded = True
except ImportError:
    loaded = False


class SmsNotifier:

    def notify_snatch(self, ep_name):
        if sickbeard.SMS_NOTIFY_ONSNATCH:
            self._notifySms(common.notifyStrings[common.NOTIFY_SNATCH]+': '+ep_name)

    def notify_download(self, ep_name):
        if sickbeard.SMS_NOTIFY_ONDOWNLOAD:
            self._notifySms(common.notifyStrings[common.NOTIFY_DOWNLOAD]+': '+ep_name)

    def test_notify(self, email, password, phonenumber):
        return self._send_sms(message='This is a test notification from Sick Beard', email=email, password=password, phonenumber=phonenumber)

    def _send_sms(self, message=None, email=None, password=None, phonenumber=None):

        # if we didnt pass creds this is not a test and should pull from config
        if not email and not password and not phonenumber:
            email = sickbeard.SMS_EMAIL
            password = sickbeard.SMS_PASSWORD
            phonenumber = sickbeard.SMS_PHONENUMBER

        # If we didnt load module return false
        if loaded:
            logger.log(u"Sending SMS: "+ message)

            voice = Voice()
            try:
                voice.login(email=email ,passwd=password)
            except googlevoice.util.LoginError, e:
                logger.log(u"Error Sending SMS: "+ex(e), logger.ERROR)
                return False

            voice.send_sms(phonenumber, message)
            return True
        else:
            logger.log(u"Error importing module pygooglevoice, SMS Notification disabled", logger.ERROR)
            return False
    
    def _notifySms(self, message='', force=False):
    
        if not sickbeard.USE_SMS and not force:
            return False
    
        return self._send_sms(message)

notifier = SmsNotifier
