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

import lib.simplejson as json

from urllib2 import Request, urlopen, URLError, HTTPError
from base64 import encodestring

class PushBullet25(object):
    """ 
        Class providing the bare minimum Python 2.5 compatible support for 
        PushBullet API v2.
    """

    PUSH_URL = "https://api.pushbullet.com/v2/pushes"

    def __init__(self, api_key):
        b64_auth = encodestring('%s:' % api_key).replace('\n', '')
        self._auth_header = ('Authorization', 'Basic %s' % b64_auth)
        self._json_header = ('Content-Type', 'application/json')

    def push_note(self, title, body, device=None, contact=None):
        data = {"type": "note", "title": title, "body": body}
        if device:
            data["device_iden"] = device.device_iden
        elif contact:
            data["email"] = contact.email
        return self._push(data)

    def _push(self, data):
        json_data = json.dumps(data)
        request = Request(self.PUSH_URL, json_data)
        request.add_header(*self._auth_header)
        request.add_header(*self._json_header)

        try:
            r = urlopen(request)
        except HTTPError, e:
            return False, json.loads(e.read())
        except URLError, e:
            return False, {"error": {"message": e.reason}}
        else:
            return True, json.loads(r.read())
