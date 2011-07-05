# -*- coding: utf-8 -*-
#
# Subliminal - Subtitles, faster than your thoughts
# Copyright (c) 2011 Antoine Bertin <diaoulael@gmail.com>
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
import gzip
import os
import socket
import xmlrpclib
import guessit
from subliminal import encodingKludge as ek


class OpenSubtitles(PluginBase.PluginBase):
    site_url = 'http://www.opensubtitles.org'
    site_name = 'OpenSubtitles'
    server_url = 'http://api.opensubtitles.org/xml-rpc'
    user_agent = 'Subliminal v0.1'
    multi_languages_queries = True
    multi_filename_queries = False
    api_based = True
    _plugin_languages = {"en": "eng",
            "fr": "fre",
            "hu": "hun",
            "cs": "cze",
            "pl": "pol",
            "sk": "slo",
            "pt": "por",
            "pt-br": "pob",
            "es": "spa",
            "el": "ell",
            "ar": "ara",
            "sq": "alb",
            "hy": "arm",
            "ay": "ass",
            "bs": "bos",
            "bg": "bul",
            "ca": "cat",
            "zh": "chi",
            "hr": "hrv",
            "da": "dan",
            "nl": "dut",
            "eo": "epo",
            "et": "est",
            "fi": "fin",
            "gl": "glg",
            "ka": "geo",
            "de": "ger",
            "he": "heb",
            "hi": "hin",
            "is": "ice",
            "id": "ind",
            "it": "ita",
            "ja": "jpn",
            "kk": "kaz",
            "ko": "kor",
            "lv": "lav",
            "lt": "lit",
            "lb": "ltz",
            "mk": "mac",
            "ms": "may",
            "no": "nor",
            "oc": "oci",
            "fa": "per",
            "ro": "rum",
            "ru": "rus",
            "sr": "scc",
            "sl": "slv",
            "sv": "swe",
            "th": "tha",
            "tr": "tur",
            "uk": "ukr",
            "vi": "vie"}

    def __init__(self, config_dict=None):
        super(OpenSubtitles, self).__init__(self._plugin_languages, config_dict)

    def list(self, filenames, languages):
        """Main method to call when you want to list subtitles """
        # as self.multi_filename_queries is false, we won't have multiple filenames in the list so pick the only one
        # once multi-filename queries are implemented, set multi_filename_queries to true and manage a list of multiple filenames here
        filepath = filenames[0]
        if ek.ek(os.path.isfile, filepath):
            filehash = self.hashFile(filepath)
            size = ek.ek(os.path.getsize, filepath)
            return self.query(moviehash=filehash, languages=languages, bytesize=size, filepath=filepath)
        else:
            return self.query(languages=languages, filepath=filepath)

    def download(self, subtitle):
        """Main method to call when you want to download a subtitle """
        subtitleFilename = subtitle["filename"].rsplit(".", 1)[0] + self.getExtension(subtitle)
        self.downloadFile(subtitle["link"], subtitleFilename + ".gz")
        f = ek.ek(gzip.open, subtitleFilename + ".gz")
        dump = ek.ek(open, subtitleFilename, "wb")
        dump.write(f.read())
        dump.close()
        f.close()
        ek.ek(os.remove, subtitleFilename + ".gz")
        return subtitleFilename

    def query(self, filepath, imdbID=None, moviehash=None, bytesize=None, languages=None):
        """Makes a query on OpenSubtitles and returns info about found subtitles.
            Note: if using moviehash, bytesize is required. """
        # prepare the search
        search = {}
        if moviehash:
            search['moviehash'] = moviehash
        if imdbID:
            search['imdbid'] = imdbID
        if bytesize:
            search['moviebytesize'] = str(bytesize)
        if languages:
            search['sublanguageid'] = ",".join([self.getLanguage(l) for l in languages])
        if not imdbID and not moviehash and not bytesize:
            self.logger.debug(u"No search term, we'll use the filename")
            guess = guessit.guess_file_info(filepath, 'autodetect')
            if guess['type'] == 'episode':
                search['query'] = guess['series']
            elif guess['type'] == 'movie':
                search['query'] = guess['title']
            else:  # we don't know what we have
                return[]
        # login
        self.server = xmlrpclib.Server(self.server_url)
        socket.setdefaulttimeout(self.timeout)
        try:
            log_result = self.server.LogIn("", "", "eng", self.user_agent)
            if not log_result["status"] or log_result["status"] != '200 OK' or not log_result["token"]:
                raise Exception('OpenSubtitles login failed')
            token = log_result["token"]
        except Exception:
            self.logger.error(u"Cannot login")
            token = None
            socket.setdefaulttimeout(None)
            return []
        # search
        sublinks = self.get_results(token, search, filepath)
        # logout
        try:
            self.server.LogOut(token)
        except:
            self.logger.error(u"Cannot logout")
        socket.setdefaulttimeout(None)
        return sublinks

    def get_results(self, token, search, filepath):
        self.logger.debug(u"Query uses token %s and search parameters %s" % (token, search))
        try:
            results = self.server.SearchSubtitles(token, [search])
        except Exception, e:
            self.logger.debug(u"Cannot query the server")
            return []
        if not results['data']:  # no subtitle found
            return []
        sublinks = []
        self.filename = self.getFileName(filepath)
        for r in sorted(results['data'], self._cmpSubFileName):
            result = {}
            result["release"] = r['SubFileName']
            result["link"] = r['SubDownloadLink']
            result["page"] = r['SubDownloadLink']
            result["lang"] = self.getRevertLanguage(r['SubLanguageID'])
            result["filename"] = filepath
            result["plugin"] = self.getClassName()
            if 'query' in search and not r["MovieReleaseName"].replace('.', ' ').startswith(search['query']):  # query mode search, filter results
                self.logger.debug(u"Skipping %s it does not start with %s" % (r["MovieReleaseName"].replace('.', ' '), search['query']))
                continue
            sublinks.append(result)
        return sublinks

    def _cmpSubFileName(self, x, y):
        """Sort based on the SubFileName name tag """
        #TODO add also support for subtitles release
        xmatch = x['SubFileName'] and (x['SubFileName'].find(self.filename) > -1 or self.filename.find(x['SubFileName']) > -1)
        ymatch = y['SubFileName'] and (y['SubFileName'].find(self.filename) > -1 or self.filename.find(y['SubFileName']) > -1)
        if xmatch and ymatch:
            if x['SubFileName'] == self.filename or x['SubFileName'].startswith(self.filename):
                return - 1
            return 0
        if not xmatch and not ymatch:
            return 0
        if xmatch and not ymatch:
            return - 1
        if not xmatch and ymatch:
            return 1
        return 0
