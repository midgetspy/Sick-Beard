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

from __future__ import with_statement

import os.path

import time
import urllib
import re
import threading
import datetime
import operator

from Cheetah.Template import Template
import cherrypy
import cherrypy.lib

from sickbeard import config
from sickbeard import history, notifiers, processTV, search, providers
from sickbeard import tv, metadata
from sickbeard import logger, helpers, exceptions, classes, db
from sickbeard import encodingKludge as ek

from sickbeard.notifiers import xbmc
from sickbeard.providers import newznab
from sickbeard.common import *

from lib.tvdb_api import tvdb_exceptions
from lib.tvdb_api import tvdb_api

try:
    import json
except ImportError:
    from lib import simplejson as json

import xml.etree.cElementTree as etree

import sickbeard

from sickbeard import browser


class Flash:
    _messages = []
    _errors = []

    def message(self, title, detail=''):
        Flash._messages.append((title, detail))

    def error(self, title, detail=''):
        Flash._errors.append((title, detail))

    def messages(self):
        tempMessages = Flash._messages
        Flash._messages = []
        return tempMessages

    def errors(self):
        tempErrors = Flash._errors
        Flash._errors = []
        return tempErrors

flash = Flash()

class PageTemplate (Template):
    def __init__(self, *args, **KWs):
        KWs['file'] = os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/", KWs['file'])
        super(PageTemplate, self).__init__(*args, **KWs)
        self.sbRoot = sickbeard.WEB_ROOT
        self.projectHomePage = "http://code.google.com/p/sickbeard/"

        logPageTitle = 'Logs & Errors'
        if len(classes.ErrorViewer.errors):
            logPageTitle += ' ('+str(len(classes.ErrorViewer.errors))+')'
        
        self.menu = [
            { 'title': 'Home',            'key': 'home'           },
            { 'title': 'Coming Episodes', 'key': 'comingEpisodes' },
            { 'title': 'History',         'key': 'history'        },
            { 'title': 'Manage',          'key': 'manage'         },
            { 'title': 'Config',          'key': 'config'         },
            { 'title': logPageTitle,      'key': 'errorlogs'      },
        ]
        self.flash = Flash()

def redirect(abspath, *args, **KWs):
    assert abspath[0] == '/'
    raise cherrypy.HTTPRedirect(sickbeard.WEB_ROOT + abspath, *args, **KWs)

class TVDBWebUI:
    def __init__(self, config, log=None):
        self.config = config
        self.log = log

    def selectSeries(self, allSeries):
        
        searchList = ",".join([x['id'] for x in allSeries])
        showDirList = ""
        for curShowDir in self.config['_showDir']:
            showDirList += "showDir="+curShowDir+"&"
        redirect("/home/addShows/addShow?" + showDirList + "seriesList=" + searchList)

def _munge(string):
    return unicode(string).encode('ascii', 'xmlcharrefreplace')

def _genericMessage(subject, message):
    t = PageTemplate(file="genericMessage.tmpl")
    t.submenu = HomeMenu
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

ManageMenu = [
            { 'title': 'Manage Searches', 'path': 'manage/manageSearches' },
           #{ 'title': 'Episode Overview', 'path': 'manageShows/episodeOverview' },
            ]

class ManageSearches:

    @cherrypy.expose
    def index(self):
        t = PageTemplate(file="manage_manageSearches.tmpl")
        t.backlogPI = sickbeard.backlogSearchScheduler.action.getProgressIndicator()
        t.backlogPaused = sickbeard.backlogSearchScheduler.action.amPaused
        t.searchStatus = sickbeard.currentSearchScheduler.action.amActive
        t.submenu = ManageMenu
        
        return _munge(t)
        
    @cherrypy.expose
    def forceBacklog(self):

        # force it to run the next time it looks
        sickbeard.backlogSearchScheduler.forceSearch()
        logger.log("Backlog search started in background")
        flash.message('Backlog search started',
                      'The backlog search has begun and will run in the background')
        redirect("/manage/manageSearches")

    @cherrypy.expose
    def forceSearch(self):

        # force it to run the next time it looks
        result = sickbeard.currentSearchScheduler.forceRun()
        if result:
            logger.log("Search forced")
            flash.message('Episode search started',
                          'Note: RSS feeds may not be updated if they have been retrieved too recently')
        
        redirect("/manage/manageSearches")

    @cherrypy.expose
    def pauseBacklog(self, paused=None):
        if paused == "1":
            setPaused = True
        else:
            setPaused = False
        
        sickbeard.backlogSearchScheduler.action.amPaused = setPaused
        
        redirect("/manage/manageSearches")



