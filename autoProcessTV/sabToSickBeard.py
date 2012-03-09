#!/usr/bin/env python

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
import autoProcessTV

if len(sys.argv) < 8:
    print "Not enough arguments received from SABnzbd. Please update it."
    sys.exit()
else:
    autoProcessTV.processEpisode(sys.argv[1], sys.argv[2], sys.argv[7])

# SABnzbd argv:
# 1	The final directory of the job (full path)
# 2	The original name of the NZB file
# 3	Clean version of the job name (no path info and ".nzb" removed)
# 4	Indexer's report number (if supported)
# 5	User-defined category
# 6	Group that the NZB was posted in e.g. alt.binaries.x
# 7	Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+21
