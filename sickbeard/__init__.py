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



import cherrypy
import webbrowser
import sqlite3
import datetime
import socket

from threading import Lock

from sickbeard import searchCurrent, searchBacklog, updateShows, tvnzbbot, helpers, db, exceptions, showAdder, scheduler
from sickbeard.logging import *
from sickbeard.common import *

SOCKET_TIMEOUT = 30

CFG = None
PROG_DIR = None

LAST_TVDB_TIMEOUT = None

backlogSearchScheduler = None
currentSearchScheduler = None
updateScheduler = None
botRunner = None
showAddScheduler = None
showUpdateScheduler = None

ircBot = None

showList = None
loadingShowList = None

missingList = None
airingList = None
comingList = None

INIT_LOCK = Lock()
__INITIALIZED__ = False

LOG_DIR = None

WEB_PORT = None
WEB_LOG = None
WEB_USERNAME = None
WEB_PASSWORD = None 
LAUNCH_BROWSER = None
CREATE_METADATA = None

QUALITY_DEFAULT = None
SEASON_FOLDERS_DEFAULT = None

USE_NZB = False
NZB_METHOD = None 
NZB_DIR = None
USENET_RETENTION = None
SEARCH_FREQUENCY = None
BACKLOG_SEARCH_FREQUENCY = None
DEFAULT_SEARCH_FREQUENCY = 15
DEFAULT_BACKLOG_SEARCH_FREQUENCY = 7

USE_TORRENT = False
TORRENT_DIR = None

NEWZBIN = False
NEWZBIN_USERNAME = None
NEWZBIN_PASSWORD = None

TVBINZ = False
TVBINZ_UID = None
TVBINZ_HASH = None

NZBS = False
NZBS_UID = None
NZBS_HASH = None

NZBMATRIX = False
NZBMATRIX_USERNAME = None
NZBMATRIX_APIKEY = None

SAB_USERNAME = None
SAB_PASSWORD = None
SAB_APIKEY = None
SAB_CATEGORY = None
SAB_HOST = None

IRC_BOT = False
IRC_SERVER = None
IRC_CHANNEL = None
IRC_KEY = None
IRC_NICK = None

XBMC_NOTIFY_ONSNATCH = False
XBMC_NOTIFY_ONDOWNLOAD = False
XBMC_UPDATE_LIBRARY = False
XBMC_HOST = None

USE_GROWL = False
GROWL_HOST = None
GROWL_PASSWORD = None

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
    Logger().log(item_name + " -> " + str(my_val), DEBUG)
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

    Logger().log(item_name + " -> " + str(my_val), DEBUG)
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
        Logger().log(item_name + " -> " + my_val, DEBUG)
    else:
        Logger().log(item_name + " -> ******", DEBUG)
    return my_val