class Manage:

    manageSearches = ManageSearches()

    @cherrypy.expose
    def index(self):
        
        t = PageTemplate(file="manage.tmpl")
        t.submenu = ManageMenu
        return _munge(t)

    @cherrypy.expose
    def massEdit(self, toEdit=None):
        
        t = PageTemplate(file="manage_massEdit.tmpl")
        t.submenu = ManageMenu

        if not toEdit:
            redirect("/manage")
        
        showIDs = toEdit.split("|")
        showList = []
        for curID in showIDs:
            curID = int(curID)
            showObj = helpers.findCertainShow(sickbeard.showList, curID)
            if showObj:
                showList.append(showObj)

        useSeasonfolders = True
        lastSeasonfolders = None

        usePaused = True
        lastPaused = None

        useQuality = True
        lastQuality = None
        
        for curShow in showList:
            if usePaused:
                if lastPaused == None:
                    lastPaused = curShow.paused
                elif lastPaused != curShow.paused:
                    usePaused = True
        
            if useSeasonfolders:
                if lastSeasonfolders == None:
                    lastSeasonfolders = curShow.seasonfolders
                elif lastSeasonfolders != curShow.seasonfolders:
                    useSeasonfolders = True
        
            if useQuality:
                if lastQuality == None:
                    lastQuality = curShow.quality
                elif lastQuality != curShow.quality:
                    useQuality = True
        
        t.showList = toEdit
        t.pausedValue = lastPaused if usePaused else False
        t.seasonfoldersValue = lastSeasonfolders if useSeasonfolders else False
        t.qualityValue = lastQuality if useQuality else SD
        t.commonPath = os.path.dirname(os.path.commonprefix([x._location for x in showList]))
        
        return _munge(t)
    
    @cherrypy.expose
    def massEditSubmit(self, paused=None, seasonfolders=None, anyQualities=[], bestQualities=[],
                       oldCommonPath=None, newCommonPath=None, toEdit=None):

        showIDs = toEdit.split("|")
        errors = []
        for curShow in showIDs:
            curErrors = []
            showObj = helpers.findCertainShow(sickbeard.showList, int(curShow))
            if not showObj:
                continue
            if oldCommonPath:
                newLocation = showObj._location.replace(oldCommonPath, newCommonPath)
            else:
                newLocation = ek.ek(os.path.join, newCommonPath, showObj._location)
            
            curErrors += Home().editShow(curShow, newLocation, anyQualities, bestQualities, seasonfolders, paused, True)

            if curErrors:
                logger.log("Errors: "+str(curErrors))
                errors.append('<b>%s:</b><br />\n<ul>' % showObj.name + '\n'.join(['<li>%s</li>' % error for error in curErrors]) + "</ul>")
        
        if len(errors) > 0:
            flash.error('%d error%s while saving changes:' % (len(errors), "" if len(errors) == 1 else "s"),
                        "<br />\n".join(errors))

        redirect("/manage")

    @cherrypy.expose
    def massUpdate(self, toUpdate=None, toRefresh=None, toRename=None, toMetadata=None):

        if toUpdate != None:
            toUpdate = toUpdate.split('|')
        else:
            toUpdate = []

        if toRefresh != None:
            toRefresh = toRefresh.split('|')
        else:
            toRefresh = []

        if toRename != None:
            toRename = toRename.split('|')
        else:
            toRename = []

        if toMetadata != None:
            toMetadata = toMetadata.split('|')
        else:
            toMetadata = []

        errors = []
        refreshes = []
        updates = []
        renames = []

        for curShowID in set(toUpdate+toRefresh+toRename+toMetadata):
            
            if curShowID == '':
                continue

            showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(curShowID))
            
            if showObj == None:
                continue

            if curShowID in toUpdate:
                try:
                    sickbeard.showQueueScheduler.action.updateShow(showObj, True)
                    updates.append(showObj.name)
                except exceptions.CantUpdateException, e:
                    errors.append("Unable to update show "+showObj.name+": "+str(e))
            
            if curShowID in toRefresh and curShowID not in toUpdate:
                try:
                    sickbeard.showQueueScheduler.action.refreshShow(showObj)
                    refreshes.append(showObj.name)
                except exceptions.CantRefreshException, e:
                    errors.append("Unable to refresh show "+showObj.name+": "+str(e))

            if curShowID in toRename:
                sickbeard.showQueueScheduler.action.renameShowEpisodes(showObj)
                renames.append(showObj.name)

            
        if len(errors) > 0:
            flash.error("Errors encountered",
                        '<br >\n'.join(errors))

        messageDetail = ""
        
        if len(updates) > 0:
            messageDetail += "<b>Updates</b><br />\n<ul>\n<li>"
            messageDetail += "</li>\n<li>".join(updates)
            messageDetail += "</li>\n</ul>\n<br />"

        if len(refreshes) > 0:
            messageDetail += "<b>Refreshes</b><br />\n<ul>\n<li>"
            messageDetail += "</li>\n<li>".join(refreshes)
            messageDetail += "</li>\n</ul>\n<br />"

        if len(renames) > 0:
            messageDetail += "<b>Renames</b><br />\n<ul>\n<li>"
            messageDetail += "</li>\n<li>".join(renames)
            messageDetail += "</li>\n</ul>\n<br />"

        if len(updates+refreshes+renames) > 0:
            flash.message("The following actions were queued:<br /><br />",
                          messageDetail)

        redirect("/manage")


class History:
    
    @cherrypy.expose
    def index(self):

        myDB = db.DBConnection()
        
#        sqlResults = myDB.select("SELECT h.*, show_name, name FROM history h, tv_shows s, tv_episodes e WHERE h.showid=s.tvdb_id AND h.showid=e.showid AND h.season=e.season AND h.episode=e.episode ORDER BY date DESC LIMIT "+str(numPerPage*(p-1))+", "+str(numPerPage))
        sqlResults = myDB.select("SELECT h.*, show_name FROM history h, tv_shows s WHERE h.showid=s.tvdb_id ORDER BY date DESC")

        t = PageTemplate(file="history.tmpl")
        t.historyResults = sqlResults
        t.submenu = [
            { 'title': 'Clear History', 'path': 'history/clearHistory' },
            { 'title': 'Trim History',  'path': 'history/trimHistory'  },
        ]
        
        return _munge(t)


    @cherrypy.expose
    def clearHistory(self):
        
        myDB = db.DBConnection()
        myDB.action("DELETE FROM history WHERE 1=1")
        flash.message('History cleared')
        redirect("/history")


    @cherrypy.expose
    def trimHistory(self):
        
        myDB = db.DBConnection()
        myDB.action("DELETE FROM history WHERE date < "+str((datetime.datetime.today()-datetime.timedelta(days=30)).strftime(history.dateFormat)))
        flash.message('Removed all history entries greater than 30 days old')
        redirect("/history")


ConfigMenu = [
    { 'title': 'General',           'path': 'config/general/'          },
    { 'title': 'Episode Downloads', 'path': 'config/episodedownloads/' },
    { 'title': 'Search Providers',  'path': 'config/providers/'        },
    { 'title': 'Notifications',     'path': 'config/notifications/'    },
]

