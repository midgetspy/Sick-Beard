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
from sickbeard import ui
from sickbeard import logger, helpers, exceptions, classes, db
from sickbeard import encodingKludge as ek
from sickbeard import search_queue
from sickbeard import image_cache
from sickbeard import naming

from sickbeard.providers import newznab
from sickbeard.common import Quality, Overview, statusStrings
from sickbeard.common import SNATCHED, SKIPPED, UNAIRED, IGNORED, ARCHIVED, WANTED
from sickbeard.exceptions import ex
from sickbeard.webapi import Api

from lib.tvdb_api import tvdb_api, tvdb_exceptions

try:
    import json
except ImportError:
    from lib import simplejson as json

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

from sickbeard import browser


class PageTemplate (Template):
    def __init__(self, *args, **KWs):
        KWs['file'] = os.path.join(sickbeard.PROG_DIR, "data/interfaces/default/", KWs['file'])
        super(PageTemplate, self).__init__(*args, **KWs)
        self.sbRoot = sickbeard.WEB_ROOT
        self.sbHttpPort = sickbeard.WEB_PORT
        self.sbHttpsPort = sickbeard.WEB_PORT
        self.sbHttpsEnabled = sickbeard.ENABLE_HTTPS
        if cherrypy.request.headers['Host'][0] == '[':
            self.sbHost = re.match("^\[.*\]", cherrypy.request.headers['Host'], re.X|re.M|re.S).group(0)
        else:
            self.sbHost = re.match("^[^:]+", cherrypy.request.headers['Host'], re.X|re.M|re.S).group(0)
        self.projectHomePage = "http://code.google.com/p/sickbeard/"

        if "X-Forwarded-Host" in cherrypy.request.headers:
            self.sbHost = cherrypy.request.headers['X-Forwarded-Host']
        if "X-Forwarded-Port" in cherrypy.request.headers:
            self.sbHttpPort = cherrypy.request.headers['X-Forwarded-Port']
            self.sbHttpsPort = self.sbHttpPort
        if "X-Forwarded-Proto" in cherrypy.request.headers:
            self.sbHttpsEnabled = True if cherrypy.request.headers['X-Forwarded-Proto'] == 'https' else False

        logPageTitle = 'Logs &amp; Errors'
        if len(classes.ErrorViewer.errors):
            logPageTitle += ' (' + str(len(classes.ErrorViewer.errors)) + ')'
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
            showDirList += "showDir=" + curShowDir + "&"
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
    { 'title': 'Backlog Overview',          'path': 'manage/backlogOverview/' },
    { 'title': 'Manage Searches',           'path': 'manage/manageSearches/'  },
    { 'title': 'Episode Status Management', 'path': 'manage/episodeStatuses/' },
]


class ManageSearches:

    @cherrypy.expose
    def index(self):
        t = PageTemplate(file="manage_manageSearches.tmpl")
        #t.backlogPI = sickbeard.backlogSearchScheduler.action.getProgressIndicator()
        t.backlogPaused = sickbeard.searchQueueScheduler.action.is_backlog_paused()  # @UndefinedVariable
        t.backlogRunning = sickbeard.searchQueueScheduler.action.is_backlog_in_progress()  # @UndefinedVariable
        t.searchStatus = sickbeard.currentSearchScheduler.action.amActive  # @UndefinedVariable
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

        redirect("/manage/manageSearches/")

    @cherrypy.expose
    def pauseBacklog(self, paused=None):
        if paused == "1":
            sickbeard.searchQueueScheduler.action.pause_backlog()  # @UndefinedVariable
        else:
            sickbeard.searchQueueScheduler.action.unpause_backlog()  # @UndefinedVariable

        redirect("/manage/manageSearches/")

    @cherrypy.expose
    def forceVersionCheck(self):

        # force a check to see if there is a new version
        result = sickbeard.versionCheckScheduler.action.check_for_new_version(force=True)  # @UndefinedVariable
        if result:
            logger.log(u"Forcing version check")

        redirect("/manage/manageSearches/")


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

        cur_show_results = myDB.select("SELECT season, episode, name FROM tv_episodes WHERE showid = ? AND season > 0 AND status IN (" + ','.join(['?'] * len(status_list)) + ")", [int(tvdb_id)] + status_list)

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
        status_results = myDB.select("SELECT show_name, tv_shows.tvdb_id as tvdb_id FROM tv_episodes, tv_shows WHERE tv_episodes.status IN (" + ','.join(['?'] * len(status_list)) + ") AND season > 0 AND tv_episodes.showid = tv_shows.tvdb_id ORDER BY show_name", status_list)

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
                all_eps_results = myDB.select("SELECT season, episode FROM tv_episodes WHERE status IN (" + ','.join(['?'] * len(status_list)) + ") AND season > 0 AND showid = ?", status_list + [cur_tvdb_id])
                all_eps = [str(x["season"]) + 'x' + str(x["episode"]) for x in all_eps_results]
                to_change[cur_tvdb_id] = all_eps

            Home().setStatus(cur_tvdb_id, '|'.join(to_change[cur_tvdb_id]), newStatus, direct=True)

        redirect("/manage/episodeStatuses/")

    @cherrypy.expose
    def backlogShow(self, tvdb_id):

        show_obj = helpers.findCertainShow(sickbeard.showList, int(tvdb_id))

        if show_obj:
            sickbeard.backlogSearchScheduler.action.searchBacklog([show_obj])  # @UndefinedVariable

        redirect("/manage/backlogOverview/")

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
            epCounts[Overview.SNATCHED] = 0

            sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? ORDER BY season DESC, episode DESC", [curShow.tvdbid])

            for curResult in sqlResults:

                curEpCat = curShow.getOverview(int(curResult["status"]))
                epCats[str(curResult["season"]) + "x" + str(curResult["episode"])] = curEpCat
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
            redirect("/manage/")

        showIDs = toEdit.split("|")
        showList = []
        for curID in showIDs:
            curID = int(curID)
            showObj = helpers.findCertainShow(sickbeard.showList, curID)
            if showObj:
                showList.append(showObj)

        flatten_folders_all_same = True
        last_flatten_folders = None

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

            if flatten_folders_all_same:
                if last_flatten_folders not in (None, curShow.flatten_folders):
                    flatten_folders_all_same = False
                else:
                    last_flatten_folders = curShow.flatten_folders

            if quality_all_same:
                if last_quality not in (None, curShow.quality):
                    quality_all_same = False
                else:
                    last_quality = curShow.quality

        t.showList = toEdit
        t.paused_value = last_paused if paused_all_same else None
        t.flatten_folders_value = last_flatten_folders if flatten_folders_all_same else None
        t.quality_value = last_quality if quality_all_same else None
        t.root_dir_list = root_dir_list

        return _munge(t)

    @cherrypy.expose
    def massEditSubmit(self, paused=None, flatten_folders=None, quality_preset=False,
                       anyQualities=[], bestQualities=[], toEdit=None, *args, **kwargs):

        dir_map = {}
        for cur_arg in kwargs:
            if not cur_arg.startswith('orig_root_dir_'):
                continue
            which_index = cur_arg.replace('orig_root_dir_', '')
            end_dir = kwargs['new_root_dir_' + which_index]
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
                logger.log(u"For show " + showObj.name + " changing dir from " + showObj._location + " to " + new_show_dir)
            else:
                new_show_dir = showObj._location

            if paused == 'keep':
                new_paused = showObj.paused
            else:
                new_paused = True if paused == 'enable' else False
            new_paused = 'on' if new_paused else 'off'

            if flatten_folders == 'keep':
                new_flatten_folders = showObj.flatten_folders
            else:
                new_flatten_folders = True if flatten_folders == 'enable' else False
            new_flatten_folders = 'on' if new_flatten_folders else 'off'

            if quality_preset == 'keep':
                anyQualities, bestQualities = Quality.splitQuality(showObj.quality)

            curErrors += Home().editShow(curShow, new_show_dir, anyQualities, bestQualities, new_flatten_folders, new_paused, directCall=True)

            if curErrors:
                logger.log(u"Errors: " + str(curErrors), logger.ERROR)
                errors.append('<b>%s:</b>\n<ul>' % showObj.name + ' '.join(['<li>%s</li>' % error for error in curErrors]) + "</ul>")

        if len(errors) > 0:
            ui.notifications.error('%d error%s while saving changes:' % (len(errors), "" if len(errors) == 1 else "s"),
                        " ".join(errors))

        redirect("/manage/")

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

        for curShowID in set(toUpdate + toRefresh + toRename + toDelete + toMetadata):

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
                    sickbeard.showQueueScheduler.action.updateShow(showObj, True)  # @UndefinedVariable
                    updates.append(showObj.name)
                except exceptions.CantUpdateException, e:
                    errors.append("Unable to update show " + showObj.name + ": " + ex(e))

            # don't bother refreshing shows that were updated anyway
            if curShowID in toRefresh and curShowID not in toUpdate:
                try:
                    sickbeard.showQueueScheduler.action.refreshShow(showObj)  # @UndefinedVariable
                    refreshes.append(showObj.name)
                except exceptions.CantRefreshException, e:
                    errors.append("Unable to refresh show " + showObj.name + ": " + ex(e))

            if curShowID in toRename:
                sickbeard.showQueueScheduler.action.renameShowEpisodes(showObj)  # @UndefinedVariable
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

        if len(updates + refreshes + renames) > 0:
            ui.notifications.message("The following actions were queued:",
                          messageDetail)

        redirect("/manage/")