def initialize():
    
    with INIT_LOCK:
        
        global LOG_DIR, WEB_PORT, WEB_LOG, WEB_USERNAME, WEB_PASSWORD, NZB_METHOD, NZB_DIR, \
                NEWZBIN, NEWZBIN_USERNAME, NEWZBIN_PASSWORD, TVBINZ, TVBINZ_UID, TVBINZ_HASH, \
                SAB_USERNAME, SAB_PASSWORD, SAB_APIKEY, SAB_CATEGORY, SAB_HOST, IRC_BOT, IRC_SERVER, \
                IRC_CHANNEL, IRC_KEY, IRC_NICK, XBMC_NOTIFY_ONSNATCH, XBMC_NOTIFY_ONDOWNLOAD, \
                XBMC_UPDATE_LIBRARY, XBMC_HOST, currentSearchScheduler, backlogSearchScheduler, \
                updateScheduler, botRunner, __INITIALIZED__, LAUNCH_BROWSER, showList, missingList, \
                airingList, comingList, loadingShowList, CREATE_METADATA, SOCKET_TIMEOUT, showAddScheduler, \
                NZBS, NZBS_UID, NZBS_HASH, USE_NZB, USE_TORRENT, TORRENT_DIR, USENET_RETENTION, \
                SEARCH_FREQUENCY, DEFAULT_SEARCH_FREQUENCY, BACKLOG_SEARCH_FREQUENCY, \
                DEFAULT_BACKLOG_SEARCH_FREQUENCY, QUALITY_DEFAULT, SEASON_FOLDERS_DEFAULT, showUpdateScheduler, \
                USE_GROWL, GROWL_HOST, GROWL_PASSWORD, PROG_DIR, NZBMATRIX, NZBMATRIX_USERNAME, \
                NZBMATRIX_APIKEY 
        
        if __INITIALIZED__:
            return False
        
        socket.setdefaulttimeout(SOCKET_TIMEOUT)
        
        CheckSection('General')
        CheckSection('Blackhole')
        CheckSection('Newzbin')
        CheckSection('TVBinz')
        CheckSection('SABnzbd')
        CheckSection('IRC')
        CheckSection('XBMC')
        CheckSection('Growl')
        
        LOG_DIR = check_setting_str(CFG, 'General', 'log_dir', 'Logs')
        if not helpers.makeDir(LOG_DIR):
            Logger().log("!!! No log folder, logging to screen only!", ERROR)

        try:
            WEB_PORT = check_setting_int(CFG, 'General', 'web_port', 8081)
        except:
            WEB_PORT = 8081
        
        if WEB_PORT < 21 or WEB_PORT > 65535:
            WEB_PORT = 8081
        
        WEB_LOG = bool(check_setting_int(CFG, 'General', 'web_log', 0))
        WEB_USERNAME = check_setting_str(CFG, 'General', 'web_username', '')
        WEB_PASSWORD = check_setting_str(CFG, 'General', 'web_password', '')
        LAUNCH_BROWSER = bool(check_setting_int(CFG, 'General', 'launch_browser', 1))
        CREATE_METADATA = bool(check_setting_int(CFG, 'General', 'create_metadata', 1))
        
        QUALITY_DEFAULT = check_setting_int(CFG, 'General', 'quality_default', SD)
        SEASON_FOLDERS_DEFAULT = bool(check_setting_int(CFG, 'General', 'season_folders_default', 0))

        NZB_METHOD = check_setting_str(CFG, 'General', 'nzb_method', 'blackhole')
        if NZB_METHOD not in ('blackhole', 'sabnzbd'):
            NZB_METHOD = 'blackhole'
        
        USE_NZB = bool(check_setting_int(CFG, 'General', 'use_nzb', 1))
        USE_TORRENT = bool(check_setting_int(CFG, 'General', 'use_torrent', 0))
        USENET_RETENTION = check_setting_int(CFG, 'General', 'usenet_retention', 200)
        
        SEARCH_FREQUENCY = check_setting_int(CFG, 'General', 'search_frequency', DEFAULT_SEARCH_FREQUENCY)
        BACKLOG_SEARCH_FREQUENCY = check_setting_int(CFG, 'General', 'backlog_search_frequency', DEFAULT_BACKLOG_SEARCH_FREQUENCY)

        NZB_DIR = check_setting_str(CFG, 'Blackhole', 'nzb_dir', '')
        TORRENT_DIR = check_setting_str(CFG, 'Blackhole', 'torrent_dir', '')
        
        NEWZBIN = bool(check_setting_int(CFG, 'Newzbin', 'newzbin', 0))
        NEWZBIN_USERNAME = check_setting_str(CFG, 'Newzbin', 'newzbin_username', '')
        NEWZBIN_PASSWORD = check_setting_str(CFG, 'Newzbin', 'newzbin_password', '')
        
        TVBINZ = bool(check_setting_int(CFG, 'TVBinz', 'tvbinz', 0))
        TVBINZ_UID = check_setting_str(CFG, 'TVBinz', 'tvbinz_uid', '')
        TVBINZ_HASH = check_setting_str(CFG, 'TVBinz', 'tvbinz_hash', '')
        
        NZBS = bool(check_setting_int(CFG, 'NZBs', 'nzbs', 0))
        NZBS_UID = check_setting_str(CFG, 'NZBs', 'nzbs_uid', '')
        NZBS_HASH = check_setting_str(CFG, 'NZBs', 'nzbs_hash', '')
        
        NZBMATRIX = bool(check_setting_int(CFG, 'NZBMatrix', 'nzbmatrix', 0))
        NZBMATRIX_USERNAME = check_setting_str(CFG, 'NZBMatrix', 'nzbmatrix_username', '')
        NZBMATRIX_APIKEY = check_setting_str(CFG, 'NZBMatrix', 'nzbmatrix_apikey', '')
        
        SAB_USERNAME = check_setting_str(CFG, 'SABnzbd', 'sab_username', '')
        SAB_PASSWORD = check_setting_str(CFG, 'SABnzbd', 'sab_password', '')
        SAB_APIKEY = check_setting_str(CFG, 'SABnzbd', 'sab_apikey', '')
        SAB_CATEGORY = check_setting_str(CFG, 'SABnzbd', 'sab_category', '')
        SAB_HOST = check_setting_str(CFG, 'SABnzbd', 'sab_host', '')

        IRC_BOT = bool(check_setting_int(CFG, 'IRC', 'irc_bot', 0))
        IRC_SERVER = check_setting_str(CFG, 'IRC', 'irc_server', '')
        IRC_CHANNEL = check_setting_str(CFG, 'IRC', 'irc_channel', '')
        IRC_KEY = check_setting_str(CFG, 'IRC', 'irc_key', '')
        IRC_NICK = check_setting_str(CFG, 'IRC', 'irc_nick', '')
        
        XBMC_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'XBMC', 'xbmc_notify_onsnatch', 0))
        XBMC_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'XBMC', 'xbmc_notify_ondownload', 0))
        XBMC_UPDATE_LIBRARY = bool(check_setting_int(CFG, 'XBMC', 'xbmc_update_library', 0))
        XBMC_HOST = check_setting_str(CFG, 'XBMC', 'xbmc_host', '')
        
        USE_GROWL = bool(check_setting_int(CFG, 'Growl', 'use_growl', 0))
        GROWL_HOST = check_setting_str(CFG, 'Growl', 'growl_host', '')
        GROWL_PASSWORD = check_setting_str(CFG, 'Growl', 'growl_password', '')
        
        #currentSearchScheduler = searchCurrent.CurrentSearchScheduler(True)
        #backlogSearchScheduler = searchBacklog.BacklogSearchScheduler()
        #updateScheduler = updateShows.UpdateScheduler(True)
        
        currentSearchScheduler = scheduler.Scheduler(searchCurrent.CurrentSearcher(),
                                                     cycleTime=datetime.timedelta(minutes=SEARCH_FREQUENCY),
                                                     threadName="SEARCH",
                                                     runImmediately=False)
        
        backlogSearchScheduler = searchBacklog.BacklogSearchScheduler(searchBacklog.BacklogSearcher(),
                                                                      cycleTime=datetime.timedelta(hours=1),
                                                                      threadName="BACKLOG",
                                                                      runImmediately=False)
        backlogSearchScheduler.action.cycleTime = BACKLOG_SEARCH_FREQUENCY
        
        updateScheduler = scheduler.Scheduler(updateShows.ShowUpdater(),
                                              cycleTime=datetime.timedelta(hours=6),
                                              threadName="UPDATE",
                                              runImmediately=False)
        
        #botRunner = tvnzbbot.NZBBotRunner()

        showAddScheduler = scheduler.Scheduler(showAdder.ShowAddQueue(),
                                               cycleTime=datetime.timedelta(seconds=3),
                                               threadName="SHOWADDQUEUE",
                                               silent=True)
        
        showUpdateScheduler = scheduler.Scheduler(updateShows.ShowUpdateQueue(),
                                               cycleTime=datetime.timedelta(seconds=3),
                                               threadName="SHOWUPDATEQUEUE",
                                               silent=True)
        
        showList = []
        loadingShowList = {}
        
        missingList = []
        airingList = []
        comingList = []
        
        __INITIALIZED__ = True
        return True