class ConfigGeneral:
    
    @cherrypy.expose
    def index(self):
        
        t = PageTemplate(file="config_general.tmpl")
        t.submenu = ConfigMenu
        return _munge(t)

    @cherrypy.expose
    def saveGeneral(self, log_dir=None, web_port=None, web_log=None,
                    launch_browser=None, create_metadata=None, web_username=None,
                    web_password=None, season_folders_default=None,
                    version_notify=None, naming_show_name=None, naming_ep_type=None,
                    naming_multi_ep_type=None, create_images=None, naming_ep_name=None,
                    naming_use_periods=None, naming_sep_type=None, naming_quality=None,
                    anyQualities = [], bestQualities = [], naming_dates=None):

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
            
        if create_images == "on":
            create_images = 1
        else:
            create_images = 0
            
        if season_folders_default == "on":
            season_folders_default = 1
        else:
            season_folders_default = 0
            
        if version_notify == "on":
            version_notify = 1
        else:
            version_notify = 0
            
        if naming_show_name == "on":
            naming_show_name = 1
        else:
            naming_show_name = 0
            
        if naming_ep_name == "on":
            naming_ep_name = 1
        else:
            naming_ep_name = 0
            
        if naming_use_periods == "on":
            naming_use_periods = 1
        else:
            naming_use_periods = 0
            
        if naming_quality == "on":
            naming_quality = 1
        else:
            naming_quality = 0
            
        if naming_dates == "on":
            naming_dates = 1
        else:
            naming_dates = 0
            
        if type(anyQualities) != list:
            anyQualities = [anyQualities]

        if type(bestQualities) != list:
            bestQualities = [bestQualities]

        newQuality = Quality.combineQualities(map(int, anyQualities), map(int, bestQualities))

        if not config.change_LOG_DIR(log_dir):
            results += ["Unable to create directory " + os.path.normpath(log_dir) + ", log dir not changed."]
        
        sickbeard.LAUNCH_BROWSER = launch_browser
        sickbeard.CREATE_METADATA = create_metadata
        sickbeard.CREATE_IMAGES = create_images
        sickbeard.SEASON_FOLDERS_DEFAULT = int(season_folders_default)
        sickbeard.QUALITY_DEFAULT = newQuality

        sickbeard.NAMING_SHOW_NAME = naming_show_name
        sickbeard.NAMING_EP_NAME = naming_ep_name
        sickbeard.NAMING_USE_PERIODS = naming_use_periods
        sickbeard.NAMING_QUALITY = naming_quality
        sickbeard.NAMING_DATES = naming_dates
        sickbeard.NAMING_EP_TYPE = int(naming_ep_type)
        sickbeard.NAMING_MULTI_EP_TYPE = int(naming_multi_ep_type)
        sickbeard.NAMING_SEP_TYPE = int(naming_sep_type)
                    
        sickbeard.WEB_PORT = int(web_port)
        sickbeard.WEB_LOG = web_log
        sickbeard.WEB_USERNAME = web_username
        sickbeard.WEB_PASSWORD = web_password

        config.change_VERSION_NOTIFY(version_notify)

        sickbeard.save_config()
        
        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            flash.error('Error(s) Saving Configuration',
                        '<br />\n'.join(results))
        else:
            flash.message('Configuration Saved')
        
        redirect("/config/general/")


    @cherrypy.expose
    def testNaming(self, show_name=None, ep_type=None, multi_ep_type=None, ep_name=None,
                   sep_type=None, use_periods=None, quality=None, whichTest="single"):
        
        if show_name == None:
            show_name = sickbeard.NAMING_SHOW_NAME
        else:
            if show_name == "0":
                show_name = False
            else:
                show_name = True
            
        if ep_name == None:
            ep_name = sickbeard.NAMING_EP_NAME
        else:
            if ep_name == "0":
                ep_name = False
            else:
                ep_name = True
            
        if use_periods == None:
            use_periods = sickbeard.NAMING_USE_PERIODS
        else:
            if use_periods == "0":
                use_periods = False
            else:
                use_periods = True
            
        if quality == None:
            quality = sickbeard.NAMING_QUALITY
        else:
            if quality == "0":
                quality = False
            else:
                quality = True
            
        if ep_type == None:
            ep_type = sickbeard.NAMING_EP_TYPE
        else:
            ep_type = int(ep_type)
            
        if multi_ep_type == None:
            multi_ep_type = sickbeard.NAMING_MULTI_EP_TYPE
        else:
            multi_ep_type = int(multi_ep_type)
        
        if sep_type == None:
            sep_type = sickbeard.NAMING_SEP_TYPE
        else:
            sep_type = int(sep_type)
            
        class TVShow():
            def __init__(self):
                self.name = "Show Name"
                self.genre = "Comedy"
        
        # fake a TVShow (hack since new TVShow is coming anyway)
        class TVEpisode(tv.TVEpisode):
            def __init__(self, season, episode, name):
                self.relatedEps = []
                self.name = name
                self.season = season
                self.episode = episode
                self.show = TVShow()
                
        
        # make a fake episode object
        ep = TVEpisode(1,2,"Ep Name")
        ep.status = Quality.compositeStatus(DOWNLOADED, Quality.HDTV)
        
        if whichTest == "multi":
            ep.name = "Ep Name (1)"
            secondEp = TVEpisode(1,3,"Ep Name (2)")
            ep.relatedEps.append(secondEp)
        
        # get the name
        name = ep.prettyName(show_name, ep_type, multi_ep_type, ep_name, sep_type, use_periods, quality)
        
        return name

class ConfigEpisodeDownloads:
    
    @cherrypy.expose
    def index(self):
        
        t = PageTemplate(file="config_episodedownloads.tmpl")
        t.submenu = ConfigMenu
        return _munge(t)

    @cherrypy.expose
    def saveEpisodeDownloads(self, nzb_dir=None, sab_username=None, sab_password=None,
                       sab_apikey=None, sab_category=None, sab_host=None, use_nzb=None,
                       use_torrent=None, torrent_dir=None, nzb_method=None, usenet_retention=None,
                       search_frequency=None, backlog_search_frequency=None, tv_download_dir=None,
                       keep_processed_dir=None, process_automatically=None, rename_episodes=None):

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
            
        if rename_episodes == "on":
            rename_episodes = 1
        else:
            rename_episodes = 0
            
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
        sickbeard.RENAME_EPISODES = rename_episodes

        sickbeard.NZB_METHOD = nzb_method
        sickbeard.USENET_RETENTION = int(usenet_retention)
        sickbeard.SEARCH_FREQUENCY = int(search_frequency)

        sickbeard.USE_NZB = use_nzb
        sickbeard.USE_TORRENT = use_torrent

        sickbeard.SAB_USERNAME = sab_username
        sickbeard.SAB_PASSWORD = sab_password
        sickbeard.SAB_APIKEY = sab_apikey.strip()
        sickbeard.SAB_CATEGORY = sab_category
        
        if sab_host.startswith('http://'):
            sickbeard.SAB_HOST = sab_host[7:].rstrip('/')
        else:
            sickbeard.SAB_HOST = sab_host
        
        sickbeard.save_config()
        
        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            flash.error('Error(s) Saving Configuration',
                        '<br />\n'.join(results))
        else:
            flash.message('Configuration Saved')
        
        redirect("/config/episodedownloads/")

