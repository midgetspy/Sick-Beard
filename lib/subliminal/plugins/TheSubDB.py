# -*- coding: utf-8 -*-
#
# Subliminal - Subtitles, faster than your thoughts
# Copyright (c) 2008-2011 Patrick Dessalle <patrick@dessalle.be>
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

import PluginBase
import hashlib
import os
import urllib2
from subliminal.classes import Subtitle


class TheSubDB(PluginBase.PluginBase):
    site_url = 'http://thesubdb.com'
    site_name = 'SubDB'
    server_url = 'http://api.thesubdb.com'  # for testing purpose, use http://sandbox.thesubdb.com instead
    api_based = True
    user_agent = 'SubDB/1.0 (Subliminal/1.0; https://github.com/Diaoul/subliminal)'  # defined by the API
    _plugin_languages = {'af': 'af', 'cs': 'cs', 'da': 'da', 'de': 'de', 'en': 'en', 'es': 'es', 'fi': 'fi', 'fr': 'fr', 'hu': 'hu', 'id': 'id',
             'it': 'it', 'la': 'la', 'nl': 'nl', 'no': 'no', 'oc': 'oc', 'pl': 'pl', 'pt': 'pt', 'ro': 'ro', 'ru': 'ru', 'sl': 'sl', 'sr': 'sr',
             'sv': 'sv', 'tr': 'tr'} # list available with the API at http://sandbox.thesubdb.com/?action=languages


    def __init__(self, config_dict=None):
        super(TheSubDB, self).__init__(self._plugin_languages, config_dict)

    def list(self, filepath, languages):
        possible_languages = self.possible_languages(languages)
        if not os.path.isfile(filepath):
            return []
        return self.query(filepath, self.hashFile(filepath), possible_languages)

    def query(self, filepath, moviehash, languages):
        searchurl = '%s/?action=%s&hash=%s' % (self.server_url, 'search', moviehash)
        self.logger.debug(u'Query URL: %s' % searchurl)
        try:
            req = urllib2.Request(searchurl, headers={'User-Agent': self.user_agent})
            page = urllib2.urlopen(req, timeout=self.timeout)
        except urllib2.HTTPError as inst:
            if inst.code == 404:  # no result found
                return []
            self.logger.error(u'Error: %s - %s' % (searchurl, inst))
            return []
        except urllib2.URLError as inst:
            self.logger.error(u'TimeOut: %s' % inst)
            return []
        available_languages = page.readlines()[0].split(',')
        self.logger.debug(u'Available languages: %s' % available_languages)
        subs = []
        for l in available_languages:
            if l in languages:
                result = Subtitle(filepath, self.getSubtitlePath(filepath, l), self.__class__.__name__, l, '%s/?action=download&hash=%s&language=%s' % (self.server_url, moviehash, l))
                subs.append(result)
        return subs

    def hashFile(self, filepath):
        """TheSubDB specific hash function"""
        readsize = 64 * 1024
        with open(filepath, 'rb') as f:
            data = f.read(readsize)
            f.seek(-readsize, os.SEEK_END)
            data += f.read(readsize)
        return hashlib.md5(data).hexdigest()

    def download(self, subtitle):
        self.downloadFile(subtitle.link, subtitle.path)
        return subtitle

