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

# SABnzbd user script parameters - see: http://wiki.sabnzbd.org/user-scripts

# 0  sys.argv[0] is the name of this script

# 1  The final directory of the job (full path)
if len(sys.argv) < 2:
    print ("No folder supplied - is this being called from SABnzbd?")
    sys.exit(1)
else:
    download_final_dir = sys.argv[1]

# 2  The original name of the NZB file
org_NZB_name = sys.argv[2] if len(sys.argv) > 3 else None

# 3  Clean version of the job name (no path info and ".nzb" removed)
clean_NZB_file = sys.argv[3] if len(sys.argv) > 4 else None

# 4  Indexer's report number (if supported)
indexer_report = sys.argv[4] if len(sys.argv) > 5 else None

# 5  User-defined category
sab_user_category = sys.argv[5] if len(sys.argv) > 6 else None

# 6  Group that the NZB was posted in e.g. alt.binaries.x
group_NZB = sys.argv[6] if len(sys.argv) > 7 else None

# 7  Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
sab_post_processing_status = sys.argv[7] if len(sys.argv) > 8 else None

# Only final_dir and org_NZB_name are being used to process episodes
autoProcessTV.processEpisode(download_final_dir, org_NZB_name)