class ConfigProviders:
    
    @cherrypy.expose
    def index(self):
        t = PageTemplate(file="config_providers.tmpl")
        t.submenu = ConfigMenu
        return _munge(t)

    @cherrypy.expose
    def canAddNewznabProvider(self, name):
        
        if not name:
            return json.dumps({'error': 'Invalid name specified'})
        
        providerDict = dict(zip([x.getID() for x in sickbeard.newznabProviderList], sickbeard.newznabProviderList))

        tempProvider = newznab.NewznabProvider(name, '')
            
        if tempProvider.getID() in providerDict:
            return json.dumps({'error': 'Exists as '+providerDict[tempProvider.getID()].name})
        else:
            return json.dumps({'success': tempProvider.getID()})

    @cherrypy.expose
    def saveNewznabProvider(self, name, url, key=''):
        
        if not name or not url:
            return '0'
        
        if not url.endswith('/'):
            url = url + '/'
        
        providerDict = dict(zip([x.name for x in sickbeard.newznabProviderList], sickbeard.newznabProviderList))

        if name in providerDict:
            if not providerDict[name].default:
                providerDict[name].name = name
                providerDict[name].url = url
            providerDict[name].key = key

            return providerDict[name].getID() + '|' + providerDict[name].configStr()
        
        else:
        
            newProvider = newznab.NewznabProvider(name, url, key)
            sickbeard.newznabProviderList.append(newProvider)
            return newProvider.getID() + '|' + newProvider.configStr()


    
    @cherrypy.expose
    def deleteNewznabProvider(self, id):

        providerDict = dict(zip([x.getID() for x in sickbeard.newznabProviderList], sickbeard.newznabProviderList))
        
        if id not in providerDict or providerDict[id].default:
            return '0'

        # delete it from the list
        sickbeard.newznabProviderList.remove(providerDict[id])
        
        if id in sickbeard.PROVIDER_ORDER:
            sickbeard.PROVIDER_ORDER.remove(id)

        return '1'

    
    @cherrypy.expose
    def saveProviders(self, tvbinz_uid=None, tvbinz_hash=None, nzbs_org_uid=None,
                      nzbs_org_hash=None, nzbmatrix_username=None, nzbmatrix_apikey=None,
                      tvbinz_auth=None, tvbinz_sabuid=None, provider_order=None,
                      nzbs_r_us_uid=None, nzbs_r_us_hash=None, newznab_string=None):

        results = []

        provider_str_list = provider_order.split()
        provider_list = []
        
        newznabProviderDict = dict(zip([x.getID() for x in sickbeard.newznabProviderList], sickbeard.newznabProviderList))

        finishedNames = []

        # add all the newznab info we got into our list
        for curNewznabProviderStr in newznab_string.split('!!!'):

            if not curNewznabProviderStr:
                continue

            curName, curURL, curKey = curNewznabProviderStr.split('|')

            newProvider = newznab.NewznabProvider(curName, curURL, curKey)
            
            curID = newProvider.getID()
            
            # if it already exists then update it
            if curID in newznabProviderDict:
                newznabProviderDict[curID].name = curName
                newznabProviderDict[curID].url = curURL
                newznabProviderDict[curID].key = curKey
            else:
                sickbeard.newznabProviderList.append(newProvider)

            finishedNames.append(curID)


        # delete anything that is missing
        for curProvider in sickbeard.newznabProviderList:
            if curProvider.getID() not in finishedNames:
                sickbeard.newznabProviderList.remove(curProvider)

        # do the enable/disable
        for curProviderStr in provider_str_list:
            curProvider, curEnabled = curProviderStr.split(':')
            curEnabled = int(curEnabled)
            
            provider_list.append(curProvider)
            
            if curProvider == 'tvbinz':
                if curEnabled or sickbeard.SHOW_TVBINZ:
                    sickbeard.TVBINZ = curEnabled
            elif curProvider == 'nzbs_org':
                sickbeard.NZBS = curEnabled
            elif curProvider == 'nzbs_r_us':
                sickbeard.NZBSRUS = curEnabled
            elif curProvider == 'nzbmatrix':
                sickbeard.NZBMATRIX = curEnabled
            elif curProvider == 'bin_req':
                sickbeard.BINREQ = curEnabled
            elif curProvider == 'eztv_bt_chat':
                sickbeard.USE_TORRENT = curEnabled
            elif curProvider in newznabProviderDict:
                newznabProviderDict[curProvider].enabled = bool(curEnabled)
            else:
                logger.log("don't know what "+curProvider+" is, skipping")

        if tvbinz_uid:
            sickbeard.TVBINZ_UID = tvbinz_uid.strip()
        if tvbinz_sabuid:
            sickbeard.TVBINZ_SABUID = tvbinz_sabuid.strip()
        if tvbinz_hash:
            sickbeard.TVBINZ_HASH = tvbinz_hash.strip()
        if tvbinz_auth:
            sickbeard.TVBINZ_AUTH = tvbinz_auth.strip()
        
        sickbeard.NZBS_UID = nzbs_org_uid.strip()
        sickbeard.NZBS_HASH = nzbs_org_hash.strip()
        
        sickbeard.NZBSRUS_UID = nzbs_r_us_uid.strip()
        sickbeard.NZBSRUS_HASH = nzbs_r_us_hash.strip()
        
        sickbeard.NZBMATRIX_USERNAME = nzbmatrix_username
        sickbeard.NZBMATRIX_APIKEY = nzbmatrix_apikey.strip()
        
        sickbeard.PROVIDER_ORDER = provider_list
        
        sickbeard.save_config()
        
        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            flash.error('Error(s) Saving Configuration',
                        '<br />\n'.join(results))
        else:
            flash.message('Configuration Saved')
        
        redirect("/config/providers/")