def start():
    
    global __INITIALIZED__, currentSearchScheduler, backlogSearchScheduler, \
            updateScheduler, IRC_BOT, botRunner, showAddScheduler, showUpdateScheduler
    
    with INIT_LOCK:
        
        if __INITIALIZED__:
        
            # start the search scheduler
            currentSearchScheduler.thread.start()
        
            # start the search scheduler
            backlogSearchScheduler.thread.start()
        
            # start the search scheduler
            updateScheduler.thread.start()

            # start the show adder
            showAddScheduler.thread.start()

            # start the show adder
            showUpdateScheduler.thread.start()

            if IRC_BOT and False:
                botRunner.thread.start()


def halt ():
    
    global __INITIALIZED__, currentSearchScheduler, backlogSearchScheduler, updateScheduler, \
            botRunner, showAddScheduler, showUpdateScheduler
    
    with INIT_LOCK:
        
        if __INITIALIZED__:

            Logger().log("Aborting all threads")
            
            # abort all the threads

            currentSearchScheduler.abort = True
            Logger().log("Waiting for the SEARCH thread to exit")
            try:
                currentSearchScheduler.thread.join(10)
            except:
                pass
            
            backlogSearchScheduler.abort = True
            Logger().log("Waiting for the BACKLOG thread to exit")
            try:
                backlogSearchScheduler.thread.join(10)
            except:
                pass

            updateScheduler.abort = True
            Logger().log("Waiting for the UPDATE thread to exit")
            try:
                updateScheduler.thread.join(10)
            except:
                pass
            
            showAddScheduler.abort = True
            Logger().log("Waiting for the SHOWADDER thread to exit")
            try:
                showAddScheduler.thread.join(10)
            except:
                pass
            
            showUpdateScheduler.abort = True
            Logger().log("Waiting for the SHOWUPDATER thread to exit")
            try:
                showUpdateScheduler.thread.join(10)
            except:
                pass
            
            if False:
                botRunner.abort = True
                Logger().log("Waiting for the IRC thread to exit")
                try:
                    botRunner.thread.join(10)
                except:
                    pass

            __INITIALIZED__ = False


