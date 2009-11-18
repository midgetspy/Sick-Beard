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
from sickbeard import nzb
from sickbeard import processTV
from sickbeard import ui
from sickbeard.tv import *
from lib.tvdb_api import tvdb_exceptions

import sickbeard
import sickbeard.helpers


class TVDBWebUI:
    def __init__(self, config, log):
        self.config = config
        self.log = log

    def selectSeries(self, allSeries):
        
        for curShow in allSeries:
            showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(curShow['sid']))
            if showObj != None:
                raise cherrypy.HTTPRedirect("addShow/?showDir=" + self.config['_showDir'] + "&seriesList=" + curShow['sid'])
        
        searchList = ",".join([x['sid'] for x in allSeries])
        raise cherrypy.HTTPRedirect("addShow/?showDir=" + self.config['_showDir'] + "&seriesList=" + searchList)

def _munge(string):
    return unicode(string).replace("&", "&amp;").encode('ascii', 'xmlcharrefreplace')

def _genericMessage(subject, message):
    t = Template(file="data/interfaces/default/genericMessage.tmpl")
    t.subject = subject
    t.message = message
    return _munge(t)

def _getEpisode(show, season, episode):

    if show == None or season == None or episode == None:
        return "Invalid parameters"
    
    showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

    if showObj == None:
        return "Show not in show list"

    epObj = showObj.getEpisode(int(season), int(episode), True)
    
    if epObj == None:
        return "Episode couldn't be retrieved"

    return epObj

class ConfigGeneral:
    
    @cherrypy.expose
    def index(self):
        
        t = Template(file="data/interfaces/default/config_general.tmpl")
        return _munge(t)

    @cherrypy.expose
    def saveGeneral(self, log_dir=None, web_port=None, web_log=None, nzb_method=None,
                    launch_browser=None, create_metadata=None, web_username=None,
                    web_password=None):

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
            
        if not config.change_LOG_DIR(log_dir):
            results += ["Unable to create directory " + os.path.normpath(log_dir) + ", log dir not changed."]
        
        sickbeard.NZB_METHOD = nzb_method
        sickbeard.LAUNCH_BROWSER = launch_browser
        sickbeard.CREATE_METADATA = create_metadata

        sickbeard.WEB_PORT = web_port
        sickbeard.WEB_LOG = web_log
        sickbeard.WEB_USERNAME = web_username
        sickbeard.WEB_PASSWORD = web_password

        sickbeard.save_config()
        
        if len(results) > 0:
            for x in results:
                Logger().log(x, ERROR)
            return "<br />\n".join(results)
        
        raise cherrypy.HTTPRedirect("index")

class ConfigNZBActions:
    
    @cherrypy.expose
    def index(self):
        
        t = Template(file="data/interfaces/default/config_nzbactions.tmpl")
        return _munge(t)

    @cherrypy.expose
    def saveNZBActions(self, nzb_dir=None, sab_username=None, sab_password=None,
                       sab_apikey=None, sab_category=None, sab_host=None):

        results = []

        if not config.change_NZB_DIR(nzb_dir):
            results += ["Unable to create directory " + os.path.normpath(nzb_dir) + ", dir not changed."]

        sickbeard.SAB_USERNAME = sab_username
        sickbeard.SAB_PASSWORD = sab_password
        sickbeard.SAB_APIKEY = sab_apikey
        sickbeard.SAB_CATEGORY = sab_category
        sickbeard.SAB_HOST = sab_host
        
        sickbeard.save_config()
        
        if len(results) > 0:
            for x in results:
                Logger().log(x, ERROR)
            return "<br />\n".join(results)
        
        raise cherrypy.HTTPRedirect("index")

