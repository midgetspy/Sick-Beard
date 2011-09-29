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

from hashlib import md5, sha256
import PluginBase
import xmlrpclib
import socket
import os


class Podnapisi(PluginBase.PluginBase):
    site_url = "http://www.podnapisi.net"
    site_name = "Podnapisi"
    server_url = 'http://ssp.podnapisi.net:8000'
    api_based = True
    _plugin_languages = {"sl": "1",
            "en": "2",
            "no": "3",
            "ko": "4",
            "de": "5",
            "is": "6",
            "cs": "7",
            "fr": "8",
            "it": "9",
            "bs": "10",
            "ja": "11",
            "ar": "12",
            "ro": "13",
            "es-ar": "14",
            "hu": "15",
            "el": "16",
            "zh": "17",
            "lt": "19",
            "et": "20",
            "lv": "21",
            "he": "22",
            "nl": "23",
            "da": "24",
            "se": "25",
            "pl": "26",
            "ru": "27",
            "es": "28",
            "sq": "29",
            "tr": "30",
            "fi": "31",
            "pt": "32",
            "bg": "33",
            "mk": "35",
            "sk": "37",
            "hr": "38",
            "zh": "40",
            "hi": "42",
            "th": "44",
            "uk": "46",
            "sr": "47",
            "pt-br": "48",
            "ga": "49",
            "be": "50",
            "vi": "51",
            "fa": "52",
            "ca": "53",
            "id": "54"}

    def __init__(self, config_dict=None):
        super(Podnapisi, self).__init__(self._plugin_languages, config_dict)
        # Podnapisi uses two reference for latin serbian and cyrillic serbian (36 and 47)
        # add the 36 manually as cyrillic seems to be more used
        self.revertPluginLanguages["36"] = "sr"

    def list(self, filenames, languages):
        """Main method to call when you want to list subtitles"""
        filepath = filenames[0]
        if not os.path.isfile(filepath):
            return []
        return self.query(self.hashFile(filepath), languages)

    def download(self, subtitle):
        return []

    def query(self, moviehash, languages=None):
        """Makes a query on podnapisi and returns info (link, lang) about found subtitles"""
        # login
        self.server = xmlrpclib.Server(self.server_url)
        socket.setdefaulttimeout(self.timeout)
        try:
            log_result = self.server.initiate(self.user_agent)
            self.logger.debug(u"Result: %s" % log_result)
            token = log_result["session"]
            nonce = log_result["nonce"]
        except Exception:
            self.logger.error(u"Cannot login" % log_result)
            socket.setdefaulttimeout(None)
            return []
        username = 'getmesubs'
        password = '99D31$$'
        hash = md5()
        hash.update(password)
        password = hash.hexdigest()
        hash = sha256()
        hash.update(password)
        hash.update(nonce)
        password = hash.hexdigest()
        self.server.authenticate(token, username, password)
        self.logger.debug(u'Authenticated')
        #if languages:
        #    self.logger.debug([self.getLanguage(l) for l in languages])
        #    self.server.setFilters(token, [self.getLanguage(l) for l in languages])
        #    self.logger.debug('Filers set for languages %s' % languages)
        self.logger.debug(u"Starting search with token %s and hashs %s" % (token, [moviehash]))
        results = self.server.search(token, [moviehash])
        return results
        subs = []
        for sub in results['results']:
            subs.append(sub)
        self.server.terminate(token)
        return subs
