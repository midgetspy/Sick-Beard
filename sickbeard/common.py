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

import os.path
import operator
import platform
import re

from sickbeard import version

USER_AGENT = 'Sick Beard/alpha2-' + version.SICKBEARD_VERSION.replace(' ', '-') + ' (' + platform.system() + ' ' + platform.release() + ')'

mediaExtensions = ['avi', 'mkv', 'mpg', 'mpeg', 'wmv',
                   'ogm', 'mp4', 'iso', 'img', 'divx',
                   'm2ts', 'm4v', 'ts', 'flv', 'f4v',
                   'mov', 'rmvb', 'vob', 'dvr-ms', 'wtv',
                   'ogv', '3gp', 'webm']

### Other constants
MULTI_EP_RESULT = -1
SEASON_RESULT = -2

### Notification Types
NOTIFY_SNATCH = 1
NOTIFY_DOWNLOAD = 2

notifyStrings = {}
notifyStrings[NOTIFY_SNATCH] = "Started Download"
notifyStrings[NOTIFY_DOWNLOAD] = "Download Finished"

### Episode statuses
UNKNOWN = -1         # should never happen
UNAIRED = 1          # episodes that haven't aired yet
SNATCHED = 2         # qualified with quality
WANTED = 3           # episodes we don't have but want to get
DOWNLOADED = 4       # qualified with quality
SKIPPED = 5          # episodes we don't want
ARCHIVED = 6         # episodes that you don't have locally (counts toward download completion stats)
IGNORED = 7          # episodes that you don't want included in your download stats
SNATCHED_PROPER = 9  # qualified with quality

NAMING_REPEAT = 1
NAMING_EXTEND = 2
NAMING_DUPLICATE = 4
NAMING_LIMITED_EXTEND = 8
NAMING_SEPARATED_REPEAT = 16
NAMING_LIMITED_EXTEND_E_PREFIXED = 32

multiEpStrings = {}
multiEpStrings[NAMING_REPEAT] = "Repeat"
multiEpStrings[NAMING_SEPARATED_REPEAT] = "Repeat (Separated)"
multiEpStrings[NAMING_DUPLICATE] = "Duplicate"
multiEpStrings[NAMING_EXTEND] = "Extend"
multiEpStrings[NAMING_LIMITED_EXTEND] = "Extend (Limited)"
multiEpStrings[NAMING_LIMITED_EXTEND_E_PREFIXED] = "Extend (Limited, E-prefixed)"


