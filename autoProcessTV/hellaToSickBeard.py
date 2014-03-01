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

try:
    import autoProcessTV
except:
    print ("Can't import autoProcessTV.py, make sure it's in the same folder as " + sys.argv[0])
    sys.exit(1)

if len(sys.argv) < 4:
    print ("No folder supplied - is this being called from HellaVCR?")
    sys.exit(1)
else:
    autoProcessTV.processEpisode(sys.argv[3], sys.argv[2])
