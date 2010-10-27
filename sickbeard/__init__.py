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
from sickbeard import providers 
from providers import eztv, nzbs_org, nzbmatrix, tvbinz, nzbsrus, binreq, newznab, womble

from sickbeard import searchCurrent, searchBacklog, showUpdater, versionChecker, properFinder, autoPostProcesser
from sickbeard import helpers, db, exceptions, queue, scheduler
from sickbeard import logger

from sickbeard.common import *

from sickbeard.databases import mainDB

SOCKET_TIMEOUT = 30

CFG = None

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
CREATE_METADATA = None
CREATE_IMAGES = None
CACHE_DIR = None

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

EXTRA_SCRIPTS = []

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


def initialize(consoleLogging=True):
    
    with INIT_LOCK:
        
        global LOG_DIR, WEB_PORT, WEB_LOG, WEB_ROOT, WEB_USERNAME, WEB_PASSWORD, WEB_HOST, \
                NZB_METHOD, NZB_DIR, TVBINZ, TVBINZ_UID, TVBINZ_HASH, DOWNLOAD_PROPERS, \
                SAB_USERNAME, SAB_PASSWORD, SAB_APIKEY, SAB_CATEGORY, SAB_HOST, \
                XBMC_NOTIFY_ONSNATCH, XBMC_NOTIFY_ONDOWNLOAD, XBMC_UPDATE_FULL, \
                XBMC_UPDATE_LIBRARY, XBMC_HOST, XBMC_USERNAME, XBMC_PASSWORD, currentSearchScheduler, backlogSearchScheduler, \
                showUpdateScheduler, __INITIALIZED__, LAUNCH_BROWSER, showList, \
                airingList, comingList, loadingShowList, CREATE_METADATA, SOCKET_TIMEOUT, \
                NZBS, NZBS_UID, NZBS_HASH, USE_NZB, USE_TORRENT, TORRENT_DIR, USENET_RETENTION, \
                SEARCH_FREQUENCY, DEFAULT_SEARCH_FREQUENCY, BACKLOG_SEARCH_FREQUENCY, \
                DEFAULT_BACKLOG_SEARCH_FREQUENCY, QUALITY_DEFAULT, SEASON_FOLDERS_DEFAULT, \
		USE_GROWL, GROWL_HOST, GROWL_PASSWORD, PROG_DIR, NZBMATRIX, NZBMATRIX_USERNAME, \
                NZBMATRIX_APIKEY, versionCheckScheduler, VERSION_NOTIFY, PROCESS_AUTOMATICALLY, \
                KEEP_PROCESSED_DIR, TV_DOWNLOAD_DIR, TVDB_BASE_URL, MIN_SEARCH_FREQUENCY, \
                MIN_BACKLOG_SEARCH_FREQUENCY, TVBINZ_AUTH, showQueueScheduler, \
                NAMING_SHOW_NAME, NAMING_EP_TYPE, NAMING_MULTI_EP_TYPE, CACHE_DIR, TVDB_API_PARMS, \
                RENAME_EPISODES, properFinderScheduler, PROVIDER_ORDER, autoPostProcesserScheduler, \
                CREATE_IMAGES, NAMING_EP_NAME, NAMING_SEP_TYPE, NAMING_USE_PERIODS, WOMBLE, \
                NZBSRUS, NZBSRUS_UID, NZBSRUS_HASH, BINREQ, NAMING_QUALITY, providerList, newznabProviderList, \
                NAMING_DATES, EXTRA_SCRIPTS, USE_TWITTER, TWITTER_USERNAME, TWITTER_PASSWORD

        
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
            logger.log("!!! No log folder, logging to screen only!", logger.ERROR)

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
        CREATE_METADATA = bool(check_setting_int(CFG, 'General', 'create_metadata', 1))
        CREATE_IMAGES = bool(check_setting_int(CFG, 'General', 'create_images', 1))

        CACHE_DIR = check_setting_str(CFG, 'General', 'cache_dir', 'cache')
        if not helpers.makeDir(CACHE_DIR):
            logger.log("!!! Creating local cache dir failed, using system default", logger.ERROR)
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

        EXTRA_SCRIPTS = [x for x in check_setting_str(CFG, 'General', 'extra_scripts', '').split('|') if x]

        newznabData = check_setting_str(CFG, 'Newznab', 'newznab_data', '')
        newznabProviderList = providers.getNewznabProviderList(newznabData)
        
        providerList = providers.makeProviderList()
        
        logger.initLogging(consoleLogging=consoleLogging)

        # initialize the main SB database
        db.upgradeDatabase(db.DBConnection(), mainDB.InitialSchema)

        currentSearchScheduler = scheduler.Scheduler(searchCurrent.CurrentSearcher(),
                                                     cycleTime=datetime.timedelta(minutes=SEARCH_FREQUENCY),
                                                     threadName="SEARCH",
                                                     runImmediately=True)
        
        backlogSearchScheduler = searchBacklog.BacklogSearchScheduler(searchBacklog.BacklogSearcher(),
                                                                      cycleTime=datetime.timedelta(minutes=67),
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

            logger.log("Aborting all threads")
            
            # abort all the threads

            currentSearchScheduler.abort = True
            logger.log("Waiting for the SEARCH thread to exit")
            try:
                currentSearchScheduler.thread.join(10)
            except:
                pass
            
            backlogSearchScheduler.abort = True
            logger.log("Waiting for the BACKLOG thread to exit")
            try:
                backlogSearchScheduler.thread.join(10)
            except:
                pass

            showUpdateScheduler.abort = True
            logger.log("Waiting for the SHOWUPDATER thread to exit")
            try:
                showUpdateScheduler.thread.join(10)
            except:
                pass
            
            versionCheckScheduler.abort = True
            logger.log("Waiting for the VERSIONCHECKER thread to exit")
            try:
                versionCheckScheduler.thread.join(10)
            except:
                pass
            
            showQueueScheduler.abort = True
            logger.log("Waiting for the SHOWQUEUE thread to exit")
            try:
                showQueueScheduler.thread.join(10)
            except:
                pass
            
            autoPostProcesserScheduler.abort = True
            logger.log("Waiting for the POSTPROCESSER thread to exit")
            try:
                autoPostProcesserScheduler.thread.join(10)
            except:
                pass
            
            properFinderScheduler.abort = True
            logger.log("Waiting for the PROPERFINDER thread to exit")
            try:
                properFinderScheduler.thread.join(10)
            except:
                pass
            
            
            __INITIALIZED__ = False


def sig_handler(signum=None, frame=None):
    if type(signum) != type(None):
        logger.log("Signal %i caught, saving and exiting..." % int(signum))
        cherrypy.engine.exit()
        saveAndShutdown()
    

def saveAll():
    
    global showList
    
    # write all shows
    logger.log("Saving all shows to the database")
    for show in showList:
        show.saveToDB()
    
    # save config
    logger.log("Saving config file to disk")
    save_config()
    

def saveAndShutdown(restart=False):

    logger.log("Killing cherrypy")
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
                logger.log("Unknown SB launch method, please file a bug report about this", logger.ERROR)
                popen_list = [sys.executable, os.path.join(sickbeard.PROG_DIR, 'updater.py'), str(os.getpid()), sys.executable, sickbeard.MY_FULLNAME ]

        if popen_list:
            popen_list += sickbeard.MY_ARGS
            logger.log("Restarting Sick Beard with " + str(popen_list))
            subprocess.Popen(popen_list, cwd=os.getcwd())
    
    os._exit(0)


def restart(soft=True):
    
    if soft:
        halt()
        saveAll()
        #logger.log("Restarting cherrypy")
        #cherrypy.engine.restart()
        logger.log("Re-initializing all data")
        initialize()
    
    else:
        saveAndShutdown(restart=True)



def save_config():
        
    CFG['General']['log_dir'] = LOG_DIR
    CFG['General']['web_port'] = WEB_PORT
    CFG['General']['web_host'] = WEB_HOST
    CFG['General']['web_log'] = int(WEB_LOG)
    CFG['General']['web_root'] = WEB_ROOT
    CFG['General']['web_username'] = WEB_USERNAME
    CFG['General']['web_password'] = WEB_PASSWORD
    CFG['General']['nzb_method'] = NZB_METHOD
    CFG['General']['usenet_retention'] = int(USENET_RETENTION)
    CFG['General']['search_frequency'] = int(SEARCH_FREQUENCY)
    CFG['General']['backlog_search_frequency'] = int(BACKLOG_SEARCH_FREQUENCY)
    CFG['General']['use_nzb'] = int(USE_NZB)
    CFG['General']['download_propers'] = int(DOWNLOAD_PROPERS)
    CFG['General']['quality_default'] = int(QUALITY_DEFAULT)
    CFG['General']['season_folders_default'] = int(SEASON_FOLDERS_DEFAULT)
    CFG['General']['provider_order'] = ' '.join([x.getID() for x in providers.sortedProviderList()])
    CFG['General']['version_notify'] = int(VERSION_NOTIFY)
    CFG['General']['naming_ep_name'] = int(NAMING_EP_NAME)
    CFG['General']['naming_show_name'] = int(NAMING_SHOW_NAME)
    CFG['General']['naming_ep_type'] = int(NAMING_EP_TYPE)
    CFG['General']['naming_multi_ep_type'] = int(NAMING_MULTI_EP_TYPE)
    CFG['General']['naming_sep_type'] = int(NAMING_SEP_TYPE)
    CFG['General']['naming_use_periods'] = int(NAMING_USE_PERIODS)
    CFG['General']['naming_quality'] = int(NAMING_QUALITY)
    CFG['General']['naming_dates'] = int(NAMING_DATES)
    CFG['General']['use_torrent'] = int(USE_TORRENT)
    CFG['General']['launch_browser'] = int(LAUNCH_BROWSER)
    CFG['General']['create_metadata'] = int(CREATE_METADATA)
    CFG['General']['create_images'] = int(CREATE_IMAGES)
    CFG['General']['cache_dir'] = CACHE_DIR
    CFG['General']['tv_download_dir'] = TV_DOWNLOAD_DIR
    CFG['General']['keep_processed_dir'] = int(KEEP_PROCESSED_DIR)
    CFG['General']['process_automatically'] = int(PROCESS_AUTOMATICALLY)
    CFG['General']['rename_episodes'] = int(RENAME_EPISODES)
    CFG['Blackhole']['nzb_dir'] = NZB_DIR
    CFG['Blackhole']['torrent_dir'] = TORRENT_DIR
    CFG['TVBinz']['tvbinz'] = int(TVBINZ)
    CFG['TVBinz']['tvbinz_uid'] = TVBINZ_UID
    CFG['TVBinz']['tvbinz_hash'] = TVBINZ_HASH
    CFG['TVBinz']['tvbinz_auth'] = TVBINZ_AUTH
    CFG['NZBs']['nzbs'] = int(NZBS)
    CFG['NZBs']['nzbs_uid'] = NZBS_UID
    CFG['NZBs']['nzbs_hash'] = NZBS_HASH
    CFG['NZBsRUS']['nzbsrus'] = int(NZBSRUS)
    CFG['NZBsRUS']['nzbsrus_uid'] = NZBSRUS_UID
    CFG['NZBsRUS']['nzbsrus_hash'] = NZBSRUS_HASH
    CFG['NZBMatrix']['nzbmatrix'] = int(NZBMATRIX)
    CFG['NZBMatrix']['nzbmatrix_username'] = NZBMATRIX_USERNAME
    CFG['NZBMatrix']['nzbmatrix_apikey'] = NZBMATRIX_APIKEY
    CFG['Bin-Req']['binreq'] = int(BINREQ)
    CFG['Womble']['womble'] = int(WOMBLE)
    CFG['SABnzbd']['sab_username'] = SAB_USERNAME
    CFG['SABnzbd']['sab_password'] = SAB_PASSWORD
    CFG['SABnzbd']['sab_apikey'] = SAB_APIKEY
    CFG['SABnzbd']['sab_category'] = SAB_CATEGORY
    CFG['SABnzbd']['sab_host'] = SAB_HOST
    CFG['XBMC']['xbmc_notify_onsnatch'] = int(XBMC_NOTIFY_ONSNATCH)
    CFG['XBMC']['xbmc_notify_ondownload'] = int(XBMC_NOTIFY_ONDOWNLOAD)
    CFG['XBMC']['xbmc_update_library'] = int(XBMC_UPDATE_LIBRARY)
    CFG['XBMC']['xbmc_update_full'] = int(XBMC_UPDATE_FULL)
    CFG['XBMC']['xbmc_host'] = XBMC_HOST
    CFG['XBMC']['xbmc_username'] = XBMC_USERNAME
    CFG['XBMC']['xbmc_password'] = XBMC_PASSWORD
    CFG['Growl']['use_growl'] = int(USE_GROWL)
    CFG['Growl']['growl_host'] = GROWL_HOST
    CFG['Growl']['growl_password'] = GROWL_PASSWORD
    CFG['Twitter']['use_twitter'] = int(USE_TWITTER)
    CFG['Twitter']['twitter_username'] = TWITTER_USERNAME
    CFG['Twitter']['twitter_password'] = TWITTER_PASSWORD
 
    CFG['Newznab']['newznab_data'] = '!!!'.join([x.configStr() for x in newznabProviderList])
    
    CFG.write()


def launchBrowser():
    browserURL = 'http://localhost:%d%s' % (WEB_PORT, WEB_ROOT)
    try:
        webbrowser.open(browserURL, 2, 1)
    except:
        try:
            webbrowser.open(browserURL, 1, 1)
        except:
            logger.log("Unable to launch a browser", logger.ERROR)


def updateAiringList():
    
    logger.log("Searching DB and building list of airing episodes")
    
    curDate = datetime.date.today().toordinal()

    myDB = db.DBConnection()
    sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE status == ? AND airdate <= ?", [UNAIRED, curDate])
    
    epList = []

    for sqlEp in sqlResults:
        
        try:
            show = helpers.findCertainShow (sickbeard.showList, int(sqlEp["showid"]))
        except exceptions.MultipleShowObjectsException:
            logger.log("ERROR: expected to find a single show matching " + sqlEp["showid"]) 
            return None
        except exceptions.SickBeardException, e:
            logger.log("Unexpected exception: "+str(e), logger.ERROR)
            continue

        # we aren't ever downloading specials
        if int(sqlEp["season"]) == 0:
            continue
        
        if show == None:
            continue
        
        ep = show.getEpisode(sqlEp["season"], sqlEp["episode"])
        
        if ep == None:
            logger.log("Somehow "+show.name+" - "+str(sqlEp["season"])+"x"+str(sqlEp["episode"])+" is None", logger.ERROR)
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
            logger.log("Unable to retrieve episode from show: "+str(e), logger.ERROR)
        
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