class ConfigNotifications:
    
    @cherrypy.expose
    def index(self):
        t = PageTemplate(file="config_notifications.tmpl")
        t.submenu = ConfigMenu
        return _munge(t)
    
    @cherrypy.expose
    def saveNotifications(self, xbmc_notify_onsnatch=None, xbmc_notify_ondownload=None, 
                          xbmc_update_library=None, xbmc_update_full=None, xbmc_host=None, xbmc_username=None, xbmc_password=None,
                          use_growl=None, growl_host=None, growl_password=None, use_twitter=None, twitter_username=None, twitter_password=None, ):

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

        if xbmc_update_full == "on":
            xbmc_update_full = 1
        else:
            xbmc_update_full = 0

        if use_growl == "on":
            use_growl = 1
        else:
            use_growl = 0

	if use_twitter == "on":
	    use_twitter = 1
	else:
	    use_twitter = 0

        sickbeard.XBMC_NOTIFY_ONSNATCH = xbmc_notify_onsnatch 
        sickbeard.XBMC_NOTIFY_ONDOWNLOAD = xbmc_notify_ondownload
        sickbeard.XBMC_UPDATE_LIBRARY = xbmc_update_library
        sickbeard.XBMC_UPDATE_FULL = xbmc_update_full
        sickbeard.XBMC_HOST = xbmc_host
        sickbeard.XBMC_USERNAME = xbmc_username
        sickbeard.XBMC_PASSWORD = xbmc_password
        
        sickbeard.USE_GROWL = use_growl
        sickbeard.GROWL_HOST = growl_host
        sickbeard.GROWL_PASSWORD = growl_password
       
        sickbeard.USE_TWITTER = use_twitter
        sickbeard.TWITTER_USERNAME = twitter_username
        sickbeard.TWITTER_PASSWORD = twitter_password

        sickbeard.save_config()
        
        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            flash.error('Error(s) Saving Configuration',
                        '<br />\n'.join(results))
        else:
            flash.message('Configuration Saved')
        
        redirect("/config/notifications/")


class Config:

    @cherrypy.expose
    def index(self):
        
        t = PageTemplate(file="config.tmpl")
        t.submenu = ConfigMenu
        return _munge(t)
    
    general = ConfigGeneral()
    
    episodedownloads = ConfigEpisodeDownloads()
    
    providers = ConfigProviders()
    
    notifications = ConfigNotifications()

def haveXBMC():
    return sickbeard.XBMC_HOST != None and len(sickbeard.XBMC_HOST) > 0

HomeMenu = [
    { 'title': 'Add Shows',              'path': 'home/addShows/'                           },
    { 'title': 'Manual Post-Processing', 'path': 'home/postprocess/'                        },
    { 'title': 'Update XBMC',            'path': 'home/updateXBMC/', 'requires': haveXBMC   },
    { 'title': 'Shutdown',               'path': 'home/shutdown/'                           },
]

class HomePostProcess:
    
    @cherrypy.expose
    def index(self):
        
        t = PageTemplate(file="home_postprocess.tmpl")
        t.submenu = HomeMenu
        return _munge(t)

    @cherrypy.expose
    def processEpisode(self, dir=None, nzbName=None, jobName=None, quiet=None):
        
        if dir == None:
            redirect("/home/postprocess")
        else:
            result = processTV.processDir(dir, nzbName)
            if quiet != None and int(quiet) == 1:
                return result  
        
            result = result.replace("\n","<br />\n")
            return _genericMessage("Postprocessing results", result)


