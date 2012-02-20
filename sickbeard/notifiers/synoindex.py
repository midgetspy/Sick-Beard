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
from sickbeard import encodingKludge as ek
from sickbeard.exceptions import ex

class synoIndexNotifier:

    def notify_snatch(self, ep_name):
        pass

    def notify_download(self, ep_name):
        pass

    def moveFolder(self, old_path, new_path):
        if sickbeard.USE_SYNOINDEX:
            synoindex_cmd = ['/usr/syno/bin/synoindex', '-N', ek.ek(os.path.abspath, new_path), ek.ek(os.path.abspath, old_path)]
            logger.log(u"Executing command "+str(synoindex_cmd))
            logger.log(u"Absolute path to command: "+ek.ek(os.path.abspath, synoindex_cmd[0]), logger.DEBUG)
            try:
                p = subprocess.Popen(synoindex_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=sickbeard.PROG_DIR)
                out, err = p.communicate() #@UnusedVariable
                logger.log(u"Script result: "+str(out), logger.DEBUG)
            except OSError, e:
                logger.log(u"Unable to run synoindex: "+ex(e))           

    def deleteFolder(self, cur_path):
        if sickbeard.USE_SYNOINDEX:
            synoindex_cmd = ['/usr/syno/bin/synoindex', '-D', ek.ek(os.path.abspath, cur_path)]
            logger.log(u"Executing command "+str(synoindex_cmd))
            logger.log(u"Absolute path to command: "+ek.ek(os.path.abspath, synoindex_cmd[0]), logger.DEBUG)
            try:
                p = subprocess.Popen(synoindex_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=sickbeard.PROG_DIR)
                out, err = p.communicate() #@UnusedVariable
                logger.log(u"Script result: "+str(out), logger.DEBUG)
            except OSError, e:
                logger.log(u"Unable to run synoindex: "+ex(e))           

    def addFolder(self, cur_path):
        if sickbeard.USE_SYNOINDEX:
            synoindex_cmd = ['/usr/syno/bin/synoindex', '-A', ek.ek(os.path.abspath, cur_path)]
            logger.log(u"Executing command "+str(synoindex_cmd))
            logger.log(u"Absolute path to command: "+ek.ek(os.path.abspath, synoindex_cmd[0]), logger.DEBUG)
            try:
                p = subprocess.Popen(synoindex_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=sickbeard.PROG_DIR)
                out, err = p.communicate() #@UnusedVariable
                logger.log(u"Script result: "+str(out), logger.DEBUG)
            except OSError, e:
                logger.log(u"Unable to run synoindex: "+ex(e))           

    def deleteFile(self, cur_file):
        if sickbeard.USE_SYNOINDEX:
            synoindex_cmd = ['/usr/syno/bin/synoindex', '-d', ek.ek(os.path.abspath, cur_file)]
            logger.log(u"Executing command "+str(synoindex_cmd))
            logger.log(u"Absolute path to command: "+ek.ek(os.path.abspath, synoindex_cmd[0]), logger.DEBUG)
            try:
                p = subprocess.Popen(synoindex_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=sickbeard.PROG_DIR)
                out, err = p.communicate() #@UnusedVariable
                logger.log(u"Script result: "+str(out), logger.DEBUG)
            except OSError, e:
                logger.log(u"Unable to run synoindex: "+ex(e))           

    def addFile(self, cur_file):
        if sickbeard.USE_SYNOINDEX:
            synoindex_cmd = ['/usr/syno/bin/synoindex', '-a', ek.ek(os.path.abspath, cur_file)]
            logger.log(u"Executing command "+str(synoindex_cmd))
            logger.log(u"Absolute path to command: "+ek.ek(os.path.abspath, synoindex_cmd[0]), logger.DEBUG)
            try:
                p = subprocess.Popen(synoindex_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=sickbeard.PROG_DIR)
                out, err = p.communicate() #@UnusedVariable
                logger.log(u"Script result: "+str(out), logger.DEBUG)
            except OSError, e:
                logger.log(u"Unable to run synoindex: "+ex(e))

notifier = synoIndexNotifier
