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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import with_statement

import cherrypy
import webbrowser
import sqlite3
import datetime
import socket
import os, sys, subprocess, re
import urllib

from threading import Lock

# apparently py2exe won't build these unless they're imported somewhere
from sickbeard import providers, metadata
from providers import ezrss, tvtorrents, torrentleech, btn, nzbsrus, newznab, womble, nzbx, omgwtfnzbs, thepiratebay
from sickbeard.config import CheckSection, check_setting_int, check_setting_str, ConfigMigrator

from sickbeard import searchCurrent, searchBacklog, showUpdater, versionChecker, properFinder, autoPostProcesser
from sickbeard import helpers, db, exceptions, show_queue, search_queue, scheduler
from sickbeard import logger
from sickbeard import naming

from common import SD, SKIPPED, NAMING_REPEAT

from sickbeard.databases import mainDB, cache_db

from lib.configobj import ConfigObj

invoked_command = None

SOCKET_TIMEOUT = 30

PID = None

CFG = None
CONFIG_FILE = None

# this is the version of the config we EXPECT to find
CONFIG_VERSION = 1

PROG_DIR = '.'
MY_FULLNAME = None
MY_NAME = None
MY_ARGS = []
SYS_ENCODING = ''
DATA_DIR = ''
CREATEPID = False
PIDFILE = ''

DAEMON = None
NO_RESIZE = False

backlogSearchScheduler = None
currentSearchScheduler = None
showUpdateScheduler = None
versionCheckScheduler = None
showQueueScheduler = None
searchQueueScheduler = None
properFinderScheduler = None
autoPostProcesserScheduler = None

showList = None
loadingShowList = None

providerList = []
newznabProviderList = []
metadata_provider_dict = {}

NEWEST_VERSION = None
NEWEST_VERSION_STRING = None
VERSION_NOTIFY = None

INIT_LOCK = Lock()
__INITIALIZED__ = False
started = False

LOG_DIR = None

WEB_PORT = None
WEB_LOG = None
WEB_ROOT = None
WEB_USERNAME = None
WEB_PASSWORD = None
WEB_HOST = None
WEB_IPV6 = None

USE_API = False
API_KEY = None

ENABLE_HTTPS = False
HTTPS_CERT = None
HTTPS_KEY = None

LAUNCH_BROWSER = None
CACHE_DIR = None
ACTUAL_CACHE_DIR = None
ROOT_DIRS = None

USE_BANNER = None
USE_LISTVIEW = None
METADATA_XBMC = None
METADATA_MEDIABROWSER = None
METADATA_PS3 = None
METADATA_WDTV = None
METADATA_TIVO = None
METADATA_SYNOLOGY = None

QUALITY_DEFAULT = None
STATUS_DEFAULT = None
FLATTEN_FOLDERS_DEFAULT = None
PROVIDER_ORDER = []

NAMING_MULTI_EP = None
NAMING_PATTERN = None
NAMING_ABD_PATTERN = None
NAMING_CUSTOM_ABD = None
NAMING_FORCE_FOLDERS = False

TVDB_API_KEY = '9DAF49C96CBF8DAC'
TVDB_BASE_URL = None
TVDB_API_PARMS = {}

USE_NZBS = None
USE_TORRENTS = None

TORRENT_METHOD = None
NZB_METHOD = None
NZB_DIR = None
USENET_RETENTION = None
DOWNLOAD_PROPERS = None

SEARCH_FREQUENCY = None
BACKLOG_SEARCH_FREQUENCY = 21

MIN_SEARCH_FREQUENCY = 10

DEFAULT_SEARCH_FREQUENCY = 60

EZRSS = False
TVTORRENTS = False
TVTORRENTS_DIGEST = None
TVTORRENTS_HASH = None

THEPIRATEBAY = False
THEPIRATEBAY_TRUSTED = False
THEPIRATEBAY_PROXY = False
THEPIRATEBAY_PROXY_URL = None
THEPIRATEBAY_URL = 'http://thepiratebay.se/'

TORRENTLEECH = False
TORRENTLEECH_KEY = None

BTN = False
BTN_API_KEY = None

TORRENT_DIR = None

ADD_SHOWS_WO_DIR = None
CREATE_MISSING_SHOW_DIRS = None
RENAME_EPISODES = False
PROCESS_AUTOMATICALLY = False
KEEP_PROCESSED_DIR = False
MOVE_ASSOCIATED_FILES = False
TV_DOWNLOAD_DIR = None

NZBS = False
NZBS_UID = None
NZBS_HASH = None

WOMBLE = False

NZBX = False
NZBX_COMPLETION = 100

OMGWTFNZBS = False
OMGWTFNZBS_UID = None
OMGWTFNZBS_KEY = None

NZBSRUS = False
NZBSRUS_UID = None
NZBSRUS_HASH = None

NZBMATRIX = False
NZBMATRIX_USERNAME = None
NZBMATRIX_APIKEY = None

NEWZBIN = False
NEWZBIN_USERNAME = None
NEWZBIN_PASSWORD = None

SAB_USERNAME = None
SAB_PASSWORD = None
SAB_APIKEY = None
SAB_CATEGORY = None
SAB_HOST = ''

UTORRENT_USERNAME = None
UTORRENT_PASSWORD = None
UTORRENT_LABEL = None
UTORRENT_HOST = ''

NZBGET_PASSWORD = None
NZBGET_CATEGORY = None
NZBGET_HOST = None

USE_XBMC = False
XBMC_NOTIFY_ONSNATCH = False
XBMC_NOTIFY_ONDOWNLOAD = False
XBMC_UPDATE_LIBRARY = False
XBMC_UPDATE_FULL = False
XBMC_UPDATE_ONLYFIRST = False
XBMC_HOST = ''
XBMC_USERNAME = None
XBMC_PASSWORD = None

USE_PLEX = False
PLEX_NOTIFY_ONSNATCH = False
PLEX_NOTIFY_ONDOWNLOAD = False
PLEX_UPDATE_LIBRARY = False
PLEX_SERVER_HOST = None
PLEX_HOST = None
PLEX_USERNAME = None
PLEX_PASSWORD = None

USE_GROWL = False
GROWL_NOTIFY_ONSNATCH = False
GROWL_NOTIFY_ONDOWNLOAD = False
GROWL_HOST = ''
GROWL_PASSWORD = None

USE_PROWL = False
PROWL_NOTIFY_ONSNATCH = False
PROWL_NOTIFY_ONDOWNLOAD = False
PROWL_API = None
PROWL_PRIORITY = 0

USE_TWITTER = False
TWITTER_NOTIFY_ONSNATCH = False
TWITTER_NOTIFY_ONDOWNLOAD = False
TWITTER_USERNAME = None
TWITTER_PASSWORD = None
TWITTER_PREFIX = None

USE_NOTIFO = False
NOTIFO_NOTIFY_ONSNATCH = False
NOTIFO_NOTIFY_ONDOWNLOAD = False
NOTIFO_USERNAME = None
NOTIFO_APISECRET = None
NOTIFO_PREFIX = None

USE_BOXCAR = False
BOXCAR_NOTIFY_ONSNATCH = False
BOXCAR_NOTIFY_ONDOWNLOAD = False
BOXCAR_USERNAME = None
BOXCAR_PASSWORD = None
BOXCAR_PREFIX = None

USE_PUSHOVER = False
PUSHOVER_NOTIFY_ONSNATCH = False
PUSHOVER_NOTIFY_ONDOWNLOAD = False
PUSHOVER_USERKEY = None

USE_LIBNOTIFY = False
LIBNOTIFY_NOTIFY_ONSNATCH = False
LIBNOTIFY_NOTIFY_ONDOWNLOAD = False

USE_NMJ = False
NMJ_HOST = None
NMJ_DATABASE = None
NMJ_MOUNT = None

USE_SYNOINDEX = False

USE_NMJv2 = False
NMJv2_HOST = None
NMJv2_DATABASE = None
NMJv2_DBLOC = None

USE_TRAKT = False
TRAKT_USERNAME = None
TRAKT_PASSWORD = None
TRAKT_API = ''

USE_PYTIVO = False
PYTIVO_NOTIFY_ONSNATCH = False
PYTIVO_NOTIFY_ONDOWNLOAD = False
PYTIVO_UPDATE_LIBRARY = False
PYTIVO_HOST = ''
PYTIVO_SHARE_NAME = ''
PYTIVO_TIVO_NAME = ''