def sig_handler(signum=None, frame=None):
    if type(signum) != type(None):
        #logging.warning('[%s] Signal %s caught, saving and exiting...', __NAME__, signum)
        Logger().log("Signal {0} caught, saving and exiting...".format(signum))
        cherrypy.engine.exit()
        saveAndShutdown()
    

def saveAll():
    
    global showList
    
    # write all shows
    Logger().log("Saving all shows to the database")
    for show in showList:
        show.saveToDB()
    
    # save config
    Logger().log("Saving config file to disk")
    save_config()
    
    Logger().log("Shutting down logging")
    Logger().shutdown()
    

def saveAndShutdown():

    halt()

    saveAll()
    
    os._exit(0)



def save_config():
    global LOG_DIR, WEB_PORT, WEB_LOG, WEB_USERNAME, WEB_PASSWORD, NZB_METHOD, NZB_DIR, \
        NEWZBIN, NEWZBIN_USERNAME, NEWZBIN_PASSWORD, TVBINZ, TVBINZ_UID, TVBINZ_HASH, \
        SAB_USERNAME, SAB_PASSWORD, SAB_APIKEY, SAB_CATEGORY, SAB_HOST, IRC_BOT, IRC_SERVER, \
        IRC_CHANNEL, IRC_KEY, IRC_NICK, XBMC_NOTIFY_ONSNATCH, XBMC_NOTIFY_ONDOWNLOAD, \
        XBMC_UPDATE_LIBRARY, XBMC_HOST, CFG, LAUNCH_BROWSER, CREATE_METADATA, USE_NZB, \
        USE_TORRENT, TORRENT_DIR, USENET_RETENTION, SEARCH_FREQUENCY, BACKLOG_SEARCH_FREQUENCY, \
        QUALITY_DEFAULT, SEASON_FOLDERS_DEFAULT, USE_GROWL, GROWL_HOST, GROWL_PASSWORD, \
        NZBMATRIX, NZBMATRIX_USERNAME, NZBMATRIX_APIKEY
        
    CFG['General']['log_dir'] = LOG_DIR
    CFG['General']['web_port'] = WEB_PORT
    CFG['General']['web_log'] = int(WEB_LOG)
    CFG['General']['web_username'] = WEB_USERNAME
    CFG['General']['web_password'] = WEB_PASSWORD
    CFG['General']['nzb_method'] = NZB_METHOD
    CFG['General']['usenet_retention'] = int(USENET_RETENTION)
    CFG['General']['search_frequency'] = int(SEARCH_FREQUENCY)
    CFG['General']['backlog_search_frequency'] = int(BACKLOG_SEARCH_FREQUENCY)
    CFG['General']['use_nzb'] = int(USE_NZB)
    CFG['General']['quality_default'] = int(QUALITY_DEFAULT)
    CFG['General']['season_folders_default'] = int(SEASON_FOLDERS_DEFAULT)
    CFG['General']['use_torrent'] = int(USE_TORRENT)
    CFG['General']['launch_browser'] = int(LAUNCH_BROWSER)
    CFG['General']['create_metadata'] = int(CREATE_METADATA)
    CFG['Blackhole']['nzb_dir'] = NZB_DIR
    CFG['Blackhole']['torrent_dir'] = TORRENT_DIR
    CFG['Newzbin']['newzbin'] = int(NEWZBIN)
    CFG['Newzbin']['newzbin_username'] = NEWZBIN_USERNAME
    CFG['Newzbin']['newzbin_password'] = NEWZBIN_PASSWORD
    CFG['TVBinz']['tvbinz'] = int(TVBINZ)
    CFG['TVBinz']['tvbinz_uid'] = TVBINZ_UID
    CFG['TVBinz']['tvbinz_hash'] = TVBINZ_HASH
    CFG['NZBs']['nzbs'] = int(NZBS)
    CFG['NZBs']['nzbs_uid'] = NZBS_UID
    CFG['NZBs']['nzbs_hash'] = NZBS_HASH
    CFG['NZBMatrix']['nzbmatrix'] = int(NZBMATRIX)
    CFG['NZBMatrix']['nzbmatrix_username'] = NZBMATRIX_USERNAME
    CFG['NZBMatrix']['nzbmatrix_apikey'] = NZBMATRIX_APIKEY
    CFG['SABnzbd']['sab_username'] = SAB_USERNAME
    CFG['SABnzbd']['sab_password'] = SAB_PASSWORD
    CFG['SABnzbd']['sab_apikey'] = SAB_APIKEY
    CFG['SABnzbd']['sab_category'] = SAB_CATEGORY
    CFG['SABnzbd']['sab_host'] = SAB_HOST
    CFG['IRC']['irc_bot'] = int(IRC_BOT)
    CFG['IRC']['irc_server'] = IRC_SERVER
    CFG['IRC']['irc_channel'] = IRC_CHANNEL
    CFG['IRC']['irc_key'] = IRC_KEY
    CFG['IRC']['irc_nick'] = IRC_NICK
    CFG['XBMC']['xbmc_notify_onsnatch'] = int(XBMC_NOTIFY_ONSNATCH)
    CFG['XBMC']['xbmc_notify_ondownload'] = int(XBMC_NOTIFY_ONDOWNLOAD)
    CFG['XBMC']['xbmc_update_library'] = int(XBMC_UPDATE_LIBRARY)
    CFG['XBMC']['xbmc_host'] = XBMC_HOST
    CFG['Growl']['use_growl'] = int(USE_GROWL)
    CFG['Growl']['growl_host'] = GROWL_HOST
    CFG['Growl']['growl_password'] = GROWL_PASSWORD
    
    CFG.write()


