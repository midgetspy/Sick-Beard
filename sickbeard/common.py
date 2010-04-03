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

import sickbeard

mediaExtensions = ['avi', 'mkv', 'mpg', 'mpeg', 'wmv', 'ogm', 'mp4', 'iso', 'img', 'divx', 'm2ts', 'm4v', 'ts', 'flv', 'f4v']

### Notification Types
NOTIFY_SNATCH = 1
NOTIFY_DOWNLOAD = 2

notifyStrings = {}
notifyStrings[NOTIFY_SNATCH] = "Started Download"
notifyStrings[NOTIFY_DOWNLOAD] = "Download Finished"

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
SNATCHED_PROPER = 9
SNATCHED_BACKLOG = 10

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
statusStrings[SNATCHED_PROPER] = "Snatched (Proper)"
statusStrings[SNATCHED_BACKLOG] = "Snatched (Backlog)"

### Qualities
HD = 1
SD = 3
ANY = 2
BEST = 4

qualityStrings = {}
qualityStrings[HD] = "HD"
qualityStrings[SD] = "SD"
qualityStrings[ANY] = "Any"
qualityStrings[BEST] = "Best"

# Actions
ACTION_SNATCHED = 1
ACTION_PRESNATCHED = 2
ACTION_DOWNLOADED = 3

actionStrings = {}
actionStrings[ACTION_SNATCHED] = "Snatched"
actionStrings[ACTION_PRESNATCHED] = "Pre Snatched"
actionStrings[ACTION_DOWNLOADED] = "Downloaded"

# Get our xml namespaces correct for lxml
XML_NSMAP = {'xsi': 'http://www.w3.org/2001/XMLSchema-instance', 
             'xsd': 'http://www.w3.org/2001/XMLSchema'}



#####################################################################
###
###  DO NOT EDIT THIS MANUALLY! If you find a show that isn't
###  being found please submit a ticket on google code so that
###  I can fix the problem for everybody:
###  http://code.google.com/p/sickbeard/issues/entry
###
#####################################################################

sceneExceptions = {72546: ['CSI'],
                   110381: ['Archer'],
                   83897: ['Life After People: The Series'],
                   80552: ['Kitchen Nightmares (US)'],
                   71256: ['The Daily Show'],
                   75692: ['Law & Order: SVU'],
                   71489: ['Law & Order: Criminal Intent', 'Law & Order: CI']
                   }

countryList = {'Australia': 'AU',
               'Canada': 'CA',
               'USA': 'US'
               }