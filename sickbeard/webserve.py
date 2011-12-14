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
import random

from Cheetah.Template import Template
import cherrypy.lib

import sickbeard

from sickbeard import config, sab
from sickbeard import history, notifiers, processTV
from sickbeard import tv, ui
from sickbeard import logger, helpers, exceptions, classes, db
from sickbeard import encodingKludge as ek
from sickbeard import search_queue
from sickbeard import image_cache

from sickbeard.providers import newznab
from sickbeard.common import Quality, Overview, statusStrings
from sickbeard.common import SNATCHED, DOWNLOADED, SKIPPED, UNAIRED, IGNORED, ARCHIVED, WANTED
from sickbeard.exceptions import ex
from sickbeard.webapi import Api

from lib.tvdb_api import tvdb_api

try:
    import json
except ImportError:
    from lib import simplejson as json

import xml.etree.cElementTree as etree

from sickbeard import browser


class PageTemplate (Template):
    def __init__(self, *args, **KWs):
        KWs['file'] = os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/", KWs['file'])
        super(PageTemplate, self).__init__(*args, **KWs)
        self.sbRoot = sickbeard.WEB_ROOT
        self.projectHomePage = "http://code.google.com/p/sickbeard/"

        logPageTitle = 'Logs &amp; Errors'
        if len(classes.ErrorViewer.errors):
            logPageTitle += ' ('+str(len(classes.ErrorViewer.errors))+')'
        self.logPageTitle = logPageTitle
        self.sbPID = str(sickbeard.PID)
        self.menu = [
            { 'title': 'Home',            'key': 'home'           },
            { 'title': 'Coming Episodes', 'key': 'comingEpisodes' },
            { 'title': 'History',         'key': 'history'        },
            { 'title': 'Manage',          'key': 'manage'         },
            { 'title': 'Config',          'key': 'config'         },
            { 'title': logPageTitle,      'key': 'errorlogs'      },
        ]

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
    return unicode(string).encode('utf-8', 'xmlcharrefreplace')

def _genericMessage(subject, message):
    t = PageTemplate(file="genericMessage.tmpl")
    t.submenu = HomeMenu()
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
    { 'title': 'Backlog Overview',          'path': 'manage/backlogOverview' },
    { 'title': 'Manage Searches',           'path': 'manage/manageSearches'  },
    { 'title': 'Episode Status Management', 'path': 'manage/episodeStatuses' },
]

class ManageSearches:

    @cherrypy.expose
    def index(self):
        t = PageTemplate(file="manage_manageSearches.tmpl")
        #t.backlogPI = sickbeard.backlogSearchScheduler.action.getProgressIndicator()
        t.backlogPaused = sickbeard.searchQueueScheduler.action.is_backlog_paused() #@UndefinedVariable
        t.backlogRunning = sickbeard.searchQueueScheduler.action.is_backlog_in_progress() #@UndefinedVariable
        t.searchStatus = sickbeard.currentSearchScheduler.action.amActive #@UndefinedVariable
        t.submenu = ManageMenu

        return _munge(t)

    @cherrypy.expose
    def forceSearch(self):

        # force it to run the next time it looks
        result = sickbeard.currentSearchScheduler.forceRun()
        if result:
            logger.log(u"Search forced")
            ui.notifications.message('Episode search started',
                          'Note: RSS feeds may not be updated if retrieved recently')

        redirect("/manage/manageSearches")

    @cherrypy.expose
    def pauseBacklog(self, paused=None):
        if paused == "1":
            sickbeard.searchQueueScheduler.action.pause_backlog() #@UndefinedVariable
        else:
            sickbeard.searchQueueScheduler.action.unpause_backlog() #@UndefinedVariable

        redirect("/manage/manageSearches")

    @cherrypy.expose
    def forceVersionCheck(self):

        # force a check to see if there is a new version
        result = sickbeard.versionCheckScheduler.action.check_for_new_version(force=True) #@UndefinedVariable
        if result:
            logger.log(u"Forcing version check")

        redirect("/manage/manageSearches")


