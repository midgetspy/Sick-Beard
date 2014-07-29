# Author: Jaap-Jan van der Veen <jjvdveen@gmail.com>
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
from lib.pushbullet import PushBullet

class PushbulletNotifier:

    def _notify(self, title, message, pushbullet_access_token=None, force=False):
        """
            Sends a message via the Pushbullet API

            title: Title of the message (required)
            message: The message to send (required)
            pushbullet_access_token: Token to use for sending the message. If 
                no token is specified, the one specified in the config is used.
            force: force sending of notifications, even if disabled in configuration
        """

        # suppress notifications if the notifier is disabled but the notify options are checked
        if not sickbeard.USE_PUSHBULLET and not force:
            return False

        # fill in omitted parameters
        if not pushbullet_access_token:
            pushbullet_access_token = sickbeard.PUSHBULLET_ACCESS_TOKEN

        pb = PushBullet(pushbullet_access_token)

        logger.log(u"Pushbullet: Sending notice with details: title=\"%s\", message=\"%s\"" % (title, message), logger.DEBUG)
        success, push = pb.push_note(title, message)

        if success:
            logger.log(u"Pushbullet: Notification sent successfully", logger.MESSAGE)
        else:
            logger.log(u"Pushbullet: Error sending notification: %s" % (push.error.message), logger.ERROR)

        return success

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        if sickbeard.PUSHBULLET_NOTIFY_ONSNATCH:
            self._notify(common.notifyStrings[common.NOTIFY_SNATCH], ep_name)

    def notify_download(self, ep_name):
        if sickbeard.PUSHBULLET_NOTIFY_ONDOWNLOAD:
            self._notify(common.notifyStrings[common.NOTIFY_DOWNLOAD], ep_name)

    def test_notify(self, pushbullet_access_token):
        return self._notify("Test", "This is a test notification from Sick Beard", pushbullet_access_token, force=True)

    def update_library(self, ep_obj=None):
        pass

notifier = PushbulletNotifier