USE_NMA = False
NMA_NOTIFY_ONSNATCH = False
NMA_NOTIFY_ONDOWNLOAD = False
NMA_API = None
NMA_PRIORITY = 0

COMING_EPS_LAYOUT = None
COMING_EPS_DISPLAY_PAUSED = None
COMING_EPS_SORT = None

EXTRA_SCRIPTS = []

GIT_PATH = None

IGNORE_WORDS = "german,french,core2hd,dutch,swedish"

__INITIALIZED__ = False


def get_backlog_cycle_time():
    cycletime = SEARCH_FREQUENCY * 2 + 7
    return max([cycletime, 720])


def initialize(consoleLogging=True):

    with INIT_LOCK:

        global LOG_DIR, WEB_PORT, WEB_LOG, WEB_ROOT, WEB_USERNAME, WEB_PASSWORD, WEB_HOST, WEB_IPV6, USE_API, API_KEY, ENABLE_HTTPS, HTTPS_CERT, HTTPS_KEY, \
                USE_NZBS, USE_TORRENTS, NZB_METHOD, NZB_DIR, DOWNLOAD_PROPERS, \
                SAB_USERNAME, SAB_PASSWORD, SAB_APIKEY, SAB_CATEGORY, SAB_HOST, \
                UTORRENT_USERNAME, UTORRENT_PASSWORD, UTORRENT_LABEL, UTORRENT_HOST, \
                NZBGET_PASSWORD, NZBGET_CATEGORY, NZBGET_HOST, currentSearchScheduler, backlogSearchScheduler, \
                USE_XBMC, XBMC_NOTIFY_ONSNATCH, XBMC_NOTIFY_ONDOWNLOAD, XBMC_UPDATE_FULL, XBMC_UPDATE_ONLYFIRST, \
                XBMC_UPDATE_LIBRARY, XBMC_HOST, XBMC_USERNAME, XBMC_PASSWORD, \
                USE_TRAKT, TRAKT_USERNAME, TRAKT_PASSWORD, TRAKT_API, \
                USE_PLEX, PLEX_NOTIFY_ONSNATCH, PLEX_NOTIFY_ONDOWNLOAD, PLEX_UPDATE_LIBRARY, \
                PLEX_SERVER_HOST, PLEX_HOST, PLEX_USERNAME, PLEX_PASSWORD, \
                showUpdateScheduler, __INITIALIZED__, LAUNCH_BROWSER, showList, loadingShowList, \
                NZBS, NZBS_UID, NZBS_HASH, EZRSS, TVTORRENTS, TVTORRENTS_DIGEST, TVTORRENTS_HASH, THEPIRATEBAY, THEPIRATEBAY_TRUSTED, THEPIRATEBAY_PROXY, THEPIRATEBAY_PROXY_URL, THEPIRATEBAY_URL, BTN, BTN_API_KEY, TORRENTLEECH, TORRENTLEECH_KEY, \
                TORRENT_DIR, TORRENT_METHOD, USENET_RETENTION, SOCKET_TIMEOUT, \
                SEARCH_FREQUENCY, DEFAULT_SEARCH_FREQUENCY, BACKLOG_SEARCH_FREQUENCY, \
                QUALITY_DEFAULT, FLATTEN_FOLDERS_DEFAULT, STATUS_DEFAULT, \
                GROWL_NOTIFY_ONSNATCH, GROWL_NOTIFY_ONDOWNLOAD, TWITTER_NOTIFY_ONSNATCH, TWITTER_NOTIFY_ONDOWNLOAD, \
                USE_GROWL, GROWL_HOST, GROWL_PASSWORD, USE_PROWL, PROWL_NOTIFY_ONSNATCH, PROWL_NOTIFY_ONDOWNLOAD, PROWL_API, PROWL_PRIORITY, PROG_DIR, NZBMATRIX, NZBMATRIX_USERNAME, \
                USE_PYTIVO, PYTIVO_NOTIFY_ONSNATCH, PYTIVO_NOTIFY_ONDOWNLOAD, PYTIVO_UPDATE_LIBRARY, PYTIVO_HOST, PYTIVO_SHARE_NAME, PYTIVO_TIVO_NAME, \
                USE_NMA, NMA_NOTIFY_ONSNATCH, NMA_NOTIFY_ONDOWNLOAD, NMA_API, NMA_PRIORITY, \
                NZBMATRIX_APIKEY, versionCheckScheduler, VERSION_NOTIFY, PROCESS_AUTOMATICALLY, \
                KEEP_PROCESSED_DIR, TV_DOWNLOAD_DIR, TVDB_BASE_URL, MIN_SEARCH_FREQUENCY, \
                showQueueScheduler, searchQueueScheduler, ROOT_DIRS, CACHE_DIR, ACTUAL_CACHE_DIR, TVDB_API_PARMS, \
                NAMING_PATTERN, NAMING_MULTI_EP, NAMING_FORCE_FOLDERS, NAMING_ABD_PATTERN, NAMING_CUSTOM_ABD, \
                RENAME_EPISODES, properFinderScheduler, PROVIDER_ORDER, autoPostProcesserScheduler, \
                NZBSRUS, NZBSRUS_UID, NZBSRUS_HASH, WOMBLE, NZBX, NZBX_COMPLETION, OMGWTFNZBS, OMGWTFNZBS_UID, OMGWTFNZBS_KEY, providerList, newznabProviderList, \
                EXTRA_SCRIPTS, USE_TWITTER, TWITTER_USERNAME, TWITTER_PASSWORD, TWITTER_PREFIX, \
                USE_NOTIFO, NOTIFO_USERNAME, NOTIFO_APISECRET, NOTIFO_NOTIFY_ONDOWNLOAD, NOTIFO_NOTIFY_ONSNATCH, \
                USE_BOXCAR, BOXCAR_USERNAME, BOXCAR_PASSWORD, BOXCAR_NOTIFY_ONDOWNLOAD, BOXCAR_NOTIFY_ONSNATCH, \
                USE_PUSHOVER, PUSHOVER_USERKEY, PUSHOVER_NOTIFY_ONDOWNLOAD, PUSHOVER_NOTIFY_ONSNATCH, \
                USE_LIBNOTIFY, LIBNOTIFY_NOTIFY_ONSNATCH, LIBNOTIFY_NOTIFY_ONDOWNLOAD, USE_NMJ, NMJ_HOST, NMJ_DATABASE, NMJ_MOUNT, USE_NMJv2, NMJv2_HOST, NMJv2_DATABASE, NMJv2_DBLOC, USE_SYNOINDEX, \
                USE_BANNER, USE_LISTVIEW, METADATA_XBMC, METADATA_MEDIABROWSER, METADATA_PS3, METADATA_SYNOLOGY, metadata_provider_dict, \
                NEWZBIN, NEWZBIN_USERNAME, NEWZBIN_PASSWORD, GIT_PATH, MOVE_ASSOCIATED_FILES, \
                COMING_EPS_LAYOUT, COMING_EPS_SORT, COMING_EPS_DISPLAY_PAUSED, METADATA_WDTV, METADATA_TIVO, IGNORE_WORDS, CREATE_MISSING_SHOW_DIRS, \
                ADD_SHOWS_WO_DIR

        if __INITIALIZED__:
            return False

        socket.setdefaulttimeout(SOCKET_TIMEOUT)

        CheckSection(CFG, 'General')
        LOG_DIR = check_setting_str(CFG, 'General', 'log_dir', 'Logs')
        if not helpers.makeDir(LOG_DIR):
            logger.log(u"!!! No log folder, logging to screen only!", logger.ERROR)

        try:
            WEB_PORT = check_setting_int(CFG, 'General', 'web_port', 8081)
        except:
            WEB_PORT = 8081

        if WEB_PORT < 21 or WEB_PORT > 65535:
            WEB_PORT = 8081

        WEB_HOST = check_setting_str(CFG, 'General', 'web_host', '0.0.0.0')
        WEB_IPV6 = bool(check_setting_int(CFG, 'General', 'web_ipv6', 0))
        WEB_ROOT = check_setting_str(CFG, 'General', 'web_root', '').rstrip("/")
        WEB_LOG = bool(check_setting_int(CFG, 'General', 'web_log', 0))
        WEB_USERNAME = check_setting_str(CFG, 'General', 'web_username', '')
        WEB_PASSWORD = check_setting_str(CFG, 'General', 'web_password', '')
        LAUNCH_BROWSER = bool(check_setting_int(CFG, 'General', 'launch_browser', 1))

        USE_API = bool(check_setting_int(CFG, 'General', 'use_api', 0))
        API_KEY = check_setting_str(CFG, 'General', 'api_key', '')

        ENABLE_HTTPS = bool(check_setting_int(CFG, 'General', 'enable_https', 0))
        HTTPS_CERT = check_setting_str(CFG, 'General', 'https_cert', 'server.crt')
        HTTPS_KEY = check_setting_str(CFG, 'General', 'https_key', 'server.key')

        ACTUAL_CACHE_DIR = check_setting_str(CFG, 'General', 'cache_dir', 'cache')
        # fix bad configs due to buggy code
        if ACTUAL_CACHE_DIR == 'None':
            ACTUAL_CACHE_DIR = 'cache'

        # unless they specify, put the cache dir inside the data dir
        if not os.path.isabs(ACTUAL_CACHE_DIR):
            CACHE_DIR = os.path.join(DATA_DIR, ACTUAL_CACHE_DIR)
        else:
            CACHE_DIR = ACTUAL_CACHE_DIR

        if not helpers.makeDir(CACHE_DIR):
            logger.log(u"!!! Creating local cache dir failed, using system default", logger.ERROR)
            CACHE_DIR = None

        ROOT_DIRS = check_setting_str(CFG, 'General', 'root_dirs', '')
        if not re.match(r'\d+\|[^|]+(?:\|[^|]+)*', ROOT_DIRS):
            ROOT_DIRS = ''

        proxies = urllib.getproxies()
        proxy_url = None # @UnusedVariable
        if 'http' in proxies:
            proxy_url = proxies['http'] # @UnusedVariable
        elif 'ftp' in proxies:
            proxy_url = proxies['ftp'] # @UnusedVariable

        # Set our common tvdb_api options here
        TVDB_API_PARMS = {'apikey': TVDB_API_KEY,
                          'language': 'en',
                          'useZip': True}

        if CACHE_DIR:
            TVDB_API_PARMS['cache'] = os.path.join(CACHE_DIR, 'tvdb')

        TVDB_BASE_URL = 'http://thetvdb.com/api/' + TVDB_API_KEY

        QUALITY_DEFAULT = check_setting_int(CFG, 'General', 'quality_default', SD)
        STATUS_DEFAULT = check_setting_int(CFG, 'General', 'status_default', SKIPPED)
        VERSION_NOTIFY = check_setting_int(CFG, 'General', 'version_notify', 1)
        FLATTEN_FOLDERS_DEFAULT = bool(check_setting_int(CFG, 'General', 'flatten_folders_default', 0))

        PROVIDER_ORDER = check_setting_str(CFG, 'General', 'provider_order', '').split()

        NAMING_PATTERN = check_setting_str(CFG, 'General', 'naming_pattern', '')
        NAMING_ABD_PATTERN = check_setting_str(CFG, 'General', 'naming_abd_pattern', '')
        NAMING_CUSTOM_ABD = check_setting_int(CFG, 'General', 'naming_custom_abd', 0)
        NAMING_MULTI_EP = check_setting_int(CFG, 'General', 'naming_multi_ep', 1)
        NAMING_FORCE_FOLDERS = naming.check_force_season_folders()

        USE_NZBS = bool(check_setting_int(CFG, 'General', 'use_nzbs', 1))
        USE_TORRENTS = bool(check_setting_int(CFG, 'General', 'use_torrents', 0))

        TORRENT_METHOD = check_setting_str(CFG, 'General', 'torrent_method', 'blackhole')

        if TORRENT_METHOD not in ('blackhole', 'utorrent'):
            NZB_METHOD = 'blackhole'

        NZB_METHOD = check_setting_str(CFG, 'General', 'nzb_method', 'blackhole')

        if NZB_METHOD not in ('blackhole', 'sabnzbd', 'nzbget'):
            NZB_METHOD = 'blackhole'

        DOWNLOAD_PROPERS = bool(check_setting_int(CFG, 'General', 'download_propers', 1))
        USENET_RETENTION = check_setting_int(CFG, 'General', 'usenet_retention', 500)
        SEARCH_FREQUENCY = check_setting_int(CFG, 'General', 'search_frequency', DEFAULT_SEARCH_FREQUENCY)
        if SEARCH_FREQUENCY < MIN_SEARCH_FREQUENCY:
            SEARCH_FREQUENCY = MIN_SEARCH_FREQUENCY

        TV_DOWNLOAD_DIR = check_setting_str(CFG, 'General', 'tv_download_dir', '')
        PROCESS_AUTOMATICALLY = check_setting_int(CFG, 'General', 'process_automatically', 0)
        RENAME_EPISODES = check_setting_int(CFG, 'General', 'rename_episodes', 1)
        KEEP_PROCESSED_DIR = check_setting_int(CFG, 'General', 'keep_processed_dir', 1)
        MOVE_ASSOCIATED_FILES = check_setting_int(CFG, 'General', 'move_associated_files', 0)
        CREATE_MISSING_SHOW_DIRS = check_setting_int(CFG, 'General', 'create_missing_show_dirs', 0)
        ADD_SHOWS_WO_DIR = check_setting_int(CFG, 'General', 'add_shows_wo_dir', 0)

        EZRSS = bool(check_setting_int(CFG, 'General', 'use_torrent', 0))
        if not EZRSS:
            CheckSection(CFG, 'EZRSS')
            EZRSS = bool(check_setting_int(CFG, 'EZRSS', 'ezrss', 0))

        GIT_PATH = check_setting_str(CFG, 'General', 'git_path', '')
        IGNORE_WORDS = check_setting_str(CFG, 'General', 'ignore_words', IGNORE_WORDS)
        EXTRA_SCRIPTS = [x for x in check_setting_str(CFG, 'General', 'extra_scripts', '').split('|') if x]

        USE_BANNER = bool(check_setting_int(CFG, 'General', 'use_banner', 0))
        USE_LISTVIEW = bool(check_setting_int(CFG, 'General', 'use_listview', 0))
        METADATA_TYPE = check_setting_str(CFG, 'General', 'metadata_type', '')

        metadata_provider_dict = metadata.get_metadata_generator_dict()

        # if this exists it's legacy, use the info to upgrade metadata to the new settings
        if METADATA_TYPE:

            old_metadata_class = None

            if METADATA_TYPE == 'xbmc':
                old_metadata_class = metadata.xbmc.metadata_class
            elif METADATA_TYPE == 'mediabrowser':
                old_metadata_class = metadata.mediabrowser.metadata_class
            elif METADATA_TYPE == 'ps3':
                old_metadata_class = metadata.ps3.metadata_class

            if old_metadata_class:

                METADATA_SHOW = bool(check_setting_int(CFG, 'General', 'metadata_show', 1))
                METADATA_EPISODE = bool(check_setting_int(CFG, 'General', 'metadata_episode', 1))

                ART_POSTER = bool(check_setting_int(CFG, 'General', 'art_poster', 1))
                ART_FANART = bool(check_setting_int(CFG, 'General', 'art_fanart', 1))
                ART_THUMBNAILS = bool(check_setting_int(CFG, 'General', 'art_thumbnails', 1))
                ART_SEASON_THUMBNAILS = bool(check_setting_int(CFG, 'General', 'art_season_thumbnails', 1))

                new_metadata_class = old_metadata_class(METADATA_SHOW,
                                                        METADATA_EPISODE,
                                                        ART_POSTER,
                                                        ART_FANART,
                                                        ART_THUMBNAILS,
                                                        ART_SEASON_THUMBNAILS)

                metadata_provider_dict[new_metadata_class.name] = new_metadata_class

        # this is the normal codepath for metadata config
        else:
            METADATA_XBMC = check_setting_str(CFG, 'General', 'metadata_xbmc', '0|0|0|0|0|0')
            METADATA_MEDIABROWSER = check_setting_str(CFG, 'General', 'metadata_mediabrowser', '0|0|0|0|0|0')
            METADATA_PS3 = check_setting_str(CFG, 'General', 'metadata_ps3', '0|0|0|0|0|0')
            METADATA_WDTV = check_setting_str(CFG, 'General', 'metadata_wdtv', '0|0|0|0|0|0')
            METADATA_TIVO = check_setting_str(CFG, 'General', 'metadata_tivo', '0|0|0|0|0|0')
            METADATA_SYNOLOGY = check_setting_str(CFG, 'General', 'metadata_synology', '0|0|0|0|0|0')

            for cur_metadata_tuple in [(METADATA_XBMC, metadata.xbmc),
                                       (METADATA_MEDIABROWSER, metadata.mediabrowser),
                                       (METADATA_PS3, metadata.ps3),
                                       (METADATA_WDTV, metadata.wdtv),
                                       (METADATA_TIVO, metadata.tivo),
                                       (METADATA_SYNOLOGY, metadata.synology),
                                       ]:

                (cur_metadata_config, cur_metadata_class) = cur_metadata_tuple
                tmp_provider = cur_metadata_class.metadata_class()
                tmp_provider.set_config(cur_metadata_config)
                metadata_provider_dict[tmp_provider.name] = tmp_provider

        CheckSection(CFG, 'GUI')
        COMING_EPS_LAYOUT = check_setting_str(CFG, 'GUI', 'coming_eps_layout', 'banner')
        COMING_EPS_DISPLAY_PAUSED = bool(check_setting_int(CFG, 'GUI', 'coming_eps_display_paused', 0))
        COMING_EPS_SORT = check_setting_str(CFG, 'GUI', 'coming_eps_sort', 'date')

        CheckSection(CFG, 'Newznab')
        newznabData = check_setting_str(CFG, 'Newznab', 'newznab_data', '')
        newznabProviderList = providers.getNewznabProviderList(newznabData)
        providerList = providers.makeProviderList()

        CheckSection(CFG, 'Blackhole')
        NZB_DIR = check_setting_str(CFG, 'Blackhole', 'nzb_dir', '')
        TORRENT_DIR = check_setting_str(CFG, 'Blackhole', 'torrent_dir', '')

        CheckSection(CFG, 'TVTORRENTS')
        TVTORRENTS = bool(check_setting_int(CFG, 'TVTORRENTS', 'tvtorrents', 0))
        TVTORRENTS_DIGEST = check_setting_str(CFG, 'TVTORRENTS', 'tvtorrents_digest', '')
        TVTORRENTS_HASH = check_setting_str(CFG, 'TVTORRENTS', 'tvtorrents_hash', '')

        THEPIRATEBAY =  bool(check_setting_int(CFG, 'THEPIRATEBAY', 'thepiratebay', 0))
        THEPIRATEBAY_TRUSTED =  bool(check_setting_int(CFG, 'THEPIRATEBAY', 'thepiratebay_trusted', 0))
        THEPIRATEBAY_PROXY =  bool(check_setting_int(CFG, 'THEPIRATEBAY', 'thepiratebay_proxy', 0))
        THEPIRATEBAY_PROXY_URL = check_setting_str(CFG, 'THEPIRATEBAY', 'thepiratebay_proxy_url', '')
        THEPIRATEBAY_URL = check_setting_str(CFG, 'THEPIRATEBAY', 'thepiratebay_url', '')

        CheckSection(CFG, 'BTN')
        BTN = bool(check_setting_int(CFG, 'BTN', 'btn', 0))
        BTN_API_KEY = check_setting_str(CFG, 'BTN', 'btn_api_key', '')

        CheckSection(CFG, 'TorrentLeech')
        TORRENTLEECH = bool(check_setting_int(CFG, 'TorrentLeech', 'torrentleech', 0))
        TORRENTLEECH_KEY = check_setting_str(CFG, 'TorrentLeech', 'torrentleech_key', '')

        CheckSection(CFG, 'NZBs')
        NZBS = bool(check_setting_int(CFG, 'NZBs', 'nzbs', 0))
        NZBS_UID = check_setting_str(CFG, 'NZBs', 'nzbs_uid', '')
        NZBS_HASH = check_setting_str(CFG, 'NZBs', 'nzbs_hash', '')

        CheckSection(CFG, 'NZBsRUS')
        NZBSRUS = bool(check_setting_int(CFG, 'NZBsRUS', 'nzbsrus', 0))
        NZBSRUS_UID = check_setting_str(CFG, 'NZBsRUS', 'nzbsrus_uid', '')
        NZBSRUS_HASH = check_setting_str(CFG, 'NZBsRUS', 'nzbsrus_hash', '')

        CheckSection(CFG, 'NZBMatrix')
        NZBMATRIX = bool(check_setting_int(CFG, 'NZBMatrix', 'nzbmatrix', 0))
        NZBMATRIX_USERNAME = check_setting_str(CFG, 'NZBMatrix', 'nzbmatrix_username', '')
        NZBMATRIX_APIKEY = check_setting_str(CFG, 'NZBMatrix', 'nzbmatrix_apikey', '')

        CheckSection(CFG, 'Newzbin')
        NEWZBIN = bool(check_setting_int(CFG, 'Newzbin', 'newzbin', 0))
        NEWZBIN_USERNAME = check_setting_str(CFG, 'Newzbin', 'newzbin_username', '')
        NEWZBIN_PASSWORD = check_setting_str(CFG, 'Newzbin', 'newzbin_password', '')

        CheckSection(CFG, 'Womble')
        WOMBLE = bool(check_setting_int(CFG, 'Womble', 'womble', 1))

        CheckSection(CFG, 'nzbX')
        NZBX = bool(check_setting_int(CFG, 'nzbX', 'nzbx', 0))
        NZBX_COMPLETION = check_setting_int(CFG, 'nzbX', 'nzbx_completion', 100)

        CheckSection(CFG, 'omgwtfnzbs')
        OMGWTFNZBS = bool(check_setting_int(CFG, 'omgwtfnzbs', 'omgwtfnzbs', 0))
        OMGWTFNZBS_UID = check_setting_str(CFG, 'omgwtfnzbs', 'omgwtfnzbs_uid', '')
        OMGWTFNZBS_KEY = check_setting_str(CFG, 'omgwtfnzbs', 'omgwtfnzbs_key', '')

        CheckSection(CFG, 'SABnzbd')
        SAB_USERNAME = check_setting_str(CFG, 'SABnzbd', 'sab_username', '')
        SAB_PASSWORD = check_setting_str(CFG, 'SABnzbd', 'sab_password', '')
        SAB_APIKEY = check_setting_str(CFG, 'SABnzbd', 'sab_apikey', '')
        SAB_CATEGORY = check_setting_str(CFG, 'SABnzbd', 'sab_category', 'tv')
        SAB_HOST = check_setting_str(CFG, 'SABnzbd', 'sab_host', '')

        CheckSection(CFG, 'uTorrent')
        UTORRENT_USERNAME = check_setting_str(CFG, 'uTorrent', 'utorrent_username', '')
        UTORRENT_PASSWORD = check_setting_str(CFG, 'uTorrent', 'utorrent_password', '')
        UTORRENT_LABEL = check_setting_str(CFG, 'uTorrent', 'utorrent_label', 'tv')
        UTORRENT_HOST = check_setting_str(CFG, 'uTorrent', 'utorrent_host', '')

        CheckSection(CFG, 'NZBget')
        NZBGET_PASSWORD = check_setting_str(CFG, 'NZBget', 'nzbget_password', 'tegbzn6789')
        NZBGET_CATEGORY = check_setting_str(CFG, 'NZBget', 'nzbget_category', 'tv')
        NZBGET_HOST = check_setting_str(CFG, 'NZBget', 'nzbget_host', '')

        CheckSection(CFG, 'XBMC')
        USE_XBMC = bool(check_setting_int(CFG, 'XBMC', 'use_xbmc', 0))
        XBMC_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'XBMC', 'xbmc_notify_onsnatch', 0))
        XBMC_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'XBMC', 'xbmc_notify_ondownload', 0))
        XBMC_UPDATE_LIBRARY = bool(check_setting_int(CFG, 'XBMC', 'xbmc_update_library', 0))
        XBMC_UPDATE_FULL = bool(check_setting_int(CFG, 'XBMC', 'xbmc_update_full', 0))
        XBMC_UPDATE_ONLYFIRST = bool(check_setting_int(CFG, 'XBMC', 'xbmc_update_onlyfirst', 0))
        XBMC_HOST = check_setting_str(CFG, 'XBMC', 'xbmc_host', '')
        XBMC_USERNAME = check_setting_str(CFG, 'XBMC', 'xbmc_username', '')
        XBMC_PASSWORD = check_setting_str(CFG, 'XBMC', 'xbmc_password', '')

        CheckSection(CFG, 'Plex')
        USE_PLEX = bool(check_setting_int(CFG, 'Plex', 'use_plex', 0))
        PLEX_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Plex', 'plex_notify_onsnatch', 0))
        PLEX_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Plex', 'plex_notify_ondownload', 0))
        PLEX_UPDATE_LIBRARY = bool(check_setting_int(CFG, 'Plex', 'plex_update_library', 0))
        PLEX_SERVER_HOST = check_setting_str(CFG, 'Plex', 'plex_server_host', '')
        PLEX_HOST = check_setting_str(CFG, 'Plex', 'plex_host', '')
        PLEX_USERNAME = check_setting_str(CFG, 'Plex', 'plex_username', '')
        PLEX_PASSWORD = check_setting_str(CFG, 'Plex', 'plex_password', '')

        CheckSection(CFG, 'Growl')
        USE_GROWL = bool(check_setting_int(CFG, 'Growl', 'use_growl', 0))
        GROWL_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Growl', 'growl_notify_onsnatch', 0))
        GROWL_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Growl', 'growl_notify_ondownload', 0))
        GROWL_HOST = check_setting_str(CFG, 'Growl', 'growl_host', '')
        GROWL_PASSWORD = check_setting_str(CFG, 'Growl', 'growl_password', '')

        CheckSection(CFG, 'Prowl')
        USE_PROWL = bool(check_setting_int(CFG, 'Prowl', 'use_prowl', 0))
        PROWL_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Prowl', 'prowl_notify_onsnatch', 0))
        PROWL_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Prowl', 'prowl_notify_ondownload', 0))
        PROWL_API = check_setting_str(CFG, 'Prowl', 'prowl_api', '')
        PROWL_PRIORITY = check_setting_str(CFG, 'Prowl', 'prowl_priority', "0")

        CheckSection(CFG, 'Twitter')
        USE_TWITTER = bool(check_setting_int(CFG, 'Twitter', 'use_twitter', 0))
        TWITTER_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Twitter', 'twitter_notify_onsnatch', 0))
        TWITTER_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Twitter', 'twitter_notify_ondownload', 0))
        TWITTER_USERNAME = check_setting_str(CFG, 'Twitter', 'twitter_username', '')
        TWITTER_PASSWORD = check_setting_str(CFG, 'Twitter', 'twitter_password', '')
        TWITTER_PREFIX = check_setting_str(CFG, 'Twitter', 'twitter_prefix', 'Sick Beard')

        CheckSection(CFG, 'Notifo')
        USE_NOTIFO = bool(check_setting_int(CFG, 'Notifo', 'use_notifo', 0))
        NOTIFO_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Notifo', 'notifo_notify_onsnatch', 0))
        NOTIFO_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Notifo', 'notifo_notify_ondownload', 0))
        NOTIFO_USERNAME = check_setting_str(CFG, 'Notifo', 'notifo_username', '')
        NOTIFO_APISECRET = check_setting_str(CFG, 'Notifo', 'notifo_apisecret', '')

        CheckSection(CFG, 'Boxcar')
        USE_BOXCAR = bool(check_setting_int(CFG, 'Boxcar', 'use_boxcar', 0))
        BOXCAR_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Boxcar', 'boxcar_notify_onsnatch', 0))
        BOXCAR_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Boxcar', 'boxcar_notify_ondownload', 0))
        BOXCAR_USERNAME = check_setting_str(CFG, 'Boxcar', 'boxcar_username', '')

        CheckSection(CFG, 'Pushover')
        USE_PUSHOVER = bool(check_setting_int(CFG, 'Pushover', 'use_pushover', 0))
        PUSHOVER_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Pushover', 'pushover_notify_onsnatch', 0))
        PUSHOVER_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Pushover', 'pushover_notify_ondownload', 0))
        PUSHOVER_USERKEY = check_setting_str(CFG, 'Pushover', 'pushover_userkey', '')

        CheckSection(CFG, 'Libnotify')
        USE_LIBNOTIFY = bool(check_setting_int(CFG, 'Libnotify', 'use_libnotify', 0))
        LIBNOTIFY_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Libnotify', 'libnotify_notify_onsnatch', 0))
        LIBNOTIFY_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Libnotify', 'libnotify_notify_ondownload', 0))

        CheckSection(CFG, 'NMJ')
        USE_NMJ = bool(check_setting_int(CFG, 'NMJ', 'use_nmj', 0))
        NMJ_HOST = check_setting_str(CFG, 'NMJ', 'nmj_host', '')
        NMJ_DATABASE = check_setting_str(CFG, 'NMJ', 'nmj_database', '')
        NMJ_MOUNT = check_setting_str(CFG, 'NMJ', 'nmj_mount', '')

        CheckSection(CFG, 'NMJv2')
        USE_NMJv2 = bool(check_setting_int(CFG, 'NMJv2', 'use_nmjv2', 0))
        NMJv2_HOST = check_setting_str(CFG, 'NMJv2', 'nmjv2_host', '')
        NMJv2_DATABASE = check_setting_str(CFG, 'NMJv2', 'nmjv2_database', '')
        NMJ_DBLOC = check_setting_str(CFG, 'NMJv2', 'nmjv2_dbloc', '')

        CheckSection(CFG, 'Synology')
        USE_SYNOINDEX = bool(check_setting_int(CFG, 'Synology', 'use_synoindex', 0))

        CheckSection(CFG, 'Trakt')
        USE_TRAKT = bool(check_setting_int(CFG, 'Trakt', 'use_trakt', 0))
        TRAKT_USERNAME = check_setting_str(CFG, 'Trakt', 'trakt_username', '')
        TRAKT_PASSWORD = check_setting_str(CFG, 'Trakt', 'trakt_password', '')
        TRAKT_API = check_setting_str(CFG, 'Trakt', 'trakt_api', '')

        CheckSection(CFG, 'pyTivo')
        USE_PYTIVO = bool(check_setting_int(CFG, 'pyTivo', 'use_pytivo', 0))
        PYTIVO_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'pyTivo', 'pytivo_notify_onsnatch', 0))
        PYTIVO_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'pyTivo', 'pytivo_notify_ondownload', 0))
        PYTIVO_UPDATE_LIBRARY = bool(check_setting_int(CFG, 'pyTivo', 'pyTivo_update_library', 0))
        PYTIVO_HOST = check_setting_str(CFG, 'pyTivo', 'pytivo_host', '')
        PYTIVO_SHARE_NAME = check_setting_str(CFG, 'pyTivo', 'pytivo_share_name', '')
        PYTIVO_TIVO_NAME = check_setting_str(CFG, 'pyTivo', 'pytivo_tivo_name', '')

        CheckSection(CFG, 'NMA')
        USE_NMA = bool(check_setting_int(CFG, 'NMA', 'use_nma', 0))
        NMA_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'NMA', 'nma_notify_onsnatch', 0))
        NMA_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'NMA', 'nma_notify_ondownload', 0))
        NMA_API = check_setting_str(CFG, 'NMA', 'nma_api', '')
        NMA_PRIORITY = check_setting_str(CFG, 'NMA', 'nma_priority', "0")

        # start up all the threads
        logger.sb_log_instance.initLogging(consoleLogging=consoleLogging)

        # initialize the main SB database
        db.upgradeDatabase(db.DBConnection(), mainDB.InitialSchema)

        # initialize the cache database
        db.upgradeDatabase(db.DBConnection("cache.db"), cache_db.InitialSchema)

        # fix up any db problems
        db.sanityCheckDatabase(db.DBConnection(), mainDB.MainSanityCheck)

        # migrate the config if it needs it
        migrator = ConfigMigrator(CFG)
        migrator.migrate_config()

        currentSearchScheduler = scheduler.Scheduler(searchCurrent.CurrentSearcher(),
                                                     cycleTime=datetime.timedelta(minutes=SEARCH_FREQUENCY),
                                                     threadName="SEARCH",
                                                     runImmediately=True)

        # the interval for this is stored inside the ShowUpdater class
        showUpdaterInstance = showUpdater.ShowUpdater()
        showUpdateScheduler = scheduler.Scheduler(showUpdaterInstance,
                                               cycleTime=showUpdaterInstance.updateInterval,
                                               threadName="SHOWUPDATER",
                                               runImmediately=False)

        versionCheckScheduler = scheduler.Scheduler(versionChecker.CheckVersion(),
                                                     cycleTime=datetime.timedelta(hours=12),
                                                     threadName="CHECKVERSION",
                                                     runImmediately=True)

        showQueueScheduler = scheduler.Scheduler(show_queue.ShowQueue(),
                                               cycleTime=datetime.timedelta(seconds=3),
                                               threadName="SHOWQUEUE",
                                               silent=True)

        searchQueueScheduler = scheduler.Scheduler(search_queue.SearchQueue(),
                                               cycleTime=datetime.timedelta(seconds=3),
                                               threadName="SEARCHQUEUE",
                                               silent=True)

        properFinderInstance = properFinder.ProperFinder()
        properFinderScheduler = scheduler.Scheduler(properFinderInstance,
                                                     cycleTime=properFinderInstance.updateInterval,
                                                     threadName="FINDPROPERS",
                                                     runImmediately=False)

        autoPostProcesserScheduler = scheduler.Scheduler(autoPostProcesser.PostProcesser(),
                                                     cycleTime=datetime.timedelta(minutes=10),
                                                     threadName="POSTPROCESSER",
                                                     runImmediately=True)

        backlogSearchScheduler = searchBacklog.BacklogSearchScheduler(searchBacklog.BacklogSearcher(),
                                                                      cycleTime=datetime.timedelta(minutes=get_backlog_cycle_time()),
                                                                      threadName="BACKLOG",
                                                                      runImmediately=True)
        backlogSearchScheduler.action.cycleTime = BACKLOG_SEARCH_FREQUENCY

        showList = []
        loadingShowList = {}

        __INITIALIZED__ = True
        return True


