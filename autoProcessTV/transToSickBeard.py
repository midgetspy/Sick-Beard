#!/usr/bin/env python

# Author: Janez Troha <janez.troha@gmail.com>
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

#TR_APP_VERSION
#TR_TIME_LOCALTIME
#TR_TORRENT_DIR
#TR_TORRENT_HASH
#TR_TORRENT_ID
#TR_TORRENT_NAME

import sys
import autoProcessTV
import os
import ConfigParser

if not os.getenv("TR_TORRENT_DIR", False):
    print "No folder supplied - is this being called from Transmission?"
    sys.exit(-1)

try:
    os.sys.path.insert(0, os.path.join(os.path.dirname(sys.argv[0]), "lib"))
    import transmissionrpc
except Exception, e:
    print "Bundled lib failed to load, trying system transmissionrpc"
else:
    import transmissionrpc

config = ConfigParser.ConfigParser()
configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessTV.cfg")
print "Loading config from", configFilename

if not os.path.isfile(configFilename):
    print "ERROR: You need an autoProcessTV.cfg file - did you rename and edit the .sample?"
    sys.exit(-1)

config.read(configFilename)




host = config.get("Transmission", "host")
port = config.get("Transmission", "port")
username = config.get("Transmission", "username")
password = config.get("Transmission", "password")

try:
    download_dir = config.get("Transmission", "download_dir")
except (ConfigParser.NoOptionError, ValueError):
    print "No download_dir supplied for Transmission autoProcessTV.cfg"
    sys.exit(-1)

try:
    tc = transmissionrpc.Client(host, port=port, user=username, password=password)
except transmissionrpc.TransmissionError, e:
    print "Unknown failure! Transmission return text is: " + str(e)
    sys.exit(-1)

try:
    trans_dir = os.getenv("TR_TORRENT_DIR")
    trans_name = os.getenv("TR_TORRENT_NAME")
    trans_hash = os.getenv("TR_TORRENT_HASH")
except Exception, e:
    print e
    sys.exit(-1)

print trans_dir
print trans_name
print trans_hash

##start processing here
if download_dir == trans_dir:
    print tc.info(trans_hash)
    tc.stop(trans_hash)
    tc.remove(trans_hash)
    autoProcessTV.processEpisode(trans_dir, trans_name)