class History:

    @cherrypy.expose
    def index(self, limit=100):

        myDB = db.DBConnection()

        if limit == "0":
            sqlResults = myDB.select("SELECT h.*, show_name FROM history h, tv_shows s WHERE h.showid=s.tvdb_id ORDER BY date DESC")
        else:
            sqlResults = myDB.select("SELECT h.*, show_name FROM history h, tv_shows s WHERE h.showid=s.tvdb_id ORDER BY date DESC LIMIT ?", [limit])

        t = PageTemplate(file="history.tmpl")
        t.historyResults = sqlResults
        t.limit = limit
        t.submenu = [
            { 'title': 'Clear History', 'path': 'history/clearHistory/' },
            { 'title': 'Trim History',  'path': 'history/trimHistory/'  },
        ]

        return _munge(t)

    @cherrypy.expose
    def clearHistory(self):

        myDB = db.DBConnection()
        myDB.action("DELETE FROM history WHERE 1=1")
        ui.notifications.message('History cleared')
        redirect("/history/")

    @cherrypy.expose
    def trimHistory(self):

        myDB = db.DBConnection()
        myDB.action("DELETE FROM history WHERE date < " + str((datetime.datetime.today() - datetime.timedelta(days=30)).strftime(history.dateFormat)))
        ui.notifications.message('Removed history entries greater than 30 days old')
        redirect("/history/")


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
    def saveAddShowDefaults(self, defaultFlattenFolders, defaultStatus, anyQualities, bestQualities):

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

        sickbeard.FLATTEN_FOLDERS_DEFAULT = config.checkbox_to_value(defaultFlattenFolders)

    @cherrypy.expose
    def generateKey(self):
        """ Return a new randomized API_KEY """

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
        logger.log(u"New SB API key generated")
        return m.hexdigest()

    @cherrypy.expose
    def saveGeneral(self, log_dir=None, web_port=None, web_log=None, web_ipv6=None,
                    launch_browser=None, web_username=None, use_api=None, api_key=None,
                    web_password=None, version_notify=None, enable_https=None, https_cert=None, https_key=None):

        results = []

        # Misc
        sickbeard.LAUNCH_BROWSER = config.checkbox_to_value(launch_browser)
        config.change_VERSION_NOTIFY(config.checkbox_to_value(version_notify))
        # sickbeard.LOG_DIR is set in config.change_LOG_DIR()

        # Web Interface
        sickbeard.WEB_IPV6 = config.checkbox_to_value(web_ipv6)
        # sickbeard.WEB_LOG is set in config.change_LOG_DIR()

        if not config.change_LOG_DIR(log_dir, web_log):
            results += ["Unable to create directory " + os.path.normpath(log_dir) + ", log directory not changed."]

        sickbeard.WEB_PORT = config.to_int(web_port, default=8081)

        sickbeard.WEB_USERNAME = web_username
        sickbeard.WEB_PASSWORD = web_password

        sickbeard.ENABLE_HTTPS = config.checkbox_to_value(enable_https)

        if not config.change_HTTPS_CERT(https_cert):
            results += ["Unable to create directory " + os.path.normpath(https_cert) + ", https cert directory not changed."]

        if not config.change_HTTPS_KEY(https_key):
            results += ["Unable to create directory " + os.path.normpath(https_key) + ", https key directory not changed."]

        # API
        sickbeard.USE_API = config.checkbox_to_value(use_api)
        sickbeard.API_KEY = api_key

        sickbeard.save_config()

        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                        '<br />\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek.ek(os.path.join, sickbeard.CONFIG_FILE))

        redirect("/config/general/")


class ConfigSearch:

    @cherrypy.expose
    def index(self):

        t = PageTemplate(file="config_search.tmpl")
        t.submenu = ConfigMenu
        return _munge(t)

    @cherrypy.expose
    def saveSearch(self, use_nzbs=None, use_torrents=None, nzb_dir=None, sab_username=None, sab_password=None,
                       sab_apikey=None, sab_category=None, sab_host=None, nzbget_username=None, nzbget_password=None, nzbget_category=None, nzbget_host=None,
                       torrent_dir=None, nzb_method=None, usenet_retention=None, search_frequency=None, download_propers=None, ignore_words=None):

        results = []

        # Episode Search
        sickbeard.DOWNLOAD_PROPERS = config.checkbox_to_value(download_propers)

        config.change_SEARCH_FREQUENCY(search_frequency)
        sickbeard.USENET_RETENTION = config.to_int(usenet_retention, default=500)

        sickbeard.IGNORE_WORDS = ignore_words

        # NZB Search
        sickbeard.USE_NZBS = config.checkbox_to_value(use_nzbs)
        sickbeard.NZB_METHOD = nzb_method

        sickbeard.SAB_HOST = config.clean_url(sab_host)
        sickbeard.SAB_USERNAME = sab_username
        sickbeard.SAB_PASSWORD = sab_password
        sickbeard.SAB_APIKEY = sab_apikey.strip()
        sickbeard.SAB_CATEGORY = sab_category

        if not config.change_NZB_DIR(nzb_dir):
            results += ["Unable to create directory " + os.path.normpath(nzb_dir) + ", directory not changed."]

        sickbeard.NZBGET_HOST = config.clean_url(nzbget_host)
        sickbeard.NZBGET_USERNAME = nzbget_username
        sickbeard.NZBGET_PASSWORD = nzbget_password
        sickbeard.NZBGET_CATEGORY = nzbget_category

        # Torrent Search
        sickbeard.USE_TORRENTS = config.checkbox_to_value(use_torrents)

        if not config.change_TORRENT_DIR(torrent_dir):
            results += ["Unable to create directory " + os.path.normpath(torrent_dir) + ", directory not changed."]

        sickbeard.save_config()

        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                        '<br />\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek.ek(os.path.join, sickbeard.CONFIG_FILE))

        redirect("/config/search/")


class ConfigPostProcessing:

    @cherrypy.expose
    def index(self):

        t = PageTemplate(file="config_postProcessing.tmpl")
        t.submenu = ConfigMenu
        return _munge(t)

    @cherrypy.expose
    def savePostProcessing(self, naming_pattern=None, naming_multi_ep=None,
                    xbmc_data=None, xbmc_12plus_data=None, mediabrowser_data=None, sony_ps3_data=None, wdtv_data=None, tivo_data=None, mede8er_data=None,
                    keep_processed_dir=None, process_automatically=None, rename_episodes=None,
                    move_associated_files=None, filter_associated_files=None, tv_download_dir=None, naming_custom_abd=None, naming_abd_pattern=None):

        results = []

        # Post-Processing
        if not config.change_TV_DOWNLOAD_DIR(tv_download_dir):
            results += ["Unable to create directory " + os.path.normpath(tv_download_dir) + ", dir not changed."]

        sickbeard.KEEP_PROCESSED_DIR = config.checkbox_to_value(keep_processed_dir)
        sickbeard.MOVE_ASSOCIATED_FILES = config.checkbox_to_value(move_associated_files)
        sickbeard.FILTER_ASSOCIATED_FILES = filter_associated_files
        sickbeard.RENAME_EPISODES = config.checkbox_to_value(rename_episodes)

        sickbeard.PROCESS_AUTOMATICALLY = config.checkbox_to_value(process_automatically)

        if sickbeard.PROCESS_AUTOMATICALLY:
            sickbeard.autoPostProcesserScheduler.silent = False
        else:
            sickbeard.autoPostProcesserScheduler.silent = True

        # Naming
        sickbeard.NAMING_CUSTOM_ABD = config.checkbox_to_value(naming_custom_abd)

        if self.isNamingValid(naming_pattern, naming_multi_ep) != "invalid":
            sickbeard.NAMING_PATTERN = naming_pattern
            sickbeard.NAMING_MULTI_EP = int(naming_multi_ep)
            sickbeard.NAMING_FORCE_FOLDERS = naming.check_force_season_folders()
        else:
            results.append("You tried saving an invalid naming config, not saving your naming settings")

        if self.isNamingValid(naming_abd_pattern, None, True) != "invalid":
            sickbeard.NAMING_ABD_PATTERN = naming_abd_pattern
        elif naming_custom_abd:
            results.append("You tried saving an invalid air-by-date naming config, not saving your air-by-date settings")

        # Metadata
        sickbeard.METADATA_XBMC = xbmc_data
        sickbeard.METADATA_XBMC_12PLUS = xbmc_12plus_data
        sickbeard.METADATA_MEDIABROWSER = mediabrowser_data
        sickbeard.METADATA_PS3 = sony_ps3_data
        sickbeard.METADATA_WDTV = wdtv_data
        sickbeard.METADATA_TIVO = tivo_data
        sickbeard.METADATA_MEDE8ER = mede8er_data

        sickbeard.metadata_provider_dict['XBMC'].set_config(sickbeard.METADATA_XBMC)
        sickbeard.metadata_provider_dict['XBMC 12+'].set_config(sickbeard.METADATA_XBMC_12PLUS)
        sickbeard.metadata_provider_dict['MediaBrowser'].set_config(sickbeard.METADATA_MEDIABROWSER)
        sickbeard.metadata_provider_dict['Sony PS3'].set_config(sickbeard.METADATA_PS3)
        sickbeard.metadata_provider_dict['WDTV'].set_config(sickbeard.METADATA_WDTV)
        sickbeard.metadata_provider_dict['TIVO'].set_config(sickbeard.METADATA_TIVO)
        sickbeard.metadata_provider_dict['Mede8er'].set_config(sickbeard.METADATA_MEDE8ER)

        # Save changes
        sickbeard.save_config()

        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                        '<br />\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek.ek(os.path.join, sickbeard.CONFIG_FILE))

        redirect("/config/postProcessing/")

    @cherrypy.expose
    def testNaming(self, pattern=None, multi=None, abd=False):

        if multi != None:
            multi = int(multi)

        result = naming.test_name(pattern, multi, abd)

        result = ek.ek(os.path.join, result['dir'], result['name'])

        return result

    @cherrypy.expose
    def isNamingValid(self, pattern=None, multi=None, abd=False):
        if pattern == None:
            return "invalid"

        # air by date shows just need one check, we don't need to worry about season folders
        if abd:
            is_valid = naming.check_valid_abd_naming(pattern)
            require_season_folders = False

        else:
            # check validity of single and multi ep cases for the whole path
            is_valid = naming.check_valid_naming(pattern, multi)

            # check validity of single and multi ep cases for only the file name
            require_season_folders = naming.check_force_season_folders(pattern, multi)

        if is_valid and not require_season_folders:
            return "valid"
        elif is_valid and require_season_folders:
            return "seasonfolders"
        else:
            return "invalid"


