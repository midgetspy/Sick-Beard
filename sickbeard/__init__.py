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

from sickbeard import searchCurrent, searchBacklog, updateShows, tvnzbbot, helpers, db, exceptions, showAdder
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

ircBot = None

showList = None
loadingShowList = None

missingList = None
airingList = None
comingList = None

INIT_LOCK = Lock()
__INITIALIZED__ = False

LOG_DIR = None
NZB_METHOD = None 

WEB_PORT = None
WEB_LOG = None
WEB_USERNAME = None
WEB_PASSWORD = None 
LAUNCH_BROWSER = None
CREATE_METADATA = None

NZB_DIR = None

NEWZBIN = False
NEWZBIN_USERNAME = None
NEWZBIN_PASSWORD = None

TVBINZ = False
TVBINZ_UID = None
TVBINZ_HASH = None

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
                airingList, comingList, loadingShowList, CREATE_METADATA, SOCKET_TIMEOUT, showAddScheduler
        
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
        
        LOG_DIR = check_setting_str(CFG, 'General', 'log_dir', '')
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
        
        NZB_METHOD = check_setting_str(CFG, 'General', 'nzb_method', 'blackhole')
        if NZB_METHOD not in ('blackhole', 'sabnzbd'):
            NZB_METHOD = 'blackhole'
        
        NZB_DIR = check_setting_str(CFG, 'Blackhole', 'nzb_dir', '')
        
        NEWZBIN = bool(check_setting_int(CFG, 'Newzbin', 'newzbin', 0))
        NEWZBIN_USERNAME = check_setting_str(CFG, 'Newzbin', 'newzbin_username', '')
        NEWZBIN_PASSWORD = check_setting_str(CFG, 'Newzbin', 'newzbin_password', '')
        
        TVBINZ = bool(check_setting_int(CFG, 'TVBinz', 'tvbinz', 0))
        TVBINZ_UID = check_setting_str(CFG, 'TVBinz', 'tvbinz_uid', '')
        TVBINZ_HASH = check_setting_str(CFG, 'TVBinz', 'tvbinz_hash', '')
        
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
        
        currentSearchScheduler = searchCurrent.CurrentSearchScheduler(True)
        backlogSearchScheduler = searchBacklog.BacklogSearchScheduler()
        updateScheduler = updateShows.UpdateScheduler(True)
        botRunner = tvnzbbot.NZBBotRunner()
        showAddScheduler = showAdder.ShowAddScheduler()
        
        showList = []
        loadingShowList = {}
        
        missingList = []
        airingList = []
        comingList = []
        
        __INITIALIZED__ = True
        return True

def start():
    
    global __INITIALIZED__, currentSearchScheduler, backlogSearchScheduler, \
            updateScheduler, IRC_BOT, botRunner, showAddScheduler
    
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

            if IRC_BOT:
                botRunner.thread.start()


