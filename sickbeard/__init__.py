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
import os, sys, subprocess

from threading import Lock

# apparently py2exe won't build these unless they're imported somewhere
from sickbeard import providers, metadata
from providers import eztv, nzbs_org, nzbmatrix, tvbinz, nzbsrus, binreq, newznab, womble, newzbin

from sickbeard import searchCurrent, searchBacklog, showUpdater, versionChecker, properFinder, autoPostProcesser
from sickbeard import helpers, db, exceptions, queue, scheduler
from sickbeard import logger

from sickbeard.common import *

from sickbeard.databases import mainDB

from lib.configobj import ConfigObj

SOCKET_TIMEOUT = 30

CFG = None
CONFIG_FILE = None

PROG_DIR = None
MY_FULLNAME = None
MY_NAME = None
MY_ARGS = []

backlogSearchScheduler = None
currentSearchScheduler = None
showUpdateScheduler = None
versionCheckScheduler = None
showQueueScheduler = None
properFinderScheduler = None
autoPostProcesserScheduler = None

showList = None
loadingShowList = None

airingList = None
comingList = None

providerList = []
newznabProviderList = []
metadata_generator = None

NEWEST_VERSION = None
NEWEST_VERSION_STRING = None
VERSION_NOTIFY = None

INIT_LOCK = Lock()
__INITIALIZED__ = False

LOG_DIR = None

WEB_PORT = None
WEB_LOG = None
WEB_ROOT = None
WEB_USERNAME = None
WEB_PASSWORD = None
WEB_HOST = None

LAUNCH_BROWSER = None
CACHE_DIR = None

METADATA_TYPE = None
METADATA_SHOW = None
METADATA_EPISODE = None

ART_POSTER = None
ART_FANART = None
ART_THUMBNAILS = None
ART_SEASON_THUMBNAILS = None

QUALITY_DEFAULT = None
SEASON_FOLDERS_DEFAULT = None
PROVIDER_ORDER = []

NAMING_SHOW_NAME = None
NAMING_EP_NAME = None
NAMING_EP_TYPE = None
NAMING_MULTI_EP_TYPE = None
NAMING_SEP_TYPE = None
NAMING_USE_PERIODS = None
NAMING_QUALITY = None
NAMING_DATES = None

TVDB_API_KEY = '9DAF49C96CBF8DAC'
TVDB_BASE_URL = None
TVDB_API_PARMS = {}

USE_NZB = False
NZB_METHOD = None
NZB_DIR = None
USENET_RETENTION = None
DOWNLOAD_PROPERS = None

SEARCH_FREQUENCY = None
BACKLOG_SEARCH_FREQUENCY = None

MIN_SEARCH_FREQUENCY = 10
MIN_BACKLOG_SEARCH_FREQUENCY = 7

DEFAULT_SEARCH_FREQUENCY = 60
DEFAULT_BACKLOG_SEARCH_FREQUENCY = 21

USE_TORRENT = False
TORRENT_DIR = None

RENAME_EPISODES = False
PROCESS_AUTOMATICALLY = False
KEEP_PROCESSED_DIR = False
TV_DOWNLOAD_DIR = None

SHOW_TVBINZ = False
TVBINZ = False
TVBINZ_UID = None
TVBINZ_HASH = None
TVBINZ_AUTH = None

NZBS = False
NZBS_UID = None
NZBS_HASH = None

BINREQ = False

WOMBLE = False

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
SAB_HOST = None

XBMC_NOTIFY_ONSNATCH = False
XBMC_NOTIFY_ONDOWNLOAD = False
XBMC_UPDATE_LIBRARY = False
XBMC_UPDATE_FULL = False
XBMC_HOST = None
XBMC_USERNAME = None
XBMC_PASSWORD = None

USE_GROWL = False
GROWL_HOST = None
GROWL_PASSWORD = None

USE_TWITTER = False
TWITTER_USERNAME = None
TWITTER_PASSWORD = None
TWITTER_PREFIX = None

EXTRA_SCRIPTS = []