class Quality:
    NONE = 0               # 0
    SDTV = 1               # 1
    SDDVD = 1 << 1         # 2
    HDTV = 1 << 2          # 4
    RAWHDTV = 1 << 3       # 8  -- 720p/1080i mpeg2 (trollhd releases)
    FULLHDTV = 1 << 4      # 16 -- 1080p HDTV (QCF releases)
    HDWEBDL = 1 << 5       # 32
    FULLHDWEBDL = 1 << 6   # 64 -- 1080p web-dl
    HDBLURAY = 1 << 7      # 128
    FULLHDBLURAY = 1 << 8  # 256

    # put these bits at the other end of the spectrum, far enough out that they shouldn't interfere
    UNKNOWN = 1 << 15      # 32768

    qualityStrings = {NONE: "N/A",
                      UNKNOWN: "Unknown",
                      SDTV: "SD TV",
                      SDDVD: "SD DVD",
                      HDTV: "HD TV",
                      RAWHDTV: "RawHD TV",
                      FULLHDTV: "1080p HD TV",
                      HDWEBDL: "720p WEB-DL",
                      FULLHDWEBDL: "1080p WEB-DL",
                      HDBLURAY: "720p BluRay",
                      FULLHDBLURAY: "1080p BluRay"}

    statusPrefixes = {DOWNLOADED: "Downloaded",
                      SNATCHED: "Snatched"}

    @staticmethod
    def _getStatusStrings(status):
        toReturn = {}
        for x in Quality.qualityStrings.keys():
            toReturn[Quality.compositeStatus(status, x)] = Quality.statusPrefixes[status] + " (" + Quality.qualityStrings[x] + ")"
        return toReturn

    @staticmethod
    def combineQualities(anyQualities, bestQualities):
        anyQuality = 0
        bestQuality = 0
        if anyQualities:
            anyQuality = reduce(operator.or_, anyQualities)
        if bestQualities:
            bestQuality = reduce(operator.or_, bestQualities)
        return anyQuality | (bestQuality << 16)

    @staticmethod
    def splitQuality(quality):
        anyQualities = []
        bestQualities = []
        for curQual in Quality.qualityStrings.keys():
            if curQual & quality:
                anyQualities.append(curQual)
            if curQual << 16 & quality:
                bestQualities.append(curQual)

        return (sorted(anyQualities), sorted(bestQualities))

    @staticmethod
    def nameQuality(name):
        name = os.path.basename(name)

        # if we have our exact text then assume we put it there
        for x in sorted(Quality.qualityStrings, reverse=True):
            if x == Quality.UNKNOWN:
                continue

            regex = '\W' + Quality.qualityStrings[x].replace(' ', '\W') + '\W'
            regex_match = re.search(regex, name, re.I)
            if regex_match:
                return x

        checkName = lambda namelist, func: func([re.search(x, name, re.I) for x in namelist])

        if checkName(["(pdtv|hdtv|dsr|tvrip).(xvid|x264)"], all) and not checkName(["(720|1080)[pi]"], all) and not checkName(["hr.ws.pdtv.x264"], any):
            return Quality.SDTV
        elif checkName(["web.dl|webrip", "xvid|x264|h.?264"], all) and not checkName(["(720|1080)[pi]"], all):
            return Quality.SDTV
        elif checkName(["(dvdrip|bdrip)(.ws)?.(xvid|divx|x264)"], any) and not checkName(["(720|1080)[pi]"], all):
            return Quality.SDDVD
        elif checkName(["720p", "hdtv", "x264"], all) or checkName(["hr.ws.pdtv.x264"], any) and not checkName(["(1080)[pi]"], all):
            return Quality.HDTV
        elif checkName(["720p|1080i", "hdtv", "mpeg-?2"], all) or checkName(["1080[pi].hdtv", "h.?264"], all):
            return Quality.RAWHDTV
        elif checkName(["1080p", "hdtv", "x264"], all):
            return Quality.FULLHDTV
        elif checkName(["720p", "web.dl|webrip"], all) or checkName(["720p", "itunes", "h.?264"], all):
            return Quality.HDWEBDL
        elif checkName(["1080p", "web.dl|webrip"], all) or checkName(["1080p", "itunes", "h.?264"], all):
            return Quality.FULLHDWEBDL
        elif checkName(["720p", "bluray|hddvd", "x264"], all):
            return Quality.HDBLURAY
        elif checkName(["1080p", "bluray|hddvd", "x264"], all):
            return Quality.FULLHDBLURAY
        else:
            return Quality.UNKNOWN

    @staticmethod
    def assumeQuality(name):
        if name.lower().endswith((".avi", ".mp4")):
            return Quality.SDTV
        elif name.lower().endswith(".mkv"):
            return Quality.HDTV
        elif name.lower().endswith(".ts"):
            return Quality.RAWHDTV
        else:
            return Quality.UNKNOWN

    @staticmethod
    def compositeStatus(status, quality):
        return status + 100 * quality

    @staticmethod
    def qualityDownloaded(status):
        return (status - DOWNLOADED) / 100

    @staticmethod
    def splitCompositeStatus(status):
        """Returns a tuple containing (status, quality)"""
        if status == UNKNOWN:
            return (UNKNOWN, Quality.UNKNOWN)

        for x in sorted(Quality.qualityStrings.keys(), reverse=True):
            if status > x * 100:
                return (status - x * 100, x)

        return (status, Quality.NONE)

    @staticmethod
    def statusFromName(name, assume=True):
        quality = Quality.nameQuality(name)
        if assume and quality == Quality.UNKNOWN:
            quality = Quality.assumeQuality(name)
        return Quality.compositeStatus(DOWNLOADED, quality)

    DOWNLOADED = None
    SNATCHED = None
    SNATCHED_PROPER = None

