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
import os.path
import datetime

from sickbeard import helpers
from sickbeard import logger

import sickbeard

naming_ep_type = ("%(seasonnumber)dx%(episodenumber)02d",
                  "s%(seasonnumber)02de%(episodenumber)02d",
                   "S%(seasonnumber)02dE%(episodenumber)02d",
                   "%(seasonnumber)02dx%(episodenumber)02d")
naming_ep_type_text = ("1x02", "s01e02", "S01E02", "01x02")

naming_multi_ep_type = {0: ["-%(episodenumber)02d"]*len(naming_ep_type),
                        1: [" - " + x for x in naming_ep_type],
                        2: [x + "%(episodenumber)02d" for x in ("x", "e", "E", "x")]}
naming_multi_ep_type_text = ("extend", "duplicate", "repeat")

naming_sep_type = (" - ", " ")
naming_sep_type_text = (" - ", "space")

def change_HTTPS_CERT(https_cert):

    if https_cert == '':
        sickbeard.HTTPS_CERT = ''
        return True

    if os.path.normpath(sickbeard.HTTPS_CERT) != os.path.normpath(https_cert):
        if helpers.makeDir(os.path.dirname(os.path.abspath(https_cert))):
            sickbeard.HTTPS_CERT = os.path.normpath(https_cert)
            logger.log(u"Changed https cert path to " + https_cert)
        else:
            return False

    return True

def change_HTTPS_KEY(https_key):

    if https_key == '':
        sickbeard.HTTPS_KEY = ''
        return True

    if os.path.normpath(sickbeard.HTTPS_KEY) != os.path.normpath(https_key):
        if helpers.makeDir(os.path.dirname(os.path.abspath(https_key))):
            sickbeard.HTTPS_KEY = os.path.normpath(https_key)
            logger.log(u"Changed https key path to " + https_key)
        else:
            return False

    return True

def change_LOG_DIR(log_dir):

    if os.path.normpath(sickbeard.LOG_DIR) != os.path.normpath(log_dir):
        if helpers.makeDir(log_dir):
            sickbeard.LOG_DIR = os.path.normpath(log_dir)
            logger.sb_log_instance.initLogging()
            logger.log(u"Initialized new log file in " + log_dir)

            cherry_log = os.path.join(sickbeard.LOG_DIR, "cherrypy.log")
            cherrypy.config.update({'log.access_file': cherry_log})

            logger.log(u"Changed cherry log file to " + cherry_log)

        else:
            return False

    return True

def change_NZB_DIR(nzb_dir):

    if nzb_dir == '':
        sickbeard.NZB_DIR = ''
        return True

    if os.path.normpath(sickbeard.NZB_DIR) != os.path.normpath(nzb_dir):
        if helpers.makeDir(nzb_dir):
            sickbeard.NZB_DIR = os.path.normpath(nzb_dir)
            logger.log(u"Changed NZB folder to " + nzb_dir)
        else:
            return False

    return True


def change_TORRENT_DIR(torrent_dir):

    if torrent_dir == '':
        sickbeard.TORRENT_DIR = ''
        return True

    if os.path.normpath(sickbeard.TORRENT_DIR) != os.path.normpath(torrent_dir):
        if helpers.makeDir(torrent_dir):
            sickbeard.TORRENT_DIR = os.path.normpath(torrent_dir)
            logger.log(u"Changed torrent folder to " + torrent_dir)
        else:
            return False

    return True


def change_TV_DOWNLOAD_DIR(tv_download_dir):

    if tv_download_dir == '':
        sickbeard.TV_DOWNLOAD_DIR = ''
        return True

    if os.path.normpath(sickbeard.TV_DOWNLOAD_DIR) != os.path.normpath(tv_download_dir):
        if helpers.makeDir(tv_download_dir):
            sickbeard.TV_DOWNLOAD_DIR = os.path.normpath(tv_download_dir)
            logger.log(u"Changed TV download folder to " + tv_download_dir)
        else:
            return False

    return True


def change_SEARCH_FREQUENCY(freq):

    if freq == None:
        freq = sickbeard.DEFAULT_SEARCH_FREQUENCY
    else:
        freq = int(freq)

    if freq < sickbeard.MIN_SEARCH_FREQUENCY:
        freq = sickbeard.MIN_SEARCH_FREQUENCY

    sickbeard.SEARCH_FREQUENCY = freq

    sickbeard.currentSearchScheduler.cycleTime = datetime.timedelta(minutes=sickbeard.SEARCH_FREQUENCY)
    sickbeard.backlogSearchScheduler.cycleTime = datetime.timedelta(minutes=sickbeard.get_backlog_cycle_time())

def change_VERSION_NOTIFY(version_notify):
   
    oldSetting = sickbeard.VERSION_NOTIFY

    sickbeard.VERSION_NOTIFY = version_notify

    if version_notify == False:
        sickbeard.NEWEST_VERSION_STRING = None;
        
    if oldSetting == False and version_notify == True:
        sickbeard.versionCheckScheduler.action.run() #@UndefinedVariable

