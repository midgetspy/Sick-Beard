# Author: Bouke van der Bijl <boukevanderbijl@gmail.com>
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
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import urllib, urllib2

import sickbeard

from sickbeard import common, logger
from sickbeard.exceptions import ex

class WebhookNotifier:
    
    def notify_snatch(self, ep_name):
        if sickbeard.WEBHOOK_NOTIFY_ONSNATCH:
            self._notify(sickbeard.WEBHOOK_URL, ep_name, common.notifyStrings[common.NOTIFY_SNATCH], 'snatch')

    def notify_download(self, ep_name):
        if sickbeard.WEBHOOK_NOTIFY_ONDOWNLOAD:
            self._notify(sickbeard.WEBHOOK_URL, ep_name, common.notifyStrings[common.NOTIFY_DOWNLOAD], 'download')

    def test_notify(self, webhook_url):
        return self._notify(webhook_url, u"Test", u"This is a test notification from Sick Beard", 'test')
    
    def _notify(self, url, ep_name, notify_string, notification_type):
        logger.log(u"Posting to webhook: " + url, logger.DEBUG)
        
        try:
            data = {}
            data['ep_name'] = ep_name
            data['notify_string'] = notify_string
            data['type'] = notification_type
            
            request = urllib2.Request(url, urllib.urlencode(data), {'User-Agent': common.USER_AGENT})
            response = urllib2.urlopen(request).read()
        except IOError, e:
            response = u"Warning: Couldn't contact webhook at " + url
            logger.log(response)
        
        return response