class ConfigProviders:
    
    @cherrypy.expose
    def index(self):
        t = Template(file="data/interfaces/default/config_providers.tmpl")
        return _munge(t)

    
    @cherrypy.expose
    def saveProviders(self, newzbin=None, newzbin_username=None, newzbin_password=None, tvbinz=None,
                   tvbinz_uid=None, tvbinz_hash=None, nzbs=None, nzbs_uid=None, nzbs_hash=None):

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

        sickbeard.NEWZBIN = newzbin
        sickbeard.NEWZBIN_USERNAME = newzbin_username
        sickbeard.NEWZBIN_PASSWORD = newzbin_password
        
        sickbeard.TVBINZ = tvbinz
        sickbeard.TVBINZ_UID = tvbinz_uid
        sickbeard.TVBINZ_HASH = tvbinz_hash
        
        sickbeard.NZBS = nzbs
        sickbeard.NZBS_UID = nzbs_uid
        sickbeard.NZBS_HASH = nzbs_hash
        
        sickbeard.save_config()
        
        if len(results) > 0:
            for x in results:
                Logger().log(x, ERROR)
            return "<br />\n".join(results)
        
        raise cherrypy.HTTPRedirect("index")

class ConfigIRC:
    
    @cherrypy.expose
    def index(self):
        t = Template(file="data/interfaces/default/config_irc.tmpl")
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
                Logger().log(x, ERROR)
            return "<br />\n".join(results)
        
        raise cherrypy.HTTPRedirect("index")

class ConfigNotifications:
    
    @cherrypy.expose
    def index(self):
        t = Template(file="data/interfaces/default/config_notifications.tmpl")
        return _munge(t)
    
    @cherrypy.expose
    def saveNotifications(self, xbmc_notify_onsnatch=None, xbmc_notify_ondownload=None, 
                          xbmc_update_library=None, xbmc_host=None):

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

        sickbeard.XBMC_NOTIFY_ONSNATCH = xbmc_notify_onsnatch 
        sickbeard.XBMC_NOTIFY_ONDOWNLOAD = xbmc_notify_ondownload
        sickbeard.XBMC_UPDATE_LIBRARY = xbmc_update_library
        sickbeard.XBMC_HOST = xbmc_host
        
        sickbeard.save_config()
        
        if len(results) > 0:
            for x in results:
                Logger().log(x, ERROR)
            return "<br />\n".join(results)
        
        raise cherrypy.HTTPRedirect("index")


class Config:

    @cherrypy.expose
    def index(self):
        
        t = Template(file="data/interfaces/default/config.tmpl")
        return _munge(t)
    
    general = ConfigGeneral()
    
    nzbActions = ConfigNZBActions()
    
    providers = ConfigProviders()
    
    irc = ConfigIRC()
    
    notifications = ConfigNotifications()

class HomeForceBacklog:
    @cherrypy.expose
    def index(self):

        # force it to run the next time it looks
        sickbeard.backlogSearchScheduler.forceSearch()
        Logger().log("Backlog set to run in background")
        
        return _genericMessage("Backlog search started", "The backlog search has begun and will run in the background")


class HomePostProcess:
    
    @cherrypy.expose
    def index(self):
        
        t = Template(file="data/interfaces/default/home_postprocess.tmpl")
        return _munge(t)

    @cherrypy.expose
    def processEpisode(self, dir=None, nzbName=None, jobName=None):
        
        if dir == None:
            raise cherrypy.HTTPRedirect("postprocess")
        else:
            result = processTV.doIt(dir, sickbeard.showList)
            return _genericMessage("Postprocessing results", result)