class ConfigProviders:

    @cherrypy.expose
    def index(self):
        t = PageTemplate(file="config_providers.tmpl")
        t.submenu = ConfigMenu
        return _munge(t)

    @cherrypy.expose
    def canAddNewznabProvider(self, name):

        if not name:
            return json.dumps({'error': 'No Provider Name specified'})

        providerDict = dict(zip([x.getID() for x in sickbeard.newznabProviderList], sickbeard.newznabProviderList))

        tempProvider = newznab.NewznabProvider(name, '')

        if tempProvider.getID() in providerDict:
            return json.dumps({'error': 'Provider Name already exists as ' + providerDict[tempProvider.getID()].name})
        else:
            return json.dumps({'success': tempProvider.getID()})

    @cherrypy.expose
    def saveNewznabProvider(self, name, url, key=''):

        if not name or not url:
            return '0'

        providerDict = dict(zip([x.name for x in sickbeard.newznabProviderList], sickbeard.newznabProviderList))

        if name in providerDict:
            if not providerDict[name].default:
                providerDict[name].name = name
                providerDict[name].url = config.clean_url(url)

            providerDict[name].key = key
            # a 0 in the key spot indicates that no key is needed
            if key == '0':
                providerDict[name].needs_auth = False
            else:
                providerDict[name].needs_auth = True

            return providerDict[name].getID() + '|' + providerDict[name].configStr()

        else:

            newProvider = newznab.NewznabProvider(name, url, key=key)
            sickbeard.newznabProviderList.append(newProvider)
            return newProvider.getID() + '|' + newProvider.configStr()

    @cherrypy.expose
    def deleteNewznabProvider(self, nnid):

        providerDict = dict(zip([x.getID() for x in sickbeard.newznabProviderList], sickbeard.newznabProviderList))

        if nnid not in providerDict or providerDict[nnid].default:
            return '0'

        # delete it from the list
        sickbeard.newznabProviderList.remove(providerDict[nnid])

        if nnid in sickbeard.PROVIDER_ORDER:
            sickbeard.PROVIDER_ORDER.remove(nnid)

        return '1'

    @cherrypy.expose
    def saveProviders(self,
                      newznab_string='',
                      omgwtfnzbs_username=None, omgwtfnzbs_apikey=None,
                      tvtorrents_digest=None, tvtorrents_hash=None,
                      torrentleech_key=None,
                      btn_api_key=None, hdbits_username=None, hdbits_passkey=None,
                      provider_order=None):

        results = []

        provider_str_list = provider_order.split()
        provider_list = []

        newznabProviderDict = dict(zip([x.getID() for x in sickbeard.newznabProviderList], sickbeard.newznabProviderList))

        finishedNames = []

        # add all the newznab info we got into our list
        if newznab_string:
            for curNewznabProviderStr in newznab_string.split('!!!'):

                if not curNewznabProviderStr:
                    continue

                cur_name, cur_url, cur_key = curNewznabProviderStr.split('|')
                cur_url = config.clean_url(cur_url)

                newProvider = newznab.NewznabProvider(cur_name, cur_url, key=cur_key)

                cur_id = newProvider.getID()

                # if it already exists then update it
                if cur_id in newznabProviderDict:
                    newznabProviderDict[cur_id].name = cur_name
                    newznabProviderDict[cur_id].url = cur_url
                    newznabProviderDict[cur_id].key = cur_key
                    # a 0 in the key spot indicates that no key is needed
                    if cur_key == '0':
                        newznabProviderDict[cur_id].needs_auth = False
                    else:
                        newznabProviderDict[cur_id].needs_auth = True

                else:
                    sickbeard.newznabProviderList.append(newProvider)

                finishedNames.append(cur_id)

            # delete anything that is missing
            for curProvider in sickbeard.newznabProviderList:
                if curProvider.getID() not in finishedNames:
                    sickbeard.newznabProviderList.remove(curProvider)

        # do the enable/disable
        for curProviderStr in provider_str_list:
            curProvider, curEnabled = curProviderStr.split(':')
            curEnabled = config.to_int(curEnabled)

            provider_list.append(curProvider)

            if curProvider == 'womble_s_index':
                sickbeard.WOMBLE = curEnabled
            elif curProvider == 'omgwtfnzbs':
                sickbeard.OMGWTFNZBS = curEnabled
            elif curProvider == 'ezrss':
                sickbeard.EZRSS = curEnabled
            elif curProvider == 'hdbits':
                sickbeard.HDBITS = curEnabled
            elif curProvider == 'tvtorrents':
                sickbeard.TVTORRENTS = curEnabled
            elif curProvider == 'torrentleech':
                sickbeard.TORRENTLEECH = curEnabled
            elif curProvider == 'btn':
                sickbeard.BTN = curEnabled
            elif curProvider in newznabProviderDict:
                newznabProviderDict[curProvider].enabled = bool(curEnabled)
            else:
                logger.log(u"don't know what " + curProvider + " is, skipping")

        sickbeard.HDBITS_USERNAME = hdbits_username.strip()
        sickbeard.HDBITS_PASSKEY = hdbits_passkey.strip()

        sickbeard.TVTORRENTS_DIGEST = tvtorrents_digest.strip()
        sickbeard.TVTORRENTS_HASH = tvtorrents_hash.strip()

        sickbeard.TORRENTLEECH_KEY = torrentleech_key.strip()

        sickbeard.BTN_API_KEY = btn_api_key.strip()

        sickbeard.OMGWTFNZBS_USERNAME = omgwtfnzbs_username.strip()
        sickbeard.OMGWTFNZBS_APIKEY = omgwtfnzbs_apikey.strip()

        sickbeard.NEWZNAB_DATA = '!!!'.join([x.configStr() for x in sickbeard.newznabProviderList])
        sickbeard.PROVIDER_ORDER = provider_list

        sickbeard.save_config()

        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                        '<br />\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek.ek(os.path.join, sickbeard.CONFIG_FILE))

        redirect("/config/providers/")