def halt ():
    
    global __INITIALIZED__, currentSearchScheduler, backlogSearchScheduler, updateScheduler, \
            botRunner, showAddScheduler
    
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
        XBMC_UPDATE_LIBRARY, XBMC_HOST, CFG, LAUNCH_BROWSER, CREATE_METADATA
        
    CFG['General']['log_dir'] = LOG_DIR
    CFG['General']['web_port'] = WEB_PORT
    CFG['General']['web_log'] = int(WEB_LOG)
    CFG['General']['web_username'] = WEB_USERNAME
    CFG['General']['web_password'] = WEB_PASSWORD
    CFG['General']['nzb_method'] = NZB_METHOD
    CFG['General']['launch_browser'] = int(LAUNCH_BROWSER)
    CFG['General']['create_metadata'] = int(CREATE_METADATA)
    CFG['Blackhole']['nzb_dir'] = NZB_DIR
    CFG['Newzbin']['newzbin'] = int(NEWZBIN)
    CFG['Newzbin']['newzbin_username'] = NEWZBIN_USERNAME
    CFG['Newzbin']['newzbin_password'] = NEWZBIN_PASSWORD
    CFG['TVBinz']['tvbinz'] = int(TVBINZ)
    CFG['TVBinz']['tvbinz_uid'] = TVBINZ_UID
    CFG['TVBinz']['tvbinz_hash'] = TVBINZ_HASH
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
    
    myDB = db.DBConnection()
    myDB.checkDB()

    Logger().log("Searching DB and building list of MISSED episodes")
    
    try:
        sql = "SELECT * FROM tv_episodes WHERE status=" + str(MISSED)
        Logger().log("SQL: " + sql, DEBUG)
        sqlResults = myDB.connection.execute(sql).fetchall()
    except sqlite3.DatabaseError as e:
        Logger().log("Fatal error executing query '" + sql + "': " + str(e), ERROR)
        raise

    epList = []

    for sqlEp in sqlResults:
        
        try:
            show = helpers.findCertainShow (sickbeard.showList, int(sqlEp["showid"]))
        except exceptions.MultipleShowObjectsException:
            Logger().log("ERROR: expected to find a single show matching " + sqlEp["showid"]) 
            return None
        ep = show.getEpisode(sqlEp["season"], sqlEp["episode"], True)

        epList.append(ep)

    sickbeard.missingList = epList


def updateAiringList():
    
    myDB = db.DBConnection()
    myDB.checkDB()

    curDate = datetime.date.today().toordinal()

    Logger().log("Searching DB and building list of airing episodes")
    
    try:
        sql = "SELECT * FROM tv_episodes WHERE status IN (" + str(UNKNOWN) + ", " + str(UNAIRED) + ", " + str(PREDOWNLOADED) + ", " + str(MISSED) + ") AND airdate <= " + str(curDate)
        Logger().log("SQL: " + sql, DEBUG)
        sqlResults = myDB.connection.execute(sql).fetchall()
    except sqlite3.DatabaseError as e:
        Logger().log("Fatal error executing query '" + sql + "': " + str(e), ERROR)
        raise

    epList = []

    for sqlEp in sqlResults:
        
        try:
            show = helpers.findCertainShow (sickbeard.showList, int(sqlEp["showid"]))
        except exceptions.MultipleShowObjectsException:
            Logger().log("ERROR: expected to find a single show matching " + sqlEp["showid"]) 
            return None
        ep = show.getEpisode(sqlEp["season"], sqlEp["episode"], True)

        epList.append(ep)

    sickbeard.airingList = epList

def updateComingList():

    epList = []
    
    for curShow in sickbeard.showList:

        curEp = None

        try:
            curEp = curShow.nextEpisode()
        except exceptions.NoNFOException as e:
            Logger().log("Unable to retrieve episode from show: "+str(e), ERROR)
        
        if curEp != None:
            epList.append(curEp)

    sickbeard.comingList = epList

def getEpList(epIDs, showid=None):
    
    if epIDs == None or len(epIDs) == 0:
        return []
    
    myDB = db.DBConnection()
    myDB.checkDB()
        
    sqlResults = []
    
    try:
        sql = "SELECT * FROM tv_episodes WHERE tvdbid in (" + ",".join([str(x) for x in epIDs]) + ")"
        if showid != None:
            sql += " AND showid = " + str(showid)
        Logger().log("SQL: " + sql, DEBUG)
        sqlResults = myDB.connection.execute(sql).fetchall()
    except sqlite3.DatabaseError as e:
        Logger().log("Fatal error executing query '" + sql + "': " + str(e), ERROR)
        raise

    epList = []

    for curEp in sqlResults:
        curShowObj = helpers.findCertainShow(sickbeard.showList, int(curEp["showid"]))
        curEpObj = curShowObj.getEpisode(int(curEp["season"]), int(curEp["episode"]), True)
        epList.append(curEpObj)
    
    return epList  