class HomeAddShows:
    
    @cherrypy.expose
    def index(self):
        
        t = Template(file="data/interfaces/default/home_addShows.tmpl")
        return _munge(t)

    @cherrypy.expose
    def addRootDir(self, dir=None):
        
        if dir == None:
            raise cherrypy.HTTPRedirect("addShows")

        result = ui.addShowsFromRootDir(dir)

        return _genericMessage("Adding root directory", result)

    @cherrypy.expose
    def addShow(self, showDir=None, showName=None, seriesList=None):
        
        myTemplate = Template(file="data/interfaces/default/home_addShow.tmpl")
        myTemplate.resultList = None
        myTemplate.showDir = showDir
        
        # if no showDir then start at the beginning
        if showDir == None:
            raise cherrypy.HTTPRedirect("addShows")

        # if we have a dir and a name it means we're mid-search, so get our TVDB list and forward them to the selection screen
        if showDir != None and showName != None:
            t = tvdb_api.Tvdb(custom_ui=TVDBWebUI)
            t.config['_showDir'] = urllib.quote_plus(showDir)
            try:
                s = t[showName] # this will throw a cherrypy exception
            except tvdb_exceptions.tvdb_shownotfound:
                return _genericMessage("Error", "Couldn't find that show")
    

        showDir = os.path.normpath(urllib.unquote_plus(showDir))

        if seriesList != None:
            showIDs = seriesList.split(",")
        else:
            showIDs = []

        # if we have a folder but no ID specified then we try scanning it for NFO
        if len(showIDs) == 0:

            try:
                #newShowAdder = ui.ShowAdder(showDir)
                sickbeard.showAddScheduler.action.addShowToQueue(showDir)
            except exceptions.NoNFOException:
                myTemplate.resultList = []
                myTemplate.showDir = urllib.quote_plus(showDir)
                return _munge(myTemplate)

            # give it a chance to get on the show list so we don't refresh and it looks like nothing happened
            time.sleep(3)

            raise cherrypy.HTTPRedirect("index")
        
        # if we have a single ID then just make a show with that ID
        elif len(showIDs) == 1:
            
            # if the dir doesn't exist then give up
            if not helpers.makeDir(showDir):
                return _genericMessage("Error", "Show dir doesn't exist and I'm unable to create it")

    
            # if the folder exists then make the show there
            if not helpers.makeShowNFO(showIDs[0], showDir):
                return _genericMessage("Error", "Unable to make tvshow.nfo?")
            
            # just go do the normal show creation now that we have the NFO
            raise cherrypy.HTTPRedirect("addShow/?showDir=" + urllib.quote_plus(showDir))
        
        # if we have multiple IDs then let them pick
        else:
            
            t = tvdb_api.Tvdb()
            myTemplate.resultList = [t[int(x)] for x in showIDs]
            myTemplate.showDir = urllib.quote_plus(showDir)
            
            return _munge(myTemplate)