def start():

    global __INITIALIZED__, currentSearchScheduler, backlogSearchScheduler, \
            showUpdateScheduler, versionCheckScheduler, showQueueScheduler, \
            properFinderScheduler, autoPostProcesserScheduler, searchQueueScheduler, \
            started

    with INIT_LOCK:

        if __INITIALIZED__:

            # start the search scheduler
            currentSearchScheduler.thread.start()

            # start the backlog scheduler
            backlogSearchScheduler.thread.start()

            # start the show updater
            showUpdateScheduler.thread.start()

            # start the version checker
            versionCheckScheduler.thread.start()

            # start the queue checker
            showQueueScheduler.thread.start()

            # start the search queue checker
            searchQueueScheduler.thread.start()

            # start the queue checker
            properFinderScheduler.thread.start()

            # start the proper finder
            autoPostProcesserScheduler.thread.start()

            started = True


def halt():

    global __INITIALIZED__, currentSearchScheduler, backlogSearchScheduler, showUpdateScheduler, \
            showQueueScheduler, properFinderScheduler, autoPostProcesserScheduler, searchQueueScheduler, \
            started

    with INIT_LOCK:

        if __INITIALIZED__:

            logger.log(u"Aborting all threads")

            # abort all the threads

            currentSearchScheduler.abort = True
            logger.log(u"Waiting for the SEARCH thread to exit")
            try:
                currentSearchScheduler.thread.join(10)
            except:
                pass

            backlogSearchScheduler.abort = True
            logger.log(u"Waiting for the BACKLOG thread to exit")
            try:
                backlogSearchScheduler.thread.join(10)
            except:
                pass

            showUpdateScheduler.abort = True
            logger.log(u"Waiting for the SHOWUPDATER thread to exit")
            try:
                showUpdateScheduler.thread.join(10)
            except:
                pass

            versionCheckScheduler.abort = True
            logger.log(u"Waiting for the VERSIONCHECKER thread to exit")
            try:
                versionCheckScheduler.thread.join(10)
            except:
                pass

            showQueueScheduler.abort = True
            logger.log(u"Waiting for the SHOWQUEUE thread to exit")
            try:
                showQueueScheduler.thread.join(10)
            except:
                pass

            searchQueueScheduler.abort = True
            logger.log(u"Waiting for the SEARCHQUEUE thread to exit")
            try:
                searchQueueScheduler.thread.join(10)
            except:
                pass

            autoPostProcesserScheduler.abort = True
            logger.log(u"Waiting for the POSTPROCESSER thread to exit")
            try:
                autoPostProcesserScheduler.thread.join(10)
            except:
                pass

            properFinderScheduler.abort = True
            logger.log(u"Waiting for the PROPERFINDER thread to exit")
            try:
                properFinderScheduler.thread.join(10)
            except:
                pass

            __INITIALIZED__ = False


