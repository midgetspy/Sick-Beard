# Author: Derek Battams <derek@battams.ca>
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

import smtplib
from email.mime.text import MIMEText

import sickbeard

from sickbeard import logger
from sickbeard.exceptions import ex

class EmailNotifier:

    def test_notify(self, host, port, smtp_from, use_tls, user, pwd, to):
        logger.log('HOST: %s; PORT: %s; FROM: %s, TLS: %s, USER: %s (%d), PWD: %s, TO: %s' % (host, port, smtp_from, use_tls, user, len(user), pwd, to), logger.DEBUG)        
        msg = MIMEText('This is a test message from Sick Beard.  If you\'re reading this, the test succeeded!')
        msg['Subject'] = 'Test Message from Sick Beard'
        msg['From'] = smtp_from
        msg['To'] = to
        srv = smtplib.SMTP(host, int(port))
        srv.set_debuglevel(1)
        try:
            if use_tls == '1' or (len(user) > 0 and len(pwd) > 0):
                srv.ehlo()
                logger.log('Sent initial EHLO command!', logger.DEBUG)
            if use_tls == '1':
                srv.starttls()
                logger.log('Sent STARTTLS command!', logger.DEBUG)
            if len(user) > 0 and len(pwd) > 0:
                srv.login(user, pwd)
                logger.log('Sent LOGIN command!', logger.DEBUG)
            srv.sendmail(smtp_from, [to], msg.as_string())
            srv.quit()
            return True
        except Exception as e:
            logger.log('Erroring sending test email: %s' % e, logger.ERROR)
            return False

    def notify_snatch(self, ep_name, title="Snatched:"):
        """
        Send a notification that an episode was snatched
        
        ep_name: The name of the episode that was snatched
        title: The title of the notification (optional)
        """
        #if sickbeard.NOTIFO_NOTIFY_ONSNATCH:
        #    self._notifyNotifo(title, ep_name)

    def notify_download(self, ep_name, title="Completed:"):
        """
        Send a notification that an episode was downloaded
        
        ep_name: The name of the episode that was downloaded
        title: The title of the notification (optional)
        """
        #if sickbeard.NOTIFO_NOTIFY_ONDOWNLOAD:
        #    self._notifyNotifo(title, ep_name)       

notifier = EmailNotifier