GIT_PATH = None

__INITIALIZED__ = False

def CheckSection(sec):
    """ Check if INI section exists, if not create it """
    try:
        CFG[sec]
        return True
    except:
        CFG[sec] = {}
        return False

################################################################################
# Check_setting_int                                                            #
################################################################################
def minimax(val, low, high):
    """ Return value forced within range """
    try:
        val = int(val)
    except:
        val = 0
    if val < low:
        return low
    if val > high:
        return high
    return val

################################################################################
# Check_setting_int                                                            #
################################################################################
def check_setting_int(config, cfg_name, item_name, def_val):
    try:
        my_val = int(config[cfg_name][item_name])
    except:
        my_val = def_val
        try:
            config[cfg_name][item_name] = my_val
        except:
            config[cfg_name] = {}
            config[cfg_name][item_name] = my_val
    logger.log(item_name + " -> " + str(my_val), logger.DEBUG)
    return my_val

################################################################################
# Check_setting_float                                                          #
################################################################################
def check_setting_float(config, cfg_name, item_name, def_val):
    try:
        my_val = float(config[cfg_name][item_name])
    except:
        my_val = def_val
        try:
            config[cfg_name][item_name] = my_val
        except:
            config[cfg_name] = {}
            config[cfg_name][item_name] = my_val

    logger.log(item_name + " -> " + str(my_val), logger.DEBUG)
    return my_val

################################################################################
# Check_setting_str                                                            #
################################################################################
def check_setting_str(config, cfg_name, item_name, def_val, log=True):
    try:
        my_val = config[cfg_name][item_name]
    except:
        my_val = def_val
        try:
            config[cfg_name][item_name] = my_val
        except:
            config[cfg_name] = {}
            config[cfg_name][item_name] = my_val

    if log:
        logger.log(item_name + " -> " + my_val, logger.DEBUG)
    else:
        logger.log(item_name + " -> ******", logger.DEBUG)
    return my_val


def get_backlog_cycle_time():
    cycletime = sickbeard.SEARCH_FREQUENCY*2+7
    return min([cycletime, 60])


