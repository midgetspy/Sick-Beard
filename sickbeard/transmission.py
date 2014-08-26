# Author: Reinier Schoof <reinier@skoef.nl>
# URL: https://github.com/midgetspy/Sick-Beard
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

import base64
import httplib

import sickbeard
from sickbeard import logger

try:
    import json
except ImportError:
    from lib import simplejson as json

def rpcCall(host, port, username, password, rpc_path, method, arguments):
    # first run, to obtain sessionid
    conn = httplib.HTTPConnection(host, int(port))
    headers = {}
    if username is not None and len(username) > 0:
        headers['Authorization'] = 'Basic %s' % base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
    conn.request('POST', rpc_path, '', headers)
    response = conn.getresponse()
    conn.close()

    # 401 means authentication failed
    if response.status == 401:
        raise Exception('Authentication failed')
    # since we don't use session_id we'd expect
    # HTTP 409/Conflict
    if response.status != 409:
        raise Exception("expected http status 409 but got %d" % response.status)

    session_id = response.getheader('x-transmission-session-id')
    if session_id is None:
        raise Exception('got 409 but no session-id')

    # perform rcp request, this time with session id
    headers['X-Transmission-Session-Id'] = session_id
    body = json.dumps({'method': method, 'arguments': arguments})
    conn.request('POST', rpc_path, body, headers)
    response = conn.getresponse()

    # check http success
    if response.status != 200:
        raise Exception('response with status %d' % response.status)

    # check json success
    response_body = response.read()
    response_json = json.loads(response_body)
    if response_json is None or 'result' not in response_json or response_json['result'] != 'success':
        raise Exception('request failed: %s' % response_body)

    return response_json['arguments']

def testAuthentication(host, port, username, password, rpc_path):
    try:
        rpcCall(host, port, username, password, rpc_path, 'torrent-verify', {})
    except Exception, e:
        return False
    return True

def sendTorrent(torrent):
    # set arguments
    arguments = {
        'download-dir': sickbeard.TRANSMISSION_DIRECTORY,
    }

    if torrent.url:
        arguments['filename'] = torrent.url

    try:
        result = rpcCall(sickbeard.TRANSMISSION_HOST, sickbeard.TRANSMISSION_PORT, sickbeard.TRANSMISSION_USERNAME,
            sickbeard.TRANSMISSION_PASSWORD, sickbeard.TRANSMISSION_RPC_PATH, 'torrent-add', arguments)
    except Exception, e:
        logger.log('could not start torrent %s: %s' % (torrent.name, str(e)))
