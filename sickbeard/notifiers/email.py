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

import smtplib
from socket import error as smtperror

class EmailNotifier:

    def notify_snatch(self, ep_name):
        if sickbeard.EMAIL_NOTIFY_ONSNATCH:
            self._notifyEmail(common.notifyStrings[common.NOTIFY_SNATCH]+': '+ep_name)

    def notify_download(self, ep_name):
        if sickbeard.EMAIL_NOTIFY_ONDOWNLOAD:
            self._notifyEmail(common.notifyStrings[common.NOTIFY_DOWNLOAD]+': '+ep_name)

    def test_notify(self):
        return self._notifyEmail("This is a test notification from Sick Beard", force=True)

    def _send_email(self, message=None):
    
        logger.log(u"Sending email: "+ message)
    
        header = ("From: %s\r\nTo: %s\r\nSubject: %s\r\n"
                    % (sickbeard.EMAIL_FROMADDR, sickbeard.EMAIL_TOADDR, '[Sickbeard Notifier]'))

        msg = header + message
    
        try:
            print sickbeard.EMAIL_SMTPHOST, sickbeard.EMAIL_SMTPPORT
            server = smtplib.SMTP(sickbeard.EMAIL_SMTPHOST, int(sickbeard.EMAIL_SMTPPORT))
            server.set_debuglevel(0)
            server.sendmail(sickbeard.EMAIL_FROMADDR, sickbeard.EMAIL_TOADDR, msg)
            server.quit()
        except smtperror, e:
            logger.log(u"Error Sending Email: "+ex(e), logger.ERROR)
            return False
        except smtplib.SMTPRecipientsRefused, e:
            logger.log(u"Error Sending Email: "+ex(e), logger.ERROR)
            return False
    
        return True
    
    def _notifyEmail(self, message='', force=False):
    
        if not sickbeard.USE_EMAIL and not force:
            return False
    
        return self._send_email(message)

notifier = EmailNotifier
