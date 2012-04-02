# Author: Mr_Orange <mr_orange@hotmail.it>
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
from sickbeard import logger
from urlparse import urlparse
import lib.transmissionrpc as transmissionrpc


def sendTORRENT(torrent):

    path = sickbeard.TORRENT_PATH
    ratio = sickbeard.TORRENT_RATIO
    paused = sickbeard.TORRENT_PAUSED
    try:
        host = urlparse(sickbeard.TORRENT_HOST)
    except Exception, e:
        logger.log(u"Host properties are not filled in correctly, port is missing.", logger.ERROR)
        return False

    # Set parameters for Transmission
    params = {}
    change_params = {}

    if not (ratio == ''):
        change_params['seedRatioLimit'] = ratio
        change_params['seedRatioMode'] = 1

    if not (paused == ''):
        params['paused'] = paused

    if not (path == ''):
        params['download_dir'] = path

    try:
        tc = transmissionrpc.Client(host.hostname, port=host.port, user=sickbeard.TORRENT_USERNAME, password=sickbeard.TORRENT_PASSWORD)
        tr_id = tc.add_uri(torrent.url, **params)

        # Change settings of added torrents
        for item in tr_id:
            try:
                tc.change(item, timeout=None, **change_params)
            except transmissionrpc.TransmissionError, e:
                logger.log(u"Failed to change settings for transfer in transmission: " + str(e), logger.ERROR)

        return True

    except transmissionrpc.TransmissionError, e:
        logger.log("Unknown failure sending Torrent to Transmission. Return text is: " + str(e), logger.ERROR)
        return False


def testAuthentication(host, username, password):

    try:
        host = urlparse(sickbeard.TORRENT_HOST)
    except Exception, e:
        return False, u"Host properties are not filled in correctly, port is missing."

    try:
        tc = transmissionrpc.Client(host.hostname, port=host.port, user=username, password=password)
        tc.list()
        return True, u"Success: Connected and Authenticated. RPC version: " + str(tc.rpc_version)

    except transmissionrpc.TransmissionError, e:
        return False, u"Transmission return text is: " + str(e)
