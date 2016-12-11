# -*- coding: utf-8 -*-
# Copyright (c) 2008-2013 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

import logging
from six import iteritems

LOGGER = logging.getLogger('transmissionrpc')
LOGGER.setLevel(logging.ERROR)

def mirror_dict(source):
    """
    Creates a dictionary with all values as keys and all keys as values.
    """
    source.update(dict((value, key) for key, value in iteritems(source)))
    return source

DEFAULT_PORT = 9091

DEFAULT_TIMEOUT = 30.0

TR_PRI_LOW    = -1
TR_PRI_NORMAL =  0
TR_PRI_HIGH   =  1

PRIORITY = mirror_dict({
    'low'    : TR_PRI_LOW,
    'normal' : TR_PRI_NORMAL,
    'high'   : TR_PRI_HIGH
})

TR_RATIOLIMIT_GLOBAL    = 0 # follow the global settings
TR_RATIOLIMIT_SINGLE    = 1 # override the global settings, seeding until a certain ratio
TR_RATIOLIMIT_UNLIMITED = 2 # override the global settings, seeding regardless of ratio

RATIO_LIMIT = mirror_dict({
    'global'    : TR_RATIOLIMIT_GLOBAL,
    'single'    : TR_RATIOLIMIT_SINGLE,
    'unlimited' : TR_RATIOLIMIT_UNLIMITED
})

TR_IDLELIMIT_GLOBAL     = 0 # follow the global settings
TR_IDLELIMIT_SINGLE     = 1 # override the global settings, seeding until a certain idle time
TR_IDLELIMIT_UNLIMITED  = 2 # override the global settings, seeding regardless of activity

IDLE_LIMIT = mirror_dict({
    'global'    : TR_RATIOLIMIT_GLOBAL,
    'single'    : TR_RATIOLIMIT_SINGLE,
    'unlimited' : TR_RATIOLIMIT_UNLIMITED
})

# A note on argument maps
# These maps are used to verify *-set methods. The information is structured in
# a tree.
# set +- <argument1> - [<type>, <added version>, <removed version>, <previous argument name>, <next argument name>, <description>]
#  |  +- <argument2> - [<type>, <added version>, <removed version>, <previous argument name>, <next argument name>, <description>]
#  |
# get +- <argument1> - [<type>, <added version>, <removed version>, <previous argument name>, <next argument name>, <description>]
#     +- <argument2> - [<type>, <added version>, <removed version>, <previous argument name>, <next argument name>, <description>]

