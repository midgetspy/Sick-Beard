# Author: Adam Landry
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
from lib.pynma import pynma


class NMA_Notifier:

    def _sendNMA(self, nma_api=None, nma_priority=None, event=None, message=None, force=False):

        title = "Sick Beard"

        # suppress notifications if the notifier is disabled but the notify options are checked
        if not sickbeard.USE_NMA and not force:
            return False

        if nma_api == None:
            nma_api = sickbeard.NMA_API

        if nma_priority == None:
            nma_priority = sickbeard.NMA_PRIORITY

        batch = False

        p = pynma.PyNMA()
        keys = nma_api.split(',')
        p.addkey(keys)

        if len(keys) > 1:
            batch = True

        logger.log("NMA: Sending notice with details: event=\"%s\", message=\"%s\", priority=%s, batch=%s" % (event, message, nma_priority, batch), logger.DEBUG)
        response = p.push(title, event, message, priority=nma_priority, batch_mode=batch)

        if not response[nma_api][u'code'] == u'200':
            logger.log(u"NMA: Could not send notification to NotifyMyAndroid", logger.ERROR)
            return False
        else:
            logger.log(u"NMA: Notification sent to NotifyMyAndroid", logger.MESSAGE)
            return True

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        if sickbeard.NMA_NOTIFY_ONSNATCH:
            self._sendNMA(nma_api=None, nma_priority=None, event=common.notifyStrings[common.NOTIFY_SNATCH], message=ep_name)

    def notify_download(self, ep_name):
        if sickbeard.NMA_NOTIFY_ONDOWNLOAD:
            self._sendNMA(nma_api=None, nma_priority=None, event=common.notifyStrings[common.NOTIFY_DOWNLOAD], message=ep_name)

    def test_notify(self, nma_api, nma_priority):
        return self._sendNMA(nma_api, nma_priority, event="Test", message="Testing NMA settings from Sick Beard", force=True)

    def update_library(self, ep_obj=None):
        pass

notifier = NMA_Notifier