def initialize(consoleLogging=True):

    with INIT_LOCK:

        global LOG_DIR, WEB_PORT, WEB_LOG, WEB_ROOT, WEB_USERNAME, WEB_PASSWORD, WEB_HOST, \
                NZB_METHOD, NZB_DIR, TVBINZ, TVBINZ_UID, TVBINZ_HASH, DOWNLOAD_PROPERS, \
                SAB_USERNAME, SAB_PASSWORD, SAB_APIKEY, SAB_CATEGORY, SAB_HOST, \
                XBMC_NOTIFY_ONSNATCH, XBMC_NOTIFY_ONDOWNLOAD, XBMC_UPDATE_FULL, \
                XBMC_UPDATE_LIBRARY, XBMC_HOST, XBMC_USERNAME, XBMC_PASSWORD, currentSearchScheduler, backlogSearchScheduler, \
                showUpdateScheduler, __INITIALIZED__, LAUNCH_BROWSER, showList, \
                airingList, comingList, loadingShowList, SOCKET_TIMEOUT, \
                NZBS, NZBS_UID, NZBS_HASH, USE_NZB, USE_TORRENT, TORRENT_DIR, USENET_RETENTION, \
                SEARCH_FREQUENCY, DEFAULT_SEARCH_FREQUENCY, BACKLOG_SEARCH_FREQUENCY, \
                DEFAULT_BACKLOG_SEARCH_FREQUENCY, QUALITY_DEFAULT, SEASON_FOLDERS_DEFAULT, \
                USE_GROWL, GROWL_HOST, GROWL_PASSWORD, PROG_DIR, NZBMATRIX, NZBMATRIX_USERNAME, \
                NZBMATRIX_APIKEY, versionCheckScheduler, VERSION_NOTIFY, PROCESS_AUTOMATICALLY, \
                KEEP_PROCESSED_DIR, TV_DOWNLOAD_DIR, TVDB_BASE_URL, MIN_SEARCH_FREQUENCY, \
                MIN_BACKLOG_SEARCH_FREQUENCY, TVBINZ_AUTH, showQueueScheduler, \
                NAMING_SHOW_NAME, NAMING_EP_TYPE, NAMING_MULTI_EP_TYPE, CACHE_DIR, TVDB_API_PARMS, \
                RENAME_EPISODES, properFinderScheduler, PROVIDER_ORDER, autoPostProcesserScheduler, \
                NAMING_EP_NAME, NAMING_SEP_TYPE, NAMING_USE_PERIODS, WOMBLE, \
                NZBSRUS, NZBSRUS_UID, NZBSRUS_HASH, BINREQ, NAMING_QUALITY, providerList, newznabProviderList, \
                NAMING_DATES, EXTRA_SCRIPTS, USE_TWITTER, TWITTER_USERNAME, TWITTER_PASSWORD, TWITTER_PREFIX, \
                METADATA_TYPE, METADATA_SHOW, METADATA_EPISODE, metadata_generator, \
                ART_POSTER, ART_FANART, ART_THUMBNAILS, ART_SEASON_THUMBNAILS, \
                NEWZBIN, NEWZBIN_USERNAME, NEWZBIN_PASSWORD, GIT_PATH


        if __INITIALIZED__:
            return False

        socket.setdefaulttimeout(SOCKET_TIMEOUT)

        CheckSection('General')
        CheckSection('Blackhole')
        CheckSection('Newzbin')
        CheckSection('TVBinz')
        CheckSection('SABnzbd')
        CheckSection('XBMC')
        CheckSection('Growl')
        CheckSection('Twitter')

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
        WEB_ROOT = check_setting_str(CFG, 'General', 'web_root', '').rstrip("/")
        WEB_LOG = bool(check_setting_int(CFG, 'General', 'web_log', 0))
        WEB_USERNAME = check_setting_str(CFG, 'General', 'web_username', '')
        WEB_PASSWORD = check_setting_str(CFG, 'General', 'web_password', '')
        LAUNCH_BROWSER = bool(check_setting_int(CFG, 'General', 'launch_browser', 1))

        CACHE_DIR = check_setting_str(CFG, 'General', 'cache_dir', 'cache')
        if not helpers.makeDir(CACHE_DIR):
            logger.log(u"!!! Creating local cache dir failed, using system default", logger.ERROR)
            CACHE_DIR = None

        # Set our common tvdb_api options here
        TVDB_API_PARMS = {'cache': True,
                          'apikey': TVDB_API_KEY,
                          'language': 'en',
                          'cache_dir': False}
        if CACHE_DIR:
            TVDB_API_PARMS['cache_dir'] = os.path.join(CACHE_DIR, 'tvdb')

        QUALITY_DEFAULT = check_setting_int(CFG, 'General', 'quality_default', SD)
        VERSION_NOTIFY = check_setting_int(CFG, 'General', 'version_notify', 1)
        SEASON_FOLDERS_DEFAULT = bool(check_setting_int(CFG, 'General', 'season_folders_default', 0))

        PROVIDER_ORDER = check_setting_str(CFG, 'General', 'provider_order', '').split()

        NAMING_SHOW_NAME = bool(check_setting_int(CFG, 'General', 'naming_show_name', 1))
        NAMING_EP_NAME = bool(check_setting_int(CFG, 'General', 'naming_ep_name', 1))
        NAMING_EP_TYPE = check_setting_int(CFG, 'General', 'naming_ep_type', 0)
        NAMING_MULTI_EP_TYPE = check_setting_int(CFG, 'General', 'naming_multi_ep_type', 0)
        NAMING_SEP_TYPE = check_setting_int(CFG, 'General', 'naming_sep_type', 0)
        NAMING_USE_PERIODS = bool(check_setting_int(CFG, 'General', 'naming_use_periods', 0))
        NAMING_QUALITY = bool(check_setting_int(CFG, 'General', 'naming_quality', 0))
        NAMING_DATES = bool(check_setting_int(CFG, 'General', 'naming_dates', 1))

        TVDB_BASE_URL = 'http://www.thetvdb.com/api/' + TVDB_API_KEY

        NZB_METHOD = check_setting_str(CFG, 'General', 'nzb_method', 'blackhole')
        if NZB_METHOD not in ('blackhole', 'sabnzbd'):
            NZB_METHOD = 'blackhole'

        DOWNLOAD_PROPERS = bool(check_setting_int(CFG, 'General', 'download_propers', 1))

        USE_NZB = bool(check_setting_int(CFG, 'General', 'use_nzb', 1))
        USE_TORRENT = bool(check_setting_int(CFG, 'General', 'use_torrent', 0))
        USENET_RETENTION = check_setting_int(CFG, 'General', 'usenet_retention', 500)

        SEARCH_FREQUENCY = check_setting_int(CFG, 'General', 'search_frequency', DEFAULT_SEARCH_FREQUENCY)
        if SEARCH_FREQUENCY < MIN_SEARCH_FREQUENCY:
            SEARCH_FREQUENCY = MIN_SEARCH_FREQUENCY

        BACKLOG_SEARCH_FREQUENCY = check_setting_int(CFG, 'General', 'backlog_search_frequency', DEFAULT_BACKLOG_SEARCH_FREQUENCY)
        if BACKLOG_SEARCH_FREQUENCY < MIN_BACKLOG_SEARCH_FREQUENCY:
            BACKLOG_SEARCH_FREQUENCY = MIN_BACKLOG_SEARCH_FREQUENCY

        NZB_DIR = check_setting_str(CFG, 'Blackhole', 'nzb_dir', '')
        TORRENT_DIR = check_setting_str(CFG, 'Blackhole', 'torrent_dir', '')

        TV_DOWNLOAD_DIR = check_setting_str(CFG, 'General', 'tv_download_dir', '')
        PROCESS_AUTOMATICALLY = check_setting_int(CFG, 'General', 'process_automatically', 0)
        RENAME_EPISODES = check_setting_int(CFG, 'General', 'rename_episodes', 1)
        KEEP_PROCESSED_DIR = check_setting_int(CFG, 'General', 'keep_processed_dir', 1)

        TVBINZ = bool(check_setting_int(CFG, 'TVBinz', 'tvbinz', 0))
        TVBINZ_UID = check_setting_str(CFG, 'TVBinz', 'tvbinz_uid', '')
        TVBINZ_HASH = check_setting_str(CFG, 'TVBinz', 'tvbinz_hash', '')
        TVBINZ_AUTH = check_setting_str(CFG, 'TVBinz', 'tvbinz_auth', '')

        NZBS = bool(check_setting_int(CFG, 'NZBs', 'nzbs', 0))
        NZBS_UID = check_setting_str(CFG, 'NZBs', 'nzbs_uid', '')
        NZBS_HASH = check_setting_str(CFG, 'NZBs', 'nzbs_hash', '')

        NZBSRUS = bool(check_setting_int(CFG, 'NZBsRUS', 'nzbsrus', 0))
        NZBSRUS_UID = check_setting_str(CFG, 'NZBsRUS', 'nzbsrus_uid', '')
        NZBSRUS_HASH = check_setting_str(CFG, 'NZBsRUS', 'nzbsrus_hash', '')

        NZBMATRIX = bool(check_setting_int(CFG, 'NZBMatrix', 'nzbmatrix', 0))
        NZBMATRIX_USERNAME = check_setting_str(CFG, 'NZBMatrix', 'nzbmatrix_username', '')
        NZBMATRIX_APIKEY = check_setting_str(CFG, 'NZBMatrix', 'nzbmatrix_apikey', '')

        NEWZBIN = bool(check_setting_int(CFG, 'Newzbin', 'newzbin', 0))
        NEWZBIN_USERNAME = check_setting_str(CFG, 'Newzbin', 'newzbin_username', '')
        NEWZBIN_PASSWORD = check_setting_str(CFG, 'Newzbin', 'newzbin_password', '')

        BINREQ = bool(check_setting_int(CFG, 'Bin-Req', 'binreq', 1))

        WOMBLE = bool(check_setting_int(CFG, 'Womble', 'womble', 1))

        SAB_USERNAME = check_setting_str(CFG, 'SABnzbd', 'sab_username', '')
        SAB_PASSWORD = check_setting_str(CFG, 'SABnzbd', 'sab_password', '')
        SAB_APIKEY = check_setting_str(CFG, 'SABnzbd', 'sab_apikey', '')
        SAB_CATEGORY = check_setting_str(CFG, 'SABnzbd', 'sab_category', 'tv')
        SAB_HOST = check_setting_str(CFG, 'SABnzbd', 'sab_host', '')

        XBMC_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'XBMC', 'xbmc_notify_onsnatch', 0))
        XBMC_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'XBMC', 'xbmc_notify_ondownload', 0))
        XBMC_UPDATE_LIBRARY = bool(check_setting_int(CFG, 'XBMC', 'xbmc_update_library', 0))
        XBMC_UPDATE_FULL = bool(check_setting_int(CFG, 'XBMC', 'xbmc_update_full', 0))
        XBMC_HOST = check_setting_str(CFG, 'XBMC', 'xbmc_host', '')
        XBMC_USERNAME = check_setting_str(CFG, 'XBMC', 'xbmc_username', '')
        XBMC_PASSWORD = check_setting_str(CFG, 'XBMC', 'xbmc_password', '')

        USE_GROWL = bool(check_setting_int(CFG, 'Growl', 'use_growl', 0))
        GROWL_HOST = check_setting_str(CFG, 'Growl', 'growl_host', '')
        GROWL_PASSWORD = check_setting_str(CFG, 'Growl', 'growl_password', '')

        USE_TWITTER = bool(check_setting_int(CFG, 'Twitter', 'use_twitter', 0))
        TWITTER_USERNAME = check_setting_str(CFG, 'Twitter', 'twitter_username', '')
        TWITTER_PASSWORD = check_setting_str(CFG, 'Twitter', 'twitter_password', '')
        TWITTER_PREFIX = check_setting_str(CFG, 'Twitter', 'twitter_prefix', 'Sick Beard')

        GIT_PATH = check_setting_str(CFG, 'General', 'git_path', '')

        EXTRA_SCRIPTS = [x for x in check_setting_str(CFG, 'General', 'extra_scripts', '').split('|') if x]

        METADATA_TYPE = check_setting_str(CFG, 'General', 'metadata_type', 'xbmc')
        METADATA_SHOW = bool(check_setting_int(CFG, 'General', 'metadata_show', 1))
        METADATA_EPISODE = bool(check_setting_int(CFG, 'General', 'metadata_episode', 1))

        ART_POSTER = bool(check_setting_int(CFG, 'General', 'art_poster', 1))
        ART_FANART = bool(check_setting_int(CFG, 'General', 'art_fanart', 1))
        ART_THUMBNAILS = bool(check_setting_int(CFG, 'General', 'art_thumbnails', 1))
        ART_SEASON_THUMBNAILS = bool(check_setting_int(CFG, 'General', 'art_season_thumbnails', 1))

        # try setting defaults if possible
        try:
            TEMP_CREATE_METADATA = bool(int(CFG['General']['create_metadata']))
            METADATA_SHOW = TEMP_CREATE_METADATA
            METADATA_EPISODE = TEMP_CREATE_METADATA
        except:
            pass
        
        try:
            TEMP_CREATE_IMAGES = bool(int(CFG['General']['create_images']))
            ART_POSTER = TEMP_CREATE_IMAGES 
            ART_FANART = TEMP_CREATE_IMAGES
            ART_THUMBNAILS = TEMP_CREATE_IMAGES
            ART_SEASON_THUMBNAILS = TEMP_CREATE_IMAGES
        except:
            pass

        newznabData = check_setting_str(CFG, 'Newznab', 'newznab_data', '')
        newznabProviderList = providers.getNewznabProviderList(newznabData)

        providerList = providers.makeProviderList()
        
        metadata_generator = metadata.getMetadataClass(METADATA_TYPE)

        logger.initLogging(consoleLogging=consoleLogging)

        # initialize the main SB database
        db.upgradeDatabase(db.DBConnection(), mainDB.InitialSchema)

        currentSearchScheduler = scheduler.Scheduler(searchCurrent.CurrentSearcher(),
                                                     cycleTime=datetime.timedelta(minutes=SEARCH_FREQUENCY),
                                                     threadName="SEARCH",
                                                     runImmediately=True)

        backlogSearchScheduler = searchBacklog.BacklogSearchScheduler(searchBacklog.BacklogSearcher(),
                                                                      cycleTime=datetime.timedelta(minutes=get_backlog_cycle_time()),
                                                                      threadName="BACKLOG",
                                                                      runImmediately=False)
        backlogSearchScheduler.action.cycleTime = BACKLOG_SEARCH_FREQUENCY

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

        showQueueScheduler = scheduler.Scheduler(queue.ShowQueue(),
                                               cycleTime=datetime.timedelta(seconds=3),
                                               threadName="SHOWQUEUE",
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


        showList = []
        loadingShowList = {}

        airingList = []
        comingList = []

        __INITIALIZED__ = True
        return True

def start():

    global __INITIALIZED__, currentSearchScheduler, backlogSearchScheduler, \
            showUpdateScheduler, versionCheckScheduler, showQueueScheduler, \
            properFinderScheduler, autoPostProcesserScheduler

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

            # start the queue checker
            properFinderScheduler.thread.start()

            # start the proper finder
            autoPostProcesserScheduler.thread.start()

def halt ():

    global __INITIALIZED__, currentSearchScheduler, backlogSearchScheduler, showUpdateScheduler, \
            showQueueScheduler, properFinderScheduler, autoPostProcesserScheduler

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
        cherrypy.engine.exit()
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

    logger.log(u"Killing cherrypy")
    cherrypy.engine.exit()

    halt()

    saveAll()

    if restart:
        install_type = sickbeard.versionCheckScheduler.action.install_type

        popen_list = []

        if install_type in ('git', 'source'):
            popen_list = [sys.executable, sickbeard.MY_FULLNAME]
        elif install_type == 'win':
            if hasattr(sys, 'frozen'):
                # c:\dir\to\updater.exe 12345 c:\dir\to\sickbeard.exe
                popen_list = [os.path.join(sickbeard.PROG_DIR, 'updater.exe'), str(os.getpid()), sys.executable]
            else:
                logger.log(u"Unknown SB launch method, please file a bug report about this", logger.ERROR)
                popen_list = [sys.executable, os.path.join(sickbeard.PROG_DIR, 'updater.py'), str(os.getpid()), sys.executable, sickbeard.MY_FULLNAME ]

        if popen_list:
            popen_list += sickbeard.MY_ARGS
            logger.log(u"Restarting Sick Beard with " + str(popen_list))
            subprocess.Popen(popen_list, cwd=os.getcwd())

    os._exit(0)


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
    new_config.filename = sickbeard.CONFIG_FILE

    new_config['General'] = {}
    new_config['General']['log_dir'] = LOG_DIR
    new_config['General']['web_port'] = WEB_PORT
    new_config['General']['web_host'] = WEB_HOST
    new_config['General']['web_log'] = int(WEB_LOG)
    new_config['General']['web_root'] = WEB_ROOT
    new_config['General']['web_username'] = WEB_USERNAME
    new_config['General']['web_password'] = WEB_PASSWORD
    new_config['General']['nzb_method'] = NZB_METHOD
    new_config['General']['usenet_retention'] = int(USENET_RETENTION)
    new_config['General']['search_frequency'] = int(SEARCH_FREQUENCY)
    new_config['General']['backlog_search_frequency'] = int(BACKLOG_SEARCH_FREQUENCY)
    new_config['General']['use_nzb'] = int(USE_NZB)
    new_config['General']['download_propers'] = int(DOWNLOAD_PROPERS)
    new_config['General']['quality_default'] = int(QUALITY_DEFAULT)
    new_config['General']['season_folders_default'] = int(SEASON_FOLDERS_DEFAULT)
    new_config['General']['provider_order'] = ' '.join([x.getID() for x in providers.sortedProviderList()])
    new_config['General']['version_notify'] = int(VERSION_NOTIFY)
    new_config['General']['naming_ep_name'] = int(NAMING_EP_NAME)
    new_config['General']['naming_show_name'] = int(NAMING_SHOW_NAME)
    new_config['General']['naming_ep_type'] = int(NAMING_EP_TYPE)
    new_config['General']['naming_multi_ep_type'] = int(NAMING_MULTI_EP_TYPE)
    new_config['General']['naming_sep_type'] = int(NAMING_SEP_TYPE)
    new_config['General']['naming_use_periods'] = int(NAMING_USE_PERIODS)
    new_config['General']['naming_quality'] = int(NAMING_QUALITY)
    new_config['General']['naming_dates'] = int(NAMING_DATES)
    new_config['General']['use_torrent'] = int(USE_TORRENT)
    new_config['General']['launch_browser'] = int(LAUNCH_BROWSER)
    new_config['General']['metadata_type'] = METADATA_TYPE
    new_config['General']['metadata_show'] = int(METADATA_SHOW)
    new_config['General']['metadata_episode'] = int(METADATA_EPISODE)
    new_config['General']['art_poster'] = int(ART_POSTER)
    new_config['General']['art_fanart'] = int(ART_FANART)
    new_config['General']['art_thumbnails'] = int(ART_THUMBNAILS)
    new_config['General']['art_season_thumbnails'] = int(ART_SEASON_THUMBNAILS)
    new_config['General']['cache_dir'] = CACHE_DIR
    new_config['General']['tv_download_dir'] = TV_DOWNLOAD_DIR
    new_config['General']['keep_processed_dir'] = int(KEEP_PROCESSED_DIR)
    new_config['General']['process_automatically'] = int(PROCESS_AUTOMATICALLY)
    new_config['General']['rename_episodes'] = int(RENAME_EPISODES)
    
    new_config['General']['extra_scripts'] = '|'.join(EXTRA_SCRIPTS)
    new_config['General']['git_path'] = GIT_PATH
    new_config['General']['web_host'] = WEB_HOST
    new_config['General']['web_root'] = WEB_ROOT

    new_config['Blackhole'] = {}
    new_config['Blackhole']['nzb_dir'] = NZB_DIR
    new_config['Blackhole']['torrent_dir'] = TORRENT_DIR

    new_config['TVBinz'] = {}
    new_config['TVBinz']['tvbinz'] = int(TVBINZ)
    new_config['TVBinz']['tvbinz_uid'] = TVBINZ_UID
    new_config['TVBinz']['tvbinz_hash'] = TVBINZ_HASH
    new_config['TVBinz']['tvbinz_auth'] = TVBINZ_AUTH

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

    new_config['Bin-Req'] = {}
    new_config['Bin-Req']['binreq'] = int(BINREQ)

    new_config['Womble'] = {}
    new_config['Womble']['womble'] = int(WOMBLE)

    new_config['SABnzbd'] = {}
    new_config['SABnzbd']['sab_username'] = SAB_USERNAME
    new_config['SABnzbd']['sab_password'] = SAB_PASSWORD
    new_config['SABnzbd']['sab_apikey'] = SAB_APIKEY
    new_config['SABnzbd']['sab_category'] = SAB_CATEGORY
    new_config['SABnzbd']['sab_host'] = SAB_HOST

    new_config['XBMC'] = {}
    new_config['XBMC']['xbmc_notify_onsnatch'] = int(XBMC_NOTIFY_ONSNATCH)
    new_config['XBMC']['xbmc_notify_ondownload'] = int(XBMC_NOTIFY_ONDOWNLOAD)
    new_config['XBMC']['xbmc_update_library'] = int(XBMC_UPDATE_LIBRARY)
    new_config['XBMC']['xbmc_update_full'] = int(XBMC_UPDATE_FULL)
    new_config['XBMC']['xbmc_host'] = XBMC_HOST
    new_config['XBMC']['xbmc_username'] = XBMC_USERNAME
    new_config['XBMC']['xbmc_password'] = XBMC_PASSWORD

    new_config['Growl'] = {}
    new_config['Growl']['use_growl'] = int(USE_GROWL)
    new_config['Growl']['growl_host'] = GROWL_HOST
    new_config['Growl']['growl_password'] = GROWL_PASSWORD

    new_config['Twitter'] = {}
    new_config['Twitter']['use_twitter'] = int(USE_TWITTER)
    new_config['Twitter']['twitter_username'] = TWITTER_USERNAME
    new_config['Twitter']['twitter_password'] = TWITTER_PASSWORD
    new_config['Twitter']['twitter_prefix'] = TWITTER_PREFIX

    new_config['Newznab'] = {}
    new_config['Newznab']['newznab_data'] = '!!!'.join([x.configStr() for x in newznabProviderList])

    new_config.write()


def launchBrowser():
    browserURL = 'http://localhost:%d%s' % (WEB_PORT, WEB_ROOT)
    try:
        webbrowser.open(browserURL, 2, 1)
    except:
        try:
            webbrowser.open(browserURL, 1, 1)
        except:
            logger.log(u"Unable to launch a browser", logger.ERROR)


def updateAiringList():

    logger.log(u"Searching DB and building list of airing episodes")

    curDate = datetime.date.today().toordinal()

    myDB = db.DBConnection()
    sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE status == ? AND airdate <= ?", [UNAIRED, curDate])

    epList = []

    for sqlEp in sqlResults:

        try:
            show = helpers.findCertainShow (sickbeard.showList, int(sqlEp["showid"]))
        except exceptions.MultipleShowObjectsException:
            logger.log(u"ERROR: expected to find a single show matching " + sqlEp["showid"])
            return None
        except exceptions.SickBeardException, e:
            logger.log(u"Unexpected exception: "+str(e).decode('utf-8'), logger.ERROR)
            continue

        # we aren't ever downloading specials
        if int(sqlEp["season"]) == 0:
            continue

        if show == None:
            continue

        ep = show.getEpisode(sqlEp["season"], sqlEp["episode"])

        if ep == None:
            logger.log(u"Somehow "+show.name+" - "+str(sqlEp["season"])+"x"+str(sqlEp["episode"])+" is None", logger.ERROR)
        else:
            epList.append(ep)

    sickbeard.airingList = epList

def updateComingList():

    epList = []

    for curShow in sickbeard.showList:

        curEps = None

        try:
            curEps = curShow.nextEpisode()
        except exceptions.NoNFOException, e:
            logger.log(u"Unable to retrieve episode from show: "+str(e).decode('utf-8'), logger.ERROR)

        for myEp in curEps:
            if myEp.season != 0:
                epList.append(myEp)

    sickbeard.comingList = epList

def getEpList(epIDs, showid=None):

    if epIDs == None or len(epIDs) == 0:
        return []

    query = "SELECT * FROM tv_episodes WHERE tvdbid in (%s)" % (",".join(["?" for x in epIDs]),)
    params = epIDs

    if showid != None:
        query += " AND showid = ?"
        params.append(showid)

    myDB = db.DBConnection()
    sqlResults = myDB.select(query, params)

    epList = []

    for curEp in sqlResults:
        curShowObj = helpers.findCertainShow(sickbeard.showList, int(curEp["showid"]))
        curEpObj = curShowObj.getEpisode(int(curEp["season"]), int(curEp["episode"]))
        epList.append(curEpObj)

    return epList
