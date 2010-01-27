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

import gc
import cgi
import sqlite3
import time

from Cheetah.Template import Template
import cherrypy

from sickbeard import config
from sickbeard import db
from sickbeard import history
from sickbeard import notifiers
from sickbeard import processTV
from sickbeard import search
from sickbeard import ui

from sickbeard.notifiers import xbmc
from sickbeard.tv import *

from lib.tvdb_api import tvdb_exceptions

import sickbeard
import sickbeard.helpers


class TVDBWebUI:
    def __init__(self, config, log):
        self.config = config
        self.log = log

    def selectSeries(self, allSeries):
        
        searchList = ",".join([x['sid'] for x in allSeries])
        showDirList = ""
        for curShowDir in self.config['_showDir']:
            showDirList += "showDir="+curShowDir+"&"
        raise cherrypy.HTTPRedirect("addShow?" + showDirList + "seriesList=" + searchList)

def _munge(string):
    return unicode(string).encode('ascii', 'xmlcharrefreplace')

def _genericMessage(subject, message):
    t = Template(file=os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/genericMessage.tmpl"))
    t.subject = subject
    t.message = message
    return _munge(t)

def _getEpisode(show, season, episode):

    if show == None or season == None or episode == None:
        return "Invalid parameters"
    
    showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

    if showObj == None:
        return "Show not in show list"

    epObj = showObj.getEpisode(int(season), int(episode))
    
    if epObj == None:
        return "Episode couldn't be retrieved"

    return epObj


class Backlog:

    @cherrypy.expose
    def index(self):
        
        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT e.*, show_name FROM tv_shows s, tv_episodes e WHERE s.tvdb_id=e.showid AND e.status IN ("+str(BACKLOG)+","+str(DISCBACKLOG)+")")
        
        t = Template(file=os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/backlog.tmpl"))
        t.backlogResults = sqlResults
        
        return _munge(t)


    @cherrypy.expose
    def forceBacklog(self):

        # force it to run the next time it looks
        sickbeard.backlogSearchScheduler.forceSearch()
        logger.log("Backlog set to run in background")
        
        return _genericMessage("Backlog search started", "The backlog search has begun and will run in the background")



class History:
    
    @cherrypy.expose
    def index(self):

        myDB = db.DBConnection()
        
#        sqlResults = myDB.select("SELECT h.*, show_name, name FROM history h, tv_shows s, tv_episodes e WHERE h.showid=s.tvdb_id AND h.showid=e.showid AND h.season=e.season AND h.episode=e.episode ORDER BY date DESC LIMIT "+str(numPerPage*(p-1))+", "+str(numPerPage))
        sqlResults = myDB.select("SELECT h.*, show_name FROM history h, tv_shows s WHERE h.showid=s.tvdb_id ORDER BY date DESC")

        t = Template(file=os.path.join(sickbeard.PROG_DIR, os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/history.tmpl")))
        t.historyResults = sqlResults
        
        return _munge(t)


    @cherrypy.expose
    def clearHistory(self):
        
        myDB = db.DBConnection()
        myDB.action("DELETE FROM history WHERE 1=1")
        
        raise cherrypy.HTTPRedirect("../history")


    @cherrypy.expose
    def trimHistory(self):
        
        myDB = db.DBConnection()
        myDB.action("DELETE FROM history WHERE date < "+str((datetime.datetime.today()-datetime.timedelta(days=30)).strftime(history.dateFormat)))
        
        raise cherrypy.HTTPRedirect("../history")




class ConfigGeneral:
    
    @cherrypy.expose
    def index(self):
        
        t = Template(file=os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/config_general.tmpl"))
        return _munge(t)

    @cherrypy.expose
    def saveGeneral(self, log_dir=None, web_port=None, web_log=None,
                    launch_browser=None, create_metadata=None, web_username=None,
                    web_password=None, quality_default=None, season_folders_default=None,
                    version_notify=None):

        results = []

        if web_log == "on":
            web_log = 1
        else:
            web_log = 0
            
        if launch_browser == "on":
            launch_browser = 1
        else:
            launch_browser = 0
            
        if create_metadata == "on":
            create_metadata = 1
        else:
            create_metadata = 0
            
        if season_folders_default == "on":
            season_folders_default = 1
        else:
            season_folders_default = 0
            
        if version_notify == "on":
            version_notify = 1
        else:
            version_notify = 0
            
        if not config.change_LOG_DIR(log_dir):
            results += ["Unable to create directory " + os.path.normpath(log_dir) + ", log dir not changed."]
        
        sickbeard.LAUNCH_BROWSER = launch_browser
        sickbeard.CREATE_METADATA = create_metadata
        sickbeard.SEASON_FOLDERS_DEFAULT = int(season_folders_default)
        sickbeard.QUALITY_DEFAULT = int(quality_default)

        sickbeard.WEB_PORT = int(web_port)
        sickbeard.WEB_LOG = web_log
        sickbeard.WEB_USERNAME = web_username
        sickbeard.WEB_PASSWORD = web_password

        config.change_VERSION_NOTIFY(version_notify)

        sickbeard.save_config()
        
        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            return _genericMessage("Error", "<br />\n".join(results))
        
        raise cherrypy.HTTPRedirect("index")

class ConfigEpisodeDownloads:
    
    @cherrypy.expose
    def index(self):
        
        t = Template(file=os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/config_episodedownloads.tmpl"))
        return _munge(t)

    @cherrypy.expose
    def saveEpisodeDownloads(self, nzb_dir=None, sab_username=None, sab_password=None,
                       sab_apikey=None, sab_category=None, sab_host=None, use_nzb=None,
                       use_torrent=None, torrent_dir=None, nzb_method=None, usenet_retention=None,
                       search_frequency=None, backlog_search_frequency=None, tv_download_dir=None,
                       keep_processed_dir=None, process_automatically=None):

        results = []

        if not config.change_TV_DOWNLOAD_DIR(tv_download_dir):
            results += ["Unable to create directory " + os.path.normpath(tv_download_dir) + ", dir not changed."]

        if not config.change_NZB_DIR(nzb_dir):
            results += ["Unable to create directory " + os.path.normpath(nzb_dir) + ", dir not changed."]

        if not config.change_TORRENT_DIR(torrent_dir):
            results += ["Unable to create directory " + os.path.normpath(torrent_dir) + ", dir not changed."]

        config.change_SEARCH_FREQUENCY(search_frequency)

        config.change_BACKLOG_SEARCH_FREQUENCY(backlog_search_frequency)

        if process_automatically == "on":
            process_automatically = 1
        else:
            process_automatically = 0
            
        if keep_processed_dir == "on":
            keep_processed_dir = 1
        else:
            keep_processed_dir = 0
            
        if use_nzb == "on":
            use_nzb = 1
        else:
            use_nzb = 0
            
        if use_torrent == "on":
            use_torrent = 1
        else:
            use_torrent = 0

        if usenet_retention == None:
            usenet_retention = 200

        sickbeard.PROCESS_AUTOMATICALLY = process_automatically
        sickbeard.KEEP_PROCESSED_DIR = keep_processed_dir

        sickbeard.NZB_METHOD = nzb_method
        sickbeard.USENET_RETENTION = int(usenet_retention)
        sickbeard.SEARCH_FREQUENCY = int(search_frequency)

        sickbeard.USE_NZB = use_nzb
        sickbeard.USE_TORRENT = use_torrent

        sickbeard.SAB_USERNAME = sab_username
        sickbeard.SAB_PASSWORD = sab_password
        sickbeard.SAB_APIKEY = sab_apikey
        sickbeard.SAB_CATEGORY = sab_category
        sickbeard.SAB_HOST = sab_host
        
        sickbeard.save_config()
        
        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            return _genericMessage("Error", "<br />\n".join(results))
        
        raise cherrypy.HTTPRedirect("index")

class ConfigProviders:
    
    @cherrypy.expose
    def index(self):
        t = Template(file=os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/config_providers.tmpl"))
        return _munge(t)

    
    @cherrypy.expose
    def saveProviders(self, newzbin=None, newzbin_username=None, newzbin_password=None, tvbinz=None,
                   tvbinz_uid=None, tvbinz_hash=None, nzbs=None, nzbs_uid=None, nzbs_hash=None,
                   nzbmatrix=None, nzbmatrix_username=None, nzbmatrix_apikey=None):

        results = []

        if newzbin == "on":
            newzbin = 1
        else:
            newzbin = 0
            
        if tvbinz == "on":
            tvbinz = 1
        else:
            tvbinz = 0
            
        if nzbs == "on":
            nzbs = 1
        else:
            nzbs = 0

        if nzbmatrix == "on":
            nzbmatrix = 1
        else:
            nzbmatrix = 0

        sickbeard.NEWZBIN = newzbin
        sickbeard.NEWZBIN_USERNAME = newzbin_username
        sickbeard.NEWZBIN_PASSWORD = newzbin_password
        
        sickbeard.TVBINZ = tvbinz
        sickbeard.TVBINZ_UID = tvbinz_uid
        sickbeard.TVBINZ_HASH = tvbinz_hash
        
        sickbeard.NZBS = nzbs
        sickbeard.NZBS_UID = nzbs_uid
        sickbeard.NZBS_HASH = nzbs_hash
        
        sickbeard.NZBMATRIX = nzbmatrix
        sickbeard.NZBMATRIX_USERNAME = nzbmatrix_username
        sickbeard.NZBMATRIX_APIKEY = nzbmatrix_apikey
        
        sickbeard.save_config()
        
        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            return _genericMessage("Error", "<br />\n".join(results))
        
        raise cherrypy.HTTPRedirect("index")

class ConfigIRC:
    
    @cherrypy.expose
    def index(self):
        t = Template(file=os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/config_irc.tmpl"))
        return _munge(t)

    @cherrypy.expose
    def saveIRC(self, irc_bot=None, irc_server=None, irc_channel=None, irc_key=None, irc_nick=None):

        results = []

        if irc_bot == "on":
            irc_bot = 1
        else:
            irc_bot = 0

        config.change_IRC_BOT(irc_bot)
        config.change_IRC_SERVER(irc_server)
        config.change_IRC_CHANNEL(irc_channel, irc_key)
        config.change_IRC_NICK(irc_nick)
        
        sickbeard.save_config()
        
        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            return _genericMessage("Error", "<br />\n".join(results))
        
        raise cherrypy.HTTPRedirect("index")

class ConfigNotifications:
    
    @cherrypy.expose
    def index(self):
        t = Template(file=os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/config_notifications.tmpl"))
        return _munge(t)
    
    @cherrypy.expose
    def saveNotifications(self, xbmc_notify_onsnatch=None, xbmc_notify_ondownload=None, 
                          xbmc_update_library=None, xbmc_host=None, xbmc_username=None, xbmc_password=None, use_growl=None,
                          growl_host=None, growl_password=None, ):

        results = []

        if xbmc_notify_onsnatch == "on":
            xbmc_notify_onsnatch = 1
        else:
            xbmc_notify_onsnatch = 0
            
        if xbmc_notify_ondownload == "on":
            xbmc_notify_ondownload = 1
        else:
            xbmc_notify_ondownload = 0
            
        if xbmc_update_library == "on":
            xbmc_update_library = 1
        else:
            xbmc_update_library = 0

        if use_growl == "on":
            use_growl = 1
        else:
            use_growl = 0

        sickbeard.XBMC_NOTIFY_ONSNATCH = xbmc_notify_onsnatch 
        sickbeard.XBMC_NOTIFY_ONDOWNLOAD = xbmc_notify_ondownload
        sickbeard.XBMC_UPDATE_LIBRARY = xbmc_update_library
        sickbeard.XBMC_HOST = xbmc_host
        sickbeard.XBMC_USERNAME = xbmc_username
        sickbeard.XBMC_PASSWORD = xbmc_password

        
        sickbeard.USE_GROWL = use_growl
        sickbeard.GROWL_HOST = growl_host
        sickbeard.GROWL_PASSWORD = growl_password
        
        sickbeard.save_config()
        
        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            return _genericMessage("Error", "<br />\n".join(results))
        
        raise cherrypy.HTTPRedirect("index")


class Config:

    @cherrypy.expose
    def index(self):
        
        t = Template(file=os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/config.tmpl"))
        return _munge(t)
    
    general = ConfigGeneral()
    
    episodedownloads = ConfigEpisodeDownloads()
    
    providers = ConfigProviders()
    
    irc = ConfigIRC()
    
    notifications = ConfigNotifications()


class HomePostProcess:
    
    @cherrypy.expose
    def index(self):
        
        t = Template(file=os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/home_postprocess.tmpl"))
        return _munge(t)

    @cherrypy.expose
    def processEpisode(self, dir=None, nzbName=None, jobName=None, quiet=None):
        
        if dir == None:
            raise cherrypy.HTTPRedirect("postprocess")
        else:
            result = processTV.doIt(dir, nzbName)
            if quiet != None and int(quiet) == 1:
                return result  
        
            result = result.replace("\n","<br />\n")
            return _genericMessage("Postprocessing results", result)


class HomeAddShows:
    
    @cherrypy.expose
    def index(self):
        
        t = Template(file=os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/home_addShows.tmpl"))
        return _munge(t)

    @cherrypy.expose
    def addRootDir(self, dir=None):
        
        if dir == None:
            raise cherrypy.HTTPRedirect("addShows")

        if not os.path.isdir(dir):
            logger.log("The provided directory "+dir+" doesn't exist", logger.ERROR)
            return _genericMessage("Error", "Unable to find the directory "+dir)
        
        showDirs = []
        
        for curDir in os.listdir(unicode(dir)):
            curPath = os.path.join(dir, curDir)
            if os.path.isdir(curPath):
                logger.log("Adding "+curPath+" to the showDir list", logger.DEBUG)
                showDirs.append(curPath)
        
        if len(showDirs) == 0:
            logger.log("The provided directory "+dir+" has no shows in it", logger.ERROR)
            return _genericMessage("Error", "The provided root folder "+dir+ " has no shows in it.")
        
        #result = ui.addShowsFromRootDir(dir)
        
        myTemplate = Template(file=os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/home_addRootDir.tmpl"))
        myTemplate.showDirs = [urllib.quote_plus(x.encode('utf-8')) for x in showDirs]
        return _munge(myTemplate)       
        
        url = "addShow?"+"&".join(["showDir="+urllib.quote_plus(x.encode('utf-8')) for x in showDirs])
        logger.log("Redirecting to URL "+url, logger.DEBUG)
        raise cherrypy.HTTPRedirect(url)

        #return _genericMessage("Adding root directory", result)

    @cherrypy.expose
    def addShow(self, showDir=None, showName=None, seriesList=None):
        
        if showDir != None and type(showDir) is not list:
            showDir = [showDir]
        
        # unquote it no matter what
        showDir = [urllib.unquote_plus(x) for x in showDir]
        
        logger.log("showDir: "+str(showDir))
        
        myTemplate = Template(file=os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/home_addShow.tmpl"))
        myTemplate.resultList = None
        myTemplate.showDir = [urllib.quote_plus(x) for x in showDir]
        
        # if no showDir then start at the beginning
        if showDir == None:
            raise cherrypy.HTTPRedirect("addShows")

        # if we have a dir and a name it means we're mid-search, so get our TVDB list and forward them to the selection screen
        if showDir != None and showName != None:
            logger.log("Getting list of possible shows and asking user to choose one", logger.DEBUG)
            t = tvdb_api.Tvdb(custom_ui=TVDBWebUI)
            t.config['_showDir'] = [urllib.quote_plus(x) for x in showDir]
            try:
                s = t[showName] # this will throw a cherrypy exception
            except tvdb_exceptions.tvdb_shownotfound:
                return _genericMessage("Error", "Couldn't find that show")
    

        curShowDir = os.path.normpath(showDir[0])
        logger.log("curShowDir: "+curShowDir)

        if seriesList != None:
            showIDs = seriesList.split(",")
        else:
            showIDs = []

        # if we have a folder but no ID specified then we try scanning it for NFO
        if len(showIDs) == 0:

            logger.log("Folder has been provided but we have no show ID, scanning it for an NFO", logger.DEBUG)

            showAdded = False

            try:
                #newShowAdder = ui.ShowAdder(showDir)
                sickbeard.showAddScheduler.action.addShowToQueue(curShowDir)
                showAdded = True
                del showDir[0]
            except exceptions.NoNFOException:
                logger.log("The show queue said we need to create an NFO for this show", logger.DEBUG)
                myTemplate.resultList = []
                myTemplate.showDir = [urllib.quote_plus(x) for x in showDir]
                return _munge(myTemplate)
            except exceptions.MultipleShowObjectsException:
                # showAdded is already false so we can pass this exception and deal with the redirect below
                del showDir[0]
                pass 

            # if the show list is empty, go to the show page
            if len(showDir) == 0:
                if showAdded:
                    # if we added a show and it's loading then visit its page
                    if curShowDir in sickbeard.loadingShowList and sickbeard.loadingShowList[curShowDir].show != None:
                        raise cherrypy.HTTPRedirect("../displayShow?show="+str(sickbeard.loadingShowList[curShowDir].show.tvdbid))
                    # if we added a show but it's not loading yet then go to the home page
                    else:
                        time.sleep(3)
                        raise cherrypy.HTTPRedirect("../")

                # if we didn't add a show and the show list is empty it means we errored on the last show, so let the user know
                else:
                    return _genericMessage("Error", "The show in "+curShowDir+" is already loaded.")
            
            # if we have at least one show left to add then redirect
            else:
                newCallList = [urllib.quote_plus(x) for x in showDir]
                logger.log("There are still shows left to add, so recursively calling myself with showDir="+str(newCallList))
                return self.addShow(newCallList)
                                    
        
        # if we have a single ID then just make a show with that ID
        elif len(showIDs) == 1:
            
            logger.log("We have a single show ID, creating a show with that ID", logger.DEBUG)
            
            # if the dir doesn't exist then give up
            if not helpers.makeDir(curShowDir):
                return _genericMessage("Error", "Show dir doesn't exist and I'm unable to create it")

    
            # if the folder exists then make the show there
            if not helpers.makeShowNFO(showIDs[0], curShowDir):
                return _genericMessage("Error", "Unable to make tvshow.nfo?")
            
            # just go do the normal show creation now that we have the NFO
            #url ="addShow?"+ "&".join(["showDir="+urllib.quote_plus(x) for x in showDir])
            #logger.log("Redirecting to "+url, logger.DEBUG)
            #raise cherrypy.HTTPRedirect(url)
            newCallList = [urllib.quote_plus(x) for x in showDir]
            logger.log("We now have an NFO for the show, so recursively calling myself with showDir="+str(newCallList))
            a = self.addShow(newCallList)
            logger.log("HOW DID WE GET HERE: "+a)
            return a
            
        
        # if we have multiple IDs then let them pick
        else:

            logger.log("Presenting a list of shows to the user", logger.DEBUG)
            
            t = tvdb_api.Tvdb()
            myTemplate.resultList = [t[int(x)] for x in showIDs]
            myTemplate.showDir = [urllib.quote_plus(x) for x in showDir]
            
            return _munge(myTemplate)



class Home:

    @cherrypy.expose
    def index(self):
        
        t = Template(file=os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/home.tmpl"))
        
        myDB = db.DBConnection()
        
        today = str(datetime.date.today().toordinal())
        
        t.downloadedEps = myDB.select("SELECT showid, COUNT(*) FROM tv_episodes WHERE status IN ("+str(DOWNLOADED)+","+str(PREDOWNLOADED)+") AND airdate != 1 AND season != 0 and episode != 0 AND airdate <= "+today+" GROUP BY showid")

        t.allEps = myDB.select("SELECT showid, COUNT(*) FROM tv_episodes WHERE airdate != 1 AND season != 0 and episode != 0 AND airdate <= "+today+" GROUP BY showid")
        
        return _munge(t)

    addShows = HomeAddShows()
    
    postprocess = HomePostProcess()
    
    @cherrypy.expose
    def testGrowl(self, host=None, password=None):
        notifiers.testGrowl(host, password)
        return "Tried sending growl to "+host+" with password "+password
        
    @cherrypy.expose
    def testXBMC(self, host=None, username=None, password=None):
        notifiers.testXBMC(urllib.unquote_plus(host), username, password)
        return "Tried sending XBMC notification to "+urllib.unquote_plus(host)
        
    @cherrypy.expose
    def shutdown(self):

        threading.Timer(2, sickbeard.saveAndShutdown).start()
        return _genericMessage("Shutting down", "Sick Beard is shutting down...")

    @cherrypy.expose
    def displayShow(self, show=None):
        
        if show == None:
            return _genericMessage("Error", "Invalid show ID")
        else:
            showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
            
            if showObj == None:
                
                return _genericMessage("Error", "Unable to find the specified show.")

        myDB = db.DBConnection()
        
        logger.log(str(showObj.tvdbid) + ": Displaying all episodes from the database")
    
        sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = " + str(showObj.tvdbid) + " ORDER BY season*1000+episode DESC")
        
        t = Template(file=os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/displayShow.tmpl"))
        
        t.show = showObj
        t.qualityStrings = sickbeard.common.qualityStrings
        t.sqlResults = sqlResults
        
        return _munge(t)

    @cherrypy.expose
    def editShow(self, show=None, location=None, quality=None, seasonfolders=None, paused=None):
        
        if show == None:
            return _genericMessage("Error", "Invalid show ID")
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            return _genericMessage("Error", "Unable to find the specified show")

        if location == None and quality == None and seasonfolders == None:
            
            t = Template(file=os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/editShow.tmpl"))
            with showObj.lock:
                t.show = showObj
                t.qualityStrings = qualityStrings
                t.qualities = (SD, HD, ANY, BEST)
            
            return _munge(t)
        
        if seasonfolders == "on":
            seasonfolders = 1
        else:
            seasonfolders = 0

        if paused == "on":
            paused = 1
        else:
            paused = 0

        with showObj.lock:

            logger.log("changing quality from " + str(showObj.quality) + " to " + str(quality), logger.DEBUG)
            showObj.quality = int(quality)
            
            if showObj.seasonfolders != seasonfolders:
                showObj.seasonfolders = seasonfolders
                showObj.refreshDir()

            showObj.paused = paused
                        
            # if we change location clear the db of episodes, change it, write to db, and rescan
            if os.path.isdir(location) and os.path.normpath(showObj._location) != os.path.normpath(location):
                
                # change it
                try:
                    showObj.location = location
                except exceptions.NoNFOException:
                    return _genericMessage("The folder at "+location+" doesn't contain a tvshow.nfo - copy your files to that folder before you change the directory in Sick Beard.")
                
                showObj.refreshDir()
                
                # grab updated info from TVDB
                #showObj.loadEpisodesFromTVDB()

                # rescan the episodes in the new folder
                showObj.loadEpisodesFromDir()
                    
            # save it to the DB
            showObj.saveToDB()
                
            raise cherrypy.HTTPRedirect("displayShow?show=" + show)

    @cherrypy.expose
    def deleteShow(self, show=None):

        if show == None:
            return _genericMessage("Error", "Invalid show ID")
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            return _genericMessage("Error", "Unable to find the specified show")

        if sickbeard.showAddScheduler.action.isBeingAdded(showObj) or \
        sickbeard.showUpdateScheduler.action.isBeingUpdated(showObj):
            return _genericMessage("Error", "Shows can't be deleted while they're being added or updated.")

        showObj.deleteShow()
        
        return _genericMessage("Show deleted", "Show has been deleted.")

    @cherrypy.expose
    def updateShow(self, show=None, force=0):
        
        if show == None:
            return _genericMessage("Error", "Invalid show ID")
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            return _genericMessage("Error", "Unable to find the specified show")
        
        if sickbeard.showAddScheduler.action.isBeingAdded(showObj):
            return _genericMessage("Error", "Show is still being added, wait until it is finished before you update.")
        
        if sickbeard.showUpdateScheduler.action.isBeingUpdated(showObj):
            return _genericMessage("Error", "This show is already being updated, can't update again until it's done.")

        # force the update from the DB
        sickbeard.showUpdateScheduler.action.addShowToQueue(showObj, bool(force))
        
        # just give it some time
        time.sleep(3)
        
        raise cherrypy.HTTPRedirect("displayShow?show="+str(showObj.tvdbid))


    @cherrypy.expose
    def updateXBMC(self):

        result = xbmc.updateLibrary()
        
        if result:
            message = "Command sent to XBMC to update library"
        else:
            message = "Unable to contact XBMC"
        
        return _genericMessage("XBMC Library Update", logger.MESSAGE)


    @cherrypy.expose
    def fixEpisodeNames(self, show=None):
        
        if show == None:
            return _genericMessage("Error", "Invalid show ID")
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            return _genericMessage("Error", "Unable to find the specified show")
        
        if sickbeard.showAddScheduler.action.isBeingAdded(showObj):
            return _genericMessage("Error", "Show is still being added, wait until it is finished before you rename files")
        
        showObj.fixEpisodeNames()

        raise cherrypy.HTTPRedirect("displayShow?show=" + show)
        
    @cherrypy.expose
    def setStatus(self, show=None, eps=None, status=None):
        
        if show == None or eps == None or status == None:
            return _genericMessage("Error", "You must specify a show and at least one episode")
        
        if not statusStrings.has_key(int(status)):
            return _genericMessage("Error", "Invalid status")
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

        if showObj == None:
            return _genericMessage("Error", "Show not in show list")

        if eps != None:

            for curEp in eps.split('|'):

                logger.log("Attempting to set status on episode "+curEp+" to "+status, logger.DEBUG)

                epInfo = curEp.split('x')

                epObj = showObj.getEpisode(int(epInfo[0]), int(epInfo[1]))
            
                if epObj == None:
                    return _genericMessage("Error", "Episode couldn't be retrieved")
            
                with epObj.lock:
                    # don't let them mess up UNAIRED episodes
                    if epObj.status == UNAIRED:
                        logger.log("Refusing to change status of "+curEp+" because it is UNAIRED", logger.ERROR)
                        continue
                    
                    if int(status) == DOWNLOADED and epObj.status != PREDOWNLOADED:
                        logger.log("Refusing to change status of "+curEp+" to DOWNLOADED because it's not PREDOWNLOADED", logger.ERROR)
                        continue

                    epObj.status = int(status)
                    epObj.saveToDB()
                    
        raise cherrypy.HTTPRedirect("displayShow?show=" + show)

    @cherrypy.expose
    def searchEpisode(self, show=None, season=None, episode=None):
        
        outStr = ""
        epObj = _getEpisode(show, season, episode)
        
        if isinstance(epObj, str):
            return _genericMessage("Error", epObj)
        
        tempStr = "Searching for download for " + epObj.prettyName()
        logger.log(tempStr)
        outStr += tempStr + "<br />\n"
        foundEpisodes = search.findEpisode(epObj)
        
        if len(foundEpisodes) == 0:
            tempStr = "No downloads were found<br />\n"
            logger.log(tempStr)
            outStr += tempStr + "<br />\n"
            return _genericMessage("Error", outStr)
        
        else:

            # just use the first result for now
            logger.log("Downloading episode from " + foundEpisodes[0].url + "<br />\n")
            result = search.snatchEpisode(foundEpisodes[0])
            
            #TODO: check if the download was successful

            # update our lists to reflect the result if this search
            sickbeard.updateMissingList()
            sickbeard.updateAiringList()
            sickbeard.updateComingList()

            
            raise cherrypy.HTTPRedirect("displayShow?show=" + str(epObj.show.tvdbid))



class WebInterface:
    
    @cherrypy.expose
    def index(self):
        
        raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def showPoster(self, show=None):
        
        if show == None:
            return "Invalid show" #TODO: make it return a standard image
        else:
            showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
            
        if showObj == None:
            return "Unable to find show" #TODO: make it return a standard image
    
        posterFilename = os.path.join(showObj.location, "folder.jpg")
        if os.path.isfile(posterFilename):
            
            posterFile = open(posterFilename, "rb")
            cherrypy.response.headers['Content-type'] = "image/jpeg"
            posterImage = posterFile.read()
            posterFile.close()
            return posterImage
        
        else:
            print "No poster" #TODO: make it return a standard image

    @cherrypy.expose
    def comingEpisodes(self):

        epList = sickbeard.missingList + sickbeard.comingList

        # sort by air date
        epList.sort(lambda x, y: cmp(x.airdate.toordinal(), y.airdate.toordinal()))
        
        t = Template(file=os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/comingEpisodes.tmpl"))
        t.epList = epList
        t.qualityStrings = qualityStrings
        
        return _munge(t)

    backlog = Backlog()

    history = History()

    config = Config()

    home = Home()
