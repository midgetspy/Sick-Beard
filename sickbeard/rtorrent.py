# Author: Nic Wolfe <nic@wolfeden.ca>
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



import httplib
import datetime

import sickbeard

import xmlrpclib

from sickbeard.providers.generic import GenericProvider

from sickbeard import logger

def sendTorrent(torrent):
    """
    Sends a torrent to rTorrent via the XMLRPC API.
    
    torrent: The Torrent Search Results object to send to rtorrent
    """

    if sickbeard.RTORRENT_URL == None:
        logger.log(u"No rTorrent host found in configuration. Please configure it.", logger.ERROR)
        return False

    rtorrent_xmlrpc = xmlrpclib.ServerProxy(sickbeard.RTORRENT_URL)

    # if it aired recently make it high priority
    for curEp in torrent.episodes:
        if datetime.date.today() - curEp.airdate <= datetime.timedelta(days=7):
            priority = 3


    # if it's a normal result need to download the torrent
    if torrent.resultType == "torrent":
        genProvider = GenericProvider("")
        data = genProvider.getURL(torrent.url)
        if (data == None):
            return False

    torrentcontent64 = xmlrpclib.Binary(data)

    logger.log(u"Sending torrent to rTorrent")
    logger.log(u"URL: " + sickbeard.RTORRENT_URL, logger.DEBUG)

    try:
        if (rtorrent_xmlrpc.load_raw_start(torrentcontent64, "d.priority.set=" + str(priority), \
            "d.custom1.set=" + str(sickbeard.RTORRENT_CATEGORY)) == 0):
            logger.log(u"torrent sent to rTorrent successfully", logger.DEBUG)
            return True
        else:
            logger.log(u"rTorrent could not add %s to the rTorrent queue" % (torrent.name + ".torrent"), logger.ERROR)
            return False

    except httplib.socket.error:
        logger.log(u"Please check your rTorrent host and port (if it is running). rTorrent is not responding to this combination", logger.ERROR)
        return False

    except xmlrpclib.ProtocolError, e:
        if (e.errmsg == "Unauthorized"):
            logger.log(u"rTorrent password is incorrect.", logger.ERROR)
        else:
            logger.log(u"Protocol Error: " + e.errmsg, logger.ERROR)
        return False