def sig_handler(signum=None, frame=None):
    if type(signum) != type(None):
        logger.log(u"Signal %i caught, saving and exiting..." % int(signum))
        saveAndShutdown()


def saveAll():

    global showList

    # write all shows
    logger.log(u"Saving all shows to the database")
    for show in showList:
        show.saveToDB()

    # save config
    logger.log(u"Saving config file to disk")
    save_config()


def saveAndShutdown(restart=False):

    halt()

    saveAll()

    logger.log(u"Killing cherrypy")
    cherrypy.engine.exit()

    if CREATEPID:
        logger.log(u"Removing pidfile " + str(PIDFILE))
        os.remove(PIDFILE)

    if restart:
        install_type = versionCheckScheduler.action.install_type

        popen_list = []

        if install_type in ('git', 'source'):
            popen_list = [sys.executable, MY_FULLNAME]
        elif install_type == 'win':
            if hasattr(sys, 'frozen'):
                # c:\dir\to\updater.exe 12345 c:\dir\to\sickbeard.exe
                popen_list = [os.path.join(PROG_DIR, 'updater.exe'), str(PID), sys.executable]
            else:
                logger.log(u"Unknown SB launch method, please file a bug report about this", logger.ERROR)
                popen_list = [sys.executable, os.path.join(PROG_DIR, 'updater.py'), str(PID), sys.executable, MY_FULLNAME ]

        if popen_list:
            popen_list += MY_ARGS
            if '--nolaunch' not in popen_list:
                popen_list += ['--nolaunch']
            logger.log(u"Restarting Sick Beard with " + str(popen_list))
            subprocess.Popen(popen_list, cwd=os.getcwd())

    os._exit(0)