Quality.DOWNLOADED = [Quality.compositeStatus(DOWNLOADED, x) for x in Quality.qualityStrings.keys()]
Quality.SNATCHED = [Quality.compositeStatus(SNATCHED, x) for x in Quality.qualityStrings.keys()]
Quality.SNATCHED_PROPER = [Quality.compositeStatus(SNATCHED_PROPER, x) for x in Quality.qualityStrings.keys()]

SD = Quality.combineQualities([Quality.SDTV, Quality.SDDVD], [])
HD = Quality.combineQualities([Quality.HDTV, Quality.FULLHDTV, Quality.HDWEBDL, Quality.FULLHDWEBDL, Quality.HDBLURAY, Quality.FULLHDBLURAY], [])  # HD720p + HD1080p
HD720p = Quality.combineQualities([Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY], [])
HD1080p = Quality.combineQualities([Quality.FULLHDTV, Quality.FULLHDWEBDL, Quality.FULLHDBLURAY], [])
ANY = Quality.combineQualities([Quality.SDTV, Quality.SDDVD, Quality.HDTV, Quality.FULLHDTV, Quality.HDWEBDL, Quality.FULLHDWEBDL, Quality.HDBLURAY, Quality.FULLHDBLURAY, Quality.UNKNOWN], [])  # SD + HD

qualityPresets = (SD, HD, HD720p, HD1080p, ANY)
qualityPresetStrings = {SD: "SD",
                        HD: "HD",
                        HD720p: "HD720p",
                        HD1080p: "HD1080p",
                        ANY: "Any"}


class StatusStrings:
    def __init__(self):
        self.statusStrings = {UNKNOWN: "Unknown",
                              UNAIRED: "Unaired",
                              SNATCHED: "Snatched",
                              DOWNLOADED: "Downloaded",
                              SKIPPED: "Skipped",
                              SNATCHED_PROPER: "Snatched (Proper)",
                              WANTED: "Wanted",
                              ARCHIVED: "Archived",
                              IGNORED: "Ignored"}

    def __getitem__(self, name):
        if name in Quality.DOWNLOADED + Quality.SNATCHED + Quality.SNATCHED_PROPER:
            status, quality = Quality.splitCompositeStatus(name)
            if quality == Quality.NONE:
                return self.statusStrings[status]
            else:
                return self.statusStrings[status] + " (" + Quality.qualityStrings[quality] + ")"
        else:
            return self.statusStrings[name]

    def has_key(self, name):
        return name in self.statusStrings or name in Quality.DOWNLOADED or name in Quality.SNATCHED or name in Quality.SNATCHED_PROPER

statusStrings = StatusStrings()


class Overview:
    UNAIRED = UNAIRED  # 1
    QUAL = 2
    WANTED = WANTED  # 3
    GOOD = 4
    SKIPPED = SKIPPED  # 5

    # For both snatched statuses. Note: SNATCHED/QUAL have same value and break dict.
    SNATCHED = SNATCHED_PROPER  # 9

    overviewStrings = {SKIPPED: "skipped",
                       WANTED: "wanted",
                       QUAL: "qual",
                       GOOD: "good",
                       UNAIRED: "unaired",
                       SNATCHED: "snatched"}

# Get our xml namespaces correct for lxml
XML_NSMAP = {'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
             'xsd': 'http://www.w3.org/2001/XMLSchema'}


countryList = {'Australia': 'AU',
               'Canada': 'CA',
               'USA': 'US'
               }