class Home:
    
    @cherrypy.expose
    def index(self):
        
        t = Template(file="data/interfaces/default/home.tmpl")
        return _munge(t)

    addShows = HomeAddShows()
    
    postprocess = HomePostProcess()
    
    forceBacklog = HomeForceBacklog()

    @cherrypy.expose
    def displayShow(self, show=None):
        
        if show == None:
            return _genericMessage("Error", "Invalid show ID")
        else:
            showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
            
            if showObj == None:
                return _genericMessage("Error", "Unable to find the specified show.")

        myDB = db.DBConnection()
        myDB.checkDB()

        Logger().log(str(showObj.tvdbid) + ": Displaying all episodes from the database")
    
        sqlResults = []

        try:
            sql = "SELECT * FROM tv_episodes WHERE showid = " + str(showObj.tvdbid) + " ORDER BY season, episode ASC"
            Logger().log("SQL: " + sql, DEBUG)
            sqlResults = myDB.connection.execute(sql).fetchall()
        except sqlite3.DatabaseError as e:
            Logger().log("Fatal error executing query '" + sql + "': " + str(e), ERROR)
            raise

        t = Template(file="data/interfaces/default/displayShow.tmpl")
        
        t.show = showObj
        t.qualityStrings = sickbeard.common.qualityStrings
        t.sqlResults = sqlResults
        
        return _munge(t)

    @cherrypy.expose
    def editShow(self, show=None, location=None, quality=None, predownload=None, seasonfolders=None):
        
        if show == None:
            return _genericMessage("Error", "Invalid show ID")
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            return _genericMessage("Error", "Unable to find the specified show")

        if location == None and quality == None and predownload == None and seasonfolders == None:
            
            t = Template(file="data/interfaces/default/editShow.tmpl")
            with showObj.lock:
                t.show = showObj
                t.qualityStrings = qualityStrings
                t.qualities = (SD, HD, ANY)
            
            return _munge(t)
        
        if seasonfolders == "on":
            seasonfolders = 1
        else:
            seasonfolders = 0

        if predownload == "on":
            predownload = 1
        else:
            predownload = 0

        with showObj.lock:

            Logger().log("changing quality from " + str(showObj.quality) + " to " + str(quality), DEBUG)
            showObj.quality = int(quality)
            showObj.predownload = int(predownload)
            
            if showObj.seasonfolders != int(seasonfolders):
                showObj.seasonfolders = int(seasonfolders)
                showObj.refreshDir()
                        
            # if we change location clear the db of episodes, change it, write to db, and rescan
            if os.path.isdir(location) and os.path.normpath(showObj._location) != os.path.normpath(location):
                
                # change it
                showObj.location = location
                
                showObj.refreshDir()
                
                # grab updated info from TVDB
                #showObj.loadEpisodesFromTVDB()

                # rescan the episodes in the new folder
                showObj.loadEpisodesFromDir()
                    
            # save it to the DB
            showObj.saveToDB()
                
            raise cherrypy.HTTPRedirect("displayShow/?show=" + show)

    @cherrypy.expose
    def deleteShow(self, show=None):

        if show == None:
            return _genericMessage("Error", "Invalid show ID")
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            return _genericMessage("Error", "Unable to find the specified show")

        showObj.deleteShow()
        
        return _genericMessage("Show deleted", "Show has been deleted.")

    @cherrypy.expose
    def updateShow(self, show=None, force=0):
        
        if show == None:
            return _genericMessage("Error", "Invalid show ID")
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            return _genericMessage("Error", "Unable to find the specified show")
        
        # force the update from the DB
        sickbeard.updateScheduler.action.updateShowFromTVDB(showObj, bool(force))
        
        raise cherrypy.HTTPRedirect("displayShow/?show=" + show)


    @cherrypy.expose
    def fixEpisodeNames(self, show=None):
        
        if show == None:
            return _genericMessage("Error", "Invalid show ID")
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            return _genericMessage("Error", "Unable to find the specified show")
        
        showObj.fixEpisodeNames()

        raise cherrypy.HTTPRedirect("displayShow/?show=" + show)
        
    
    @cherrypy.expose
    def refreshDir(self, show=None):
        
        if show == None:
            return _genericMessage("Error", "Invalid show ID")
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            return _genericMessage("Error", "Unable to find the specified show")

        showObj.refreshDir()

        raise cherrypy.HTTPRedirect("displayShow/?show=" + show)
        
    
    @cherrypy.expose
    def setStatus(self, show=None, season=None, episode=None, status=None):
        
        if show == None or season == None or status == None:
            return _genericMessage("Error", "You must specify a show and season at least")
        
        if not statusStrings.has_key(int(status)):
            return _genericMessage("Error", "Invalid status")
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

        if showObj == None:
            return _genericMessage("Error", "Show not in show list")

        if episode != None:

            epObj = showObj.getEpisode(int(season), int(episode), True)
            
            if epObj == None:
                return _genericMessage("Error", "Episode couldn't be retrieved")
        
            with epObj.lock:
                #if epObj.status == SKIPPED:
                epObj.status = status
                epObj.saveToDB()

        else:
            
            myDB = db.DBConnection()
            myDB.checkDB()

            Logger().log(str(showObj.tvdbid) + ": Setting status " + str(status) + " on all episodes")
        
            sqlResults = []
    
            try:
                sql = "SELECT * FROM tv_episodes WHERE showid = " + str(showObj.tvdbid) + " AND season = " + str(season)
                Logger().log("SQL: " + sql, DEBUG)
                sqlResults = myDB.connection.execute(sql).fetchall()
            except sqlite3.DatabaseError as e:
                Logger().log("Fatal error executing query '" + sql + "': " + str(e), ERROR)
                raise

            for curEp in sqlResults:
                
                curSeason = int(curEp["season"])
                curEpisode = int(curEp["episode"])
                
                epObj = showObj.getEpisode(curSeason, curEpisode, True)
                Logger().log(str(showObj.tvdbid) + ": Setting status for " + str(curSeason) + "x" + str(curEpisode) + " to " + statusStrings[int(status)], DEBUG)
                with epObj.lock:
                    epObj.status = int(status)
                    epObj.saveToDB()
                    
        raise cherrypy.HTTPRedirect("displayShow/?show=" + show)



    @cherrypy.expose
    def searchEpisode(self, show=None, season=None, episode=None):
        
        outStr = ""
        epObj = _getEpisode(show, season, episode)
        
        if isinstance(epObj, str):
            return _genericMessage("Error", epObj)
        
        tempStr = "Searching for NZB for " + epObj.prettyName()
        Logger().log(tempStr)
        outStr += tempStr + "<br />\n"
        foundNZBs = nzb.findNZB(epObj)
        
        if len(foundNZBs) == 0:
            tempStr = "No NZBs were found<br />\n"
            Logger().log(tempStr)
            outStr += tempStr + "<br />\n"
            return _genericMessage("Error", outStr)
        
        else:

            # just use the first result for now
            Logger().log("Downloading NZB from " + foundNZBs[0].url + "<br />\n")
            result = nzb.snatchNZB(foundNZBs[0])
            
            #TODO: check if the download was successful
            
            raise cherrypy.HTTPRedirect("displayShow/?show=" + str(epObj.show.tvdbid))



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
        
        t = Template(file="data/interfaces/default/comingEpisodes.tmpl")
        t.epList = epList
        t.qualityStrings = qualityStrings
        
        return _munge(t)

    config = Config()

    home = Home()