def restart():
    
    sickbeard.halt()

    saveAll()
    
    INIT_OK = initialize()
    if INIT_OK:
        start()
    
def launchBrowser(browserURL):
    try:
        webbrowser.open(browserURL, 2, 1)
    except:
        try:
            webbrowser.open(browserURL, 1, 1)
        except:
            Logger().log("Unable to launch a browser", ERROR)


def updateMissingList():
    
    Logger().log("Searching DB and building list of MISSED episodes")
    
    myDB = db.DBConnection()
    sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE status=" + str(MISSED))
    
    epList = []

    for sqlEp in sqlResults:
        
        try:
            show = helpers.findCertainShow (sickbeard.showList, int(sqlEp["showid"]))
        except exceptions.MultipleShowObjectsException:
            Logger().log("ERROR: expected to find a single show matching " + sqlEp["showid"]) 
            return None
        
        # we aren't ever downloading specials
        if int(sqlEp["season"]) == 0:
            continue
        
        if show == None:
            continue
        
        ep = show.getEpisode(sqlEp["season"], sqlEp["episode"])
        
        if ep == None:
            Logger().log("Somehow "+show.name+" - "+str(sqlEp["season"])+"x"+str(sqlEp["episode"])+" is None", ERROR)
        else:
            epList.append(ep)

    sickbeard.missingList = epList


