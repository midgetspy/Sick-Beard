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