class Whatever:
    
    test = WebInterface()
    
    @cherrypy.expose
    def index(self):

        t = Template(file="data/includes/index.html")

        t.showList = sickbeard.showList
        t.loadingShowList = sickbeard.loadingShowList.values()

        return _munge(t)
    
    @cherrypy.expose
    def shutdown(self):

        threading.Timer(2, sickbeard.saveAndShutdown).start()
        return "Shutting down..."
    
    @cherrypy.expose
    def restart(self):

        threading.Timer(2, sickbeard.restart).start()
        return "Restarting... (wait ~30 seconds)"

    
    @cherrypy.expose
    def forceBacklog(self):

        # force it to run the next time it looks
        sickbeard.backlogSearchScheduler.forceSearch()
        Logger().log("Backlog set to run in background")
        
        return "Backlog will run in the background"
    
    
    @cherrypy.expose
    def addRootDir(self, dir=None):
        
        if dir == None:
            myTemplate = Template(file="data/includes/addRootDir.html")
            return _munge(myTemplate) 
        
        result = ui.addShowsFromRootDir(dir)

        return _munge(result)
        
    
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
    def createShow(self, showName=None, showID=None, showDir=None):

        if showName != None:
            t = tvdb_api.Tvdb(custom_ui=TVDBWebUI)
            try:
                s = t[showName]
            except tvdb_exceptions.tvdb_shownotfound:
                return "Couldn't find that show"

            # should never get here
            return "Whoops, shouldn't be here"

        myTemplate = Template(file="data/includes/createShow.html")
        myTemplate.resultList = []
        
        if showID != None:
            showIDList = showID.split(",")
            
            if len(showIDList) == 1:
                return "making NFO for show " + showIDList[0] + " and then creating a show for that folder"
            else:
                t = tvdb_api.Tvdb()
                myTemplate.resultList = [t[int(x)] for x in showIDList]
        
        return _munge(myTemplate)
    
    
    @cherrypy.expose
    def displayShow(self, show=None):
        
        if show == None:
            return "Invalid show"
        else:
            showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
            
            if showObj == None:
                return "Unable to find show"

        myDB = db.DBConnection()
        myDB.checkDB()

        Logger().log(str(showObj.tvdbid) + ": Displaying all episodes from the database")
    
        sqlResults = []

        try:
            sql = "SELECT * FROM tv_episodes WHERE showid = " + str(showObj.tvdbid) + " ORDER BY season, episode ASC"
            Logger().log("SQL: " + sql, DEBUG)
            sqlResults = myDB.connection.execute(sql).fetchall()
        except sqlite3.DatabaseError as e:
            Logger().log("Fatal error executing query '" + sql + "': " + str(e), ERROR)
            raise

        t = Template(file="data/includes/displayShow.html")
        
        t.show = showObj
        t.qualityStrings = sickbeard.common.qualityStrings
        t.sqlResults = sqlResults
        
        return _munge(t)
    
    @cherrypy.expose
    def updateShow(self, show=None, force=0):
        
        if show == None:
            return "Invalid show"
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            return "Unable to find the specified show"
        
        # force the update from the DB
        sickbeard.updateScheduler.action.updateShowFromTVDB(showObj, bool(force))
        
        raise cherrypy.HTTPRedirect("/displayShow/?show=" + show)

    @cherrypy.expose
    def deleteShow(self, show=None):

        if show == None:
            return "Invalid show"
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            return "Unable to find the specified show"

        showObj.deleteShow()
        
        return _munge("Show has been deleted.")


    @cherrypy.expose
    def fixEpisodeNames(self, show=None):
        
        if show == None:
            return "Invalid show"
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            return "Unable to find the specified show"
        
        showObj.fixEpisodeNames()

        raise cherrypy.HTTPRedirect("/displayShow/?show=" + show)
        
    
    @cherrypy.expose
    def refreshDir(self, show=None):
        
        if show == None:
            return "Invalid show"
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            return "Unable to find the specified show"
        
        showObj.refreshDir()

        raise cherrypy.HTTPRedirect("/displayShow/?show=" + show)
        
    
    @cherrypy.expose
    def editShow(self, show=None, location=None, quality=None, predownload=None, seasonfolders=None):
        
        if show == None:
            return "Invalid show"
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            return "Unable to find the specified show"

        if location == None and quality == None and predownload == None and seasonfolders == None:
            
            t = Template(file="data/includes/editShow.html")
            with showObj.lock:
                t.show = showObj
                t.qualityStrings = qualityStrings
                t.qualities = (SD, HD, ANY)
            
            return _munge(t)
        
        if seasonfolders == "on":
            seasonfolders = 1
        else:
            seasonfolders = 0

        if predownload == "on":
            predownload = 1
        else:
            predownload = 0

        with showObj.lock:

            print "changing quality from", showObj.quality, "to", quality
            showObj.quality = int(quality)
            showObj.predownload = int(predownload)
            
            if showObj.seasonfolders != int(seasonfolders):
                showObj.seasonfolders = int(seasonfolders)
                showObj.refreshDir()
                        
            # if we change location clear the db of episodes, change it, write to db, and rescan
            if os.path.isdir(location) and os.path.normpath(showObj._location) != os.path.normpath(location):
                
                #myDB = db.DBConnection()
                #myDB.checkDB()
                
                #Logger().log(str(showObj.tvdbid)+": Refreshing ")
            
                # delete all the episodes that had a file associated with them
                #try:
                #    sql = "DELETE FROM tv_episodes WHERE showid = " + str(showObj.tvdbid) + " AND location != ''"
                #    myDB.connection.execute(sql).fetchall()
                #    myDB.connection.commit()
                #except sqlite3.DatabaseError as e:
                #    Logger().log("Fatal error executing query '"+sql+"': "+str(e), ERROR)
                #    raise

                # get rid of lingering references
                #showObj.flushEpisodes()

                # change it
                showObj.location = location
                
                showObj.refreshDir()
                
                # grab updated info from TVDB
                #showObj.loadEpisodesFromTVDB()

                # rescan the episodes in the new folder
                showObj.loadEpisodesFromDir()
                    
            # save it to the DB
            showObj.saveToDB()
                
            raise cherrypy.HTTPRedirect("/displayShow/?show=" + show)

    @cherrypy.expose
    def addShow(self, showDir=None, showName=None, seriesList=None):
        
        myTemplate = Template(file="data/includes/addShow.html")
        myTemplate.resultList = None
        myTemplate.showDir = showDir
        
        # if no showDir then start at the beginning
        if showDir == None:
            return _munge(myTemplate)

        # if we have a dir and a name it means we're mid-search, so get our TVDB list and forward them to the selection screen
        if showDir != None and showName != None:
            t = tvdb_api.Tvdb(custom_ui=TVDBWebUI)
            t.config['_showDir'] = urllib.quote_plus(showDir)
            try:
                s = t[showName] # this will throw a cherrypy exception
            except tvdb_exceptions.tvdb_shownotfound:
                return "Couldn't find that show"
    

        showDir = os.path.normpath(urllib.unquote_plus(showDir))

        if seriesList != None:
            showIDs = seriesList.split(",")
        else:
            showIDs = []

        # if we have a folder but no ID specified then we try scanning it for NFO
        if len(showIDs) == 0:


            try:
                #newShowAdder = ui.ShowAdder(showDir)
                sickbeard.showAddScheduler.action.addShowToQueue(showDir)
            except exceptions.NoNFOException:
                myTemplate.resultList = []
                myTemplate.showDir = urllib.quote_plus(showDir)
                return _munge(myTemplate)

            raise cherrypy.HTTPRedirect("/")
        
        # if we have a single ID then just make a show with that ID
        elif len(showIDs) == 1:
            
            # if the dir doesn't exist then give up
            if not helpers.makeDir(showDir):
                return "Show dir doesn't exist and I'm unable to create it"
    
            # if the folder exists then make the show there
            if not helpers.makeShowNFO(showIDs[0], showDir):
                return "Unable to make tvshow.nfo?"
            
            # just go do the normal show creation now that we have the NFO
            raise cherrypy.HTTPRedirect("/addShow/?showDir=" + urllib.quote_plus(showDir))
        
        # if we have multiple IDs then let them pick
        else:
            
            t = tvdb_api.Tvdb()
            myTemplate.resultList = [t[int(x)] for x in showIDs]
            myTemplate.showDir = urllib.quote_plus(showDir)
            
            return _munge(myTemplate)

    
    @cherrypy.expose
    def displayEpisode(self, show=None, season=None, episode=None):
        
        epObj = _getEpisode(show, season, episode)
        
        if isinstance(epObj, str):
            return _genericMessage("Error", epObj)
        else:
            t = Template(file="data/includes/displayEpisode.html")
            t.episode = epObj
            t.statusStrings = statusStrings
            
        return _munge(t)

    @cherrypy.expose
    def setStatus(self, show=None, season=None, episode=None, status=None):
        
        if show == None or season == None or status == None:
            return "You must specify a show and season at least"
        
        if not statusStrings.has_key(int(status)):
            return "Invalid status"
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

        if showObj == None:
            return "Show not in show list"

        if episode != None:

            epObj = showObj.getEpisode(int(season), int(episode), True)
            
            if epObj == None:
                return "Episode couldn't be retrieved"
        
            with epObj.lock:
                if epObj.status == SKIPPED:
                    epObj.status = status
                    epObj.saveToDB()

        else:
            
            myDB = db.DBConnection()
            myDB.checkDB()

            Logger().log(str(showObj.tvdbid) + ": Setting status " + str(status) + " on all episodes")
        
            sqlResults = []
    
            try:
                sql = "SELECT * FROM tv_episodes WHERE showid = " + str(showObj.tvdbid) + " AND season = " + str(season)
                Logger().log("SQL: " + sql, DEBUG)
                sqlResults = myDB.connection.execute(sql).fetchall()
            except sqlite3.DatabaseError as e:
                Logger().log("Fatal error executing query '" + sql + "': " + str(e), ERROR)
                raise

            for curEp in sqlResults:
                
                curSeason = int(curEp["season"])
                curEpisode = int(curEp["episode"])
                
                epObj = showObj.getEpisode(curSeason, curEpisode, True)
                Logger().log(str(showObj.tvdbid) + ": Setting status for " + str(curSeason) + "x" + str(curEpisode) + " to " + statusStrings[int(status)], DEBUG)
                with epObj.lock:
                    epObj.status = int(status)
                    epObj.saveToDB()
                    
        raise cherrypy.HTTPRedirect("/displayShow/?show=" + show)



    @cherrypy.expose
    def searchEpisode(self, show=None, season=None, episode=None):
        
        outStr = ""
        epObj = _getEpisode(show, season, episode)
        
        if isinstance(epObj, str):
            return _genericMessage("Error", epObj)
        
        tempStr = "Searching for NZB for " + epObj.prettyName()
        Logger().log(tempStr)
        outStr += tempStr + "<br />\n"
        foundNZBs = nzb.findNZB(epObj)
        
        if len(foundNZBs) == 0:
            tempStr = "No NZBs were found<br />\n"
            Logger().log(tempStr)
            outStr += tempStr + "<br />\n"
            return outStr
        
        else:

            # just use the first result for now
            Logger().log("Downloading NZB from " + foundNZBs[0].url + "<br />\n")
            result = nzb.snatchNZB(foundNZBs[0])
            
            #TODO: check if the download was successful
            
            raise cherrypy.HTTPRedirect("/displayEpisode/?show=" + str(epObj.show.tvdbid) + "&season=" + str(epObj.season) + "&episode=" + str(epObj.episode))
        
    
    @cherrypy.expose
    def processEpisode(self, dir=None, nzbName=None, jobName=None):
        
        if dir == None:
            t = Template(file="data/includes/processEpisode.html")
            return _munge(t)
        else:
            result = processTV.doIt(dir, sickbeard.showList)
            return _munge(result)
    
    @cherrypy.expose
    def comingEpisodes(self):
        
        epList = sickbeard.missingList + sickbeard.comingList
                
        # sort by air date
        epList.sort(lambda x, y: cmp(x.airdate.toordinal(), y.airdate.toordinal()))
        
        t = Template(file="data/includes/comingEpisodes.html")
        t.epList = epList
        t.qualityStrings = qualityStrings
        
        return _munge(t)
        

    @cherrypy.expose
    def editConfig(self, message=None):
        
        t = Template(file="data/includes/editConfig.html")
        t.config = sickbeard.CFG
        t.message = message
        
        return _munge(t)

    @cherrypy.expose
    def editConfigSub(self, log_dir=None, nzb_dir=None, web_username=None, web_password=None,
                   newzbin=None, newzbin_username=None, newzbin_password=None, tvbinz=None,
                   tvbinz_uid=None, tvbinz_hash=None, sab_useapi=None, sab_username=None,
                   sab_password=None, sab_apikey=None, sab_category=None, sab_host=None,
                   irc_bot=None, irc_server=None, irc_channel=None, irc_key=None, irc_nick=None,
                   xbmc_notify_onsnatch=None, xbmc_notify_ondownload=None, xbmc_update_library=None,
                   xbmc_host=None, web_port=None, web_log=None, nzb_method=None, launch_browser=None,
                   create_metadata=None, nzbs=None, nzbs_uid=None, nzbs_hash=None):

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
            
        if irc_bot == "on":
            irc_bot = 1
        else:
            irc_bot = 0
            
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
            
        if not config.change_LOG_DIR(log_dir):
            results += ["Unable to create directory " + os.path.normpath(log_dir) + ", log dir not changed."]
        
        sickbeard.NZB_METHOD = nzb_method
        sickbeard.WEB_USERNAME = web_username
        sickbeard.WEB_PASSWORD = web_password
        
        sickbeard.WEB_PORT = web_port
        sickbeard.WEB_LOG = web_log

        sickbeard.LAUNCH_BROWSER = launch_browser
        sickbeard.CREATE_METADATA = create_metadata

        if not config.change_NZB_DIR(nzb_dir):
            results += ["Unable to create directory " + os.path.normpath(nzb_dir) + ", dir not changed."]

        sickbeard.NEWZBIN = newzbin
        sickbeard.NEWZBIN_USERNAME = newzbin_username
        sickbeard.NEWZBIN_PASSWORD = newzbin_password
        
        sickbeard.TVBINZ = tvbinz
        sickbeard.TVBINZ_UID = tvbinz_uid
        sickbeard.TVBINZ_HASH = tvbinz_hash
        
        sickbeard.NZBS = nzbs
        sickbeard.NZBS_UID = nzbs_uid
        sickbeard.NZBS_HASH = nzbs_hash
        
        sickbeard.SAB_USERNAME = sab_username
        sickbeard.SAB_PASSWORD = sab_password
        sickbeard.SAB_APIKEY = sab_apikey
        sickbeard.SAB_CATEGORY = sab_category
        sickbeard.SAB_HOST = sab_host

        config.change_IRC_BOT(irc_bot)
        config.change_IRC_SERVER(irc_server)
        config.change_IRC_CHANNEL(irc_channel, irc_key)
        config.change_IRC_NICK(irc_nick)
        
        sickbeard.XBMC_NOTIFY_ONSNATCH = xbmc_notify_onsnatch 
        sickbeard.XBMC_NOTIFY_ONDOWNLOAD = xbmc_notify_ondownload
        sickbeard.XBMC_UPDATE_LIBRARY = xbmc_update_library
        sickbeard.XBMC_HOST = xbmc_host
        
        sickbeard.save_config()
        
        if len(results) > 0:
            for x in results:
                Logger().log(x, ERROR)
            return "<br />\n".join(results)
        
        raise cherrypy.HTTPRedirect("/editConfig/?message=Config updated")



    def _getEpisode(self, show, season, episode):

        if show == None or season == None or episode == None:
            return "Invalid parameters"
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

        if showObj == None:
            return "Show not in show list"

        epObj = showObj.getEpisode(int(season), int(episode), True)
        
        if epObj == None:
            return "Episode couldn't be retrieved"

        return epObj