def updateAiringList():
    
    Logger().log("Searching DB and building list of airing episodes")
    
    curDate = datetime.date.today().toordinal()

    myDB = db.DBConnection()
    sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE status IN (" + str(UNKNOWN) + ", " + str(UNAIRED) + ", " + str(PREDOWNLOADED) + ") AND airdate <= " + str(curDate))
    
    epList = []

    for sqlEp in sqlResults:
        
        try:
            show = helpers.findCertainShow (sickbeard.showList, int(sqlEp["showid"]))
        except exceptions.MultipleShowObjectsException:
            Logger().log("ERROR: expected to find a single show matching " + sqlEp["showid"]) 
            return None
        except exceptions.SickBeardException as e:
            Logger().log("Unexpected exception: "+str(e), ERROR)
            continue

        # we aren't ever downloading specials
        if int(sqlEp["season"]) == 0:
            continue
        
        if show == None:
            continue
        
        ep = show.getEpisode(sqlEp["season"], sqlEp["episode"])
        
        if ep == None:
            Logger().log("Somehow "+show.name+" - "+str(sqlEp["season"])+"x"+str(sqlEp["episode"])+" is None", ERROR)
        else:
            epList.append(ep)

    sickbeard.airingList = epList

def updateComingList():

    epList = []
    
    for curShow in sickbeard.showList:

        curEps = None

        try:
            curEps = curShow.nextEpisode()
        except exceptions.NoNFOException as e:
            Logger().log("Unable to retrieve episode from show: "+str(e), ERROR)
        
        for myEp in curEps:
            if myEp.season != 0:
                epList.append(myEp)

    sickbeard.comingList = epList

def getEpList(epIDs, showid=None):
    
    if epIDs == None or len(epIDs) == 0:
        return []
    
    if showid != None:
        showStr = " AND showid = "+str(showid)
    else:
        showStr = ""
    
    myDB = db.DBConnection()
    sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE tvdbid in (" + ",".join([str(x) for x in epIDs]) + ")"+showStr)

    epList = []

    for curEp in sqlResults:
        curShowObj = helpers.findCertainShow(sickbeard.showList, int(curEp["showid"]))
        curEpObj = curShowObj.getEpisode(int(curEp["season"]), int(curEp["episode"]))
        epList.append(curEpObj)
    
    return epList  