class ConfigNotifications:

    @cherrypy.expose
    def index(self):
        t = PageTemplate(file="config_notifications.tmpl")
        t.submenu = ConfigMenu
        return _munge(t)

    @cherrypy.expose
    def saveNotifications(self,
                          use_xbmc=None, xbmc_always_on=None, xbmc_notify_onsnatch=None, xbmc_notify_ondownload=None, xbmc_update_onlyfirst=None,
                              xbmc_update_library=None, xbmc_update_full=None, xbmc_host=None, xbmc_username=None, xbmc_password=None,
                          use_plex=None, plex_notify_onsnatch=None, plex_notify_ondownload=None, plex_update_library=None,
                              plex_server_host=None, plex_host=None, plex_username=None, plex_password=None,
                          use_growl=None, growl_notify_onsnatch=None, growl_notify_ondownload=None, growl_host=None, growl_password=None,
                          use_prowl=None, prowl_notify_onsnatch=None, prowl_notify_ondownload=None, prowl_api=None, prowl_priority=0,
                          use_twitter=None, twitter_notify_onsnatch=None, twitter_notify_ondownload=None,
                          use_boxcar2=None, boxcar2_notify_onsnatch=None, boxcar2_notify_ondownload=None, boxcar2_access_token=None, boxcar2_sound=None,
                          use_pushover=None, pushover_notify_onsnatch=None, pushover_notify_ondownload=None, pushover_userkey=None,
                          use_libnotify=None, libnotify_notify_onsnatch=None, libnotify_notify_ondownload=None,
                          use_nmj=None, nmj_host=None, nmj_database=None, nmj_mount=None,
                          use_synoindex=None, synoindex_notify_onsnatch=None, synoindex_notify_ondownload=None, synoindex_update_library=None,
                          use_nmjv2=None, nmjv2_host=None, nmjv2_dbloc=None, nmjv2_database=None,
                          use_trakt=None, trakt_username=None, trakt_password=None, trakt_api=None,
                          use_pytivo=None, pytivo_notify_onsnatch=None, pytivo_notify_ondownload=None, pytivo_update_library=None,
                              pytivo_host=None, pytivo_share_name=None, pytivo_tivo_name=None,
                          use_nma=None, nma_notify_onsnatch=None, nma_notify_ondownload=None, nma_api=None, nma_priority=0,
                          use_pushalot=None, pushalot_notify_onsnatch=None, pushalot_notify_ondownload=None, pushalot_authorizationtoken=None):

        results = []

        # Home Theater / NAS
        sickbeard.USE_XBMC = config.checkbox_to_value(use_xbmc)
        sickbeard.XBMC_ALWAYS_ON = config.checkbox_to_value(xbmc_always_on)
        sickbeard.XBMC_NOTIFY_ONSNATCH = config.checkbox_to_value(xbmc_notify_onsnatch)
        sickbeard.XBMC_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(xbmc_notify_ondownload)
        sickbeard.XBMC_UPDATE_LIBRARY = config.checkbox_to_value(xbmc_update_library)
        sickbeard.XBMC_UPDATE_FULL = config.checkbox_to_value(xbmc_update_full)
        sickbeard.XBMC_UPDATE_ONLYFIRST = config.checkbox_to_value(xbmc_update_onlyfirst)
        sickbeard.XBMC_HOST = config.clean_hosts(xbmc_host)
        sickbeard.XBMC_USERNAME = xbmc_username
        sickbeard.XBMC_PASSWORD = xbmc_password

        sickbeard.USE_PLEX = config.checkbox_to_value(use_plex)
        sickbeard.PLEX_NOTIFY_ONSNATCH = config.checkbox_to_value(plex_notify_onsnatch)
        sickbeard.PLEX_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(plex_notify_ondownload)
        sickbeard.PLEX_UPDATE_LIBRARY = config.checkbox_to_value(plex_update_library)
        sickbeard.PLEX_SERVER_HOST = config.clean_host(plex_server_host)
        sickbeard.PLEX_HOST = config.clean_hosts(plex_host)
        sickbeard.PLEX_USERNAME = plex_username
        sickbeard.PLEX_PASSWORD = plex_password

        sickbeard.USE_NMJ = config.checkbox_to_value(use_nmj)
        sickbeard.NMJ_HOST = config.clean_host(nmj_host)
        sickbeard.NMJ_DATABASE = nmj_database
        sickbeard.NMJ_MOUNT = nmj_mount

        sickbeard.USE_NMJv2 = config.checkbox_to_value(use_nmjv2)
        sickbeard.NMJv2_HOST = config.clean_host(nmjv2_host)
        sickbeard.NMJv2_DATABASE = nmjv2_database
        sickbeard.NMJv2_DBLOC = nmjv2_dbloc

        sickbeard.USE_SYNOINDEX = config.checkbox_to_value(use_synoindex)
        sickbeard.SYNOINDEX_NOTIFY_ONSNATCH = config.checkbox_to_value(synoindex_notify_onsnatch)
        sickbeard.SYNOINDEX_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(synoindex_notify_ondownload)
        sickbeard.SYNOINDEX_UPDATE_LIBRARY = config.checkbox_to_value(synoindex_update_library)

        sickbeard.USE_PYTIVO = config.checkbox_to_value(use_pytivo)
        # sickbeard.PYTIVO_NOTIFY_ONSNATCH = config.checkbox_to_value(pytivo_notify_onsnatch)
        # sickbeard.PYTIVO_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(pytivo_notify_ondownload)
        # sickbeard.PYTIVO_UPDATE_LIBRARY = config.checkbox_to_value(pytivo_update_library)
        sickbeard.PYTIVO_HOST = config.clean_host(pytivo_host)
        sickbeard.PYTIVO_SHARE_NAME = pytivo_share_name
        sickbeard.PYTIVO_TIVO_NAME = pytivo_tivo_name

        # Devices
        sickbeard.USE_GROWL = config.checkbox_to_value(use_growl)
        sickbeard.GROWL_NOTIFY_ONSNATCH = config.checkbox_to_value(growl_notify_onsnatch)
        sickbeard.GROWL_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(growl_notify_ondownload)
        sickbeard.GROWL_HOST = config.clean_host(growl_host, default_port=23053)
        sickbeard.GROWL_PASSWORD = growl_password

        sickbeard.USE_PROWL = config.checkbox_to_value(use_prowl)
        sickbeard.PROWL_NOTIFY_ONSNATCH = config.checkbox_to_value(prowl_notify_onsnatch)
        sickbeard.PROWL_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(prowl_notify_ondownload)
        sickbeard.PROWL_API = prowl_api
        sickbeard.PROWL_PRIORITY = prowl_priority

        sickbeard.USE_LIBNOTIFY = config.checkbox_to_value(use_libnotify)
        sickbeard.LIBNOTIFY_NOTIFY_ONSNATCH = config.checkbox_to_value(libnotify_notify_onsnatch)
        sickbeard.LIBNOTIFY_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(libnotify_notify_ondownload)

        sickbeard.USE_PUSHOVER = config.checkbox_to_value(use_pushover)
        sickbeard.PUSHOVER_NOTIFY_ONSNATCH = config.checkbox_to_value(pushover_notify_onsnatch)
        sickbeard.PUSHOVER_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(pushover_notify_ondownload)
        sickbeard.PUSHOVER_USERKEY = pushover_userkey

        sickbeard.USE_BOXCAR2 = config.checkbox_to_value(use_boxcar2)
        sickbeard.BOXCAR2_NOTIFY_ONSNATCH = config.checkbox_to_value(boxcar2_notify_onsnatch)
        sickbeard.BOXCAR2_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(boxcar2_notify_ondownload)
        sickbeard.BOXCAR2_ACCESS_TOKEN = boxcar2_access_token
        sickbeard.BOXCAR2_SOUND = boxcar2_sound

        sickbeard.USE_NMA = config.checkbox_to_value(use_nma)
        sickbeard.NMA_NOTIFY_ONSNATCH = config.checkbox_to_value(nma_notify_onsnatch)
        sickbeard.NMA_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(nma_notify_ondownload)
        sickbeard.NMA_API = nma_api
        sickbeard.NMA_PRIORITY = nma_priority

        sickbeard.USE_PUSHALOT = config.checkbox_to_value(use_pushalot)
        sickbeard.PUSHALOT_NOTIFY_ONSNATCH = config.checkbox_to_value(pushalot_notify_onsnatch)
        sickbeard.PUSHALOT_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(pushalot_notify_ondownload)
        sickbeard.PUSHALOT_AUTHORIZATIONTOKEN = pushalot_authorizationtoken

        # Online
        sickbeard.USE_TWITTER = config.checkbox_to_value(use_twitter)
        sickbeard.TWITTER_NOTIFY_ONSNATCH = config.checkbox_to_value(twitter_notify_onsnatch)
        sickbeard.TWITTER_NOTIFY_ONDOWNLOAD = config.checkbox_to_value(twitter_notify_ondownload)

        sickbeard.USE_TRAKT = config.checkbox_to_value(use_trakt)
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
            ui.notifications.message('Configuration Saved', ek.ek(os.path.join, sickbeard.CONFIG_FILE))

        redirect("/config/notifications/")


