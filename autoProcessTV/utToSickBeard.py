#!/usr/bin/env python

# Author: Derek Battams <derek@battams.ca>
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
#
# INSTRUCTIONS
#
# Use this script as the exe to run _on a uTorrent state change_; it will
# only trigger post processing after a torrent is done.
#
# Pass the script the download dir, file and torrent state.  In uTorrent,
# configure the command line something like this:
#
# C:\SickBeard\autoProcessTV\utToSickBeard.py "%D\%F" "%S"

import sys
import os.path
import tempfile
import shutil
import autoProcessTV
import ConfigParser

# uTorrent states
STATE_ERROR = 1
STATE_CHECKED = 2
STATE_PAUSED = 3
STATE_SUPER_SEEDING = 4
STATE_SEEDING = 5
STATE_DOWNLOADING = 6
STATE_SUPER_SEED_F = 7
STATE_SEEDING_F = 8
STATE_DOWNLOADING_F = 9
STATE_QUEUED_SEED = 10
STATE_FINISHED = 11
STATE_QUEUED = 12
STATE_STOPPED = 13

if len(sys.argv) < 3:
    print '%s: <dir|file> <state>' % os.path.basename(sys.argv[0])
    print 'dir|file: The directory or file of the torrent download; always'
    print '          specify the full file path for single file torrents'
    print '   state: The current state of the torrent job from uTorrent'
    sys.exit(1)

if int(sys.argv[2]) != STATE_FINISHED:
    print 'Ignoring all states but "Finished"!'
    sys.exit(1)

config = ConfigParser.ConfigParser()
configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessTV.cfg")
print "Loading config from", configFilename
if not os.path.isfile(configFilename):
    print "ERROR: You need an autoProcessTV.cfg file - did you rename and edit the .sample?"
    sys.exit(1)
config.read(configFilename)

src = os.path.normcase(os.path.normpath(sys.argv[1]))
utDownloadDir = os.path.normcase(os.path.normpath(config.get('uTorrent', 'download_dir')))
processDir = None
if os.path.isfile(src):
    parent = os.path.dirname(src)
    if parent == utDownloadDir:
        # We need to move a file to a tmp dir then let SB process that dir
        # Why? If SB is set to _not_ keep originals after a rename then it will
        # attempt to nuke the dir the file was processed from, which can cause
        # all sorts of headaches with uTorrent
        tdir = tempfile.mkdtemp('', 'tmp_', parent)
        shutil.move(src, tdir)
        processDir = tdir
    else:
        # A subdir was created for the single file torrent; just process that dir then
        processDir = parent
elif os.path.isdir(src) and src != utDownloadDir:
    # A multi file torrent in its own dir
    processDir = sys.argv[1]
elif src == utDownloadDir:
    # We CANNOT process the defined uTorrent download dir or else we may nuke it!
    print 'ERROR: Cannot process defined uTorrent download dir; check your settings! [%s]' % src
else:
    print 'ERROR: Unknown argument type! [%s]' % src

if processDir != None:
    processDir = os.path.abspath(processDir)
    print 'Processing: %s' % processDir
    autoProcessTV.processEpisode(processDir)

