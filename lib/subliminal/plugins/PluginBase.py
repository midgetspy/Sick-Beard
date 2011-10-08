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
import urllib2
import struct
import threading
import socket
from subliminal.classes import DownloadFailedError


class PluginBase(object):
    __metaclass__ = abc.ABCMeta
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
        self.logger = logging.getLogger('subliminal.%s' % self.__class__.__name__)

    @staticmethod
    def getFileName(filepath):
        filename = filepath
        if os.path.isfile(filename):
            filename = os.path.basename(filename)
        if filename.endswith(('.avi', '.wmv', '.mov', '.mp4', '.mpeg', '.mpg', '.mkv')):
            filename = filename.rsplit('.', 1)[0]
        return filename

    def possible_languages(self, languages):
        possible_languages = languages & set(self.pluginLanguages.keys())
        if not possible_languages:
            self.logger.debug(u'Languages %r are not in supported languages' % languages)
        return possible_languages

    def hashFile(self, filename):
        """Hash a file like OpenSubtitles"""
        longlongformat = 'q'  # long long
        bytesize = struct.calcsize(longlongformat)
        f = open(filename, 'rb')
        filesize = os.path.getsize(filename)
        hash = filesize
        if filesize < 65536 * 2:
            self.logger.error(u'File %s is too small (SizeError < 2**16)' % filename)
            return []
        for _ in range(65536 / bytesize):
            buffer = f.read(bytesize)
            (l_value,) = struct.unpack(longlongformat, buffer)
            hash += l_value
            hash = hash & 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number
        f.seek(max(0, filesize - 65536), 0)
        for _ in range(65536 / bytesize):
            buffer = f.read(bytesize)
            (l_value,) = struct.unpack(longlongformat, buffer)
            hash += l_value
            hash = hash & 0xFFFFFFFFFFFFFFFF
        f.close()
        returnedhash = '%016x' % hash
        return returnedhash

    def downloadFile(self, url, filepath, data=None):
        """Download a subtitle file"""
        self.logger.info(u'Downloading %s' % url)
        socket.setdefaulttimeout(self.timeout)
        try:
            req = urllib2.Request(url, headers={'Referer': url, 'User-Agent': self.user_agent})
            with open(filepath, 'wb') as dump:
                f = urllib2.urlopen(req, data=data)
                dump.write(f.read())
                self.adjustPermissions(filepath)
                f.close()
        except Exception as e:
            self.logger.error(u'Download %s failed: %s' % (url, e))
            if os.path.exists(filepath):
                os.remove(filepath)
            raise DownloadFailedError(str(e))
        finally:
            socket.setdefaulttimeout(self.timeout)
        self.logger.debug(u'Download finished for file %s. Size: %s' % (filepath, os.path.getsize(filepath)))

    def adjustPermissions(self, filepath):
        if self.config_dict and 'files_mode' in self.config_dict and self.config_dict['files_mode'] != -1:
            os.chmod(filepath, self.config_dict['files_mode'])

    @abc.abstractmethod
    def list(self, filepath, languages):
        """List subtitles"""

    @abc.abstractmethod
    def download(self, subtitle):
        """Download a subtitle"""

    def getRevertLanguage(self, language):
        """ISO-639-1 language code from plugin language code"""
        try:
            return self.revertPluginLanguages[language]
        except KeyError:
            self.logger.warn(u'Ooops, you found a missing language in the configuration file of %s: %s. Send a bug report to have it added.' % (self.__class__.__name__, language))

    def getLanguage(self, language):
        """Plugin language code from ISO-639-1 language code"""
        try:
            return self.pluginLanguages[language]
        except KeyError:
            self.logger.warn(u'Ooops, you found a missing language in the configuration file of %s: %s. Send a bug report to have it added.' % (self.__class__.__name__, language))
    
    def getSubtitlePath(self, video_path, language):
        if not os.path.exists(video_path):
            video_path = os.path.split(video_path)[1]
        path = video_path.rsplit('.', 1)[0]
        if self.config_dict and self.config_dict['multi']:
            return path + '.%s.srt' % language
        return path + '.srt'

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

    def _cmpReleaseGroup(self, x, y):
        """Sort based on teams matching"""
        return -cmp(len(x.teams.intersection(self.release_group)), len(y.teams.intersection(self.release_group)))

