#!/usr/bin/python

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


import sys
import zipimport
try:
    import autoProcessTV
except zipimport.ZipImportError:
    # This script does not work well with the current default python path SabNZBD sets
    # Set it to the same python path as OS X defaults
    # stolen from http://forums.sabnzbd.org/index.php?topic=3562.msg25576
    osx_python_path = [
        sys.path[0],
        "/System/Library/Frameworks/Python.framework/Versions/2.6/lib/python26.zip",
        "/System/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6",
        "/System/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/plat-darwin",
        "/System/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/plat-mac",
        "/System/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/plat-mac/lib-scriptpackages",
        "/System/Library/Frameworks/Python.framework/Versions/2.6/Extras/lib/python",
        "/System/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/lib-tk",
        "/System/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/lib-old",
        "/System/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/lib-dynload",
        "/Library/Python/2.6/site-packages",
        "/System/Library/Frameworks/Python.framework/Versions/2.6/Extras/lib/python/PyObjC",
        "/System/Library/Frameworks/Python.framework/Versions/2.6/Extras/lib/python/wx-2.8-mac-unicode"
    ]

    sys.path = osx_python_path
    import autoProcessTV

if len(sys.argv) < 2:
    print "No folder supplied - is this being called from SABnzbd?"
    sys.exit()
elif len(sys.argv) >= 3:
    autoProcessTV.processEpisode(sys.argv[1], sys.argv[2])
else:
    autoProcessTV.processEpisode(sys.argv[1])