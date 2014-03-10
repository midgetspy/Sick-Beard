# Authors:
# Derek Battams <derek@battams.ca>
# Pedro Jose Pereira Vieito (@pvieito) <pvieito@gmail.com>
#
# URL: https://github.com/mr-orange/Sick-Beard
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
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import re

import sickbeard

from sickbeard import logger
from sickbeard import db
from sickbeard.exceptions import ex

class EmailNotifier:
    def __init__(self):
        self.last_err = None

    def test_notify(self, host, port, smtp_from, use_tls, user, pwd, to):
        msg = MIMEText('This is a test message from Sick Beard.  If you\'re reading this, the test succeeded.')
        msg['Subject'] = 'Sick Beard: Test Message'
        msg['From'] = smtp_from
        msg['To'] = to
        try:
            self._sendmail(host, port, smtp_from, use_tls, user, pwd, [to], msg, True)
            return True
        except Exception as e:
            return False

    def notify_snatch(self, ep_name, title="Snatched:"):
        """
        Send a notification that an episode was snatched

        ep_name: The name of the episode that was snatched
        title: The title of the notification (optional)
        """
        if sickbeard.EMAIL_NOTIFY_ONSNATCH:
            show = self._parseEp(ep_name)
            to = self._generate_recepients(show)
            if len(to) == 0:
                logger.log('Skipping email notify because there are no configured recepients', logger.WARNING)
            else:
              try:
                  msg = MIMEMultipart('alternative')
                  msg.attach(MIMEText("<body style='font-family:Helvetica, Arial, sans-serif;'><h3>Sick Beard Notification - Snatched</h3>\n<p>Show: <b>" + re.search("(.+?) -.+", ep_name).group(1) + "</b></p>\n<p>Episode: <b>" + re.search(".+ - (.+?-.+) -.+", ep_name).group(1) + "</b></p>\n\n<footer style='margin-top: 2.5em; padding: .7em 0; color: #777; border-top: #BBB solid 1px;'>Powered by Sick Beard.</footer></body>", 'html'))
              except:
                  msg = MIMEText(ep_name)

              msg['Subject'] = 'Snatched: ' + ep_name
              msg['From'] = sickbeard.EMAIL_FROM
              msg['To'] = ','.join(to)

              try:
                  self._sendmail(sickbeard.EMAIL_HOST, sickbeard.EMAIL_PORT, sickbeard.EMAIL_FROM, sickbeard.EMAIL_TLS, sickbeard.EMAIL_USER, sickbeard.EMAIL_PASSWORD, to, msg)
                  logger.log("Download notification sent to [%s] for '%s'" % (to, ep_name), logger.DEBUG)
              except Exception as e:
                  logger.log("Download notification ERROR: %s" % e, logger.ERROR)

    def notify_download(self, ep_name, title="Completed:"):
        """
        Send a notification that an episode was downloaded

        ep_name: The name of the episode that was downloaded
        title: The title of the notification (optional)
        """
        if sickbeard.EMAIL_NOTIFY_ONDOWNLOAD:
            show = self._parseEp(ep_name)
            to = self._generate_recepients(show)
            if len(to) == 0:
                logger.log('Skipping email notify because there are no configured recepients', logger.WARNING)
            else:
              try:
                  msg = MIMEMultipart('alternative')
                  msg.attach(MIMEText("<body style='font-family:Helvetica, Arial, sans-serif;'><h3>Sick Beard Notification - Downloaded</h3>\n<p>Show: <b>" + re.search("(.+?) -.+", ep_name).group(1) + "</b></p>\n<p>Episode: <b>" + re.search(".+ - (.+?-.+) -.+", ep_name).group(1) + "</b></p>\n\n<footer style='margin-top: 2.5em; padding: .7em 0; color: #777; border-top: #BBB solid 1px;'>Powered by Sick Beard.</footer></body>", 'html'))
              except:
                  msg = MIMEText(ep_name)

              msg['Subject'] = 'Downloaded: ' + ep_name
              msg['From'] = sickbeard.EMAIL_FROM
              msg['To'] = ','.join(to)

              try:
                  self._sendmail(sickbeard.EMAIL_HOST, sickbeard.EMAIL_PORT, sickbeard.EMAIL_FROM, sickbeard.EMAIL_TLS, sickbeard.EMAIL_USER, sickbeard.EMAIL_PASSWORD, to, msg)
                  logger.log("Download notification sent to [%s] for '%s'" % (to, ep_name), logger.DEBUG)
              except Exception as e:
                  logger.log("Download notification ERROR: %s" % e, logger.ERROR)

    def notify_subtitle_download(self, ep_name, lang, title="Downloaded subtitle:"):
        """
        Send a notification that an subtitle was downloaded

        ep_name: The name of the episode that was downloaded
        lang: Subtitle language wanted
        """
        if sickbeard.EMAIL_NOTIFY_ONSUBTITLEDOWNLOAD:
            show = self._parseEp(ep_name)
            to = self._generate_recepients(show)
            if len(to) == 0:
                logger.log('Skipping email notify because there are no configured recepients', logger.WARNING)
            else:
              try:
                  msg = MIMEMultipart('alternative')
                  msg.attach(MIMEText("<body style='font-family:Helvetica, Arial, sans-serif;'><h3>Sick Beard Notification - Subtitle Downloaded</h3>\n<p>Show: <b>" + re.search("(.+?) -.+", ep_name).group(1) + "</b></p>\n<p>Episode: <b>" + re.search(".+ - (.+?-.+) -.+", ep_name).group(1) + "</b></p>\n<p>Language: <b>" + lang + "</b></p>\n\n<footer style='margin-top: 2.5em; padding: .7em 0; color: #777; border-top: #BBB solid 1px;'>Powered by Sick Beard.</footer></body>", 'html'))
              except:
                  msg = MIMEText(ep_name + ": " + lang)

              msg['Subject'] = lang + ' Subtitle Downloaded: ' + ep_name
              msg['From'] = sickbeard.EMAIL_FROM
              msg['To'] = ','.join(to)

              try:
                  self._sendmail(sickbeard.EMAIL_HOST, sickbeard.EMAIL_PORT, sickbeard.EMAIL_FROM, sickbeard.EMAIL_TLS, sickbeard.EMAIL_USER, sickbeard.EMAIL_PASSWORD, to, msg)
                  logger.log("Download notification sent to [%s] for '%s'" % (to, ep_name), logger.DEBUG)
              except Exception as e:
                  logger.log("Download notification ERROR: %s" % e, logger.ERROR)

    def _generate_recepients(self, show):
        addrs = []

        # Grab the global recipients
        for addr in sickbeard.EMAIL_LIST.split(','):
            if(len(addr.strip()) > 0):
                addrs.append(addr)

        # Grab the recipients for the show
        mydb = db.DBConnection()
        for s in show:
            for subs in mydb.select("SELECT notify_list FROM tv_shows WHERE show_name = ?", (s,)):
                if subs['notify_list']:
                    for addr in subs['notify_list'].split(','):
                        if(len(addr.strip()) > 0):
                            addrs.append(addr)

        addrs = set(addrs)
        logger.log('Notification recepients: %s' % addrs, logger.DEBUG)
        return addrs

    def _sendmail(self, host, port, smtp_from, use_tls, user, pwd, to, msg, smtpDebug=False):
        logger.log('HOST: %s; PORT: %s; FROM: %s, TLS: %s, USER: %s, PWD: %s, TO: %s' % (host, port, smtp_from, use_tls, user, pwd, to), logger.DEBUG)
        srv = smtplib.SMTP(host, int(port))
        if smtpDebug:
            srv.set_debuglevel(1)
        if (use_tls == '1' or use_tls == True) or (len(user) > 0 and len(pwd) > 0):
            srv.ehlo()
            logger.log('Sent initial EHLO command!', logger.DEBUG)
        if use_tls == '1' or use_tls == True:
            srv.starttls()
            logger.log('Sent STARTTLS command!', logger.DEBUG)
        if len(user) > 0 and len(pwd) > 0:
            srv.login(user, pwd)
            logger.log('Sent LOGIN command!', logger.DEBUG)

        srv.sendmail(smtp_from, to, msg.as_string())
        srv.quit()

    def _parseEp(self, ep_name):
        sep = " - "
        titles = ep_name.split(sep)
        titles.sort(key=len, reverse=True)
        logger.log("TITLES: %s" % titles, logger.DEBUG)
        return titles

notifier = EmailNotifier