class Manage:

    manageSearches = ManageSearches()

    @cherrypy.expose
    def index(self):

        t = PageTemplate(file="manage.tmpl")
        t.submenu = ManageMenu
        return _munge(t)

    @cherrypy.expose
    def showEpisodeStatuses(self, tvdb_id, whichStatus):
        myDB = db.DBConnection()

        status_list = [int(whichStatus)]
        if status_list[0] == SNATCHED:
            status_list = Quality.SNATCHED + Quality.SNATCHED_PROPER
        
        cur_show_results = myDB.select("SELECT season, episode, name FROM tv_episodes WHERE showid = ? AND season != 0 AND status IN ("+','.join(['?']*len(status_list))+")", [int(tvdb_id)] + status_list)
        
        result = {}
        for cur_result in cur_show_results:
            cur_season = int(cur_result["season"])
            cur_episode = int(cur_result["episode"])
            
            if cur_season not in result:
                result[cur_season] = {}
            
            result[cur_season][cur_episode] = cur_result["name"]
        
        return json.dumps(result)

    @cherrypy.expose
    def episodeStatuses(self, whichStatus=None):

        if whichStatus:
            whichStatus = int(whichStatus)
            status_list = [whichStatus]
            if status_list[0] == SNATCHED:
                status_list = Quality.SNATCHED + Quality.SNATCHED_PROPER
        else:
            status_list = []
        
        t = PageTemplate(file="manage_episodeStatuses.tmpl")
        t.submenu = ManageMenu
        t.whichStatus = whichStatus

        # if we have no status then this is as far as we need to go
        if not status_list:
            return _munge(t)
        
        myDB = db.DBConnection()
        status_results = myDB.select("SELECT show_name, tv_shows.tvdb_id as tvdb_id FROM tv_episodes, tv_shows WHERE tv_episodes.status IN ("+','.join(['?']*len(status_list))+") AND season != 0 AND tv_episodes.showid = tv_shows.tvdb_id ORDER BY show_name", status_list)

        ep_counts = {}
        show_names = {}
        sorted_show_ids = []
        for cur_status_result in status_results:
            cur_tvdb_id = int(cur_status_result["tvdb_id"])
            if cur_tvdb_id not in ep_counts:
                ep_counts[cur_tvdb_id] = 1
            else:
                ep_counts[cur_tvdb_id] += 1
        
            show_names[cur_tvdb_id] = cur_status_result["show_name"]
            if cur_tvdb_id not in sorted_show_ids:
                sorted_show_ids.append(cur_tvdb_id)
        
        t.show_names = show_names
        t.ep_counts = ep_counts
        t.sorted_show_ids = sorted_show_ids
        return _munge(t)

    @cherrypy.expose
    def changeEpisodeStatuses(self, oldStatus, newStatus, *args, **kwargs):
        
        status_list = [int(oldStatus)]
        if status_list[0] == SNATCHED:
            status_list = Quality.SNATCHED + Quality.SNATCHED_PROPER

        to_change = {}
        
        # make a list of all shows and their associated args
        for arg in kwargs:
            tvdb_id, what = arg.split('-')
            
            # we don't care about unchecked checkboxes
            if kwargs[arg] != 'on':
                continue
            
            if tvdb_id not in to_change:
                to_change[tvdb_id] = []
            
            to_change[tvdb_id].append(what)
        
        myDB = db.DBConnection()

        for cur_tvdb_id in to_change:

            # get a list of all the eps we want to change if they just said "all"
            if 'all' in to_change[cur_tvdb_id]:
                all_eps_results = myDB.select("SELECT season, episode FROM tv_episodes WHERE status IN ("+','.join(['?']*len(status_list))+") AND season != 0 AND showid = ?", status_list + [cur_tvdb_id])
                all_eps = [str(x["season"])+'x'+str(x["episode"]) for x in all_eps_results]
                to_change[cur_tvdb_id] = all_eps

            Home().setStatus(cur_tvdb_id, '|'.join(to_change[cur_tvdb_id]), newStatus, direct=True)
            
        redirect('/manage/episodeStatuses')

    @cherrypy.expose
    def backlogShow(self, tvdb_id):
        
        show_obj = helpers.findCertainShow(sickbeard.showList, int(tvdb_id))
        
        if show_obj:
            sickbeard.backlogSearchScheduler.action.searchBacklog([show_obj]) #@UndefinedVariable
        
        redirect("/manage/backlogOverview")
        
    @cherrypy.expose
    def backlogOverview(self):

        t = PageTemplate(file="manage_backlogOverview.tmpl")
        t.submenu = ManageMenu

        myDB = db.DBConnection()

        showCounts = {}
        showCats = {}
        showSQLResults = {}

        for curShow in sickbeard.showList:

            epCounts = {}
            epCats = {}
            epCounts[Overview.SKIPPED] = 0
            epCounts[Overview.WANTED] = 0
            epCounts[Overview.QUAL] = 0
            epCounts[Overview.GOOD] = 0
            epCounts[Overview.UNAIRED] = 0

            sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? ORDER BY season*1000+episode DESC", [curShow.tvdbid])

            for curResult in sqlResults:

                curEpCat = curShow.getOverview(int(curResult["status"]))
                epCats[str(curResult["season"])+"x"+str(curResult["episode"])] = curEpCat
                epCounts[curEpCat] += 1

            showCounts[curShow.tvdbid] = epCounts
            showCats[curShow.tvdbid] = epCats
            showSQLResults[curShow.tvdbid] = sqlResults

        t.showCounts = showCounts
        t.showCats = showCats
        t.showSQLResults = showSQLResults

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

        season_folders_all_same = True
        last_season_folders = None

        paused_all_same = True
        last_paused = None

        quality_all_same = True
        last_quality = None

        root_dir_list = []

        for curShow in showList:
            
            cur_root_dir = ek.ek(os.path.dirname, curShow._location)
            if cur_root_dir not in root_dir_list:
                root_dir_list.append(cur_root_dir) 
            
            # if we know they're not all the same then no point even bothering
            if paused_all_same:
                # if we had a value already and this value is different then they're not all the same
                if last_paused not in (curShow.paused, None):
                    paused_all_same = False
                else:
                    last_paused = curShow.paused

            if season_folders_all_same:
                if last_season_folders not in (None, curShow.seasonfolders):
                    season_folders_all_same = False
                else:
                    last_season_folders = curShow.seasonfolders

            if quality_all_same:
                if last_quality not in (None, curShow.quality):
                    quality_all_same = False
                else:
                    last_quality = curShow.quality

        t.showList = toEdit
        t.paused_value = last_paused if paused_all_same else None
        t.season_folders_value = last_season_folders if season_folders_all_same else None
        t.quality_value = last_quality if quality_all_same else None
        t.root_dir_list = root_dir_list

        return _munge(t)

    @cherrypy.expose
    def massEditSubmit(self, paused=None, season_folders=None, quality_preset=False,
                       anyQualities=[], bestQualities=[], toEdit=None, *args, **kwargs):

        dir_map = {}
        for cur_arg in kwargs:
            if not cur_arg.startswith('orig_root_dir_'):
                continue
            which_index = cur_arg.replace('orig_root_dir_', '')
            end_dir = kwargs['new_root_dir_'+which_index]
            dir_map[kwargs[cur_arg]] = end_dir

        showIDs = toEdit.split("|")
        errors = []
        for curShow in showIDs:
            curErrors = []
            showObj = helpers.findCertainShow(sickbeard.showList, int(curShow))
            if not showObj:
                continue

            cur_root_dir = ek.ek(os.path.dirname, showObj._location)
            cur_show_dir = ek.ek(os.path.basename, showObj._location)
            if cur_root_dir in dir_map and cur_root_dir != dir_map[cur_root_dir]:
                new_show_dir = ek.ek(os.path.join, dir_map[cur_root_dir], cur_show_dir)
                logger.log(u"For show "+showObj.name+" changing dir from "+showObj._location+" to "+new_show_dir)
            else:
                new_show_dir = showObj._location
            
            if paused == 'keep':
                new_paused = showObj.paused
            else:
                new_paused = True if paused == 'enable' else False
            new_paused = 'on' if new_paused else 'off'

            if season_folders == 'keep':
                new_season_folders = showObj.seasonfolders
            else:
                new_season_folders = True if season_folders == 'enable' else False
            new_season_folders = 'on' if new_season_folders else 'off'

            if quality_preset == 'keep':
                anyQualities, bestQualities = Quality.splitQuality(showObj.quality)
            
            curErrors += Home().editShow(curShow, new_show_dir, anyQualities, bestQualities, new_season_folders, new_paused, directCall=True)

            if curErrors:
                logger.log(u"Errors: "+str(curErrors), logger.ERROR)
                errors.append('<b>%s:</b><br />\n<ul>' % showObj.name + '\n'.join(['<li>%s</li>' % error for error in curErrors]) + "</ul>")

        if len(errors) > 0:
            ui.notifications.error('%d error%s while saving changes:' % (len(errors), "" if len(errors) == 1 else "s"),
                        "<br />\n".join(errors))

        redirect("/manage")

    @cherrypy.expose
    def massUpdate(self, toUpdate=None, toRefresh=None, toRename=None, toDelete=None, toMetadata=None):

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

        if toDelete != None:
            toDelete = toDelete.split('|')
        else:
            toDelete = []

        if toMetadata != None:
            toMetadata = toMetadata.split('|')
        else:
            toMetadata = []

        errors = []
        refreshes = []
        updates = []
        renames = []

        for curShowID in set(toUpdate+toRefresh+toRename+toDelete+toMetadata):

            if curShowID == '':
                continue

            showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(curShowID))

            if showObj == None:
                continue

            if curShowID in toDelete:
                showObj.deleteShow()
                # don't do anything else if it's being deleted
                continue

            if curShowID in toUpdate:
                try:
                    sickbeard.showQueueScheduler.action.updateShow(showObj, True) #@UndefinedVariable
                    updates.append(showObj.name)
                except exceptions.CantUpdateException, e:
                    errors.append("Unable to update show "+showObj.name+": "+ex(e))

            # don't bother refreshing shows that were updated anyway
            if curShowID in toRefresh and curShowID not in toUpdate:
                try:
                    sickbeard.showQueueScheduler.action.refreshShow(showObj) #@UndefinedVariable
                    refreshes.append(showObj.name)
                except exceptions.CantRefreshException, e:
                    errors.append("Unable to refresh show "+showObj.name+": "+ex(e))

            if curShowID in toRename:
                sickbeard.showQueueScheduler.action.renameShowEpisodes(showObj) #@UndefinedVariable
                renames.append(showObj.name)

        if len(errors) > 0:
            ui.notifications.error("Errors encountered",
                        '<br >\n'.join(errors))

        messageDetail = ""

        if len(updates) > 0:
            messageDetail += "<br /><b>Updates</b><br /><ul><li>"
            messageDetail += "</li><li>".join(updates)
            messageDetail += "</li></ul>"

        if len(refreshes) > 0:
            messageDetail += "<br /><b>Refreshes</b><br /><ul><li>"
            messageDetail += "</li><li>".join(refreshes)
            messageDetail += "</li></ul>"

        if len(renames) > 0:
            messageDetail += "<br /><b>Renames</b><br /><ul><li>"
            messageDetail += "</li><li>".join(renames)
            messageDetail += "</li></ul>"

        if len(updates+refreshes+renames) > 0:
            ui.notifications.message("The following actions were queued:",
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
        ui.notifications.message('History cleared')
        redirect("/history")


    @cherrypy.expose
    def trimHistory(self):

        myDB = db.DBConnection()
        myDB.action("DELETE FROM history WHERE date < "+str((datetime.datetime.today()-datetime.timedelta(days=30)).strftime(history.dateFormat)))
        ui.notifications.message('Removed history entries greater than 30 days old')
        redirect("/history")


ConfigMenu = [
    { 'title': 'General',           'path': 'config/general/'          },
    { 'title': 'Search Settings',   'path': 'config/search/'           },
    { 'title': 'Search Providers',  'path': 'config/providers/'        },
    { 'title': 'Post Processing',   'path': 'config/postProcessing/'   },
    { 'title': 'Notifications',     'path': 'config/notifications/'    },
]

class ConfigGeneral:

    @cherrypy.expose
    def index(self):

        t = PageTemplate(file="config_general.tmpl")
        t.submenu = ConfigMenu
        return _munge(t)

    @cherrypy.expose
    def saveRootDirs(self, rootDirString=None):
        sickbeard.ROOT_DIRS = rootDirString
    
    @cherrypy.expose
    def saveAddShowDefaults(self, defaultSeasonFolders, defaultStatus, anyQualities, bestQualities):

        if anyQualities:
            anyQualities = anyQualities.split(',')
        else:
            anyQualities = []

        if bestQualities:
            bestQualities = bestQualities.split(',')
        else:
            bestQualities = []

        newQuality = Quality.combineQualities(map(int, anyQualities), map(int, bestQualities))
        
        sickbeard.STATUS_DEFAULT = int(defaultStatus)
        sickbeard.QUALITY_DEFAULT = int(newQuality)

        if defaultSeasonFolders == "true":
            defaultSeasonFolders = 1
        else:
            defaultSeasonFolders = 0

        sickbeard.SEASON_FOLDERS_DEFAULT = int(defaultSeasonFolders)

    @cherrypy.expose
    def generateKey(self):
        """ Return a new randomized API_KEY
        """

        try:
            from hashlib import md5
        except ImportError:
            from md5 import md5
        
        # Create some values to seed md5
        t = str(time.time())
        r = str(random.random())
        
        # Create the md5 instance and give it the current time
        m = md5(t)
        
        # Update the md5 instance with the random variable
        m.update(r)

        # Return a hex digest of the md5, eg 49f68a5c8493ec2c0bf489821c21fc3b
        logger.log(u"New API generated")
        return m.hexdigest()

    @cherrypy.expose
    def saveGeneral(self, log_dir=None, web_port=None, web_log=None, web_ipv6=None,
                    launch_browser=None, web_username=None, use_api=None, api_key=None,
                    web_password=None, version_notify=None):

        results = []

        if web_ipv6 == "on":
            web_ipv6 = 1
        else:
            web_ipv6 = 0

        if web_log == "on":
            web_log = 1
        else:
            web_log = 0

        if launch_browser == "on":
            launch_browser = 1
        else:
            launch_browser = 0

        if version_notify == "on":
            version_notify = 1
        else:
            version_notify = 0

        if not config.change_LOG_DIR(log_dir):
            results += ["Unable to create directory " + os.path.normpath(log_dir) + ", log dir not changed."]

        sickbeard.LAUNCH_BROWSER = launch_browser

        sickbeard.WEB_PORT = int(web_port)
        sickbeard.WEB_IPV6 = web_ipv6
        sickbeard.WEB_LOG = web_log
        sickbeard.WEB_USERNAME = web_username
        sickbeard.WEB_PASSWORD = web_password

        if use_api == "on":
            use_api = 1
        else:
            use_api = 0

        sickbeard.USE_API = use_api
        sickbeard.API_KEY = api_key

        config.change_VERSION_NOTIFY(version_notify)

        sickbeard.save_config()

        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                        '<br />\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek.ek(os.path.join, sickbeard.CONFIG_FILE) )

        redirect("/config/general/")


class ConfigSearch:

    @cherrypy.expose
    def index(self):

        t = PageTemplate(file="config_search.tmpl")
        t.submenu = ConfigMenu
        return _munge(t)

    @cherrypy.expose
    def saveSearch(self, use_nzbs=None, use_torrents=None, nzb_dir=None, sab_username=None, sab_password=None,
                       sab_apikey=None, sab_category=None, sab_host=None, nzbget_password=None, nzbget_category=None, nzbget_host=None,
                       torrent_dir=None, nzb_method=None, usenet_retention=None, search_frequency=None, download_propers=None):

        results = []

        if not config.change_NZB_DIR(nzb_dir):
            results += ["Unable to create directory " + os.path.normpath(nzb_dir) + ", dir not changed."]

        if not config.change_TORRENT_DIR(torrent_dir):
            results += ["Unable to create directory " + os.path.normpath(torrent_dir) + ", dir not changed."]

        config.change_SEARCH_FREQUENCY(search_frequency)

        if download_propers == "on":
            download_propers = 1
        else:
            download_propers = 0

        if use_nzbs == "on":
            use_nzbs = 1
        else:
            use_nzbs = 0

        if use_torrents == "on":
            use_torrents = 1
        else:
            use_torrents = 0

        if usenet_retention == None:
            usenet_retention = 200

        sickbeard.USE_NZBS = use_nzbs
        sickbeard.USE_TORRENTS = use_torrents

        sickbeard.NZB_METHOD = nzb_method
        sickbeard.USENET_RETENTION = int(usenet_retention)

        sickbeard.DOWNLOAD_PROPERS = download_propers

        sickbeard.SAB_USERNAME = sab_username
        sickbeard.SAB_PASSWORD = sab_password
        sickbeard.SAB_APIKEY = sab_apikey.strip()
        sickbeard.SAB_CATEGORY = sab_category

        if sab_host and not re.match('https?://.*', sab_host):
            sab_host = 'http://' + sab_host

        if not sab_host.endswith('/'):
            sab_host = sab_host + '/'

        sickbeard.SAB_HOST = sab_host

        sickbeard.NZBGET_PASSWORD = nzbget_password
        sickbeard.NZBGET_CATEGORY = nzbget_category
        sickbeard.NZBGET_HOST = nzbget_host


        sickbeard.save_config()

        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                        '<br />\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek.ek(os.path.join, sickbeard.CONFIG_FILE) )

        redirect("/config/search/")

class ConfigPostProcessing:

    @cherrypy.expose
    def index(self):

        t = PageTemplate(file="config_postProcessing.tmpl")
        t.submenu = ConfigMenu
        return _munge(t)

    @cherrypy.expose
    def savePostProcessing(self, season_folders_format=None, naming_show_name=None, naming_ep_type=None,
                    naming_multi_ep_type=None, naming_ep_name=None, naming_use_periods=None,
                    naming_sep_type=None, naming_quality=None, naming_dates=None,
                    xbmc_data=None, mediabrowser_data=None, sony_ps3_data=None, wdtv_data=None, tivo_data=None,
                    use_banner=None, keep_processed_dir=None, process_automatically=None, rename_episodes=None,
                    move_associated_files=None, tv_download_dir=None):

        results = []

        if not config.change_TV_DOWNLOAD_DIR(tv_download_dir):
            results += ["Unable to create directory " + os.path.normpath(tv_download_dir) + ", dir not changed."]

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

        if use_banner == "on":
            use_banner = 1
        else:
            use_banner = 0

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

        if move_associated_files == "on":
            move_associated_files = 1
        else:
            move_associated_files = 0

        sickbeard.PROCESS_AUTOMATICALLY = process_automatically
        sickbeard.KEEP_PROCESSED_DIR = keep_processed_dir
        sickbeard.RENAME_EPISODES = rename_episodes
        sickbeard.MOVE_ASSOCIATED_FILES = move_associated_files

        sickbeard.metadata_provider_dict['XBMC'].set_config(xbmc_data)
        sickbeard.metadata_provider_dict['MediaBrowser'].set_config(mediabrowser_data)
        sickbeard.metadata_provider_dict['Sony PS3'].set_config(sony_ps3_data)
        sickbeard.metadata_provider_dict['WDTV'].set_config(wdtv_data)
        sickbeard.metadata_provider_dict['TIVO'].set_config(tivo_data)
        
        sickbeard.SEASON_FOLDERS_FORMAT = season_folders_format

        sickbeard.NAMING_SHOW_NAME = naming_show_name
        sickbeard.NAMING_EP_NAME = naming_ep_name
        sickbeard.NAMING_USE_PERIODS = naming_use_periods
        sickbeard.NAMING_QUALITY = naming_quality
        sickbeard.NAMING_DATES = naming_dates
        sickbeard.NAMING_EP_TYPE = int(naming_ep_type)
        sickbeard.NAMING_MULTI_EP_TYPE = int(naming_multi_ep_type)
        sickbeard.NAMING_SEP_TYPE = int(naming_sep_type)

        sickbeard.USE_BANNER = use_banner

        sickbeard.save_config()

        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                        '<br />\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek.ek(os.path.join, sickbeard.CONFIG_FILE) )

        redirect("/config/postProcessing/")

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
                self.air_by_date = 0

        # fake a TVShow (hack since new TVShow is coming anyway)
        class TVEpisode(tv.TVEpisode):
            def __init__(self, season, episode, name):
                self.relatedEps = []
                self._name = name
                self._season = season
                self._episode = episode
                self.show = TVShow()


        # make a fake episode object
        ep = TVEpisode(1,2,"Ep Name")
        ep._status = Quality.compositeStatus(DOWNLOADED, Quality.HDTV)

        if whichTest == "multi":
            ep._name = "Ep Name (1)"
            secondEp = TVEpisode(1,3,"Ep Name (2)")
            ep.relatedEps.append(secondEp)

        # get the name
        name = ep.prettyName(show_name, ep_type, multi_ep_type, ep_name, sep_type, use_periods, quality)

        return name

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
    def saveProviders(self, nzbs_org_uid=None, nzbs_org_hash=None,
                      nzbmatrix_username=None, nzbmatrix_apikey=None,
                      nzbs_r_us_uid=None, nzbs_r_us_hash=None, newznab_string=None,
                      tvtorrents_digest=None, tvtorrents_hash=None, 
                      newzbin_username=None, newzbin_password=None,
                      provider_order=None):

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

            if curProvider == 'nzbs_org':
                sickbeard.NZBS = curEnabled
            elif curProvider == 'nzbs_r_us':
                sickbeard.NZBSRUS = curEnabled
            elif curProvider == 'nzbmatrix':
                sickbeard.NZBMATRIX = curEnabled
            elif curProvider == 'newzbin':
                sickbeard.NEWZBIN = curEnabled
            elif curProvider == 'bin_req':
                sickbeard.BINREQ = curEnabled
            elif curProvider == 'womble_s_index':
                sickbeard.WOMBLE = curEnabled
            elif curProvider == 'ezrss':
                sickbeard.EZRSS = curEnabled
            elif curProvider == 'tvtorrents':
                sickbeard.TVTORRENTS = curEnabled
            elif curProvider in newznabProviderDict:
                newznabProviderDict[curProvider].enabled = bool(curEnabled)
            else:
                logger.log(u"don't know what "+curProvider+" is, skipping")

        sickbeard.TVTORRENTS_DIGEST = tvtorrents_digest.strip()
        sickbeard.TVTORRENTS_HASH = tvtorrents_hash.strip()

        sickbeard.NZBS_UID = nzbs_org_uid.strip()
        sickbeard.NZBS_HASH = nzbs_org_hash.strip()

        sickbeard.NZBSRUS_UID = nzbs_r_us_uid.strip()
        sickbeard.NZBSRUS_HASH = nzbs_r_us_hash.strip()

        sickbeard.NZBMATRIX_USERNAME = nzbmatrix_username
        sickbeard.NZBMATRIX_APIKEY = nzbmatrix_apikey.strip()

        sickbeard.NEWZBIN_USERNAME = newzbin_username
        sickbeard.NEWZBIN_PASSWORD = newzbin_password

        sickbeard.PROVIDER_ORDER = provider_list

        sickbeard.save_config()

        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                        '<br />\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek.ek(os.path.join, sickbeard.CONFIG_FILE) )

        redirect("/config/providers/")

class ConfigNotifications:

    @cherrypy.expose
    def index(self):
        t = PageTemplate(file="config_notifications.tmpl")
        t.submenu = ConfigMenu
        return _munge(t)

    @cherrypy.expose
    def saveNotifications(self, use_xbmc=None, xbmc_notify_onsnatch=None, xbmc_notify_ondownload=None,
                          xbmc_update_library=None, xbmc_update_full=None, xbmc_host=None, xbmc_username=None, xbmc_password=None,
                          use_plex=None, plex_notify_onsnatch=None, plex_notify_ondownload=None, plex_update_library=None,
                          plex_server_host=None, plex_host=None, plex_username=None, plex_password=None,
                          use_growl=None, growl_notify_onsnatch=None, growl_notify_ondownload=None, growl_host=None, growl_password=None, 
                          use_prowl=None, prowl_notify_onsnatch=None, prowl_notify_ondownload=None, prowl_api=None, prowl_priority=0, 
                          use_twitter=None, twitter_notify_onsnatch=None, twitter_notify_ondownload=None, 
                          use_notifo=None, notifo_notify_onsnatch=None, notifo_notify_ondownload=None, notifo_username=None, notifo_apisecret=None,
                          use_boxcar=None, boxcar_notify_onsnatch=None, boxcar_notify_ondownload=None, boxcar_username=None,
                          use_libnotify=None, libnotify_notify_onsnatch=None, libnotify_notify_ondownload=None,
                          use_nmj=None, nmj_host=None, nmj_database=None, nmj_mount=None, use_synoindex=None,
                          use_trakt=None, trakt_username=None, trakt_password=None, trakt_api=None):

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

        if use_xbmc == "on":
            use_xbmc = 1
        else:
            use_xbmc = 0

        if plex_update_library == "on":
            plex_update_library = 1
        else:
            plex_update_library = 0

        if plex_notify_onsnatch == "on":
            plex_notify_onsnatch = 1
        else:
            plex_notify_onsnatch = 0

        if plex_notify_ondownload == "on":
            plex_notify_ondownload = 1
        else:
            plex_notify_ondownload = 0

        if use_plex == "on":
            use_plex = 1
        else:
            use_plex = 0

        if growl_notify_onsnatch == "on":
            growl_notify_onsnatch = 1
        else:
            growl_notify_onsnatch = 0

        if growl_notify_ondownload == "on":
            growl_notify_ondownload = 1
        else:
            growl_notify_ondownload = 0

        if use_growl == "on":
            use_growl = 1
        else:
            use_growl = 0
            
        if prowl_notify_onsnatch == "on":
            prowl_notify_onsnatch = 1
        else:
            prowl_notify_onsnatch = 0

        if prowl_notify_ondownload == "on":
            prowl_notify_ondownload = 1
        else:
            prowl_notify_ondownload = 0
        if use_prowl == "on":
            use_prowl = 1
        else:
            use_prowl = 0

        if twitter_notify_onsnatch == "on":
            twitter_notify_onsnatch = 1
        else:
            twitter_notify_onsnatch = 0

        if twitter_notify_ondownload == "on":
            twitter_notify_ondownload = 1
        else:
            twitter_notify_ondownload = 0
        if use_twitter == "on":
            use_twitter = 1
        else:
            use_twitter = 0

        if notifo_notify_onsnatch == "on":
            notifo_notify_onsnatch = 1
        else:
            notifo_notify_onsnatch = 0

        if notifo_notify_ondownload == "on":
            notifo_notify_ondownload = 1
        else:
            notifo_notify_ondownload = 0
        if use_notifo == "on":
            use_notifo = 1
        else:
            use_notifo = 0

        if boxcar_notify_onsnatch == "on":
            boxcar_notify_onsnatch = 1
        else:
            boxcar_notify_onsnatch = 0

        if boxcar_notify_ondownload == "on":
            boxcar_notify_ondownload = 1
        else:
            boxcar_notify_ondownload = 0
        if use_boxcar == "on":
            use_boxcar = 1
        else:
            use_boxcar = 0

        if use_nmj == "on":
            use_nmj = 1
        else:
            use_nmj = 0

        if use_synoindex == "on":
            use_synoindex = 1
        else:
            use_synoindex = 0

        if use_trakt == "on":
            use_trakt = 1
        else:
            use_trakt = 0

        sickbeard.USE_XBMC = use_xbmc
        sickbeard.XBMC_NOTIFY_ONSNATCH = xbmc_notify_onsnatch
        sickbeard.XBMC_NOTIFY_ONDOWNLOAD = xbmc_notify_ondownload
        sickbeard.XBMC_UPDATE_LIBRARY = xbmc_update_library
        sickbeard.XBMC_UPDATE_FULL = xbmc_update_full
        sickbeard.XBMC_HOST = xbmc_host
        sickbeard.XBMC_USERNAME = xbmc_username
        sickbeard.XBMC_PASSWORD = xbmc_password

        sickbeard.USE_PLEX = use_plex
        sickbeard.PLEX_NOTIFY_ONSNATCH = plex_notify_onsnatch
        sickbeard.PLEX_NOTIFY_ONDOWNLOAD = plex_notify_ondownload
        sickbeard.PLEX_UPDATE_LIBRARY = plex_update_library
        sickbeard.PLEX_HOST = plex_host
        sickbeard.PLEX_SERVER_HOST = plex_server_host
        sickbeard.PLEX_USERNAME = plex_username
        sickbeard.PLEX_PASSWORD = plex_password

        sickbeard.USE_GROWL = use_growl
        sickbeard.GROWL_NOTIFY_ONSNATCH = growl_notify_onsnatch
        sickbeard.GROWL_NOTIFY_ONDOWNLOAD = growl_notify_ondownload
        sickbeard.GROWL_HOST = growl_host
        sickbeard.GROWL_PASSWORD = growl_password

        sickbeard.USE_PROWL = use_prowl
        sickbeard.PROWL_NOTIFY_ONSNATCH = prowl_notify_onsnatch
        sickbeard.PROWL_NOTIFY_ONDOWNLOAD = prowl_notify_ondownload
        sickbeard.PROWL_API = prowl_api
        sickbeard.PROWL_PRIORITY = prowl_priority

        sickbeard.USE_TWITTER = use_twitter
        sickbeard.TWITTER_NOTIFY_ONSNATCH = twitter_notify_onsnatch
        sickbeard.TWITTER_NOTIFY_ONDOWNLOAD = twitter_notify_ondownload

        sickbeard.USE_NOTIFO = use_notifo
        sickbeard.NOTIFO_NOTIFY_ONSNATCH = notifo_notify_onsnatch
        sickbeard.NOTIFO_NOTIFY_ONDOWNLOAD = notifo_notify_ondownload
        sickbeard.NOTIFO_USERNAME = notifo_username
        sickbeard.NOTIFO_APISECRET = notifo_apisecret

        sickbeard.USE_BOXCAR = use_boxcar
        sickbeard.BOXCAR_NOTIFY_ONSNATCH = boxcar_notify_onsnatch
        sickbeard.BOXCAR_NOTIFY_ONDOWNLOAD = boxcar_notify_ondownload
        sickbeard.BOXCAR_USERNAME = boxcar_username

        sickbeard.USE_LIBNOTIFY = use_libnotify == "on"
        sickbeard.LIBNOTIFY_NOTIFY_ONSNATCH = libnotify_notify_onsnatch == "on"
        sickbeard.LIBNOTIFY_NOTIFY_ONDOWNLOAD = libnotify_notify_ondownload == "on"

        sickbeard.USE_NMJ = use_nmj
        sickbeard.NMJ_HOST = nmj_host
        sickbeard.NMJ_DATABASE = nmj_database
        sickbeard.NMJ_MOUNT = nmj_mount

        sickbeard.USE_SYNOINDEX = use_synoindex

        sickbeard.USE_TRAKT = use_trakt
        sickbeard.TRAKT_USERNAME = trakt_username
        sickbeard.TRAKT_PASSWORD = trakt_password
        sickbeard.TRAKT_API = trakt_api

        sickbeard.save_config()

        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                        '<br />\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek.ek(os.path.join, sickbeard.CONFIG_FILE) )

        redirect("/config/notifications/")


class Config:

    @cherrypy.expose
    def index(self):

        t = PageTemplate(file="config.tmpl")
        t.submenu = ConfigMenu
        return _munge(t)

    general = ConfigGeneral()

    search = ConfigSearch()
    
    postProcessing = ConfigPostProcessing()

    providers = ConfigProviders()

    notifications = ConfigNotifications()

def haveXBMC():
    return sickbeard.XBMC_HOST

def havePLEX():
    return sickbeard.PLEX_SERVER_HOST

def HomeMenu():
    return [
        { 'title': 'Add Shows',              'path': 'home/addShows/',                                          },
        { 'title': 'Manual Post-Processing', 'path': 'home/postprocess/'                                        },
        { 'title': 'Update XBMC',            'path': 'home/updateXBMC/', 'requires': haveXBMC                   },
        { 'title': 'Update Plex',            'path': 'home/updatePLEX/', 'requires': havePLEX                   },
        { 'title': 'Restart',                'path': 'home/restart/?pid='+str(sickbeard.PID), 'confirm': True   },
        { 'title': 'Shutdown',               'path': 'home/shutdown/', 'confirm': True                          },
    ]

class HomePostProcess:

    @cherrypy.expose
    def index(self):

        t = PageTemplate(file="home_postprocess.tmpl")
        t.submenu = HomeMenu()
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
        t.submenu = HomeMenu()
        return _munge(t)

    @cherrypy.expose
    def getTVDBLanguages(self):
        result = tvdb_api.Tvdb().config['valid_languages']

        # Make sure list is sorted alphabetically but 'en' is in front
        if 'en' in result:
            del result[result.index('en')]
        result.sort()
        result.insert(0,'en')

        return json.dumps({'results': result})

    @cherrypy.expose
    def sanitizeFileName(self, name):
        return helpers.sanitizeFileName(name)

    @cherrypy.expose
    def searchTVDBForShowName(self, name, lang="en"):
        if not lang or lang == 'null':
                lang = "en"

        baseURL = "http://thetvdb.com/api/GetSeries.php?"

        params = {'seriesname': name.encode('utf-8'),
                  'language': lang}

        finalURL = baseURL + urllib.urlencode(params)

        urlData = helpers.getURL(finalURL)

        try:
            seriesXML = etree.ElementTree(etree.XML(urlData))
        except Exception, e:
            logger.log(u"Unable to parse XML for some reason: "+ex(e)+" from XML: "+urlData, logger.ERROR)
            return ''

        series = seriesXML.getiterator('Series')

        results = []

        for curSeries in series:
            results.append((int(curSeries.findtext('seriesid')), curSeries.findtext('SeriesName'), curSeries.findtext('FirstAired')))

        lang_id = tvdb_api.Tvdb().config['langabbv_to_id'][lang]

        return json.dumps({'results': results, 'langid': lang_id})

    @cherrypy.expose
    def massAddTable(self, rootDir=None):
        t = PageTemplate(file="home_massAddTable.tmpl")
        t.submenu = HomeMenu()
        
        myDB = db.DBConnection()

        if not rootDir:
            return "No folders selected." 
        elif type(rootDir) != list:
            root_dirs = [rootDir]
        else:
            root_dirs = rootDir
        
        root_dirs = [urllib.unquote_plus(x) for x in root_dirs]

        default_index = int(sickbeard.ROOT_DIRS.split('|')[0])
        if len(root_dirs) > default_index:
            tmp = root_dirs[default_index]
            if tmp in root_dirs:
                root_dirs.remove(tmp)
                root_dirs = [tmp]+root_dirs
        
        dir_list = []
        
        for root_dir in root_dirs:
            try:
                file_list = ek.ek(os.listdir, root_dir)
            except:
                continue

            for cur_file in file_list:

                cur_path = ek.ek(os.path.normpath, ek.ek(os.path.join, root_dir, cur_file))
                if not ek.ek(os.path.isdir, cur_path):
                    continue
                
                cur_dir = {
                           'dir': cur_path,
                           'display_dir': '<b>'+ek.ek(os.path.dirname, cur_path)+os.sep+'</b>'+ek.ek(os.path.basename, cur_path),
                           }
                
                # see if the folder is in XBMC already
                dirResults = myDB.select("SELECT * FROM tv_shows WHERE location = ?", [cur_path])
                
                if dirResults:
                    cur_dir['added_already'] = True
                else:
                    cur_dir['added_already'] = False
                
                dir_list.append(cur_dir)
                
                tvdb_id = ''
                show_name = ''
                for cur_provider in sickbeard.metadata_provider_dict.values():
                    (tvdb_id, show_name) = cur_provider.retrieveShowMetadata(cur_path)
                    if tvdb_id and show_name:
                        break
                
                cur_dir['existing_info'] = (tvdb_id, show_name)
                
                if tvdb_id and helpers.findCertainShow(sickbeard.showList, tvdb_id):
                    cur_dir['added_already'] = True 

        t.dirList = dir_list
        
        return _munge(t)

    @cherrypy.expose
    def newShow(self, show_to_add=None, other_shows=None):
        """
        Display the new show page which collects a tvdb id, folder, and extra options and
        posts them to addNewShow
        """
        t = PageTemplate(file="home_newShow.tmpl")
        t.submenu = HomeMenu()
        
        show_dir, tvdb_id, show_name = self.split_extra_show(show_to_add)
        
        if tvdb_id and show_name:
            use_provided_info = True
        else:
            use_provided_info = False
        
        # tell the template whether we're giving it show name & TVDB ID
        t.use_provided_info = use_provided_info
        
        # use the given show_dir for the tvdb search if available 
        if not show_dir:
            t.default_show_name = ''
        elif not show_name:
            t.default_show_name = ek.ek(os.path.basename, ek.ek(os.path.normpath, show_dir)).replace('.',' ')
        else:
            t.default_show_name = show_name
        
        # carry a list of other dirs if given
        if not other_shows:
            other_shows = []
        elif type(other_shows) != list:
            other_shows = [other_shows]
        
        if use_provided_info:
            t.provided_tvdb_id = tvdb_id
            t.provided_tvdb_name = show_name
            
        t.provided_show_dir = show_dir
        t.other_shows = other_shows
        
        return _munge(t)

    @cherrypy.expose
    def addNewShow(self, whichSeries=None, tvdbLang="en", rootDir=None, defaultStatus=None,
                   anyQualities=None, bestQualities=None, seasonFolders=None, fullShowPath=None,
                   other_shows=None, skipShow=None):
        """
        Receive tvdb id, dir, and other options and create a show from them. If extra show dirs are
        provided then it forwards back to newShow, if not it goes to /home.
        """
        
        # grab our list of other dirs if given
        if not other_shows:
            other_shows = []
        elif type(other_shows) != list:
            other_shows = [other_shows]
            
        def finishAddShow(): 
            # if there are no extra shows then go home
            if not other_shows:
                redirect('/home')
            
            # peel off the next one
            next_show_dir = other_shows[0]
            rest_of_show_dirs = other_shows[1:]
            
            # go to add the next show
            return self.newShow(next_show_dir, rest_of_show_dirs)
        
        # if we're skipping then behave accordingly
        if skipShow:
            return finishAddShow()
        
        # sanity check on our inputs
        if (not rootDir and not fullShowPath) or not whichSeries:
            return "Missing params, no tvdb id or folder:"+repr(whichSeries)+" and "+repr(rootDir)+"/"+repr(fullShowPath)
        
        # figure out what show we're adding and where
        series_pieces = whichSeries.partition('|')
        if len(series_pieces) < 3:
            return "Error with show selection."
        
        tvdb_id = int(series_pieces[0])
        show_name = series_pieces[2]
        
        # use the whole path if it's given, or else append the show name to the root dir to get the full show path
        if fullShowPath:
            show_dir = ek.ek(os.path.normpath, fullShowPath)
        else:
            show_dir = ek.ek(os.path.join, rootDir, helpers.sanitizeFileName(show_name))
        
        # blanket policy - if the dir exists you should have used "add existing show" numbnuts
        if ek.ek(os.path.isdir, show_dir) and not fullShowPath:
            ui.notifications.error("Unable to add show", "Folder "+show_dir+" exists already")
            redirect('/home')
        
        # create the dir and make sure it worked
        dir_exists = helpers.makeDir(show_dir)
        if not dir_exists:
            logger.log(u"Unable to create the folder "+show_dir+", can't add the show", logger.ERROR)
            ui.notifications.error("Unable to add show", "Unable to create the folder "+show_dir+", can't add the show")
            redirect("/home")
        else:
            helpers.chmodAsParent(show_dir)

        # prepare the inputs for passing along
        if seasonFolders == "on":
            seasonFolders = 1
        else:
            seasonFolders = 0
        
        if not anyQualities:
            anyQualities = []
        if not bestQualities:
            bestQualities = []
        if type(anyQualities) != list:
            anyQualities = [anyQualities]
        if type(bestQualities) != list:
            bestQualities = [bestQualities]
        newQuality = Quality.combineQualities(map(int, anyQualities), map(int, bestQualities))
        
        # add the show
        sickbeard.showQueueScheduler.action.addShow(tvdb_id, show_dir, int(defaultStatus), newQuality, seasonFolders, tvdbLang) #@UndefinedVariable
        ui.notifications.message('Show added', 'Adding the specified show into '+show_dir)

        return finishAddShow()
        

    @cherrypy.expose
    def existingShows(self):
        """
        Prints out the page to add existing shows from a root dir 
        """
        t = PageTemplate(file="home_addExistingShow.tmpl")
        t.submenu = HomeMenu()
        
        return _munge(t)

    def split_extra_show(self, extra_show):
        if not extra_show:
            return (None, None, None)
        split_vals = extra_show.split('|')
        if len(split_vals) < 3:
            return (extra_show, None, None)
        show_dir = split_vals[0]
        tvdb_id = split_vals[1]
        show_name = '|'.join(split_vals[2:])
        
        return (show_dir, tvdb_id, show_name)

    @cherrypy.expose
    def addExistingShows(self, shows_to_add=None, promptForSettings=None):
        """
        Receives a dir list and add them. Adds the ones with given TVDB IDs first, then forwards
        along to the newShow page.
        """

        # grab a list of other shows to add, if provided
        if not shows_to_add:
            shows_to_add = []
        elif type(shows_to_add) != list:
            shows_to_add = [shows_to_add]
        
        shows_to_add = [urllib.unquote_plus(x) for x in shows_to_add]
        
        if promptForSettings == "on":
            promptForSettings = 1
        else:
            promptForSettings = 0
        
        tvdb_id_given = []
        dirs_only = []
        # separate all the ones with TVDB IDs
        for cur_dir in shows_to_add:
            if not '|' in cur_dir:
                dirs_only.append(cur_dir)
            else:
                show_dir, tvdb_id, show_name = self.split_extra_show(cur_dir)
                if not show_dir or not tvdb_id or not show_name:
                    continue
                tvdb_id_given.append((show_dir, int(tvdb_id), show_name))


        # if they want me to prompt for settings then I will just carry on to the newShow page
        if promptForSettings and shows_to_add:
            return self.newShow(shows_to_add[0], shows_to_add[1:])
        
        # if they don't want me to prompt for settings then I can just add all the nfo shows now
        num_added = 0
        for cur_show in tvdb_id_given:
            show_dir, tvdb_id, show_name = cur_show

            # add the show
            sickbeard.showQueueScheduler.action.addShow(tvdb_id, show_dir, SKIPPED, sickbeard.QUALITY_DEFAULT, sickbeard.SEASON_FOLDERS_DEFAULT) #@UndefinedVariable
            num_added += 1
         
        if num_added:
            ui.notifications.message("Shows Added", "Automatically added "+str(num_added)+" from their existing metadata files")

        # if we're done then go home
        if not dirs_only:
            redirect('/home')

        # for the remaining shows we need to prompt for each one, so forward this on to the newShow page
        return self.newShow(dirs_only[0], dirs_only[1:])




ErrorLogsMenu = [
    { 'title': 'Clear Errors', 'path': 'errorlogs/clearerrors' },
    #{ 'title': 'View Log',  'path': 'errorlogs/viewlog'  },
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
        if os.path.isfile(logger.sb_log_instance.log_file):
            f = ek.ek(open, logger.sb_log_instance.log_file)
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
    def is_alive(self):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        if sickbeard.started:
            return str(sickbeard.PID)
        else:
            return "nope"

    @cherrypy.expose
    def index(self):

        t = PageTemplate(file="home.tmpl")
        t.submenu = HomeMenu()
        return _munge(t)

    addShows = NewHomeAddShows()

    postprocess = HomePostProcess()

    @cherrypy.expose
    def testSABnzbd(self, host=None, username=None, password=None, apikey=None):
        connection, accesMsg = sab.getSabAccesMethod(host, username, password, apikey)
        if connection:
            authed, authMsg = sab.testAuthentication(host, username, password, apikey) #@UnusedVariable
            if authed:
                return "Success. Connected and authenticated"
            else:
                return "Authentication failed. SABnzbd expects '"+accesMsg+"' as authentication method"
        else:
            return "Unable to connect to host"

    @cherrypy.expose
    def testGrowl(self, host=None, password=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.growl_notifier.test_notify(host, password)
        if password==None or password=='':
            pw_append = ''
        else:
            pw_append = " with password: " + password

        if result:
            return "Registered and Tested growl successfully "+urllib.unquote_plus(host)+pw_append
        else:
            return "Registration and Testing of growl failed "+urllib.unquote_plus(host)+pw_append

    @cherrypy.expose
    def testProwl(self, prowl_api=None, prowl_priority=0):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.prowl_notifier.test_notify(prowl_api, prowl_priority)
        if result:
            return "Test prowl notice sent successfully"
        else:
            return "Test prowl notice failed"

    @cherrypy.expose
    def testNotifo(self, username=None, apisecret=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.notifo_notifier.test_notify(username, apisecret)
        if result:
            return "Notifo notification succeeded. Check your Notifo clients to make sure it worked"
        else:
            return "Error sending Notifo notification"

    @cherrypy.expose
    def testBoxcar(self, username=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.boxcar_notifier.test_notify(username)
        if result:
            return "Boxcar notification succeeded. Check your Boxcar clients to make sure it worked"
        else:
            return "Error sending Boxcar notification"

    @cherrypy.expose
    def twitterStep1(self):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        return notifiers.twitter_notifier._get_authorization()

    @cherrypy.expose
    def twitterStep2(self, key):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.twitter_notifier._get_credentials(key)
        logger.log(u"result: "+str(result))
        if result:
            return "Key verification successful"
        else:
            return "Unable to verify key"

    @cherrypy.expose
    def testTwitter(self):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.twitter_notifier.test_notify()
        if result:
            return "Tweet successful, check your twitter to make sure it worked"
        else:
            return "Error sending tweet"

    @cherrypy.expose
    def testXBMC(self, host=None, username=None, password=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.xbmc_notifier.test_notify(urllib.unquote_plus(host), username, password)
        if len(result.split(":")) > 2 and 'OK' in result.split(":")[2]:
            return "Test notice sent successfully to "+urllib.unquote_plus(host)
        else:
            return "Test notice failed to "+urllib.unquote_plus(host)

    @cherrypy.expose
    def testPLEX(self, host=None, username=None, password=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.plex_notifier.test_notify(urllib.unquote_plus(host), username, password)
        if result:
            return "Test notice sent successfully to "+urllib.unquote_plus(host)
        else:
            return "Test notice failed to "+urllib.unquote_plus(host)

    @cherrypy.expose
    def testLibnotify(self):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        if notifiers.libnotify_notifier.test_notify():
            return "Tried sending desktop notification via libnotify"
        else:
            return notifiers.libnotify.diagnose()

    @cherrypy.expose
    def testNMJ(self, host=None, database=None, mount=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.nmj_notifier.test_notify(urllib.unquote_plus(host), database, mount)
        if result:
            return "Successfull started the scan update"
        else:
            return "Test failed to start the scan update"

    @cherrypy.expose
    def settingsNMJ(self, host=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.nmj_notifier.notify_settings(urllib.unquote_plus(host))
        if result:
            return '{"message": "Got settings from %(host)s", "database": "%(database)s", "mount": "%(mount)s"}' % {"host": host, "database": sickbeard.NMJ_DATABASE, "mount": sickbeard.NMJ_MOUNT}
        else:
            return '{"message": "Failed! Make sure your Popcorn is on and NMJ is running. (see Log & Errors -> Debug for detailed info)", "database": "", "mount": ""}'

    @cherrypy.expose
    def testTrakt(self, api=None, username=None, password=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.trakt_notifier.test_notify(api, username, password)
        if result:
            return "Test notice sent successfully to Trakt"
        else:
            return "Test notice failed to Trakt"


    @cherrypy.expose
    def shutdown(self):

        threading.Timer(2, sickbeard.invoke_shutdown).start()

        title = "Shutting down"
        message = "Sick Beard is shutting down..."

        return _genericMessage(title, message)

    @cherrypy.expose
    def restart(self, pid=None):

        if str(pid) != str(sickbeard.PID):
            redirect("/home")

        t = PageTemplate(file="restart.tmpl")
        t.submenu = HomeMenu()

        # do a soft restart
        threading.Timer(2, sickbeard.invoke_restart, [False]).start()

        return _munge(t)

    @cherrypy.expose
    def update(self, pid=None):

        if str(pid) != str(sickbeard.PID):
            redirect("/home")

        updated = sickbeard.versionCheckScheduler.action.update() #@UndefinedVariable

        if updated:
            # do a hard restart
            threading.Timer(2, sickbeard.invoke_restart, [False]).start()
            t = PageTemplate(file="restart_bare.tmpl")
            return _munge(t)
        else:
            return _genericMessage("Update Failed","Update wasn't successful, not restarting. Check your log for more information.")

    @cherrypy.expose
    def displayShow(self, show=None):

        if show == None:
            return _genericMessage("Error", "Invalid show ID")
        else:
            showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

            if showObj == None:

                return _genericMessage("Error", "Unable to find the specified show.")

        myDB = db.DBConnection()

        seasonResults = myDB.select(
            "SELECT DISTINCT season FROM tv_episodes WHERE showid = ? ORDER BY season desc",
            [showObj.tvdbid]
        )

        sqlResults = myDB.select(
            "SELECT * FROM tv_episodes WHERE showid = ? ORDER BY season*1000+episode DESC",
            [showObj.tvdbid]
        )

        t = PageTemplate(file="displayShow.tmpl")
        t.submenu = [ { 'title': 'Edit', 'path': 'home/editShow?show=%d'%showObj.tvdbid } ]

        try:
            t.showLoc = (showObj.location, True)
        except sickbeard.exceptions.ShowDirNotFoundException:
            t.showLoc = (showObj._location, False)

        show_message = ''

        if sickbeard.showQueueScheduler.action.isBeingAdded(showObj): #@UndefinedVariable
            show_message = 'This show is in the process of being downloaded from theTVDB.com - the info below is incomplete.'

        elif sickbeard.showQueueScheduler.action.isBeingUpdated(showObj): #@UndefinedVariable
            show_message = 'The information below is in the process of being updated.'

        elif sickbeard.showQueueScheduler.action.isBeingRefreshed(showObj): #@UndefinedVariable
            show_message = 'The episodes below are currently being refreshed from disk'

        elif sickbeard.showQueueScheduler.action.isInRefreshQueue(showObj): #@UndefinedVariable
            show_message = 'This show is queued to be refreshed.'

        elif sickbeard.showQueueScheduler.action.isInUpdateQueue(showObj): #@UndefinedVariable
            show_message = 'This show is queued and awaiting an update.'

        if not sickbeard.showQueueScheduler.action.isBeingAdded(showObj): #@UndefinedVariable
            if not sickbeard.showQueueScheduler.action.isBeingUpdated(showObj): #@UndefinedVariable
                t.submenu.append({ 'title': 'Delete',               'path': 'home/deleteShow?show=%d'%showObj.tvdbid, 'confirm': True })
                t.submenu.append({ 'title': 'Re-scan files',        'path': 'home/refreshShow?show=%d'%showObj.tvdbid })
                t.submenu.append({ 'title': 'Force Full Update',    'path': 'home/updateShow?show=%d&amp;force=1'%showObj.tvdbid })
                t.submenu.append({ 'title': 'Update show in XBMC',  'path': 'home/updateXBMC?showName=%s'%urllib.quote_plus(showObj.name.encode('utf-8')), 'requires': haveXBMC })
                t.submenu.append({ 'title': 'Rename Episodes',      'path': 'home/fixEpisodeNames?show=%d'%showObj.tvdbid, 'confirm': True })

        t.show = showObj
        t.sqlResults = sqlResults
        t.seasonResults = seasonResults
        t.show_message = show_message

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

        def titler(x):
            if not x:
                return x
            if x.lower().startswith('a '):
                    x = x[2:]
            elif x.lower().startswith('the '):
                    x = x[4:]
            return x
        t.sortedShowList = sorted(sickbeard.showList, lambda x, y: cmp(titler(x.name), titler(y.name)))

        t.epCounts = epCounts
        t.epCats = epCats

        return _munge(t)

    @cherrypy.expose
    def plotDetails(self, show, season, episode):
        result = db.DBConnection().action("SELECT description FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?", (show, season, episode)).fetchone()
        return result['description'] if result else 'Episode not found.'

    @cherrypy.expose
    def editShow(self, show=None, location=None, anyQualities=[], bestQualities=[], seasonfolders=None, paused=None, directCall=False, air_by_date=None, tvdbLang=None):

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
            t.submenu = HomeMenu()
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

        if tvdbLang and tvdbLang in tvdb_api.Tvdb().config['valid_languages']:
            tvdb_lang = tvdbLang
        else:
            tvdb_lang = showObj.lang

        # if we changed the language then kick off an update
        if tvdb_lang == showObj.lang:
            do_update = False
        else:
            do_update = True

        if type(anyQualities) != list:
            anyQualities = [anyQualities]

        if type(bestQualities) != list:
            bestQualities = [bestQualities]

        errors = []
        with showObj.lock:
            newQuality = Quality.combineQualities(map(int, anyQualities), map(int, bestQualities))
            showObj.quality = newQuality

            if bool(showObj.seasonfolders) != bool(seasonfolders):
                showObj.seasonfolders = seasonfolders
                try:
                    sickbeard.showQueueScheduler.action.refreshShow(showObj) #@UndefinedVariable
                except exceptions.CantRefreshException, e:
                    errors.append("Unable to refresh this show: "+ex(e))

            showObj.paused = paused
            showObj.air_by_date = air_by_date
            showObj.lang = tvdb_lang

            # if we change location clear the db of episodes, change it, write to db, and rescan
            if os.path.normpath(showObj._location) != os.path.normpath(location):
                logger.log(os.path.normpath(showObj._location)+" != "+os.path.normpath(location))
                if not ek.ek(os.path.isdir, location):
                    errors.append("New location <tt>%s</tt> does not exist" % location)

                # don't bother if we're going to update anyway
                elif not do_update:
                    # change it
                    try:
                        showObj.location = location
                        try:
                            sickbeard.showQueueScheduler.action.refreshShow(showObj) #@UndefinedVariable
                        except exceptions.CantRefreshException, e:
                            errors.append("Unable to refresh this show:"+ex(e))
                        # grab updated info from TVDB
                        #showObj.loadEpisodesFromTVDB()
                        # rescan the episodes in the new folder
                    except exceptions.NoNFOException:
                        errors.append("The folder at <tt>%s</tt> doesn't contain a tvshow.nfo - copy your files to that folder before you change the directory in Sick Beard." % location)

            # save it to the DB
            showObj.saveToDB()

        # force the update
        if do_update:
            try:
                sickbeard.showQueueScheduler.action.updateShow(showObj, True) #@UndefinedVariable
                time.sleep(1)
            except exceptions.CantUpdateException, e:
                errors.append("Unable to force an update on the show.")

        if directCall:
            return errors

        if len(errors) > 0:
            ui.notifications.error('%d error%s while saving changes:' % (len(errors), "" if len(errors) == 1 else "s"),
                        '<ul>' + '\n'.join(['<li>%s</li>' % error for error in errors]) + "</ul>")

        redirect("/home/displayShow?show=" + show)

    @cherrypy.expose
    def deleteShow(self, show=None):

        if show == None:
            return _genericMessage("Error", "Invalid show ID")

        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

        if showObj == None:
            return _genericMessage("Error", "Unable to find the specified show")

        if sickbeard.showQueueScheduler.action.isBeingAdded(showObj) or sickbeard.showQueueScheduler.action.isBeingUpdated(showObj): #@UndefinedVariable
            return _genericMessage("Error", "Shows can't be deleted while they're being added or updated.")

        showObj.deleteShow()

        ui.notifications.message('<b>%s</b> has been deleted' % showObj.name)
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
            sickbeard.showQueueScheduler.action.refreshShow(showObj) #@UndefinedVariable
        except exceptions.CantRefreshException, e:
            ui.notifications.error("Unable to refresh this show.",
                        ex(e))

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
            sickbeard.showQueueScheduler.action.updateShow(showObj, bool(force)) #@UndefinedVariable
        except exceptions.CantUpdateException, e:
            ui.notifications.error("Unable to update this show.",
                        ex(e))

        # just give it some time
        time.sleep(3)

        redirect("/home/displayShow?show="+str(showObj.tvdbid))


    @cherrypy.expose
    def updateXBMC(self, showName=None):

        for curHost in [x.strip() for x in sickbeard.XBMC_HOST.split(",")]:
            if notifiers.xbmc_notifier._update_library(curHost, showName=showName):
                ui.notifications.message("Command sent to XBMC host " + curHost + " to update library")
            else:
                ui.notifications.error("Unable to contact XBMC host " + curHost)
        redirect('/home')


    @cherrypy.expose
    def updatePLEX(self):

        if notifiers.plex_notifier._update_library():
            ui.notifications.message("Command sent to Plex Media Server host " + sickbeard.PLEX_HOST + " to update library")
            logger.log(u"Plex library update initiated for host " + sickbeard.PLEX_HOST, logger.DEBUG)
        else:
            ui.notifications.error("Unable to contact Plex Media Server host " + sickbeard.PLEX_HOST)
            logger.log(u"Plex library update failed for host " + sickbeard.PLEX_HOST, logger.ERROR)
        redirect('/home')


    @cherrypy.expose
    def fixEpisodeNames(self, show=None):

        if show == None:
            return _genericMessage("Error", "Invalid show ID")

        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

        if showObj == None:
            return _genericMessage("Error", "Unable to find the specified show")

        if sickbeard.showQueueScheduler.action.isBeingAdded(showObj): #@UndefinedVariable
            return _genericMessage("Error", "Show is still being added, wait until it is finished before you rename files")

        showObj.fixEpisodeNames()

        redirect("/home/displayShow?show=" + show)

    @cherrypy.expose
    def setStatus(self, show=None, eps=None, status=None, direct=False):

        if show == None or eps == None or status == None:
            errMsg = "You must specify a show and at least one episode"
            if direct:
                ui.notifications.error('Error', errMsg)
                return json.dumps({'result': 'error'})
            else:
                return _genericMessage("Error", errMsg)

        if not statusStrings.has_key(int(status)):
            errMsg = "Invalid status"
            if direct:
                ui.notifications.error('Error', errMsg)
                return json.dumps({'result': 'error'})
            else:
                return _genericMessage("Error", errMsg)

        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

        if showObj == None:
            errMsg = "Error", "Show not in show list"
            if direct:
                ui.notifications.error('Error', errMsg)
                return json.dumps({'result': 'error'})
            else:
                return _genericMessage("Error", errMsg)

        segment_list = []

        if eps != None:

            for curEp in eps.split('|'):

                logger.log(u"Attempting to set status on episode "+curEp+" to "+status, logger.DEBUG)

                epInfo = curEp.split('x')

                epObj = showObj.getEpisode(int(epInfo[0]), int(epInfo[1]))

                if int(status) == WANTED:
                    # figure out what segment the episode is in and remember it so we can backlog it
                    if epObj.show.air_by_date:
                        ep_segment = str(epObj.airdate)[:7]
                    else:
                        ep_segment = epObj.season
    
                    if ep_segment not in segment_list:
                        segment_list.append(ep_segment)

                if epObj == None:
                    return _genericMessage("Error", "Episode couldn't be retrieved")

                with epObj.lock:
                    # don't let them mess up UNAIRED episodes
                    if epObj.status == UNAIRED:
                        logger.log(u"Refusing to change status of "+curEp+" because it is UNAIRED", logger.ERROR)
                        continue

                    if int(status) in Quality.DOWNLOADED and epObj.status not in Quality.SNATCHED + Quality.SNATCHED_PROPER + Quality.DOWNLOADED + [IGNORED] and not ek.ek(os.path.isfile, epObj.location):
                        logger.log(u"Refusing to change status of "+curEp+" to DOWNLOADED because it's not SNATCHED/DOWNLOADED", logger.ERROR)
                        continue

                    epObj.status = int(status)
                    epObj.saveToDB()

        msg = "Backlog was automatically started for the following seasons of <b>"+showObj.name+"</b>:<br />"
        for cur_segment in segment_list:
            msg += "<li>Season "+str(cur_segment)+"</li>"
            logger.log(u"Sending backlog for "+showObj.name+" season "+str(cur_segment)+" because some eps were set to wanted")
            cur_backlog_queue_item = search_queue.BacklogQueueItem(showObj, cur_segment)
            sickbeard.searchQueueScheduler.action.add_item(cur_backlog_queue_item) #@UndefinedVariable
        msg += "</ul>"

        if segment_list:
            ui.notifications.message("Backlog started", msg)

        if direct:
            return json.dumps({'result': 'success'})
        else:
            redirect("/home/displayShow?show=" + show)

    @cherrypy.expose
    def searchEpisode(self, show=None, season=None, episode=None):

        # retrieve the episode object and fail if we can't get one 
        ep_obj = _getEpisode(show, season, episode)
        if isinstance(ep_obj, str):
            return json.dumps({'result': 'failure'})

        # make a queue item for it and put it on the queue
        ep_queue_item = search_queue.ManualSearchQueueItem(ep_obj)
        sickbeard.searchQueueScheduler.action.add_item(ep_queue_item) #@UndefinedVariable

        # wait until the queue item tells us whether it worked or not
        while ep_queue_item.success == None: #@UndefinedVariable
            time.sleep(1)

        # return the correct json value
        if ep_queue_item.success:
            return json.dumps({'result': statusStrings[ep_obj.status]})

        return json.dumps({'result': 'failure'})

class UI:
    
    @cherrypy.expose
    def add_message(self):
        
        ui.notifications.message('Test 1', 'This is test number 1')
        ui.notifications.error('Test 2', 'This is test number 2')
        
        return "ok"

    @cherrypy.expose
    def get_messages(self):
        messages = {}
        cur_notification_num = 1
        for cur_notification in ui.notifications.get_notifications():
            messages['notification-'+str(cur_notification_num)] = {'title': cur_notification.title,
                                                                   'message': cur_notification.message,
                                                                   'type': cur_notification.type}
            cur_notification_num += 1

        return json.dumps(messages)

   
class WebInterface:

    @cherrypy.expose
    def index(self):

        redirect("/home")

    @cherrypy.expose
    def showPoster(self, show=None, which=None):

        if which == 'poster':
            default_image_name = 'poster.png'
        else:
            default_image_name = 'banner.png'

        default_image_path = ek.ek(os.path.join, sickbeard.PROG_DIR, 'data', 'images', default_image_name)
        if show == None:
            return cherrypy.lib.static.serve_file(default_image_path, content_type="image/jpeg")
        else:
            showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

        if showObj == None:
            return cherrypy.lib.static.serve_file(default_image_path, content_type="image/jpeg")

        cache_obj = image_cache.ImageCache()
        
        if which == 'poster':
            image_file_name = cache_obj.poster_path(showObj.tvdbid)
        # this is for 'banner' but also the default case
        else:
            image_file_name = cache_obj.banner_path(showObj.tvdbid)

        if ek.ek(os.path.isfile, image_file_name):
            try:
                from PIL import Image
                from cStringIO import StringIO
            except ImportError: # PIL isn't installed
                return cherrypy.lib.static.serve_file(image_file_name, content_type="image/jpeg")
            else:
                im = Image.open(image_file_name)
                if im.mode == 'P': # Convert GIFs to RGB
                    im = im.convert('RGB')
                if which == 'banner':
                    size = 600, 112
                elif which == 'poster':
                    size = 136, 200
                else:
                    return cherrypy.lib.static.serve_file(image_file_name, content_type="image/jpeg")
                im = im.resize(size, Image.ANTIALIAS)
                buffer = StringIO()
                im.save(buffer, 'JPEG', quality=85)
                cherrypy.response.headers['Content-Type'] = 'image/jpeg'
                return buffer.getvalue()
        else:
            return cherrypy.lib.static.serve_file(default_image_path, content_type="image/jpeg")

    @cherrypy.expose
    def setComingEpsLayout(self, layout):
        if layout not in ('poster', 'banner', 'list'):
            layout = 'banner'
        
        sickbeard.COMING_EPS_LAYOUT = layout
        
        redirect("/comingEpisodes")

    @cherrypy.expose
    def toggleComingEpsDisplayPaused(self):
        
        sickbeard.COMING_EPS_DISPLAY_PAUSED = not sickbeard.COMING_EPS_DISPLAY_PAUSED
        
        redirect("/comingEpisodes")

    @cherrypy.expose
    def setComingEpsSort(self, sort):
        if sort not in ('date', 'network', 'show'):
            sort = 'date'
        
        sickbeard.COMING_EPS_SORT = sort
        
        redirect("/comingEpisodes")

    @cherrypy.expose
    def comingEpisodes(self, layout="None"):

        myDB = db.DBConnection()
        
        today = datetime.date.today().toordinal()
        next_week = (datetime.date.today() + datetime.timedelta(days=7)).toordinal()
        recently = (datetime.date.today() - datetime.timedelta(days=3)).toordinal()

        done_show_list = []
        qualList = Quality.DOWNLOADED + Quality.SNATCHED + [ARCHIVED, IGNORED]
        sql_results = myDB.select("SELECT *, tv_shows.status as show_status FROM tv_episodes, tv_shows WHERE season != 0 AND airdate >= ? AND airdate < ? AND tv_shows.tvdb_id = tv_episodes.showid AND tv_episodes.status NOT IN ("+','.join(['?']*len(qualList))+")", [today, next_week] + qualList)
        for cur_result in sql_results:
            done_show_list.append(int(cur_result["showid"]))

        more_sql_results = myDB.select("SELECT *, tv_shows.status as show_status FROM tv_episodes outer_eps, tv_shows WHERE season != 0 AND showid NOT IN ("+','.join(['?']*len(done_show_list))+") AND tv_shows.tvdb_id = outer_eps.showid AND airdate = (SELECT airdate FROM tv_episodes inner_eps WHERE inner_eps.showid = outer_eps.showid AND inner_eps.airdate >= ? ORDER BY inner_eps.airdate ASC LIMIT 1) AND outer_eps.status NOT IN ("+','.join(['?']*len(Quality.DOWNLOADED+Quality.SNATCHED))+")", done_show_list + [next_week] + Quality.DOWNLOADED + Quality.SNATCHED)
        sql_results += more_sql_results

        more_sql_results = myDB.select("SELECT *, tv_shows.status as show_status FROM tv_episodes, tv_shows WHERE season != 0 AND tv_shows.tvdb_id = tv_episodes.showid AND airdate < ? AND airdate >= ? AND tv_episodes.status = ? AND tv_episodes.status NOT IN ("+','.join(['?']*len(qualList))+")", [today, recently, WANTED] + qualList)
        sql_results += more_sql_results

        #epList = sickbeard.comingList

        # sort by air date
        sorts = {
            'date': (lambda x, y: cmp(int(x["airdate"]), int(y["airdate"]))),
            'show': (lambda a, b: cmp(a["show_name"], b["show_name"])),
            'network': (lambda a, b: cmp(a["network"], b["network"])),
        }

        #epList.sort(sorts[sort])
        sql_results.sort(sorts[sickbeard.COMING_EPS_SORT])

        t = PageTemplate(file="comingEpisodes.tmpl")
        paused_item = { 'title': '', 'path': 'toggleComingEpsDisplayPaused' }
        paused_item['title'] = 'Hide Paused' if sickbeard.COMING_EPS_DISPLAY_PAUSED else 'Show Paused'
        t.submenu = [
            { 'title': 'Sort by:', 'path': {'Date': 'setComingEpsSort/?sort=date',
                                            'Show': 'setComingEpsSort/?sort=show',
                                            'Network': 'setComingEpsSort/?sort=network',
                                           }},

            { 'title': 'Layout:', 'path': {'Banner': 'setComingEpsLayout/?layout=banner',
                                           'Poster': 'setComingEpsLayout/?layout=poster',
                                           'List': 'setComingEpsLayout/?layout=list',
                                           }},
            paused_item,
        ]

        t.next_week = next_week
        t.today = today
        t.sql_results = sql_results

        # Allow local overriding of layout parameter
        if layout and layout in ('poster', 'banner', 'list'):
            t.layout = layout
        else:
            t.layout = sickbeard.COMING_EPS_LAYOUT
                

        return _munge(t)

    manage = Manage()

    history = History()

    config = Config()

    home = Home()
    
    api = Api()

    browser = browser.WebFileBrowser()

    errorlogs = ErrorLogs()
    
    ui = UI()