class NewHomeAddShows:
    
    @cherrypy.expose
    def index(self):
        
        t = PageTemplate(file="home_addShows.tmpl")
        t.submenu = HomeMenu
        return _munge(t)

    @cherrypy.expose
    def searchTVDBForShowName(self, name):
        
        baseURL = "http://thetvdb.com/api/GetSeries.php?" 
        
        params = {'seriesname': name.encode('utf-8'),
                  'language': 'en'}
        
        finalURL = baseURL + urllib.urlencode(params)
        
        urlData = helpers.getURL(finalURL)
        
        try:
            seriesXML = etree.ElementTree(etree.XML(urlData))
        except Exception, e:
            logger.log("Unable to parse XML for some reason: "+str(e)+" from XML: "+urlData, logger.ERROR)
            return ''
        
        series = seriesXML.getiterator('Series')
        
        results = []
        
        for curSeries in series:
            results.append((int(curSeries.findtext('seriesid')), curSeries.findtext('SeriesName'), curSeries.findtext('FirstAired')))
    
        return json.dumps({'results': results})

    @cherrypy.expose
    def addRootDir(self, dir=None):
        if dir == None:
            redirect("/home/addShows")

        if not os.path.isdir(dir):
            logger.log("The provided directory "+dir+" doesn't exist", logger.ERROR)
            flash.error("Unable to find the directory <tt>%s</tt>" % dir)
            redirect("/home/addShows")
        
        showDirs = []
        
        for curDir in os.listdir(unicode(dir)):
            curPath = os.path.join(dir, curDir)
            if os.path.isdir(curPath):
                logger.log("Adding "+curPath+" to the showDir list", logger.DEBUG)
                showDirs.append(curPath)
        
        if len(showDirs) == 0:
            logger.log("The provided directory "+dir+" has no shows in it", logger.ERROR)
            flash.error("The provided root folder <tt>%s</tt> has no shows in it." % dir)
            redirect("/home/addShows")
        
        #result = ui.addShowsFromRootDir(dir)
        
        myTemplate = PageTemplate(file="home_addRootDir.tmpl")
        myTemplate.showDirs = [urllib.quote_plus(x.encode('utf-8')) for x in showDirs]
        myTemplate.submenu = HomeMenu
        return _munge(myTemplate)       
        
        url = "/home/addShows/addShow?"+"&".join(["showDir="+urllib.quote_plus(x.encode('utf-8')) for x in showDirs])
        logger.log("Redirecting to URL "+url, logger.DEBUG)
        redirect(url)
    
    @cherrypy.expose
    def addSingleShow(self, showToAdd, whichSeries=None, skipShow=False, showDirs=[]):
        
        # we don't need to unquote the rest of the showDirs cause we're going to pass them straight through 
        showToAdd = urllib.unquote_plus(showToAdd)

        # if they intentionally skipped the show then oblige them
        if skipShow == "1":
            return self.addShows(showDirs)

        # if we got a TVDB ID then make a show out of it
        sickbeard.showQueueScheduler.action.addShow(int(whichSeries), showToAdd)
        flash.message('Show added', 'Adding the specified show into '+showToAdd)
        # no need to display anything now that we added the show, so continue on to the next show
        return self.addShows(showDirs)

    @cherrypy.expose
    def addShows(self, showDirs=[]):
        
        if showDirs and type(showDirs) != list:
            showDirs = [showDirs]

        # don't allow blank shows
        showDirs = [x for x in showDirs if x]

        # if there's nothing left to add, go home
        if len(showDirs) == 0:
            redirect("/home")
        
        t = PageTemplate(file="home_addShow.tmpl")
        t.submenu = HomeMenu

        # make sure everything's unescaped
        showDirs = [os.path.normpath(urllib.unquote_plus(x)) for x in showDirs]

        # peel off a single show that we'll be working on, leave the rest in a list
        showToAdd = showDirs[0]
        restOfShowDirs = showDirs[1:]

        # if the dir we're given doesn't exist and we can't create it then skip it
        if not helpers.makeDir(showToAdd):
            flash.error("Warning", "Unable to create dir "+showToAdd+", skipping")
            # recursively continue on our way, encoding the input as though we came from the web form
            return self.addShows([urllib.quote_plus(x.encode('utf-8')) for x in restOfShowDirs])
        
        # if there's a tvshow.nfo then try to get a TVDB ID out of it
        if ek.ek(os.path.isfile, ek.ek(os.path.join, showToAdd, "tvshow.nfo")):
            tvdb_id = None
            try:
                tvdb_id = metadata.getTVDBIDFromNFO(showToAdd)
            except exceptions.NoNFOException, e:
                # we couldn't get a tvdb id from the file so let them know and just print the search page
                if ek.ek(os.path.isfile, ek.ek(os.path.join, showToAdd, "tvshow.nfo.old")):
                    flash.error('Warning', 'Unable to retrieve TVDB ID from tvshow.nfo, renamed it to tvshow.nfo.old and ignoring it')

                # no tvshow.nfo.old means we couldn't rename it and we can't continue adding this show
                # encode the input as though we came from the web form
                else:
                    flash.error('Warning', 'Unable to retrieve TVDB ID from tvshow.nfo and unable to rename it - you will need to remove it manually')
                    return self.addShows([urllib.quote_plus(x.encode('utf-8')) for x in restOfShowDirs])
        
            # if we got a TVDB ID then make a show out of it
            if tvdb_id:
                sickbeard.showQueueScheduler.action.addShow(tvdb_id, showToAdd)
                flash.message('Show added', 'Auto-added show from tvshow.nfo in '+showToAdd)
                # no need to display anything now that we added the show, so continue on to the next show
                return self.addShows([urllib.quote_plus(x.encode('utf-8')) for x in restOfShowDirs])
        
        # encode any info we send to the web page
        t.showToAdd = showToAdd
        t.showNameToAdd = os.path.split(showToAdd)[1]
        
        # get the rest so we can pass them along
        t.showDirs = [x for x in restOfShowDirs]
        
        return _munge(t)
        


ErrorLogsMenu = [
    { 'title': 'Clear Errors', 'path': 'errorlogs/clearerrors' },
    { 'title': 'View Log',  'path': 'errorlogs/viewlog'  },
]


class ErrorLogs:
    
    @cherrypy.expose
    def index(self):

        t = PageTemplate(file="errorlogs.tmpl")
        t.submenu = ErrorLogsMenu
        
        return _munge(t)
    

    @cherrypy.expose
    def clearerrors(self):
        classes.ErrorViewer.clear()
        redirect("/errorlogs")

    @cherrypy.expose
    def viewlog(self, minLevel=logger.MESSAGE, maxLines=500):
        
        t = PageTemplate(file="viewlogs.tmpl")
        t.submenu = ErrorLogsMenu

        minLevel = int(minLevel)

        data = []
        if os.path.isfile(logger.logFile):
            f = ek.ek(open, logger.logFile)
            data = f.readlines()
            f.close()

        regex =  "^(\w{3})\-(\d\d)\s*(\d\d)\:(\d\d):(\d\d)\s*([A-Z]+)\s*(.+?)\s*\:\:\s*(.*)$"

        finalData = []

        numLines = 0
        lastLine = False
        numToShow = min(maxLines, len(data))
        
        for x in reversed(data):

            x = x.decode('utf-8')
            match = re.match(regex, x)
            
            if match:
                level = match.group(6)
                if level not in logger.reverseNames:
                    lastLine = False
                    continue
                
                if logger.reverseNames[level] >= minLevel:
                    lastLine = True
                    finalData.append(x)
                else:
                    lastLine = False
                    continue

            elif lastLine:
                finalData.append("AA"+x)
            
            numLines += 1
            
            if numLines >= numToShow:
                break

        result = "".join(finalData)
        
        t.logLines = result
        t.minLevel = minLevel
        
        return _munge(t)


