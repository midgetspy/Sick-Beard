# -*- coding: utf-8 -*-
#
# Subliminal - Subtitles, faster than your thoughts
# Copyright (c) 2011 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of Subliminal.
#
# Subliminal is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import abc
import logging
import os
import re
import sys
import urllib2
import struct
import threading
from subliminal import encodingKludge as ek


class PluginBase(object):
    __metaclass__ = abc.ABCMeta
    multi_languages_queries = False
    multi_filename_queries = False
    api_based = True
    timeout = 3
    user_agent = 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.1.3)'
    lock = threading.Lock()

    @abc.abstractmethod
    def __init__(self, pluginLanguages, config_dict=None, isRevert=False):
        self.config_dict = config_dict
        if not pluginLanguages:
            self.pluginLanguages = None
            self.revertPluginLanguages = None
        elif not isRevert:
            self.pluginLanguages = pluginLanguages
            self.revertPluginLanguages = dict((v, k) for k, v in self.pluginLanguages.iteritems())
        else:
            self.revertPluginLanguages = pluginLanguages
            self.pluginLanguages = dict((v, k) for k, v in self.revertPluginLanguages.iteritems())
        self.logger = logging.getLogger('subliminal.%s' % self.getClassName())

    @staticmethod
    def getFileName(filepath):
        filename = filepath
        if ek.ek(os.path.isfile, filename):
            filename = ek.ek(os.path.basename, filename)
        if filename.endswith(('.avi', '.wmv', '.mov', '.mp4', '.mpeg', '.mpg', '.mkv')):
            filename = filename.rsplit('.', 1)[0]
        return filename

    def hashFile(self, filename):
        """Hash a file like OpenSubtitles"""
        longlongformat = 'q'  # long long
        bytesize = struct.calcsize(longlongformat)
        f = ek.ek(open, filename, "rb")
        filesize = ek.ek(os.path.getsize, filename)
        hash = filesize
        if filesize < 65536 * 2:
            self.logger.error(u"File %s is too small (SizeError < 2**16)" % filename)
            return []
        for x in range(65536 / bytesize):
            buffer = f.read(bytesize)
            (l_value,) = struct.unpack(longlongformat, buffer)
            hash += l_value
            hash = hash & 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number
        f.seek(max(0, filesize - 65536), 0)
        for x in range(65536 / bytesize):
            buffer = f.read(bytesize)
            (l_value,) = struct.unpack(longlongformat, buffer)
            hash += l_value
            hash = hash & 0xFFFFFFFFFFFFFFFF
        f.close()
        returnedhash = "%016x" % hash
        return returnedhash

    def downloadFile(self, url, filename, data=None):
        """Downloads the given url to the given filename"""
        try:
            self.logger.info(u"Downloading %s" % url)
            req = urllib2.Request(url, headers={'Referer': url, 'User-Agent': self.user_agent})
            f = urllib2.urlopen(req, data=data)
            dump = ek.ek(open, filename, "wb")
            dump.write(f.read())
            self.adjustPermissions(filename)
            dump.close()
            f.close()
            self.logger.debug(u"Download finished for file %s. Size: %s" % (filename, ek.ek(os.path.getsize, filename)))
        except urllib2.HTTPError, e:
            self.logger.error(u"HTTP Error:", e.code, url)
        except urllib2.URLError, e:
            self.logger.error(u"URL Error:", e.reason, url)

    def adjustPermissions(self, filepath):
        if self.config_dict and 'files_mode' in self.config_dict and self.config_dict['files_mode'] != -1:
            ek.ek(os.chmod, filepath, self.config_dict['files_mode'])

    @abc.abstractmethod
    def list(self, filenames, languages):
        """Main method to call when you want to list subtitles"""

    @abc.abstractmethod
    def download(self, subtitle):
        """Main method to call when you want to download a subtitle"""

    def getRevertLanguage(self, language):
        """Returns the short (two-character) representation from the long language name"""
        try:
            return self.revertPluginLanguages[language]
        except KeyError, e:
            self.logger.warn(u"Ooops, you found a missing language in the configuration file of %s: %s. Send a bug report to have it added." % (self.getClassName(), language))

    def checkLanguages(self, languages):
        if languages and not set(languages).intersection((self._plugin_languages.values())):
            self.logger.debug(u'None of requested languages %s are available' % languages)
            return False
        return True

    def getLanguage(self, language):
        """Returns the long naming of the language from a two character code"""
        try:
            return self.pluginLanguages[language]
        except KeyError, e:
            self.logger.warn(u"Ooops, you found a missing language in the configuration file of %s: %s. Send a bug report to have it added." % (self.getClassName(), language))

    def getExtension(self, subtitle):
        if self.config_dict and self.config_dict['multi']:
            return ".%s.srt" % subtitle['lang']
        return ".srt"

    def getClassName(self):
        return self.__class__.__name__

    def splitTask(self, task):
        """Determines if the plugin can handle multi-thing queries and output splited tasks for list task only"""
        if task['task'] != 'list':
            return [task]
        tasks = [task]
        if not self.multi_filename_queries:
            tasks = self._splitOnField(tasks, 'filenames')
        if not self.multi_languages_queries:
            tasks = self._splitOnField(tasks, 'languages')
        return tasks

    @staticmethod
    def _splitOnField(elements, field):
        """
        Split a list of dict in a bigger one if the element field in the dict has multiple elements too
        i.e. [{'a': 1, 'b': [2,3]}, {'a': 7, 'b': [4]}] => [{'a': 1, 'b': [2]}, {'a': 1, 'b': [3]}, {'a': 7, 'b': [4]}]
        with field = 'b'
        """
        results = []
        for e in elements:
            for v in e[field]:
                newElement = {}
                for (key, value) in e.items():
                    if key != field:
                        newElement[key] = value
                    else:
                        newElement[key] = [v]
                results.append(newElement)
        return results

    def listTeams(self, sub_teams, separators):
        """List teams of a given string using separators"""
        for sep in separators:
            sub_teams = self.splitTeam(sub_teams, sep)
        return set(sub_teams)

    def splitTeam(self, sub_teams, sep):
        """Split teams of a given string using separators"""
        teams = []
        for t in sub_teams:
            teams += t.split(sep)
        return teams
