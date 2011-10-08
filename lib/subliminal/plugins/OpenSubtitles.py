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
import gzip
import os
import socket
import xmlrpclib
import guessit
import unicodedata
from subliminal.classes import Subtitle, DownloadFailedError


class OpenSubtitles(PluginBase.PluginBase):
    site_url = 'http://www.opensubtitles.org'
    site_name = 'OpenSubtitles'
    server_url = 'http://api.opensubtitles.org/xml-rpc'
    user_agent = 'Subliminal v1.0'
    api_based = True
    _plugin_languages = {'aa': 'aar', 'ab': 'abk', 'af': 'afr', 'ak': 'aka', 'sq': 'alb', 'am': 'amh', 'ar': 'ara', 'an': 'arg', 'hy': 'arm',
            'as': 'asm', 'av': 'ava', 'ae': 'ave', 'ay': 'aym', 'az': 'aze', 'ba': 'bak', 'bm': 'bam', 'eu': 'baq', 'be': 'bel', 'bn': 'ben',
            'bh': 'bih', 'bi': 'bis', 'bs': 'bos', 'br': 'bre', 'bg': 'bul', 'my': 'bur', 'ca': 'cat', 'ch': 'cha', 'ce': 'che', 'zh': 'chi',
            'cu': 'chu', 'cv': 'chv', 'kw': 'cor', 'co': 'cos', 'cr': 'cre', 'cs': 'cze', 'da': 'dan', 'dv': 'div', 'nl': 'dut', 'dz': 'dzo',
            'en': 'eng', 'eo': 'epo', 'et': 'est', 'ee': 'ewe', 'fo': 'fao', 'fj': 'fij', 'fi': 'fin', 'fr': 'fre', 'fy': 'fry', 'ff': 'ful',
            'ka': 'geo', 'de': 'ger', 'gd': 'gla', 'ga': 'gle', 'gl': 'glg', 'gv': 'glv', 'el': 'ell', 'gn': 'grn', 'gu': 'guj', 'ht': 'hat',
            'ha': 'hau', 'he': 'heb', 'hz': 'her', 'hi': 'hin', 'ho': 'hmo', 'hr': 'hrv', 'hu': 'hun', 'ig': 'ibo', 'is': 'ice', 'io': 'ido',
            'ii': 'iii', 'iu': 'iku', 'ie': 'ile', 'ia': 'ina', 'id': 'ind', 'ik': 'ipk', 'it': 'ita', 'jv': 'jav', 'ja': 'jpn', 'kl': 'kal',
            'kn': 'kan', 'ks': 'kas', 'kr': 'kau', 'kk': 'kaz', 'km': 'khm', 'ki': 'kik', 'rw': 'kin', 'ky': 'kir', 'kv': 'kom', 'kg': 'kon',
            'ko': 'kor', 'kj': 'kua', 'ku': 'kur', 'lo': 'lao', 'la': 'lat', 'lv': 'lav', 'li': 'lim', 'ln': 'lin', 'lt': 'lit', 'lb': 'ltz',
            'lu': 'lub', 'lg': 'lug', 'mk': 'mac', 'mh': 'mah', 'ml': 'mal', 'mi': 'mao', 'mr': 'mar', 'ms': 'may', 'mg': 'mlg', 'mt': 'mlt',
            'mo': 'mol', 'mn': 'mon', 'na': 'nau', 'nv': 'nav', 'nr': 'nbl', 'nd': 'nde', 'ng': 'ndo', 'ne': 'nep', 'nn': 'nno', 'nb': 'nob',
            'no': 'nor', 'ny': 'nya', 'oc': 'oci', 'oj': 'oji', 'or': 'ori', 'om': 'orm', 'os': 'oss', 'pa': 'pan', 'fa': 'per', 'pi': 'pli',
            'pl': 'pol', 'pt': 'por', 'ps': 'pus', 'qu': 'que', 'rm': 'roh', 'rn': 'run', 'ru': 'rus', 'sg': 'sag', 'sa': 'san', 'sr': 'scc',
            'si': 'sin', 'sk': 'slo', 'sl': 'slv', 'se': 'sme', 'sm': 'smo', 'sn': 'sna', 'sd': 'snd', 'so': 'som', 'st': 'sot', 'es': 'spa',
            'sc': 'srd', 'ss': 'ssw', 'su': 'sun', 'sw': 'swa', 'sv': 'swe', 'ty': 'tah', 'ta': 'tam', 'tt': 'tat', 'te': 'tel', 'tg': 'tgk',
            'tl': 'tgl', 'th': 'tha', 'bo': 'tib', 'ti': 'tir', 'to': 'ton', 'tn': 'tsn', 'ts': 'tso', 'tk': 'tuk', 'tr': 'tur', 'tw': 'twi',
            'ug': 'uig', 'uk': 'ukr', 'ur': 'urd', 'uz': 'uzb', 've': 'ven', 'vi': 'vie', 'vo': 'vol', 'cy': 'wel', 'wa': 'wln', 'wo': 'wol',
            'xh': 'xho', 'yi': 'yid', 'yo': 'yor', 'za': 'zha', 'zu': 'zul', 'ro': 'rum', 'pb': 'pob', 'un': 'unk', 'ay': 'ass'}

    def __init__(self, config_dict=None):
        super(OpenSubtitles, self).__init__(self._plugin_languages, config_dict)

    def list(self, filepath, languages):
        possible_languages = self.possible_languages(languages)
        if os.path.isfile(filepath):
            filehash = self.hashFile(filepath)
            size = os.path.getsize(filepath)
            return self.query(moviehash=filehash, languages=possible_languages, bytesize=size, filepath=filepath)
        else:
            return self.query(languages=possible_languages, filepath=filepath)

    def download(self, subtitle):
        try:
            self.downloadFile(subtitle.link, subtitle.path + '.gz')
            with open(subtitle.path, 'wb') as dump:
                gz = gzip.open(subtitle.path + '.gz')
                dump.write(gz.read())
                gz.close()
                self.adjustPermissions(subtitle.path)
            os.remove(subtitle.path + '.gz')
        except Exception as e:
            if os.path.exists(subtitle.path):
                os.remove(subtitle.path)
            raise DownloadFailedError(str(e))
        return subtitle

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
            search['sublanguageid'] = ','.join([self.getLanguage(l) for l in languages])
        if not imdbID and not moviehash and not bytesize:
            self.logger.debug(u'No search term, using the filename')
            guess = guessit.guess_file_info(filepath, 'autodetect')
            if guess['type'] == 'episode' and 'series' in guess:
                search['query'] = guess['series'].lower()
            elif guess['type'] == 'movie':
                search['query'] = guess['title'].lower()
            else:  # we don't know what we have
                return[]
        # login
        self.server = xmlrpclib.Server(self.server_url)
        socket.setdefaulttimeout(self.timeout)
        try:
            log_result = self.server.LogIn('', '', 'eng', self.user_agent)
            if not log_result['status'] or log_result['status'] != '200 OK' or not log_result['token']:
                raise Exception('OpenSubtitles login failed')
            token = log_result['token']
        except Exception:
            self.logger.error(u'Cannot login')
            token = None
            socket.setdefaulttimeout(None)
            return []
        # search
        sublinks = self.get_results(token, search, filepath)
        # logout
        try:
            self.server.LogOut(token)
        except:
            self.logger.error(u'Cannot logout')
        socket.setdefaulttimeout(None)
        return sublinks

    def get_results(self, token, search, filepath):
        self.logger.debug(u'Query uses token %s and search parameters %s' % (token, search))
        try:
            results = self.server.SearchSubtitles(token, [search])
        except Exception:
            self.logger.debug(u'Cannot query the server')
            return []
        if not results['data']:  # no subtitle found
            return []
        sublinks = []
        self.filename = self.getFileName(filepath)
        for r in sorted(results['data'], self._cmpSubFileName):
            result = Subtitle(filepath, self.getSubtitlePath(filepath, self.getRevertLanguage(r['SubLanguageID'])), self.__class__.__name__, self.getRevertLanguage(r['SubLanguageID']), r['SubDownloadLink'], r['SubFileName'])
            if 'query' in search:  # query mode search, filter results
                query_encoded = search['query']
                if isinstance(query_encoded, unicode):
                    query_encoded = unicodedata.normalize('NFKD', query_encoded).encode('ascii', 'ignore')
                if not r['MovieReleaseName'].replace('.', ' ').lower().startswith(query_encoded):
                    self.logger.debug(u'Skipping %s it does not start with %s' % (r['MovieReleaseName'].replace('.', ' ').lower(), query_encoded))
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