# Arguments for torrent methods
TORRENT_ARGS = {
    'get' : {
        'activityDate':                 ('number', 1, None, None, None, 'Last time of upload or download activity.'),
        'addedDate':                    ('number', 1, None, None, None, 'The date when this torrent was first added.'),
        'announceResponse':             ('string', 1, 7, None, None, 'The announce message from the tracker.'),
        'announceURL':                  ('string', 1, 7, None, None, 'Current announce URL.'),
        'bandwidthPriority':            ('number', 5, None, None, None, 'Bandwidth priority. Low (-1), Normal (0) or High (1).'),
        'comment':                      ('string', 1, None, None, None, 'Torrent comment.'),
        'corruptEver':                  ('number', 1, None, None, None, 'Number of bytes of corrupt data downloaded.'),
        'creator':                      ('string', 1, None, None, None, 'Torrent creator.'),
        'dateCreated':                  ('number', 1, None, None, None, 'Torrent creation date.'),
        'desiredAvailable':             ('number', 1, None, None, None, 'Number of bytes avalable and left to be downloaded.'),
        'doneDate':                     ('number', 1, None, None, None, 'The date when the torrent finished downloading.'),
        'downloadDir':                  ('string', 4, None, None, None, 'The directory path where the torrent is downloaded to.'),
        'downloadedEver':               ('number', 1, None, None, None, 'Number of bytes of good data downloaded.'),
        'downloaders':                  ('number', 4, 7, None, None, 'Number of downloaders.'),
        'downloadLimit':                ('number', 1, None, None, None, 'Download limit in Kbps.'),
        'downloadLimited':              ('boolean', 5, None, None, None, 'Download limit is enabled'),
        'downloadLimitMode':            ('number', 1, 5, None, None, 'Download limit mode. 0 means global, 1 means signle, 2 unlimited.'),
        'error':                        ('number', 1, None, None, None, 'Kind of error. 0 means OK, 1 means tracker warning, 2 means tracker error, 3 means local error.'),
        'errorString':                  ('number', 1, None, None, None, 'Error message.'),
        'eta':                          ('number', 1, None, None, None, 'Estimated number of seconds left when downloading or seeding. -1 means not available and -2 means unknown.'),
        'etaIdle':                      ('number', 15, None, None, None, 'Estimated number of seconds left until the idle time limit is reached. -1 means not available and -2 means unknown.'),        
        'files':                        ('array', 1, None, None, None, 'Array of file object containing key, bytesCompleted, length and name.'),
        'fileStats':                    ('array', 5, None, None, None, 'Aray of file statistics containing bytesCompleted, wanted and priority.'),
        'hashString':                   ('string', 1, None, None, None, 'Hashstring unique for the torrent even between sessions.'),
        'haveUnchecked':                ('number', 1, None, None, None, 'Number of bytes of partial pieces.'),
        'haveValid':                    ('number', 1, None, None, None, 'Number of bytes of checksum verified data.'),
        'honorsSessionLimits':          ('boolean', 5, None, None, None, 'True if session upload limits are honored'),
        'id':                           ('number', 1, None, None, None, 'Session unique torrent id.'),
        'isFinished':                   ('boolean', 9, None, None, None, 'True if the torrent is finished. Downloaded and seeded.'),
        'isPrivate':                    ('boolean', 1, None, None, None, 'True if the torrent is private.'),
        'isStalled':                    ('boolean', 14, None, None, None, 'True if the torrent has stalled (been idle for a long time).'),
        'lastAnnounceTime':             ('number', 1, 7, None, None, 'The time of the last announcement.'),
        'lastScrapeTime':               ('number', 1, 7, None, None, 'The time af the last successful scrape.'),
        'leechers':                     ('number', 1, 7, None, None, 'Number of leechers.'),
        'leftUntilDone':                ('number', 1, None, None, None, 'Number of bytes left until the download is done.'),
        'magnetLink':                   ('string', 7, None, None, None, 'The magnet link for this torrent.'),
        'manualAnnounceTime':           ('number', 1, None, None, None, 'The time until you manually ask for more peers.'),
        'maxConnectedPeers':            ('number', 1, None, None, None, 'Maximum of connected peers.'),
        'metadataPercentComplete':      ('number', 7, None, None, None, 'Download progress of metadata. 0.0 to 1.0.'),
        'name':                         ('string', 1, None, None, None, 'Torrent name.'),
        'nextAnnounceTime':             ('number', 1, 7, None, None, 'Next announce time.'),
        'nextScrapeTime':               ('number', 1, 7, None, None, 'Next scrape time.'),
        'peer-limit':                   ('number', 5, None, None, None, 'Maximum number of peers.'),
        'peers':                        ('array', 2, None, None, None, 'Array of peer objects.'),
        'peersConnected':               ('number', 1, None, None, None, 'Number of peers we are connected to.'),
        'peersFrom':                    ('object', 1, None, None, None, 'Object containing download peers counts for different peer types.'),
        'peersGettingFromUs':           ('number', 1, None, None, None, 'Number of peers we are sending data to.'),
        'peersKnown':                   ('number', 1, 13, None, None, 'Number of peers that the tracker knows.'),
        'peersSendingToUs':             ('number', 1, None, None, None, 'Number of peers sending to us'),
        'percentDone':                  ('double', 5, None, None, None, 'Download progress of selected files. 0.0 to 1.0.'),
        'pieces':                       ('string', 5, None, None, None, 'String with base64 encoded bitfield indicating finished pieces.'),
        'pieceCount':                   ('number', 1, None, None, None, 'Number of pieces.'),
        'pieceSize':                    ('number', 1, None, None, None, 'Number of bytes in a piece.'),
        'priorities':                   ('array', 1, None, None, None, 'Array of file priorities.'),
        'queuePosition':                ('number', 14, None, None, None, 'The queue position.'),
        'rateDownload':                 ('number', 1, None, None, None, 'Download rate in bps.'),
        'rateUpload':                   ('number', 1, None, None, None, 'Upload rate in bps.'),
        'recheckProgress':              ('double', 1, None, None, None, 'Progress of recheck. 0.0 to 1.0.'),
        'secondsDownloading':           ('number', 15, None, None, None, ''),
        'secondsSeeding':               ('number', 15, None, None, None, ''),
        'scrapeResponse':               ('string', 1, 7, None, None, 'Scrape response message.'),
        'scrapeURL':                    ('string', 1, 7, None, None, 'Current scrape URL'),
        'seeders':                      ('number', 1, 7, None, None, 'Number of seeders reported by the tracker.'),
        'seedIdleLimit':                ('number', 10, None, None, None, 'Idle limit in minutes.'),
        'seedIdleMode':                 ('number', 10, None, None, None, 'Use global (0), torrent (1), or unlimited (2) limit.'),
        'seedRatioLimit':               ('double', 5, None, None, None, 'Seed ratio limit.'),
        'seedRatioMode':                ('number', 5, None, None, None, 'Use global (0), torrent (1), or unlimited (2) limit.'),
        'sizeWhenDone':                 ('number', 1, None, None, None, 'Size of the torrent download in bytes.'),
        'startDate':                    ('number', 1, None, None, None, 'The date when the torrent was last started.'),
        'status':                       ('number', 1, None, None, None, 'Current status, see source'),
        'swarmSpeed':                   ('number', 1, 7, None, None, 'Estimated speed in Kbps in the swarm.'),
        'timesCompleted':               ('number', 1, 7, None, None, 'Number of successful downloads reported by the tracker.'),
        'trackers':                     ('array', 1, None, None, None, 'Array of tracker objects.'),
        'trackerStats':                 ('object', 7, None, None, None, 'Array of object containing tracker statistics.'),
        'totalSize':                    ('number', 1, None, None, None, 'Total size of the torrent in bytes'),
        'torrentFile':                  ('string', 5, None, None, None, 'Path to .torrent file.'),
        'uploadedEver':                 ('number', 1, None, None, None, 'Number of bytes uploaded, ever.'),
        'uploadLimit':                  ('number', 1, None, None, None, 'Upload limit in Kbps'),
        'uploadLimitMode':              ('number', 1, 5, None, None, 'Upload limit mode. 0 means global, 1 means signle, 2 unlimited.'),
        'uploadLimited':                ('boolean', 5, None, None, None, 'Upload limit enabled.'),
        'uploadRatio':                  ('double', 1, None, None, None, 'Seed ratio.'),
        'wanted':                       ('array', 1, None, None, None, 'Array of booleans indicated wanted files.'),
        'webseeds':                     ('array', 1, None, None, None, 'Array of webseeds objects'),
        'webseedsSendingToUs':          ('number', 1, None, None, None, 'Number of webseeds seeding to us.'),
    },
    'set': {
        'bandwidthPriority':            ('number', 5, None, None, None, 'Priority for this transfer.'),
        'downloadLimit':                ('number', 5, None, 'speed-limit-down', None, 'Set the speed limit for download in Kib/s.'),
        'downloadLimited':              ('boolean', 5, None, 'speed-limit-down-enabled', None, 'Enable download speed limiter.'),
        'files-wanted':                 ('array', 1, None, None, None, "A list of file id's that should be downloaded."),
        'files-unwanted':               ('array', 1, None, None, None, "A list of file id's that shouldn't be downloaded."),
        'honorsSessionLimits':          ('boolean', 5, None, None, None, "Enables or disables the transfer to honour the upload limit set in the session."),
        'location':                     ('array', 1, None, None, None, 'Local download location.'),
        'peer-limit':                   ('number', 1, None, None, None, 'The peer limit for the torrents.'),
        'priority-high':                ('array', 1, None, None, None, "A list of file id's that should have high priority."),
        'priority-low':                 ('array', 1, None, None, None, "A list of file id's that should have normal priority."),
        'priority-normal':              ('array', 1, None, None, None, "A list of file id's that should have low priority."),
        'queuePosition':                ('number', 14, None, None, None, 'Position of this transfer in its queue.'),
        'seedIdleLimit':                ('number', 10, None, None, None, 'Seed inactivity limit in minutes.'),
        'seedIdleMode':                 ('number', 10, None, None, None, 'Seed inactivity mode. 0 = Use session limit, 1 = Use transfer limit, 2 = Disable limit.'),
        'seedRatioLimit':               ('double', 5, None, None, None, 'Seeding ratio.'),
        'seedRatioMode':                ('number', 5, None, None, None, 'Which ratio to use. 0 = Use session limit, 1 = Use transfer limit, 2 = Disable limit.'),
        'speed-limit-down':             ('number', 1, 5, None, 'downloadLimit', 'Set the speed limit for download in Kib/s.'),
        'speed-limit-down-enabled':     ('boolean', 1, 5, None, 'downloadLimited', 'Enable download speed limiter.'),
        'speed-limit-up':               ('number', 1, 5, None, 'uploadLimit', 'Set the speed limit for upload in Kib/s.'),
        'speed-limit-up-enabled':       ('boolean', 1, 5, None, 'uploadLimited', 'Enable upload speed limiter.'),
        'trackerAdd':                   ('array', 10, None, None, None, 'Array of string with announce URLs to add.'),
        'trackerRemove':                ('array', 10, None, None, None, 'Array of ids of trackers to remove.'),
        'trackerReplace':               ('array', 10, None, None, None, 'Array of (id, url) tuples where the announce URL should be replaced.'),
        'uploadLimit':                  ('number', 5, None, 'speed-limit-up', None, 'Set the speed limit for upload in Kib/s.'),
        'uploadLimited':                ('boolean', 5, None, 'speed-limit-up-enabled', None, 'Enable upload speed limiter.'),
    },
    'add': {
        'bandwidthPriority':            ('number', 8, None, None, None, 'Priority for this transfer.'),
        'download-dir':                 ('string', 1, None, None, None, 'The directory where the downloaded contents will be saved in.'),
        'cookies':                      ('string', 13, None, None, None, 'One or more HTTP cookie(s).'),
        'filename':                     ('string', 1, None, None, None, "A file path or URL to a torrent file or a magnet link."),
        'files-wanted':                 ('array', 1, None, None, None, "A list of file id's that should be downloaded."),
        'files-unwanted':               ('array', 1, None, None, None, "A list of file id's that shouldn't be downloaded."),
        'metainfo':                     ('string', 1, None, None, None, 'The content of a torrent file, base64 encoded.'),
        'paused':                       ('boolean', 1, None, None, None, 'If True, does not start the transfer when added.'),
        'peer-limit':                   ('number', 1, None, None, None, 'Maximum number of peers allowed.'),
        'priority-high':                ('array', 1, None, None, None, "A list of file id's that should have high priority."),
        'priority-low':                 ('array', 1, None, None, None, "A list of file id's that should have low priority."),
        'priority-normal':              ('array', 1, None, None, None, "A list of file id's that should have normal priority."),
    }
}

