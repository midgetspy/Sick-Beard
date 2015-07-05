# Author: Sebastien Erard <sebastien_erard@hotmail.com>
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

import os
import subprocess

import sickbeard

from sickbeard import logger
from sickbeard.common import notifyStrings, NOTIFY_SNATCH, NOTIFY_DOWNLOAD
from sickbeard import encodingKludge as ek
from sickbeard.exceptions import ex


class synoIndexNotifier:

    def moveFolder(self, old_path, new_path):
        self.moveObject(old_path, new_path)

    def moveFile(self, old_file, new_file):
        self.moveObject(old_file, new_file)

    def moveObject(self, old_path, new_path):
        if sickbeard.USE_SYNOINDEX:
            synoindex_cmd = ['/usr/syno/bin/synoindex', '-N', ek.ek(os.path.abspath, new_path), ek.ek(os.path.abspath, old_path)]
            logger.log(u"SYNOINDEX: Executing command " + str(synoindex_cmd), logger.DEBUG)
            logger.log(u"SYNOINDEX: Absolute path to command: " + ek.ek(os.path.abspath, synoindex_cmd[0]), logger.DEBUG)
            try:
                p = subprocess.Popen(synoindex_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=sickbeard.PROG_DIR)
                out, err = p.communicate()  # @UnusedVariable
                logger.log(u"SYNOINDEX: Script result: " + str(out), logger.DEBUG)
            except OSError, e:
                logger.log(u"SYNOINDEX: Unable to run synoindex: " + ex(e), logger.WARNING)

    def deleteFolder(self, cur_path):
        self.makeObject('-D', cur_path)

    def addFolder(self, cur_path):
        self.makeObject('-A', cur_path)

    def deleteFile(self, cur_file):
        self.makeObject('-d', cur_file)

    def addFile(self, cur_file):
        self.makeObject('-a', cur_file)

    def makeObject(self, cmd_arg, cur_path):
        if sickbeard.USE_SYNOINDEX:
            synoindex_cmd = ['/usr/syno/bin/synoindex', cmd_arg, ek.ek(os.path.abspath, cur_path)]
            logger.log(u"SYNOINDEX: Executing command " + str(synoindex_cmd), logger.DEBUG)
            logger.log(u"SYNOINDEX: Absolute path to command: " + ek.ek(os.path.abspath, synoindex_cmd[0]), logger.DEBUG)
            try:
                p = subprocess.Popen(synoindex_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=sickbeard.PROG_DIR)
                out, err = p.communicate()  # @UnusedVariable
                logger.log(u"SYNOINDEX: Script result: " + str(out), logger.DEBUG)
            except OSError, e:
                logger.log(u"SYNOINDEX: Unable to run synoindex: " + ex(e), logger.WARNING)

    def _notify(self, message, title, force=False):
        # suppress notifications if the notifier is disabled but the notify options are checked
        if not sickbeard.USE_SYNOINDEX and not force:
            return False

        synodsmnotify_cmd = ['/usr/syno/bin/synodsmnotify', '@administrators', title, message]
        logger.log(u"SYNOINDEX: Executing command " + str(synodsmnotify_cmd), logger.DEBUG)

        try:
            p = subprocess.Popen(synodsmnotify_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 cwd=sickbeard.PROG_DIR)

            output, err = p.communicate()  # @UnusedVariable
            exit_status = p.returncode

            logger.log(u"SYNOINDEX: Script result: " + str(output), logger.DEBUG)

            if exit_status == 0:
                return True
            else:
                return False

        except OSError, e:
            logger.log(u"SYNOINDEX: Unable to run synodsmnotify: " + ex(e), logger.WARNING)
            return False

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        if sickbeard.SYNOINDEX_NOTIFY_ONSNATCH:
            self._notify(notifyStrings[NOTIFY_SNATCH], ep_name)

    def notify_download(self, ep_name):
        if sickbeard.SYNOINDEX_NOTIFY_ONDOWNLOAD:
            self._notify(notifyStrings[NOTIFY_DOWNLOAD], ep_name)

    def test_notify(self):
        return self._notify("This is a test notification from Sick Beard", "Test", force=True)

    def update_library(self, ep_obj=None):
        if sickbeard.USE_SYNOINDEX:
            self.addFile(ep_obj.location)

notifier = synoIndexNotifier
