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
import os.path
import operator

mediaExtensions = ['avi', 'mkv', 'mpg', 'mpeg', 'wmv',
                   'ogm', 'mp4', 'iso', 'img', 'divx',
                   'm2ts', 'm4v', 'ts', 'flv', 'f4v',
                   'mov', 'rmvb']

resultFilters = ("subpack", "nlsub", "samplefix", "nfofix", "sample")

### Notification Types
NOTIFY_SNATCH = 1
NOTIFY_DOWNLOAD = 2

notifyStrings = {}
notifyStrings[NOTIFY_SNATCH] = "Started Download"
notifyStrings[NOTIFY_DOWNLOAD] = "Download Finished"

### Episode statuses
UNKNOWN = -1 # should never happen
UNAIRED = 1 # episodes that haven't aired yet
SNATCHED = 2 # qualified with quality
WANTED = 3 # episodes we don't have but want to get
DOWNLOADED = 4 # qualified with quality
SKIPPED = 5 # episodes we don't want
ARCHIVED = 6 # episodes that you don't have locally (counts toward download completion stats)
IGNORED = 7 # episodes that you don't want included in your download stats
SNATCHED_PROPER = 9 # qualified with quality

class Quality:

    NONE = 0
    SDTV = 1
    SDDVD = 1<<1 # 2
    HDTV = 1<<2 # 4
    HDWEBDL = 1<<3 # 8
    HDBLURAY = 1<<4 # 16
    FULLHDBLURAY = 1<<5 # 32

    # put these bits at the other end of the spectrum, far enough out that they shouldn't interfere
    UNKNOWN = 1<<15
    
    qualityStrings = {NONE: "N/A",
                      UNKNOWN: "Unknown",
                      SDTV: "SD TV",
                      SDDVD: "SD DVD",
                      HDTV: "720p TV",
                      HDWEBDL: "720p WEB-DL",
                      HDBLURAY: "720p BluRay",
                      FULLHDBLURAY: "1080p BluRay"}

    statusPrefixes = {DOWNLOADED: "Downloaded",
                      SNATCHED: "Snatched"}

    @staticmethod
    def _getStatusStrings(status):
        toReturn = {}
        for x in Quality.qualityStrings.keys():
            toReturn[Quality.compositeStatus(status, x)] = Quality.statusPrefixes[status]+" ("+Quality.qualityStrings[x]+")"
        return toReturn

    @staticmethod
    def combineQualities(anyQualities, bestQualities):
        anyQuality = 0
        bestQuality = 0
        if anyQualities:
            anyQuality = reduce(operator.or_, anyQualities)
        if bestQualities:
            bestQuality = reduce(operator.or_, bestQualities)
        return anyQuality | (bestQuality<<16)

    @staticmethod
    def splitQuality(quality):
        anyQualities = []
        bestQualities = []
        for curQual in Quality.qualityStrings.keys():
            if curQual & quality:
                anyQualities.append(curQual)
            if curQual<<16 & quality:
                bestQualities.append(curQual)
        
        return (anyQualities, bestQualities)

    @staticmethod
    def nameQuality(name, nzbMatrix=False):
        
        name = os.path.basename(name)
        
        # if we have our exact text then assume we put it there 
        for x in Quality.qualityStrings:
            if Quality.qualityStrings[x] in name:
                return x
        
        if nzbMatrix:
            fixName = lambda x: x.replace("."," ").replace("-"," ")
        else:
            fixName = lambda x: x
        
        containsOne = lambda list: any([fixName(x) in name.lower() for x in list])
        containsAll = lambda list: all([fixName(x) in name.lower() for x in list])
    
        if containsOne(["pdtv.xvid", "hdtv.xvid", "dsr.xvid"]):
            return Quality.SDTV
        elif containsOne(["dvdrip.xvid", "bdrip.xvid"]):
            return Quality.SDDVD
        elif containsAll(["720p", "hdtv", "x264"]):
            return Quality.HDTV
        elif containsAll(["720p", "web-dl"]):
            return Quality.HDWEBDL
        elif containsAll(["720p", "bluray", "x264"]):
            return Quality.HDBLURAY
        elif containsAll(["1080p", "bluray", "x264"]):
            return Quality.FULLHDBLURAY
        else:
            return Quality.UNKNOWN

    @staticmethod
    def assumeQuality(name):
        
        if name.endswith(".avi"):
            return Quality.SDTV
        elif name.endswith(".mkv"):
            return Quality.HDTV
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
        for x in sorted(Quality.qualityStrings.keys(), reverse=True):
            if status > x*100:
                return (status-x*100, x)
        
        return (Quality.NONE, status)

    @staticmethod
    def statusFromName(name, assume=True):
        quality = Quality.nameQuality(name)
        if assume and quality == Quality.UNKNOWN:
            quality = Quality.assumeQuality(name)
        return Quality.compositeStatus(DOWNLOADED, quality)


Quality.DOWNLOADED = [Quality.compositeStatus(DOWNLOADED, x) for x in Quality.qualityStrings.keys()]
Quality.SNATCHED = [Quality.compositeStatus(SNATCHED, x) for x in Quality.qualityStrings.keys()]
Quality.SNATCHED_PROPER = [Quality.compositeStatus(SNATCHED_PROPER, x) for x in Quality.qualityStrings.keys()]

HD = Quality.combineQualities([Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY], []) 
SD = Quality.combineQualities([Quality.SDTV, Quality.SDDVD], [])
ANY = Quality.combineQualities([Quality.SDTV, Quality.SDDVD, Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY], [])
BEST = Quality.combineQualities([Quality.SDTV, Quality.HDTV], [Quality.SDTV, Quality.HDTV])

qualityPresets = (SD, HD, ANY, BEST)
qualityPresetStrings = {SD: "SD",
                        HD: "HD",
                        ANY: "Any",
                        BEST: "Best"}

class StatusStrings:
    def __init__(self):
        self.statusStrings = {UNKNOWN: "Unknown",
                              UNAIRED: "Unaired",
                              SNATCHED: "Snatched",
                              DOWNLOADED:  "Downloaded",
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
                return self.statusStrings[status]+" ("+Quality.qualityStrings[quality]+")"
        else:
            return self.statusStrings[name]

    def has_key(self, name):
        return name in self.statusStrings or name in Quality.DOWNLOADED or name in Quality.SNATCHED or name in Quality.SNATCHED_PROPER

statusStrings = StatusStrings()

class Overview:
    SKIPPED = 1
    WANTED = 2
    QUAL = 3
    GOOD = 4
    UNAIRED = 5
    
    overviewStrings = {SKIPPED: "skipped",
                       WANTED: "wanted",
                       QUAL: "qual",
                       GOOD: "good",
                       UNAIRED: "unaired"}

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
                   73696: ['CSI: New York'],
                   110381: ['Archer'],
                   83897: ['Life After People: The Series'],
                   80552: ['Kitchen Nightmares (US)'],
                   71256: ['The Daily Show'],
                   75692: ['Law & Order: SVU'],
                   71489: ['Law & Order: Criminal Intent', 'Law & Order: CI'],
                   79590: ['Dancing With The Stars (US)']
                   }

countryList = {'Australia': 'AU',
               'Canada': 'CA',
               'USA': 'US'
               }