# Arguments for session methods
SESSION_ARGS = {
    'get': {
        "alt-speed-down":               ('number', 5, None, None, None, 'Alternate session download speed limit (in Kib/s).'),
        "alt-speed-enabled":            ('boolean', 5, None, None, None, 'True if alternate global download speed limiter is ebabled.'),
        "alt-speed-time-begin":         ('number', 5, None, None, None, 'Time when alternate speeds should be enabled. Minutes after midnight.'),
        "alt-speed-time-enabled":       ('boolean', 5, None, None, None, 'True if alternate speeds scheduling is enabled.'),
        "alt-speed-time-end":           ('number', 5, None, None, None, 'Time when alternate speeds should be disabled. Minutes after midnight.'),
        "alt-speed-time-day":           ('number', 5, None, None, None, 'Days alternate speeds scheduling is enabled.'),
        "alt-speed-up":                 ('number', 5, None, None, None, 'Alternate session upload speed limit (in Kib/s)'),
        "blocklist-enabled":            ('boolean', 5, None, None, None, 'True when blocklist is enabled.'),
        "blocklist-size":               ('number', 5, None, None, None, 'Number of rules in the blocklist'),
        "blocklist-url":                ('string', 11, None, None, None, 'Location of the block list. Updated with blocklist-update.'),
        "cache-size-mb":                ('number', 10, None, None, None, 'The maximum size of the disk cache in MB'),
        "config-dir":                   ('string', 8, None, None, None, 'location of transmissions configuration directory'),
        "dht-enabled":                  ('boolean', 6, None, None, None, 'True if DHT enabled.'),
        "download-dir":                 ('string', 1, None, None, None, 'The download directory.'),
        "download-dir-free-space":      ('number', 12, None, None, None, 'Free space in the download directory, in bytes'),
        "download-queue-size":          ('number', 14, None, None, None, 'Number of slots in the download queue.'),
        "download-queue-enabled":       ('boolean', 14, None, None, None, 'True if the download queue is enabled.'),
        "encryption":                   ('string', 1, None, None, None, 'Encryption mode, one of ``required``, ``preferred`` or ``tolerated``.'),
        "idle-seeding-limit":           ('number', 10, None, None, None, 'Seed inactivity limit in minutes.'),
        "idle-seeding-limit-enabled":   ('boolean', 10, None, None, None, 'True if the seed activity limit is enabled.'),
        "incomplete-dir":               ('string', 7, None, None, None, 'The path to the directory for incomplete torrent transfer data.'),
        "incomplete-dir-enabled":       ('boolean', 7, None, None, None, 'True if the incomplete dir is enabled.'),
        "lpd-enabled":                  ('boolean', 9, None, None, None, 'True if local peer discovery is enabled.'),
        "peer-limit":                   ('number', 1, 5, None, 'peer-limit-global', 'Maximum number of peers.'),
        "peer-limit-global":            ('number', 5, None, 'peer-limit', None, 'Maximum number of peers.'),
        "peer-limit-per-torrent":       ('number', 5, None, None, None, 'Maximum number of peers per transfer.'),
        "pex-allowed":                  ('boolean', 1, 5, None, 'pex-enabled', 'True if PEX is allowed.'),
        "pex-enabled":                  ('boolean', 5, None, 'pex-allowed', None, 'True if PEX is enabled.'),
        "port":                         ('number', 1, 5, None, 'peer-port', 'Peer port.'),
        "peer-port":                    ('number', 5, None, 'port', None, 'Peer port.'),
        "peer-port-random-on-start":    ('boolean', 5, None, None, None, 'Enables randomized peer port on start of Transmission.'),
        "port-forwarding-enabled":      ('boolean', 1, None, None, None, 'True if port forwarding is enabled.'),
        "queue-stalled-minutes":        ('number', 14, None, None, None, 'Number of minutes of idle that marks a transfer as stalled.'),
        "queue-stalled-enabled":        ('boolean', 14, None, None, None, 'True if stalled tracking of transfers is enabled.'),
        "rename-partial-files":         ('boolean', 8, None, None, None, 'True if ".part" is appended to incomplete files'),
        "rpc-version":                  ('number', 4, None, None, None, 'Transmission RPC API Version.'),
        "rpc-version-minimum":          ('number', 4, None, None, None, 'Minimum accepted RPC API Version.'),
        "script-torrent-done-enabled":  ('boolean', 9, None, None, None, 'True if the done script is enabled.'),
        "script-torrent-done-filename": ('string', 9, None, None, None, 'Filename of the script to run when the transfer is done.'),
        "seedRatioLimit":               ('double', 5, None, None, None, 'Seed ratio limit. 1.0 means 1:1 download and upload ratio.'),
        "seedRatioLimited":             ('boolean', 5, None, None, None, 'True if seed ration limit is enabled.'),
        "seed-queue-size":              ('number', 14, None, None, None, 'Number of slots in the upload queue.'),
        "seed-queue-enabled":           ('boolean', 14, None, None, None, 'True if upload queue is enabled.'),
        "speed-limit-down":             ('number', 1, None, None, None, 'Download speed limit (in Kib/s).'),
        "speed-limit-down-enabled":     ('boolean', 1, None, None, None, 'True if the download speed is limited.'),
        "speed-limit-up":               ('number', 1, None, None, None, 'Upload speed limit (in Kib/s).'),
        "speed-limit-up-enabled":       ('boolean', 1, None, None, None, 'True if the upload speed is limited.'),
        "start-added-torrents":         ('boolean', 9, None, None, None, 'When true uploaded torrents will start right away.'),
        "trash-original-torrent-files": ('boolean', 9, None, None, None, 'When true added .torrent files will be deleted.'),
        'units':                        ('object', 10, None, None, None, 'An object containing units for size and speed.'),
        'utp-enabled':                  ('boolean', 13, None, None, None, 'True if Micro Transport Protocol (UTP) is enabled.'),
        "version":                      ('string', 3, None, None, None, 'Transmission version.'),
    },
    'set': {
        "alt-speed-down":               ('number', 5, None, None, None, 'Alternate session download speed limit (in Kib/s).'),
        "alt-speed-enabled":            ('boolean', 5, None, None, None, 'Enables alternate global download speed limiter.'),
        "alt-speed-time-begin":         ('number', 5, None, None, None, 'Time when alternate speeds should be enabled. Minutes after midnight.'),
        "alt-speed-time-enabled":       ('boolean', 5, None, None, None, 'Enables alternate speeds scheduling.'),
        "alt-speed-time-end":           ('number', 5, None, None, None, 'Time when alternate speeds should be disabled. Minutes after midnight.'),
        "alt-speed-time-day":           ('number', 5, None, None, None, 'Enables alternate speeds scheduling these days.'),
        "alt-speed-up":                 ('number', 5, None, None, None, 'Alternate session upload speed limit (in Kib/s).'),
        "blocklist-enabled":            ('boolean', 5, None, None, None, 'Enables the block list'),
        "blocklist-url":                ('string', 11, None, None, None, 'Location of the block list. Updated with blocklist-update.'),
        "cache-size-mb":                ('number', 10, None, None, None, 'The maximum size of the disk cache in MB'),
        "dht-enabled":                  ('boolean', 6, None, None, None, 'Enables DHT.'),
        "download-dir":                 ('string', 1, None, None, None, 'Set the session download directory.'),
        "download-queue-size":          ('number', 14, None, None, None, 'Number of slots in the download queue.'),
        "download-queue-enabled":       ('boolean', 14, None, None, None, 'Enables download queue.'),
        "encryption":                   ('string', 1, None, None, None, 'Set the session encryption mode, one of ``required``, ``preferred`` or ``tolerated``.'),
        "idle-seeding-limit":           ('number', 10, None, None, None, 'The default seed inactivity limit in minutes.'),
        "idle-seeding-limit-enabled":   ('boolean', 10, None, None, None, 'Enables the default seed inactivity limit'),
        "incomplete-dir":               ('string', 7, None, None, None, 'The path to the directory of incomplete transfer data.'),
        "incomplete-dir-enabled":       ('boolean', 7, None, None, None, 'Enables the incomplete transfer data directory. Otherwise data for incomplete transfers are stored in the download target.'),
        "lpd-enabled":                  ('boolean', 9, None, None, None, 'Enables local peer discovery for public torrents.'),
        "peer-limit":                   ('number', 1, 5, None, 'peer-limit-global', 'Maximum number of peers.'),
        "peer-limit-global":            ('number', 5, None, 'peer-limit', None, 'Maximum number of peers.'),
        "peer-limit-per-torrent":       ('number', 5, None, None, None, 'Maximum number of peers per transfer.'),
        "pex-allowed":                  ('boolean', 1, 5, None, 'pex-enabled', 'Allowing PEX in public torrents.'),
        "pex-enabled":                  ('boolean', 5, None, 'pex-allowed', None, 'Allowing PEX in public torrents.'),
        "port":                         ('number', 1, 5, None, 'peer-port', 'Peer port.'),
        "peer-port":                    ('number', 5, None, 'port', None, 'Peer port.'),
        "peer-port-random-on-start":    ('boolean', 5, None, None, None, 'Enables randomized peer port on start of Transmission.'),
        "port-forwarding-enabled":      ('boolean', 1, None, None, None, 'Enables port forwarding.'),
        "rename-partial-files":         ('boolean', 8, None, None, None, 'Appends ".part" to incomplete files'),
        "queue-stalled-minutes":        ('number', 14, None, None, None, 'Number of minutes of idle that marks a transfer as stalled.'),
        "queue-stalled-enabled":        ('boolean', 14, None, None, None, 'Enable tracking of stalled transfers.'),
        "script-torrent-done-enabled":  ('boolean', 9, None, None, None, 'Whether or not to call the "done" script.'),
        "script-torrent-done-filename": ('string', 9, None, None, None, 'Filename of the script to run when the transfer is done.'),
        "seed-queue-size":              ('number', 14, None, None, None, 'Number of slots in the upload queue.'),
        "seed-queue-enabled":           ('boolean', 14, None, None, None, 'Enables upload queue.'),
        "seedRatioLimit":               ('double', 5, None, None, None, 'Seed ratio limit. 1.0 means 1:1 download and upload ratio.'),
        "seedRatioLimited":             ('boolean', 5, None, None, None, 'Enables seed ration limit.'),
        "speed-limit-down":             ('number', 1, None, None, None, 'Download speed limit (in Kib/s).'),
        "speed-limit-down-enabled":     ('boolean', 1, None, None, None, 'Enables download speed limiting.'),
        "speed-limit-up":               ('number', 1, None, None, None, 'Upload speed limit (in Kib/s).'),
        "speed-limit-up-enabled":       ('boolean', 1, None, None, None, 'Enables upload speed limiting.'),
        "start-added-torrents":         ('boolean', 9, None, None, None, 'Added torrents will be started right away.'),
        "trash-original-torrent-files": ('boolean', 9, None, None, None, 'The .torrent file of added torrents will be deleted.'),
        'utp-enabled':                  ('boolean', 13, None, None, None, 'Enables Micro Transport Protocol (UTP).'),
    },
}