class Home:

    @cherrypy.expose
    def index(self):
        
        t = PageTemplate(file="home.tmpl")
        t.submenu = HomeMenu
        return _munge(t)

    addShows = NewHomeAddShows()
    
    postprocess = HomePostProcess()
    
    @cherrypy.expose
    def testGrowl(self, host=None, password=None):
        notifiers.testGrowl(host, password)
        return "Tried sending growl to "+host+" with password "+password
      
    @cherrypy.expose
    def twitterStep1(self):
        notifiers.testTwitter1()
        return "Getting Twitter Authorization"

    @cherrypy.expose
    def twitterStep2(self, key):
        notifiers.testTwitter2(key)
        return "Getting Twitter creds with key "+key

    @cherrypy.expose
    def testTwitter(self, username=None, password=None):
        notifiers.testTwitter(username, password)
        return "Tried sending tweet"
 
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
        
        sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = " + str(showObj.tvdbid) + " ORDER BY season*1000+episode DESC")

        t = PageTemplate(file="displayShow.tmpl")
        t.submenu = [ { 'title': 'Edit',              'path': 'home/editShow?show=%d'%showObj.tvdbid } ]

        try:
            t.showLoc = (showObj.location, True)
        except sickbeard.exceptions.ShowDirNotFoundException:
            t.showLoc = (showObj._location, False)

        if sickbeard.showQueueScheduler.action.isBeingAdded(showObj):
            flash.message('This show is in the process of being downloaded from theTVDB.com - the info below is incomplete.')
            
        elif sickbeard.showQueueScheduler.action.isBeingUpdated(showObj):
            flash.message('The information below is in the process of being updated.')
        
        elif sickbeard.showQueueScheduler.action.isBeingRefreshed(showObj):
            flash.message('The episodes below are currently being refreshed from disk')
        
        elif sickbeard.showQueueScheduler.action.isInRefreshQueue(showObj):
            flash.message('This show is queued to be refreshed.')
        
        elif sickbeard.showQueueScheduler.action.isInUpdateQueue(showObj):
            flash.message('This show is queued and awaiting an update.')

        if not sickbeard.showQueueScheduler.action.isBeingAdded(showObj):
            if not sickbeard.showQueueScheduler.action.isBeingUpdated(showObj):
                t.submenu.append({ 'title': 'Delete',            'path': 'home/deleteShow?show=%d'%showObj.tvdbid         })
                t.submenu.append({ 'title': 'Re-scan files',           'path': 'home/refreshShow?show=%d'%showObj.tvdbid         })
                t.submenu.append({ 'title': 'Force Full Update', 'path': 'home/updateShow?show=%d&force=1'%showObj.tvdbid })
                t.submenu.append({ 'title': 'Update show in XBMC', 'path': 'home/updateXBMC?showName=%s'%urllib.quote_plus(showObj.name.encode('utf-8')), 'requires': haveXBMC })
            t.submenu.append({ 'title': 'Rename Episodes',   'path': 'home/fixEpisodeNames?show=%d'%showObj.tvdbid        })
        
        t.show = showObj
        t.sqlResults = sqlResults
        
        myDB = db.DBConnection()
        
        epCounts = {}
        epCats = {}
        epCounts[Overview.SKIPPED] = 0
        epCounts[Overview.WANTED] = 0
        epCounts[Overview.QUAL] = 0
        epCounts[Overview.GOOD] = 0
        epCounts[Overview.UNAIRED] = 0

        for curResult in sqlResults:

            curEpCat = showObj.getOverview(int(curResult["status"]))
            epCats[str(curResult["season"])+"x"+str(curResult["episode"])] = curEpCat
            epCounts[curEpCat] += 1
        
        
        t.epCounts = epCounts
        t.epCats = epCats

        return _munge(t)

    @cherrypy.expose
    def plotDetails(self, show, season, episode):
        result = db.DBConnection().action("SELECT description FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?", (show, season, episode)).fetchone()
        return result['description'] if result else 'Episode not found.'

    @cherrypy.expose
    def editShow(self, show=None, location=None, anyQualities=[], bestQualities=[], seasonfolders=None, paused=None, directCall=False, air_by_date=None):
        
        if show == None:
            errString = "Invalid show ID: "+str(show)
            if directCall:
                return [errString]
            else:
                return _genericMessage("Error", errString)
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            errString = "Unable to find the specified show: "+str(show)
            if directCall:
                return [errString]
            else:
                return _genericMessage("Error", errString)

        if not location and not anyQualities and not bestQualities and not seasonfolders:
            
            t = PageTemplate(file="editShow.tmpl")
            t.submenu = HomeMenu
            with showObj.lock:
                t.show = showObj
            
            return _munge(t)
        
        if seasonfolders == "on":
            seasonfolders = 1
        else:
            seasonfolders = 0

        if paused == "on":
            paused = 1
        else:
            paused = 0

        if air_by_date == "on":
            air_by_date = 1
        else:
            air_by_date = 0

        if type(anyQualities) != list:
            anyQualities = [anyQualities]

        if type(bestQualities) != list:
            bestQualities = [bestQualities]

        errors = []
        with showObj.lock:
            newQuality = Quality.combineQualities(map(int, anyQualities), map(int, bestQualities))
            showObj.quality = newQuality
            
            if showObj.seasonfolders != seasonfolders:
                showObj.seasonfolders = seasonfolders
                try:
                    sickbeard.showQueueScheduler.action.refreshShow(showObj)
                except exceptions.CantRefreshException, e:
                    errors.append("Unable to refresh this show: "+str(e))

            showObj.paused = paused
            showObj.air_by_date = air_by_date
                        
            # if we change location clear the db of episodes, change it, write to db, and rescan
            if os.path.normpath(showObj._location) != os.path.normpath(location):
                if not os.path.isdir(location):
                    errors.append("New location <tt>%s</tt> does not exist" % location)

                else:
                    # change it
                    try:
                        showObj.location = location
                        try:
                            sickbeard.showQueueScheduler.action.refreshShow(showObj)
                        except exceptions.CantRefreshException, e:
                            errors.append("Unable to refresh this show:"+str(e))
                        # grab updated info from TVDB
                        #showObj.loadEpisodesFromTVDB()
                        # rescan the episodes in the new folder
                    except exceptions.NoNFOException:
                        errors.append("The folder at <tt>%s</tt> doesn't contain a tvshow.nfo - copy your files to that folder before you change the directory in Sick Beard." % location)
                    
            # save it to the DB
            showObj.saveToDB()

        if directCall:
            return errors

        if len(errors) > 0:
            flash.error('%d error%s while saving changes:' % (len(errors), "" if len(errors) == 1 else "s"),
                        '<ul>' + '\n'.join(['<li>%s</li>' % error for error in errors]) + "</ul>")

        redirect("/home/displayShow?show=" + show)

    @cherrypy.expose
    def deleteShow(self, show=None):

        if show == None:
            return _genericMessage("Error", "Invalid show ID")
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            return _genericMessage("Error", "Unable to find the specified show")

        if sickbeard.showQueueScheduler.action.isBeingAdded(showObj) or \
        sickbeard.showQueueScheduler.action.isBeingUpdated(showObj):
            return _genericMessage("Error", "Shows can't be deleted while they're being added or updated.")

        showObj.deleteShow()
        
        flash.message('<b>%s</b> has been deleted' % showObj.name)
        redirect("/home")

    @cherrypy.expose
    def refreshShow(self, show=None):

        if show == None:
            return _genericMessage("Error", "Invalid show ID")
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            return _genericMessage("Error", "Unable to find the specified show")
        
        # force the update from the DB
        try:
            sickbeard.showQueueScheduler.action.refreshShow(showObj)
        except exceptions.CantRefreshException, e:
            flash.error("Unable to refresh this show.",
                        str(e))

        time.sleep(3)

        redirect("/home/displayShow?show="+str(showObj.tvdbid))

    @cherrypy.expose
    def updateShow(self, show=None, force=0):
        
        if show == None:
            return _genericMessage("Error", "Invalid show ID")
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            return _genericMessage("Error", "Unable to find the specified show")
        
        # force the update
        try:
            sickbeard.showQueueScheduler.action.updateShow(showObj, bool(force))
        except exceptions.CantUpdateException, e:
            flash.error("Unable to update this show.",
                        str(e))
        
        # just give it some time
        time.sleep(3)
        
        redirect("/home/displayShow?show="+str(showObj.tvdbid))


    @cherrypy.expose
    def updateXBMC(self, showName=None):

        for curHost in [x.strip() for x in sickbeard.XBMC_HOST.split(",")]:
            if xbmc.updateLibrary(curHost, showName=showName):
                flash.message("Command sent to XBMC host " + curHost + " to update library")
            else:
                flash.error("Unable to contact XBMC host " + curHost)
        redirect('/home')


    @cherrypy.expose
    def fixEpisodeNames(self, show=None):
        
        if show == None:
            return _genericMessage("Error", "Invalid show ID")
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        
        if showObj == None:
            return _genericMessage("Error", "Unable to find the specified show")
        
        if sickbeard.showQueueScheduler.action.isBeingAdded(showObj):
            return _genericMessage("Error", "Show is still being added, wait until it is finished before you rename files")
        
        showObj.fixEpisodeNames()

        redirect("/home/displayShow?show=" + show)
        
    @cherrypy.expose
    def setStatus(self, show=None, eps=None, status=None, direct=False):
        
        if show == None or eps == None or status == None:
            errMsg = "You must specify a show and at least one episode"
            if direct:
                flash.error('Error', errMsg)
                return json.dumps({'result': 'error'})
            else:
                return _genericMessage("Error", errMsg)
        
        if not statusStrings.has_key(int(status)):
            errMsg = "Invalid status"
            if direct:
                flash.error('Error', errMsg)
                return json.dumps({'result': 'error'})
            else:
                return _genericMessage("Error", errMsg)
        
        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

        if showObj == None:
            errMsg = "Error", "Show not in show list"
            if direct:
                flash.error('Error', errMsg)
                return json.dumps({'result': 'error'})
            else:
                return _genericMessage("Error", errMsg)

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
                    
                    if int(status) in Quality.DOWNLOADED and epObj.status not in Quality.SNATCHED + Quality.SNATCHED_PROPER + Quality.DOWNLOADED:
                        logger.log("Refusing to change status of "+curEp+" to DOWNLOADED because it's not SNATCHED/DOWNLOADED", logger.ERROR)
                        continue

                    epObj.status = int(status)
                    epObj.saveToDB()
                    
        if direct:
            return json.dumps({'result': 'success'})
        else:
            redirect("/home/displayShow?show=" + show)

    @cherrypy.expose
    def searchEpisode(self, show=None, season=None, episode=None):
        
        outStr = ""
        epObj = _getEpisode(show, season, episode)
        
        if isinstance(epObj, str):
            return _genericMessage("Error", epObj)
        
        tempStr = "Searching for download for " + epObj.prettyName(True)
        logger.log(tempStr)
        outStr += tempStr + "<br />\n"
        foundEpisode = search.findEpisode(epObj, manualSearch=True)
        
        if not foundEpisode:
            message = 'No downloads were found'
            flash.error(message, "Couldn't find a download for <i>%s</i>" % epObj.prettyName(True))
            logger.log(message)
        
        else:

            # just use the first result for now
            logger.log("Downloading episode from " + foundEpisode.url)
            result = search.snatchEpisode(foundEpisode)
            providerModule = foundEpisode.provider
            if providerModule == None:
                flash.error('Provider is configured incorrectly, unable to download')
            else: 
                flash.message('Episode <b>%s</b> snatched from <b>%s</b>' % (foundEpisode.name, providerModule.name))
            
            #TODO: check if the download was successful

            # update our lists to reflect the result if this search
            sickbeard.updateAiringList()
            sickbeard.updateComingList()

        redirect("/home/displayShow?show=" + str(epObj.show.tvdbid))