class ConfigHidden:

    @cherrypy.expose
    def index(self):

        t = PageTemplate(file="config_hidden.tmpl")
        t.submenu = ConfigMenu
        return _munge(t)

    @cherrypy.expose
    def saveHidden(self, anon_redirect=None, git_path=None, extra_scripts=None, create_missing_show_dirs=None, add_shows_wo_dir=None):

        results = []

        sickbeard.ANON_REDIRECT = anon_redirect
        sickbeard.GIT_PATH = git_path
        sickbeard.EXTRA_SCRIPTS = [x.strip() for x in extra_scripts.split('|') if x.strip()]
        sickbeard.CREATE_MISSING_SHOW_DIRS = config.checkbox_to_value(create_missing_show_dirs)
        sickbeard.ADD_SHOWS_WO_DIR = config.checkbox_to_value(add_shows_wo_dir)

        sickbeard.save_config()

        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                        '<br />\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek.ek(os.path.join, sickbeard.CONFIG_FILE))

        redirect("/config/hidden/")

    @cherrypy.expose
    def sbEnded(self, username=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()
        t = tvdb_api.Tvdb(**ltvdb_api_parms)

        results = []
        errMatch = []
        changeState = []

        myDB = db.DBConnection()
        sql_result = myDB.select("SELECT tvdb_id,show_name,status FROM tv_shows WHERE status != 'Continuing' ORDER BY show_id DESC LIMIT 400")
        myDB.connection.close()

        if (len(sql_result)) > 1:
            logger.log(u"There were " + str(len(sql_result)) + " shows in your database that need checking (limited to 400).", logger.MESSAGE)
            results.append("There were <b>" + str(len(sql_result)) + "</b> shows in your database that need checking (limited to 400).<br>")
        else:
            logger.log(u"There were no shows that needed to be checked at this time.", logger.MESSAGE)
            results.append("There were no shows that needed to be checked at this time.<br>")

        for ended_show in sql_result:

            tvdb_id = ended_show['tvdb_id']
            show_name = ended_show['show_name']
            status = ended_show['status']

            try:
                show = t[show_name]
            except:
                logger.log(u"Issue found when looking up \"%s\"" % (show_name), logger.ERROR)
                continue

            logger.log(u"Checking \"%s\" with local status \"%s\" against thetvdb" % (show_name, status), logger.MESSAGE)

            show_id = show['id']
            if int(tvdb_id) != int(show_id):
                logger.log("Warning: Issue matching \"%s\" on tvdb. Got \"%s\" and \"%s\"" % (show_name, tvdb_id, show_id), logger.ERROR)
                errMatch.append("<tr><td class='tvShow'><a target='_blank' href='%s/home/displayShow?show=%s'>%s</a></td><td>%s</td><td>%s</td>" % (sickbeard.WEB_ROOT, tvdb_id, show_name, tvdb_id, show_id))
            else:
                show_status = show['status']

                if not show_status:
                    show_status = ""

                if show_status != status:
                    changeState.append("<tr><td class='tvShow'><a target='_blank' href='%s/home/displayShow?show=%s'>%s</a></td><td>%s</td><td>%s</td>" % (sickbeard.WEB_ROOT, tvdb_id, show_name, status, show_status))

            show.clear()  # needed to free up memory since python's garbage collection would keep this around

        if len(errMatch):
            errMatch.insert(0, "<br>These shows need to be removed then added back to Sick Beard to correct their TVDBID.<br><table class='tablesorter'><thead><tr><th>show name</th><th>local tvdbid</th><th>remote tvdbid</th></tr></thead>")
            errMatch.append("</table>")
            results += errMatch

        if len(changeState):
            changeState.insert(0, "<br>These shows need to have 'force full update' ran on them to correct their status.<br><table class='tablesorter'><thead><tr><th>show name</th><th>local status</th><th>remote status</th></tr></thead>")
            changeState.append("</table>")
            results += changeState

        return results


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

    hidden = ConfigHidden()


def haveXBMC():
    return sickbeard.USE_XBMC and sickbeard.XBMC_UPDATE_LIBRARY


def havePLEX():
    return sickbeard.USE_PLEX and sickbeard.PLEX_UPDATE_LIBRARY


def HomeMenu():
    return [
        { 'title': 'Add Shows',              'path': 'home/addShows/',                                          },
        { 'title': 'Manual Post-Processing', 'path': 'home/postprocess/'                                        },
        { 'title': 'Update XBMC',            'path': 'home/updateXBMC/', 'requires': haveXBMC                   },
        { 'title': 'Update Plex',            'path': 'home/updatePLEX/', 'requires': havePLEX                   },
        { 'title': 'Restart',                'path': 'home/restart/?pid=' + str(sickbeard.PID), 'confirm': True   },
        { 'title': 'Shutdown',               'path': 'home/shutdown/?pid=' + str(sickbeard.PID), 'confirm': True  },
    ]


class HomePostProcess:

    @cherrypy.expose
    def index(self):

        t = PageTemplate(file="home_postprocess.tmpl")
        t.submenu = HomeMenu()
        return _munge(t)

    @cherrypy.expose
    def processEpisode(self, dir=None, nzbName=None, method=None, jobName=None, quiet=None, *args, **kwargs):

        if not dir:
            redirect("/home/postprocess/")
        else:
            pp_options = {}
            for key, value in kwargs.iteritems():
                if value == 'on':
                    value = True
                pp_options[key] = value

            result = processTV.processDir(dir, nzbName, method=method, pp_options=pp_options)
            if quiet != None and int(quiet) == 1:
                return result

            result = result.replace("\n", "<br />\n")
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
        result.insert(0, 'en')

        return json.dumps({'results': result})

    @cherrypy.expose
    def sanitizeFileName(self, name):
        return helpers.sanitizeFileName(name)

    @cherrypy.expose
    def searchTVDBForShowName(self, name, lang="en"):
        if not lang or lang == 'null':
                lang = "en"

        baseURL = "http://thetvdb.com/api/GetSeries.php?"
        nameUTF8 = name.encode('utf-8')

        logger.log(u"Trying to find Show on thetvdb.com with: " + nameUTF8.decode('utf-8'), logger.DEBUG)

        # Use each word in the show's name as a possible search term
        keywords = nameUTF8.split(' ')

        # Insert the whole show's name as the first search term so best results are first
        # ex: keywords = ['Some Show Name', 'Some', 'Show', 'Name']
        if len(keywords) > 1:
            keywords.insert(0, nameUTF8)

        # Query the TVDB for each search term and build the list of results
        results = []

        for searchTerm in keywords:
            params = {'seriesname': searchTerm,
                  'language': lang}

            finalURL = baseURL + urllib.urlencode(params)

            logger.log(u"Searching for Show with searchterm: \'" + searchTerm.decode('utf-8') + u"\' on URL " + finalURL, logger.DEBUG)
            urlData = helpers.getURL(finalURL)

            if urlData is None:
                # When urlData is None, trouble connecting to TVDB, don't try the rest of the keywords
                logger.log(u"Unable to get URL: " + finalURL, logger.ERROR)
                break
            else:
                try:
                    seriesXML = etree.ElementTree(etree.XML(urlData))
                    series = seriesXML.getiterator('Series')

                except Exception, e:
                    # use finalURL in log, because urlData can be too much information
                    logger.log(u"Unable to parse XML for some reason: " + ex(e) + " from XML: " + finalURL, logger.ERROR)
                    series = ''

                # add each result to our list
                for curSeries in series:
                    tvdb_id = int(curSeries.findtext('seriesid'))

                    # don't add duplicates
                    if tvdb_id in [x[0] for x in results]:
                        continue

                    results.append((tvdb_id, curSeries.findtext('SeriesName'), curSeries.findtext('FirstAired')))

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

        if sickbeard.ROOT_DIRS:
            default_index = int(sickbeard.ROOT_DIRS.split('|')[0])
        else:
            default_index = 0

        if len(root_dirs) > default_index:
            tmp = root_dirs[default_index]
            if tmp in root_dirs:
                root_dirs.remove(tmp)
                root_dirs = [tmp] + root_dirs

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
                           'display_dir': '<b>' + ek.ek(os.path.dirname, cur_path) + os.sep + '</b>' + ek.ek(os.path.basename, cur_path),
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
            t.default_show_name = ek.ek(os.path.basename, ek.ek(os.path.normpath, show_dir)).replace('.', ' ')
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
                   anyQualities=None, bestQualities=None, flatten_folders=None, fullShowPath=None,
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
                redirect("/home/")

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
            return "Missing params, no tvdb id or folder:" + repr(whichSeries) + " and " + repr(rootDir) + "/" + repr(fullShowPath)

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
            ui.notifications.error("Unable to add show", "Folder " + show_dir + " exists already")
            redirect("/home/addShows/existingShows/")

        # don't create show dir if config says not to
        if sickbeard.ADD_SHOWS_WO_DIR:
            logger.log(u"Skipping initial creation of " + show_dir + " due to config.ini setting")
        else:
            dir_exists = helpers.makeDir(show_dir)
            if not dir_exists:
                logger.log(u"Unable to create the folder " + show_dir + ", can't add the show", logger.ERROR)
                ui.notifications.error("Unable to add show", "Unable to create the folder " + show_dir + ", can't add the show")
                redirect("/home/")
            else:
                helpers.chmodAsParent(show_dir)

        # prepare the inputs for passing along
        flatten_folders = config.checkbox_to_value(flatten_folders)

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
        sickbeard.showQueueScheduler.action.addShow(tvdb_id, show_dir, int(defaultStatus), newQuality, flatten_folders, tvdbLang)  # @UndefinedVariable
        ui.notifications.message('Show added', 'Adding the specified show into ' + show_dir)

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

        promptForSettings = config.checkbox_to_value(promptForSettings)

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
            sickbeard.showQueueScheduler.action.addShow(tvdb_id, show_dir, SKIPPED, sickbeard.QUALITY_DEFAULT, sickbeard.FLATTEN_FOLDERS_DEFAULT)  # @UndefinedVariable
            num_added += 1

        if num_added:
            ui.notifications.message("Shows Added", "Automatically added " + str(num_added) + " from their existing metadata files")

        # if we're done then go home
        if not dirs_only:
            redirect("/home/")

        # for the remaining shows we need to prompt for each one, so forward this on to the newShow page
        return self.newShow(dirs_only[0], dirs_only[1:])


ErrorLogsMenu = [
    { 'title': 'Clear Errors', 'path': 'errorlogs/clearerrors/' },
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
        redirect("/errorlogs/")

    @cherrypy.expose
    def viewlog(self, minLevel=logger.MESSAGE, maxLines=500):

        t = PageTemplate(file="viewlogs.tmpl")
        t.submenu = ErrorLogsMenu

        minLevel = int(minLevel)

        data = []
        if os.path.isfile(logger.sb_log_instance.log_file_path):
            with ek.ek(open, logger.sb_log_instance.log_file_path) as f:
                data = f.readlines()

        regex = "^(\d\d\d\d)\-(\d\d)\-(\d\d)\s*(\d\d)\:(\d\d):(\d\d)\s*([A-Z]+)\s*(.+?)\s*\:\:\s*(.*)$"

        finalData = []

        numLines = 0
        lastLine = False
        numToShow = min(maxLines, len(data))

        for x in reversed(data):

            x = x.decode('utf-8')
            match = re.match(regex, x)

            if match:
                level = match.group(7)
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
                finalData.append("AA" + x)

            numLines += 1

            if numLines >= numToShow:
                break

        result = "".join(finalData)

        t.logLines = result
        t.minLevel = minLevel

        return _munge(t)


class Home:

    @cherrypy.expose
    def is_alive(self, *args, **kwargs):
        if 'callback' in kwargs and '_' in kwargs:
            callback, _ = kwargs['callback'], kwargs['_']
        else:
            return "Error: Unsupported Request. Send jsonp request with 'callback' variable in the query stiring."
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        cherrypy.response.headers['Content-Type'] = 'text/javascript'
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        cherrypy.response.headers['Access-Control-Allow-Headers'] = 'x-requested-with'

        if sickbeard.started:
            return callback + '(' + json.dumps({"msg": str(sickbeard.PID)}) + ');'
        else:
            return callback + '(' + json.dumps({"msg": "nope"}) + ');'

    @cherrypy.expose
    def index(self):

        t = PageTemplate(file="home.tmpl")
        t.submenu = HomeMenu()
        return _munge(t)

    addShows = NewHomeAddShows()

    postprocess = HomePostProcess()

    @cherrypy.expose
    def testSABnzbd(self, host=None, username=None, password=None, apikey=None):

        host = config.clean_url(host)

        connection, accesMsg = sab.getSabAccesMethod(host, username, password, apikey)
        if connection:
            authed, authMsg = sab.testAuthentication(host, username, password, apikey)  # @UnusedVariable
            if authed:
                return "Success. Connected and authenticated"
            else:
                return "Authentication failed. SABnzbd expects '" + accesMsg + "' as authentication method"
        else:
            return "Unable to connect to host"

    @cherrypy.expose
    def testGrowl(self, host=None, password=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        host = config.clean_host(host, default_port=23053)

        result = notifiers.growl_notifier.test_notify(host, password)
        if password == None or password == '':
            pw_append = ''
        else:
            pw_append = " with password: " + password

        if result:
            return "Registered and Tested growl successfully " + urllib.unquote_plus(host) + pw_append
        else:
            return "Registration and Testing of growl failed " + urllib.unquote_plus(host) + pw_append

    @cherrypy.expose
    def testProwl(self, prowl_api=None, prowl_priority=0):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.prowl_notifier.test_notify(prowl_api, prowl_priority)
        if result:
            return "Test prowl notice sent successfully"
        else:
            return "Test prowl notice failed"

    @cherrypy.expose
    def testBoxcar2(self, accessToken=None, sound=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.boxcar2_notifier.test_notify(accessToken, sound)
        if result:
            return "Boxcar2 notification succeeded. Check your Boxcar2 clients to make sure it worked"
        else:
            return "Error sending Boxcar2 notification"

    @cherrypy.expose
    def testPushover(self, userKey=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.pushover_notifier.test_notify(userKey)
        if result:
            return "Pushover notification succeeded. Check your Pushover clients to make sure it worked"
        else:
            return "Error sending Pushover notification"

    @cherrypy.expose
    def twitterStep1(self):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        return notifiers.twitter_notifier._get_authorization()

    @cherrypy.expose
    def twitterStep2(self, key):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.twitter_notifier._get_credentials(key)
        logger.log(u"result: " + str(result))
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
            return "Error sending Tweet"

    @cherrypy.expose
    def testXBMC(self, host=None, username=None, password=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        host = config.clean_hosts(host)
        finalResult = ''

        for curHost in [x.strip() for x in host.split(",")]:
            curResult = notifiers.xbmc_notifier.test_notify(urllib.unquote_plus(curHost), username, password)
            if len(curResult.split(":")) > 2 and 'OK' in curResult.split(":")[2]:
                finalResult += "Test XBMC notice sent successfully to " + urllib.unquote_plus(curHost)
            else:
                finalResult += "Test XBMC notice failed to " + urllib.unquote_plus(curHost)
            finalResult += "<br />\n"

        return finalResult

    @cherrypy.expose
    def testPLEX(self, host=None, username=None, password=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        host = config.clean_hosts(host)
        finalResult = ''

        for curHost in [x.strip() for x in host.split(",")]:
            curResult = notifiers.plex_notifier.test_notify(urllib.unquote_plus(curHost), username, password)
            if len(curResult.split(":")) > 2 and 'OK' in curResult.split(":")[2]:
                finalResult += "Test Plex notice sent successfully to " + urllib.unquote_plus(curHost)
            else:
                finalResult += "Test Plex notice failed to " + urllib.unquote_plus(curHost)
            finalResult += "<br />\n"

        return finalResult

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

        host = config.clean_host(host)
        result = notifiers.nmj_notifier.test_notify(urllib.unquote_plus(host), database, mount)
        if result:
            return "Successfully started the scan update for NMJ"
        else:
            return "Failed to start the scan update for NMJ"

    @cherrypy.expose
    def settingsNMJ(self, host=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        host = config.clean_host(host)
        result = notifiers.nmj_notifier.notify_settings(urllib.unquote_plus(host))
        if result:
            return '{"message": "Got settings from %(host)s", "database": "%(database)s", "mount": "%(mount)s"}' % {"host": host, "database": sickbeard.NMJ_DATABASE, "mount": sickbeard.NMJ_MOUNT}
        else:
            return '{"message": "Failed! Make sure your Popcorn is on and NMJ is running. (see Log & Errors -> Debug for detailed info)", "database": "", "mount": ""}'

    @cherrypy.expose
    def testNMJv2(self, host=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        host = config.clean_host(host)
        result = notifiers.nmjv2_notifier.test_notify(urllib.unquote_plus(host))
        if result:
            return "Successfully started the scan update for NMJv2"
        else:
            return "Failed to start the scan update for NMJv2"

    @cherrypy.expose
    def settingsNMJv2(self, host=None, dbloc=None, instance=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        host = config.clean_host(host)
        result = notifiers.nmjv2_notifier.notify_settings(urllib.unquote_plus(host), dbloc, instance)
        if result:
            return '{"message": "NMJv2 Database found at: %(host)s", "database": "%(database)s"}' % {"host": host, "database": sickbeard.NMJv2_DATABASE}
        else:
            return '{"message": "Unable to find NMJv2 Database at location: %(dbloc)s. Is the right location selected and PCH running?", "database": ""}' % {"dbloc": dbloc}

    @cherrypy.expose
    def testTrakt(self, api=None, username=None, password=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.trakt_notifier.test_notify(api, username, password)
        if result:
            return "Test notice sent successfully to Trakt"
        else:
            return "Test notice failed to Trakt"

    @cherrypy.expose
    def testNMA(self, nma_api=None, nma_priority=0):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.nma_notifier.test_notify(nma_api, nma_priority)
        if result:
            return "Test NMA notice sent successfully"
        else:
            return "Test NMA notice failed"

    @cherrypy.expose
    def testPushalot(self, authorizationtoken=None):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.pushalot_notifier.test_notify(authorizationtoken)
        if result:
            return "Pushalot notification succeeded. Check your Pushalot clients to make sure it worked"
        else:
            return "Error sending Pushalot notification"

    @cherrypy.expose
    def testSynoNotify(self):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        result = notifiers.synoindex_notifier.test_notify()
        if result:
            return "Test Synology notice sent successfully"
        else:
            return "Test Synology notice failed"

    @cherrypy.expose
    def shutdown(self, pid=None):

        if str(pid) != str(sickbeard.PID):
            redirect("/home/")

        threading.Timer(2, sickbeard.invoke_shutdown).start()

        title = "Shutting down"
        message = "Sick Beard is shutting down..."

        return _genericMessage(title, message)

    @cherrypy.expose
    def restart(self, pid=None):

        if str(pid) != str(sickbeard.PID):
            redirect("/home/")

        t = PageTemplate(file="restart.tmpl")
        t.submenu = HomeMenu()

        # do a soft restart
        threading.Timer(2, sickbeard.invoke_restart, [False]).start()

        return _munge(t)

    @cherrypy.expose
    def update(self, pid=None):

        if str(pid) != str(sickbeard.PID):
            redirect("/home/")

        updated = sickbeard.versionCheckScheduler.action.update()  # @UndefinedVariable

        if updated:
            # do a hard restart
            threading.Timer(2, sickbeard.invoke_restart, [False]).start()
            t = PageTemplate(file="restart_bare.tmpl")
            return _munge(t)
        else:
            return _genericMessage("Update Failed", "Update wasn't successful, not restarting. Check your log for more information.")

    @cherrypy.expose
    def displayShow(self, show=None):

        if show == None:
            return _genericMessage("Error", "Invalid show ID")
        else:
            showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

            if showObj == None:
                return _genericMessage("Error", "Show not in show list")

        myDB = db.DBConnection()

        seasonResults = myDB.select(
            "SELECT DISTINCT season FROM tv_episodes WHERE showid = ? ORDER BY season desc",
            [showObj.tvdbid]
        )

        sqlResults = myDB.select(
            "SELECT * FROM tv_episodes WHERE showid = ? ORDER BY season DESC, episode DESC",
            [showObj.tvdbid]
        )

        t = PageTemplate(file="displayShow.tmpl")
        t.submenu = [ { 'title': 'Edit', 'path': 'home/editShow?show=%d' % showObj.tvdbid } ]

        try:
            t.showLoc = (showObj.location, True)
        except sickbeard.exceptions.ShowDirNotFoundException:
            t.showLoc = (showObj._location, False)

        show_message = ''

        if sickbeard.showQueueScheduler.action.isBeingAdded(showObj):  # @UndefinedVariable
            show_message = 'This show is in the process of being downloaded from theTVDB.com - the info below is incomplete.'

        elif sickbeard.showQueueScheduler.action.isBeingUpdated(showObj):  # @UndefinedVariable
            show_message = 'The information below is in the process of being updated.'

        elif sickbeard.showQueueScheduler.action.isBeingRefreshed(showObj):  # @UndefinedVariable
            show_message = 'The episodes below are currently being refreshed from disk'

        elif sickbeard.showQueueScheduler.action.isInRefreshQueue(showObj):  # @UndefinedVariable
            show_message = 'This show is queued to be refreshed.'

        elif sickbeard.showQueueScheduler.action.isInUpdateQueue(showObj):  # @UndefinedVariable
            show_message = 'This show is queued and awaiting an update.'

        if not sickbeard.showQueueScheduler.action.isBeingAdded(showObj):  # @UndefinedVariable
            if not sickbeard.showQueueScheduler.action.isBeingUpdated(showObj):  # @UndefinedVariable
                t.submenu.append({ 'title': 'Delete',               'path': 'home/deleteShow?show=%d' % showObj.tvdbid, 'confirm': True })
                t.submenu.append({ 'title': 'Re-scan files',        'path': 'home/refreshShow?show=%d' % showObj.tvdbid })
                t.submenu.append({ 'title': 'Force Full Update',    'path': 'home/updateShow?show=%d&amp;force=1' % showObj.tvdbid })
                t.submenu.append({ 'title': 'Update show in XBMC',  'path': 'home/updateXBMC?show=%d' % showObj.tvdbid, 'requires': haveXBMC })
                t.submenu.append({ 'title': 'Preview Rename',       'path': 'home/testRename?show=%d' % showObj.tvdbid })

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
        epCounts[Overview.SNATCHED] = 0

        for curResult in sqlResults:

            curEpCat = showObj.getOverview(int(curResult["status"]))
            epCats[str(curResult["season"]) + "x" + str(curResult["episode"])] = curEpCat
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
    def editShow(self, show=None, location=None, anyQualities=[], bestQualities=[], flatten_folders=None, paused=None, directCall=False, air_by_date=None, tvdbLang=None, rls_ignore_words=None, rls_require_words=None):

        if show == None:
            errString = "Invalid show ID: " + str(show)
            if directCall:
                return [errString]
            else:
                return _genericMessage("Error", errString)

        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

        if showObj == None:
            errString = "Unable to find the specified show: " + str(show)
            if directCall:
                return [errString]
            else:
                return _genericMessage("Error", errString)

        if not location and not anyQualities and not bestQualities and not flatten_folders:

            t = PageTemplate(file="editShow.tmpl")
            t.submenu = HomeMenu()
            with showObj.lock:
                t.show = showObj

            return _munge(t)

        flatten_folders = config.checkbox_to_value(flatten_folders)
        paused = config.checkbox_to_value(paused)
        air_by_date = config.checkbox_to_value(air_by_date)

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

            # reversed for now
            if bool(showObj.flatten_folders) != bool(flatten_folders):
                showObj.flatten_folders = flatten_folders
                try:
                    sickbeard.showQueueScheduler.action.refreshShow(showObj)  # @UndefinedVariable
                except exceptions.CantRefreshException, e:
                    errors.append("Unable to refresh this show: " + ex(e))

            showObj.paused = paused

            # if this routine was called via the mass edit, do not change the options that are not passed
            if not directCall:
                showObj.air_by_date = air_by_date
                showObj.lang = tvdb_lang
                showObj.rls_ignore_words = rls_ignore_words.strip()
                showObj.rls_require_words = rls_require_words.strip()

            # if we change location clear the db of episodes, change it, write to db, and rescan
            if os.path.normpath(showObj._location) != os.path.normpath(location):
                logger.log(os.path.normpath(showObj._location) + " != " + os.path.normpath(location), logger.DEBUG)
                if not ek.ek(os.path.isdir, location):
                    errors.append("New location <tt>%s</tt> does not exist" % location)

                # don't bother if we're going to update anyway
                elif not do_update:
                    # change it
                    try:
                        showObj.location = location
                        try:
                            sickbeard.showQueueScheduler.action.refreshShow(showObj)  # @UndefinedVariable
                        except exceptions.CantRefreshException, e:
                            errors.append("Unable to refresh this show:" + ex(e))
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
                sickbeard.showQueueScheduler.action.updateShow(showObj, True)  # @UndefinedVariable
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

        if sickbeard.showQueueScheduler.action.isBeingAdded(showObj) or sickbeard.showQueueScheduler.action.isBeingUpdated(showObj):  # @UndefinedVariable
            return _genericMessage("Error", "Shows can't be deleted while they're being added or updated.")

        showObj.deleteShow()

        ui.notifications.message('<b>%s</b> has been deleted' % showObj.name)
        redirect("/home/")

    @cherrypy.expose
    def refreshShow(self, show=None):

        if show == None:
            return _genericMessage("Error", "Invalid show ID")

        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

        if showObj == None:
            return _genericMessage("Error", "Unable to find the specified show")

        # force the update from the DB
        try:
            sickbeard.showQueueScheduler.action.refreshShow(showObj)  # @UndefinedVariable
        except exceptions.CantRefreshException, e:
            ui.notifications.error("Unable to refresh this show.", ex(e))

        time.sleep(3)

        redirect("/home/displayShow?show=" + str(showObj.tvdbid))

    @cherrypy.expose
    def updateShow(self, show=None, force=0):

        if show == None:
            return _genericMessage("Error", "Invalid show ID")

        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

        if showObj == None:
            return _genericMessage("Error", "Unable to find the specified show")

        # force the update
        try:
            sickbeard.showQueueScheduler.action.updateShow(showObj, bool(force))  # @UndefinedVariable
        except exceptions.CantUpdateException, e:
            ui.notifications.error("Unable to update this show.", ex(e))

        # just give it some time
        time.sleep(3)

        redirect("/home/displayShow?show=" + str(showObj.tvdbid))

    @cherrypy.expose
    def updateXBMC(self, show=None):
        if sickbeard.XBMC_UPDATE_ONLYFIRST:
            # only send update to first host in the list -- workaround for xbmc sql backend users
            host = sickbeard.XBMC_HOST.split(",")[0].strip()
        else:
            host = sickbeard.XBMC_HOST

        if show:
            show_obj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))
        else:
            show_obj = None

        if notifiers.xbmc_notifier.update_library(show_obj=show_obj):
            ui.notifications.message("Library update command sent to XBMC host(s): " + host)
        else:
            ui.notifications.error("Unable to contact one or more XBMC host(s): " + host)
        redirect("/home/")

    @cherrypy.expose
    def updatePLEX(self):
        if notifiers.plex_notifier.update_library():
            ui.notifications.message("Library update command sent to Plex Media Server host: " + sickbeard.PLEX_SERVER_HOST)
        else:
            ui.notifications.error("Unable to contact Plex Media Server host: " + sickbeard.PLEX_SERVER_HOST)
        redirect("/home/")

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

                logger.log(u"Attempting to set status on episode " + curEp + " to " + status, logger.DEBUG)

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
                        logger.log(u"Refusing to change status of " + curEp + " because it is UNAIRED", logger.ERROR)
                        continue

                    if int(status) in Quality.DOWNLOADED and epObj.status not in Quality.SNATCHED + Quality.SNATCHED_PROPER + Quality.DOWNLOADED + [IGNORED] and not ek.ek(os.path.isfile, epObj.location):
                        logger.log(u"Refusing to change status of " + curEp + " to DOWNLOADED because it's not SNATCHED/DOWNLOADED", logger.ERROR)
                        continue

                    epObj.status = int(status)
                    epObj.saveToDB()

        msg = "Backlog was automatically started for the following seasons of <b>" + showObj.name + "</b>:<br /><ul>"
        for cur_segment in segment_list:
            msg += "<li>Season " + str(cur_segment) + "</li>"
            logger.log(u"Sending backlog for " + showObj.name + " season " + str(cur_segment) + " because some eps were set to wanted")
            cur_backlog_queue_item = search_queue.BacklogQueueItem(showObj, cur_segment)
            sickbeard.searchQueueScheduler.action.add_item(cur_backlog_queue_item)  # @UndefinedVariable
        msg += "</ul>"

        if segment_list:
            ui.notifications.message("Backlog started", msg)

        if direct:
            return json.dumps({'result': 'success'})
        else:
            redirect("/home/displayShow?show=" + show)

    @cherrypy.expose
    def testRename(self, show=None):

        if show == None:
            return _genericMessage("Error", "You must specify a show")

        showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

        if showObj == None:
            return _genericMessage("Error", "Show not in show list")

        try:
            show_loc = showObj.location  # @UnusedVariable
        except exceptions.ShowDirNotFoundException:
            return _genericMessage("Error", "Can't rename episodes when the show dir is missing.")

        ep_obj_rename_list = []

        ep_obj_list = showObj.getAllEpisodes(has_location=True)

        for cur_ep_obj in ep_obj_list:
            # Only want to rename if we have a location
            if cur_ep_obj.location:
                if cur_ep_obj.relatedEps:
                    # do we have one of multi-episodes in the rename list already
                    have_already = False
                    for cur_related_ep in cur_ep_obj.relatedEps + [cur_ep_obj]:
                        if cur_related_ep in ep_obj_rename_list:
                            have_already = True
                            break
                    if not have_already:
                        ep_obj_rename_list.append(cur_ep_obj)

                else:
                    ep_obj_rename_list.append(cur_ep_obj)

        if ep_obj_rename_list:
            # present season DESC episode DESC on screen
            ep_obj_rename_list.reverse()

        t = PageTemplate(file="testRename.tmpl")
        t.submenu = [{'title': 'Edit', 'path': 'home/editShow?show=%d' % showObj.tvdbid}]
        t.ep_obj_list = ep_obj_rename_list
        t.show = showObj

        return _munge(t)

    @cherrypy.expose
    def doRename(self, show=None, eps=None):

        if show == None or eps == None:
            errMsg = "You must specify a show and at least one episode"
            return _genericMessage("Error", errMsg)

        show_obj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

        if show_obj == None:
            errMsg = "Error", "Show not in show list"
            return _genericMessage("Error", errMsg)

        try:
            show_loc = show_obj.location  # @UnusedVariable
        except exceptions.ShowDirNotFoundException:
            return _genericMessage("Error", "Can't rename episodes when the show dir is missing.")

        myDB = db.DBConnection()

        if eps == None:
            redirect("/home/displayShow?show=" + show)

        for curEp in eps.split('|'):

            epInfo = curEp.split('x')

            # this is probably the worst possible way to deal with double eps but I've kinda painted myself into a corner here with this stupid database
            ep_result = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ? AND 5=5", [show, epInfo[0], epInfo[1]])
            if not ep_result:
                logger.log(u"Unable to find an episode for " + curEp + ", skipping", logger.WARNING)
                continue

            related_eps_result = myDB.select("SELECT * FROM tv_episodes WHERE location = ? AND episode != ?", [ep_result[0]["location"], epInfo[1]])

            root_ep_obj = show_obj.getEpisode(int(epInfo[0]), int(epInfo[1]))
            root_ep_obj.relatedEps = []

            for cur_related_ep in related_eps_result:
                related_ep_obj = show_obj.getEpisode(int(cur_related_ep["season"]), int(cur_related_ep["episode"]))
                if related_ep_obj not in root_ep_obj.relatedEps:
                    root_ep_obj.relatedEps.append(related_ep_obj)

            root_ep_obj.rename()

        redirect("/home/displayShow?show=" + show)

    @cherrypy.expose
    def searchEpisode(self, show=None, season=None, episode=None):

        # retrieve the episode object and fail if we can't get one
        ep_obj = _getEpisode(show, season, episode)
        if isinstance(ep_obj, str):
            return json.dumps({'result': 'failure'})

        # make a queue item for it and put it on the queue
        ep_queue_item = search_queue.ManualSearchQueueItem(ep_obj)
        sickbeard.searchQueueScheduler.action.add_item(ep_queue_item)  # @UndefinedVariable

        # wait until the queue item tells us whether it worked or not
        while ep_queue_item.success == None:  # @UndefinedVariable
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
            messages['notification-' + str(cur_notification_num)] = {'title': cur_notification.title,
                                                                   'message': cur_notification.message,
                                                                   'type': cur_notification.type}
            cur_notification_num += 1

        return json.dumps(messages)


class WebInterface:

    @cherrypy.expose
    def robots_txt(self):
        """ Keep web crawlers out """
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        return 'User-agent: *\nDisallow: /\n'

    @cherrypy.expose
    def index(self):

        redirect("/home/")

    @cherrypy.expose
    def showPoster(self, show=None, which=None):

        if which == 'poster':
            default_image_name = 'poster.png'
        else:
            default_image_name = 'banner.png'

        default_image_path = ek.ek(os.path.join, sickbeard.PROG_DIR, 'data', 'images', default_image_name)
        if show is None:
            return cherrypy.lib.static.serve_file(default_image_path, content_type="image/png")
        else:
            showObj = sickbeard.helpers.findCertainShow(sickbeard.showList, int(show))

        if showObj is None:
            return cherrypy.lib.static.serve_file(default_image_path, content_type="image/png")

        cache_obj = image_cache.ImageCache()

        if which == 'poster':
            image_file_name = cache_obj.poster_path(showObj.tvdbid)
        # this is for 'banner' but also the default case
        else:
            image_file_name = cache_obj.banner_path(showObj.tvdbid)

        if ek.ek(os.path.isfile, image_file_name):
            # use startup argument to prevent using PIL even if installed
            if sickbeard.NO_RESIZE:
                return cherrypy.lib.static.serve_file(image_file_name, content_type="image/jpeg")
            try:
                from PIL import Image
                from cStringIO import StringIO
            except ImportError:  # PIL isn't installed
                return cherrypy.lib.static.serve_file(image_file_name, content_type="image/jpeg")
            else:
                im = Image.open(image_file_name)
                if im.mode == 'P':  # Convert GIFs to RGB
                    im = im.convert('RGB')
                if which == 'banner':
                    size = 606, 112
                elif which == 'poster':
                    size = 136, 200
                else:
                    return cherrypy.lib.static.serve_file(image_file_name, content_type="image/jpeg")
                im = im.resize(size, Image.ANTIALIAS)
                imgbuffer = StringIO()
                im.save(imgbuffer, 'JPEG', quality=85)
                cherrypy.response.headers['Content-Type'] = 'image/jpeg'
                return imgbuffer.getvalue()
        else:
            return cherrypy.lib.static.serve_file(default_image_path, content_type="image/png")

    @cherrypy.expose
    def setComingEpsLayout(self, layout):
        if layout not in ('poster', 'banner', 'list'):
            layout = 'banner'

        sickbeard.COMING_EPS_LAYOUT = layout

        redirect("/comingEpisodes/")

    @cherrypy.expose
    def toggleComingEpsDisplayPaused(self):

        sickbeard.COMING_EPS_DISPLAY_PAUSED = not sickbeard.COMING_EPS_DISPLAY_PAUSED

        redirect("/comingEpisodes/")

    @cherrypy.expose
    def setComingEpsSort(self, sort):
        if sort not in ('date', 'network', 'show'):
            sort = 'date'

        sickbeard.COMING_EPS_SORT = sort

        redirect("/comingEpisodes/")

    @cherrypy.expose
    def comingEpisodes(self, layout="None"):

        myDB = db.DBConnection()

        today = datetime.date.today().toordinal()
        next_week = (datetime.date.today() + datetime.timedelta(days=7)).toordinal()
        recently = (datetime.date.today() - datetime.timedelta(days=3)).toordinal()

        done_show_list = []
        qualList = Quality.DOWNLOADED + Quality.SNATCHED + [ARCHIVED, IGNORED]
        sql_results = myDB.select("SELECT *, tv_shows.status as show_status FROM tv_episodes, tv_shows WHERE season > 0 AND airdate >= ? AND airdate < ? AND tv_shows.tvdb_id = tv_episodes.showid AND tv_episodes.status NOT IN (" + ','.join(['?'] * len(qualList)) + ")", [today, next_week] + qualList)
        for cur_result in sql_results:
            done_show_list.append(int(cur_result["showid"]))

        more_sql_results = myDB.select("SELECT *, tv_shows.status as show_status FROM tv_episodes outer_eps, tv_shows WHERE season > 0 AND showid NOT IN (" + ','.join(['?'] * len(done_show_list)) + ") AND tv_shows.tvdb_id = outer_eps.showid AND airdate = (SELECT airdate FROM tv_episodes inner_eps WHERE inner_eps.season > 0 AND inner_eps.showid = outer_eps.showid AND inner_eps.airdate >= ? ORDER BY inner_eps.airdate ASC LIMIT 1) AND outer_eps.status NOT IN (" + ','.join(['?'] * len(Quality.DOWNLOADED + Quality.SNATCHED)) + ")", done_show_list + [next_week] + Quality.DOWNLOADED + Quality.SNATCHED)
        sql_results += more_sql_results

        more_sql_results = myDB.select("SELECT *, tv_shows.status as show_status FROM tv_episodes, tv_shows WHERE season > 0 AND tv_shows.tvdb_id = tv_episodes.showid AND airdate < ? AND airdate >= ? AND tv_episodes.status = ? AND tv_episodes.status NOT IN (" + ','.join(['?'] * len(qualList)) + ")", [today, recently, WANTED] + qualList)
        sql_results += more_sql_results

        # sort by air date
        sorts = {
            'date': (lambda x, y: cmp(int(x["airdate"]), int(y["airdate"]))),
            'show': (lambda a, b: cmp(a["show_name"], b["show_name"])),
            'network': (lambda a, b: cmp(a["network"], b["network"])),
        }

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

        # allow local overriding of layout parameter
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
