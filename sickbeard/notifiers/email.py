# Author: Ivan Filippov <ivan.v.f@gmail.com>
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
import string

import sickbeard

from sickbeard import logger

class EmailNotifier:

	def test_notify(self, server, sender, recipient):
		title = "Test:"
		return self._sendEmail("This is a test notification from SickBeard", title, server, sender, recipient)

	def _sendEmail(self, msg, title, server, sender, recipient):
	
		email = string.join((
					"From: %s" % sender,
					"To: %s" % recipient,
					"Subject: [Sick-Beard] %s" % title,
					"",
					msg
					), "\r\n")
		
		try:
			smtp = smtplib.SMTP(server)
			smtp.sendmail(sender,recipient,email)
			smtp.quit()
		except (smtplib.socket.error, smtplib.SMTPException):
			return False
			
		return True

	def notify_snatch(self, ep_name, title="Snatched:"):
		if sickbeard.EMAIL_NOTIFY_ONSNATCH:
			self._notifyEmail(title, ep_name)

	def notify_download(self, ep_name, title="Completed:"):
		if sickbeard.EMAIL_NOTIFY_ONDOWNLOAD:
			self._notifyEmail(title, ep_name)

	def _notifyEmail(self, title, message, server, sender, recipient, force=False):
		if not sickbeard.USE_EMAIL and not force:
			logger.log("Notification for Email not enabled, skipping this notification", logger.DEBUG)
			return False
		if not sender:
			sender = sickbeard.EMAIL_SENDER
		if not recipient:
			recipient = sickbeard.EMAIL_RECIPIENT
		if not server:
			server = sickbeard.EMAIL_SERVER

		self._sendEmail(message, title, server, sender, recipient)
		
		logger.log(u"Sending notification for " + message, logger.DEBUG)
		return True

notifier = EmailNotifier