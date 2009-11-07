# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of SickBeard.
#
# SickBeard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickBeard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with SickBeard.  If not, see <http://www.gnu.org/licenses/>.



mediaExtensions = ['avi', 'mkv', 'mpg', 'mpeg']

### Episode statuses
UNKNOWN = -1
UNAIRED = 1
SNATCHED = 2
PREDOWNLOADED = 3
DOWNLOADED = 4
SKIPPED = 5
MISSED = 6
BACKLOG = 7
DISCBACKLOG = 8

statusStrings = {}
statusStrings[UNKNOWN] = "Unknown"
statusStrings[UNAIRED] = "Unaired"
statusStrings[SNATCHED] = "Snatched"
statusStrings[PREDOWNLOADED] = "Predownloaded"
statusStrings[DOWNLOADED] = "Downloaded"
statusStrings[SKIPPED] = "Skipped"
statusStrings[MISSED] = "Missed"
statusStrings[BACKLOG] = "Backlog"
statusStrings[DISCBACKLOG] = "Disc Backlog"

# Provider stuff
#TODO: refactor to providers package
NEWZBIN = 0
TVNZB = 1
TVBINZ = 2

providerNames = {}
providerNames[NEWZBIN] = "Newzbin"
providerNames[TVNZB] = "TVNZB"
providerNames[TVBINZ] = "TVBinz"

### Qualities
HD = 1
SD = 0
ANY = 2

qualityStrings = {}
qualityStrings[HD] = "HD"
qualityStrings[SD] = "SD"
qualityStrings[ANY] = "Any"