def invoke_command(to_call, *args, **kwargs):
    global invoked_command

    def delegate():
        to_call(*args, **kwargs)
    invoked_command = delegate
    logger.log(u"Placed invoked command: " + repr(invoked_command) + " for " + repr(to_call) + " with " + repr(args) + " and " + repr(kwargs), logger.DEBUG)


def invoke_restart(soft=True):
    invoke_command(restart, soft=soft)


def invoke_shutdown():
    invoke_command(saveAndShutdown)


def restart(soft=True):
    if soft:
        halt()
        saveAll()
        #logger.log(u"Restarting cherrypy")
        #cherrypy.engine.restart()
        logger.log(u"Re-initializing all data")
        initialize()

    else:
        saveAndShutdown(restart=True)


def save_config():

    new_config = ConfigObj()
    new_config.filename = CONFIG_FILE

    new_config['General'] = {}
    new_config['General']['log_dir'] = LOG_DIR
    new_config['General']['web_port'] = WEB_PORT
    new_config['General']['web_host'] = WEB_HOST
    new_config['General']['web_ipv6'] = int(WEB_IPV6)
    new_config['General']['web_log'] = int(WEB_LOG)
    new_config['General']['web_root'] = WEB_ROOT
    new_config['General']['web_username'] = WEB_USERNAME
    new_config['General']['web_password'] = WEB_PASSWORD
    new_config['General']['use_api'] = int(USE_API)
    new_config['General']['api_key'] = API_KEY
    new_config['General']['enable_https'] = int(ENABLE_HTTPS)
    new_config['General']['https_cert'] = HTTPS_CERT
    new_config['General']['https_key'] = HTTPS_KEY
    new_config['General']['use_nzbs'] = int(USE_NZBS)
    new_config['General']['use_torrents'] = int(USE_TORRENTS)
    new_config['General']['torrent_method'] = TORRENT_METHOD
    new_config['General']['nzb_method'] = NZB_METHOD
    new_config['General']['usenet_retention'] = int(USENET_RETENTION)
    new_config['General']['search_frequency'] = int(SEARCH_FREQUENCY)
    new_config['General']['download_propers'] = int(DOWNLOAD_PROPERS)
    new_config['General']['quality_default'] = int(QUALITY_DEFAULT)
    new_config['General']['status_default'] = int(STATUS_DEFAULT)
    new_config['General']['flatten_folders_default'] = int(FLATTEN_FOLDERS_DEFAULT)
    new_config['General']['provider_order'] = ' '.join([x.getID() for x in providers.sortedProviderList()])
    new_config['General']['version_notify'] = int(VERSION_NOTIFY)
    new_config['General']['naming_pattern'] = NAMING_PATTERN
    new_config['General']['naming_custom_abd'] = int(NAMING_CUSTOM_ABD)
    new_config['General']['naming_abd_pattern'] = NAMING_ABD_PATTERN
    new_config['General']['naming_multi_ep'] = int(NAMING_MULTI_EP)
    new_config['General']['launch_browser'] = int(LAUNCH_BROWSER)

    new_config['General']['use_banner'] = int(USE_BANNER)
    new_config['General']['use_listview'] = int(USE_LISTVIEW)
    new_config['General']['metadata_xbmc'] = metadata_provider_dict['XBMC'].get_config()
    new_config['General']['metadata_mediabrowser'] = metadata_provider_dict['MediaBrowser'].get_config()
    new_config['General']['metadata_ps3'] = metadata_provider_dict['Sony PS3'].get_config()
    new_config['General']['metadata_wdtv'] = metadata_provider_dict['WDTV'].get_config()
    new_config['General']['metadata_tivo'] = metadata_provider_dict['TIVO'].get_config()
    new_config['General']['metadata_synology'] = metadata_provider_dict['Synology'].get_config()

    new_config['General']['cache_dir'] = ACTUAL_CACHE_DIR if ACTUAL_CACHE_DIR else 'cache'
    new_config['General']['root_dirs'] = ROOT_DIRS if ROOT_DIRS else ''
    new_config['General']['tv_download_dir'] = TV_DOWNLOAD_DIR
    new_config['General']['keep_processed_dir'] = int(KEEP_PROCESSED_DIR)
    new_config['General']['move_associated_files'] = int(MOVE_ASSOCIATED_FILES)
    new_config['General']['process_automatically'] = int(PROCESS_AUTOMATICALLY)
    new_config['General']['rename_episodes'] = int(RENAME_EPISODES)
    new_config['General']['create_missing_show_dirs'] = CREATE_MISSING_SHOW_DIRS
    new_config['General']['add_shows_wo_dir'] = ADD_SHOWS_WO_DIR

    new_config['General']['extra_scripts'] = '|'.join(EXTRA_SCRIPTS)
    new_config['General']['git_path'] = GIT_PATH
    new_config['General']['ignore_words'] = IGNORE_WORDS

    new_config['Blackhole'] = {}
    new_config['Blackhole']['nzb_dir'] = NZB_DIR
    new_config['Blackhole']['torrent_dir'] = TORRENT_DIR

    new_config['EZRSS'] = {}
    new_config['EZRSS']['ezrss'] = int(EZRSS)

    new_config['TVTORRENTS'] = {}
    new_config['TVTORRENTS']['tvtorrents'] = int(TVTORRENTS)
    new_config['TVTORRENTS']['tvtorrents_digest'] = TVTORRENTS_DIGEST
    new_config['TVTORRENTS']['tvtorrents_hash'] = TVTORRENTS_HASH

    new_config['THEPIRATEBAY'] = {}
    new_config['THEPIRATEBAY']['thepiratebay'] = int(THEPIRATEBAY)
    new_config['THEPIRATEBAY']['thepiratebay_trusted'] = int(THEPIRATEBAY_TRUSTED)
    new_config['THEPIRATEBAY']['thepiratebay_proxy'] = int(THEPIRATEBAY_PROXY)
    new_config['THEPIRATEBAY']['thepiratebay_proxy_url'] = THEPIRATEBAY_PROXY_URL
    new_config['THEPIRATEBAY']['thepiratebay_url'] = THEPIRATEBAY_URL

    new_config['BTN'] = {}
    new_config['BTN']['btn'] = int(BTN)
    new_config['BTN']['btn_api_key'] = BTN_API_KEY

    new_config['TorrentLeech'] = {}
    new_config['TorrentLeech']['torrentleech'] = int(TORRENTLEECH)
    new_config['TorrentLeech']['torrentleech_key'] = TORRENTLEECH_KEY

    new_config['NZBs'] = {}
    new_config['NZBs']['nzbs'] = int(NZBS)
    new_config['NZBs']['nzbs_uid'] = NZBS_UID
    new_config['NZBs']['nzbs_hash'] = NZBS_HASH

    new_config['NZBsRUS'] = {}
    new_config['NZBsRUS']['nzbsrus'] = int(NZBSRUS)
    new_config['NZBsRUS']['nzbsrus_uid'] = NZBSRUS_UID
    new_config['NZBsRUS']['nzbsrus_hash'] = NZBSRUS_HASH

    new_config['NZBMatrix'] = {}
    new_config['NZBMatrix']['nzbmatrix'] = int(NZBMATRIX)
    new_config['NZBMatrix']['nzbmatrix_username'] = NZBMATRIX_USERNAME
    new_config['NZBMatrix']['nzbmatrix_apikey'] = NZBMATRIX_APIKEY

    new_config['Newzbin'] = {}
    new_config['Newzbin']['newzbin'] = int(NEWZBIN)
    new_config['Newzbin']['newzbin_username'] = NEWZBIN_USERNAME
    new_config['Newzbin']['newzbin_password'] = NEWZBIN_PASSWORD

    new_config['Womble'] = {}
    new_config['Womble']['womble'] = int(WOMBLE)

    new_config['nzbX'] = {}
    new_config['nzbX']['nzbx'] = int(NZBX)
    new_config['nzbX']['nzbx_completion'] = int(NZBX_COMPLETION)

    new_config['omgwtfnzbs'] = {}
    new_config['omgwtfnzbs']['omgwtfnzbs'] = int(OMGWTFNZBS)
    new_config['omgwtfnzbs']['omgwtfnzbs_uid'] = OMGWTFNZBS_UID
    new_config['omgwtfnzbs']['omgwtfnzbs_key'] = OMGWTFNZBS_KEY

    new_config['SABnzbd'] = {}
    new_config['SABnzbd']['sab_username'] = SAB_USERNAME
    new_config['SABnzbd']['sab_password'] = SAB_PASSWORD
    new_config['SABnzbd']['sab_apikey'] = SAB_APIKEY
    new_config['SABnzbd']['sab_category'] = SAB_CATEGORY
    new_config['SABnzbd']['sab_host'] = SAB_HOST

    new_config['uTorrent'] = {}
    new_config['uTorrent']['utorrent_username'] = UTORRENT_USERNAME
    new_config['uTorrent']['utorrent_password'] = UTORRENT_PASSWORD
    new_config['uTorrent']['utorrent_label'] = UTORRENT_LABEL
    new_config['uTorrent']['utorrent_host'] = UTORRENT_HOST

    new_config['NZBget'] = {}
    new_config['NZBget']['nzbget_password'] = NZBGET_PASSWORD
    new_config['NZBget']['nzbget_category'] = NZBGET_CATEGORY
    new_config['NZBget']['nzbget_host'] = NZBGET_HOST

    new_config['XBMC'] = {}
    new_config['XBMC']['use_xbmc'] = int(USE_XBMC)
    new_config['XBMC']['xbmc_notify_onsnatch'] = int(XBMC_NOTIFY_ONSNATCH)
    new_config['XBMC']['xbmc_notify_ondownload'] = int(XBMC_NOTIFY_ONDOWNLOAD)
    new_config['XBMC']['xbmc_update_library'] = int(XBMC_UPDATE_LIBRARY)
    new_config['XBMC']['xbmc_update_full'] = int(XBMC_UPDATE_FULL)
    new_config['XBMC']['xbmc_update_onlyfirst'] = int(XBMC_UPDATE_ONLYFIRST)
    new_config['XBMC']['xbmc_host'] = XBMC_HOST
    new_config['XBMC']['xbmc_username'] = XBMC_USERNAME
    new_config['XBMC']['xbmc_password'] = XBMC_PASSWORD

    new_config['Plex'] = {}
    new_config['Plex']['use_plex'] = int(USE_PLEX)
    new_config['Plex']['plex_notify_onsnatch'] = int(PLEX_NOTIFY_ONSNATCH)
    new_config['Plex']['plex_notify_ondownload'] = int(PLEX_NOTIFY_ONDOWNLOAD)
    new_config['Plex']['plex_update_library'] = int(PLEX_UPDATE_LIBRARY)
    new_config['Plex']['plex_server_host'] = PLEX_SERVER_HOST
    new_config['Plex']['plex_host'] = PLEX_HOST
    new_config['Plex']['plex_username'] = PLEX_USERNAME
    new_config['Plex']['plex_password'] = PLEX_PASSWORD

    new_config['Growl'] = {}
    new_config['Growl']['use_growl'] = int(USE_GROWL)
    new_config['Growl']['growl_notify_onsnatch'] = int(GROWL_NOTIFY_ONSNATCH)
    new_config['Growl']['growl_notify_ondownload'] = int(GROWL_NOTIFY_ONDOWNLOAD)
    new_config['Growl']['growl_host'] = GROWL_HOST
    new_config['Growl']['growl_password'] = GROWL_PASSWORD

    new_config['Prowl'] = {}
    new_config['Prowl']['use_prowl'] = int(USE_PROWL)
    new_config['Prowl']['prowl_notify_onsnatch'] = int(PROWL_NOTIFY_ONSNATCH)
    new_config['Prowl']['prowl_notify_ondownload'] = int(PROWL_NOTIFY_ONDOWNLOAD)
    new_config['Prowl']['prowl_api'] = PROWL_API
    new_config['Prowl']['prowl_priority'] = PROWL_PRIORITY

    new_config['Twitter'] = {}
    new_config['Twitter']['use_twitter'] = int(USE_TWITTER)
    new_config['Twitter']['twitter_notify_onsnatch'] = int(TWITTER_NOTIFY_ONSNATCH)
    new_config['Twitter']['twitter_notify_ondownload'] = int(TWITTER_NOTIFY_ONDOWNLOAD)
    new_config['Twitter']['twitter_username'] = TWITTER_USERNAME
    new_config['Twitter']['twitter_password'] = TWITTER_PASSWORD
    new_config['Twitter']['twitter_prefix'] = TWITTER_PREFIX

    new_config['Notifo'] = {}
    new_config['Notifo']['use_notifo'] = int(USE_NOTIFO)
    new_config['Notifo']['notifo_notify_onsnatch'] = int(NOTIFO_NOTIFY_ONSNATCH)
    new_config['Notifo']['notifo_notify_ondownload'] = int(NOTIFO_NOTIFY_ONDOWNLOAD)
    new_config['Notifo']['notifo_username'] = NOTIFO_USERNAME
    new_config['Notifo']['notifo_apisecret'] = NOTIFO_APISECRET

    new_config['Boxcar'] = {}
    new_config['Boxcar']['use_boxcar'] = int(USE_BOXCAR)
    new_config['Boxcar']['boxcar_notify_onsnatch'] = int(BOXCAR_NOTIFY_ONSNATCH)
    new_config['Boxcar']['boxcar_notify_ondownload'] = int(BOXCAR_NOTIFY_ONDOWNLOAD)
    new_config['Boxcar']['boxcar_username'] = BOXCAR_USERNAME

    new_config['Pushover'] = {}
    new_config['Pushover']['use_pushover'] = int(USE_PUSHOVER)
    new_config['Pushover']['pushover_notify_onsnatch'] = int(PUSHOVER_NOTIFY_ONSNATCH)
    new_config['Pushover']['pushover_notify_ondownload'] = int(PUSHOVER_NOTIFY_ONDOWNLOAD)
    new_config['Pushover']['pushover_userkey'] = PUSHOVER_USERKEY

    new_config['Libnotify'] = {}
    new_config['Libnotify']['use_libnotify'] = int(USE_LIBNOTIFY)
    new_config['Libnotify']['libnotify_notify_onsnatch'] = int(LIBNOTIFY_NOTIFY_ONSNATCH)
    new_config['Libnotify']['libnotify_notify_ondownload'] = int(LIBNOTIFY_NOTIFY_ONDOWNLOAD)

    new_config['NMJ'] = {}
    new_config['NMJ']['use_nmj'] = int(USE_NMJ)
    new_config['NMJ']['nmj_host'] = NMJ_HOST
    new_config['NMJ']['nmj_database'] = NMJ_DATABASE
    new_config['NMJ']['nmj_mount'] = NMJ_MOUNT

    new_config['Synology'] = {}
    new_config['Synology']['use_synoindex'] = int(USE_SYNOINDEX)

    new_config['NMJv2'] = {}
    new_config['NMJv2']['use_nmjv2'] = int(USE_NMJv2)
    new_config['NMJv2']['nmjv2_host'] = NMJv2_HOST
    new_config['NMJv2']['nmjv2_database'] = NMJv2_DATABASE
    new_config['NMJv2']['nmjv2_dbloc'] = NMJv2_DBLOC

    new_config['Trakt'] = {}
    new_config['Trakt']['use_trakt'] = int(USE_TRAKT)
    new_config['Trakt']['trakt_username'] = TRAKT_USERNAME
    new_config['Trakt']['trakt_password'] = TRAKT_PASSWORD
    new_config['Trakt']['trakt_api'] = TRAKT_API

    new_config['pyTivo'] = {}
    new_config['pyTivo']['use_pytivo'] = int(USE_PYTIVO)
    new_config['pyTivo']['pytivo_notify_onsnatch'] = int(PYTIVO_NOTIFY_ONSNATCH)
    new_config['pyTivo']['pytivo_notify_ondownload'] = int(PYTIVO_NOTIFY_ONDOWNLOAD)
    new_config['pyTivo']['pyTivo_update_library'] = int(PYTIVO_UPDATE_LIBRARY)
    new_config['pyTivo']['pytivo_host'] = PYTIVO_HOST
    new_config['pyTivo']['pytivo_share_name'] = PYTIVO_SHARE_NAME
    new_config['pyTivo']['pytivo_tivo_name'] = PYTIVO_TIVO_NAME

    new_config['NMA'] = {}
    new_config['NMA']['use_nma'] = int(USE_NMA)
    new_config['NMA']['nma_notify_onsnatch'] = int(NMA_NOTIFY_ONSNATCH)
    new_config['NMA']['nma_notify_ondownload'] = int(NMA_NOTIFY_ONDOWNLOAD)
    new_config['NMA']['nma_api'] = NMA_API
    new_config['NMA']['nma_priority'] = NMA_PRIORITY

    new_config['Newznab'] = {}
    new_config['Newznab']['newznab_data'] = '!!!'.join([x.configStr() for x in newznabProviderList])

    new_config['GUI'] = {}
    new_config['GUI']['coming_eps_layout'] = COMING_EPS_LAYOUT
    new_config['GUI']['coming_eps_display_paused'] = int(COMING_EPS_DISPLAY_PAUSED)
    new_config['GUI']['coming_eps_sort'] = COMING_EPS_SORT

    new_config['General']['config_version'] = CONFIG_VERSION

    new_config.write()


def launchBrowser(startPort=None):
    if not startPort:
        startPort = WEB_PORT
    if ENABLE_HTTPS:
        browserURL = 'https://localhost:%d%s' % (startPort, WEB_ROOT)
    else:
        browserURL = 'http://localhost:%d%s' % (startPort, WEB_ROOT)
    try:
        webbrowser.open(browserURL, 2, 1)
    except:
        try:
            webbrowser.open(browserURL, 1, 1)
        except:
            logger.log(u"Unable to launch a browser", logger.ERROR)


def getEpList(epIDs, showid=None):
    if epIDs == None or len(epIDs) == 0:
        return []

    query = "SELECT * FROM tv_episodes WHERE tvdbid in (%s)" % (",".join(['?'] * len(epIDs)),)
    params = epIDs

    if showid != None:
        query += " AND showid = ?"
        params.append(showid)

    myDB = db.DBConnection()
    sqlResults = myDB.select(query, params)

    epList = []

    for curEp in sqlResults:
        curShowObj = helpers.findCertainShow(showList, int(curEp["showid"]))
        curEpObj = curShowObj.getEpisode(int(curEp["season"]), int(curEp["episode"]))
        epList.append(curEpObj)

    return epList