class WebInterface:
    
    @cherrypy.expose
    def index(self):
        
        redirect("/home")

    @cherrypy.expose
    def showPoster(self, show=None):
        
        if show == None:
            return "Invalid show" #TODO: make it return a standard image
        else:
            showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
            
        if showObj == None:
            return "Unable to find show" #TODO: make it return a standard image
    
        posterFilename = os.path.abspath(os.path.join(showObj.location, "folder.jpg"))
        if os.path.isfile(posterFilename):
            
            return cherrypy.lib.static.serve_file(posterFilename, content_type="image/jpeg")
        
        else:
            logger.log("No poster for show "+show.name, logger.WARNING) #TODO: make it return a standard image

    @cherrypy.expose
    def comingEpisodes(self):

        epList = sickbeard.comingList

        # sort by air date
        epList.sort(lambda x, y: cmp(x.airdate.toordinal(), y.airdate.toordinal()))
        
        t = PageTemplate(file="comingEpisodes.tmpl")
        t.submenu = [
            { 'title': 'Sort by Date', 'path': 'comingEpisodes/#' },
            { 'title': 'Sort by Show', 'path': 'comingEpisodes/#' },
        ]
        t.epList = epList
        
        return _munge(t)

    manage = Manage()

    history = History()

    config = Config()

    home = Home()

    browser = browser.WebFileBrowser()

    errorlogs = ErrorLogs()
