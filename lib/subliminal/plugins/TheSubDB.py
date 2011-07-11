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
from subliminal import encodingKludge as ek


class TheSubDB(PluginBase.PluginBase):
    site_url = 'http://thesubdb.com'
    site_name = 'SubDB'
    server_url = 'http://api.thesubdb.com'  # for testing purpose, use http://sandbox.thesubdb.com instead
    multi_languages_queries = True
    multi_filename_queries = False
    api_based = True
    user_agent = 'SubDB/1.0 (Subliminal/0.1; https://github.com/Diaoul/subliminal)'  # defined by the API
    _plugin_languages = {'cs': 'cs',  # the whole list is available with the API: http://sandbox.thesubdb.com/?action=languages
            'da': 'da',
            'de': 'de',
            'en': 'en',
            'fi': 'fi',
            'fr': 'fr',
            'hu': 'hu',
            'id': 'id',
            'it': 'it',
            'nl': 'nl',
            'no': 'no',
            'pl': 'pl',
            'pt': 'pt',
            'ro': 'ro',
            'ru': 'ru',
            'sl': 'sl',
            'sr': 'sr',
            'sv': 'sv',
            'tr': 'tr'}

    def __init__(self, config_dict=None):
        super(TheSubDB, self).__init__(self._plugin_languages, config_dict)

    def list(self, filenames, languages):
        """Main method to call when you want to list subtitles"""
        # as self.multi_filename_queries is false, we won't have multiple filenames in the list so pick the only one
        # once multi-filename queries are implemented, set multi_filename_queries to true and manage a list of multiple filenames here
        filepath = filenames[0]
        if not ek.ek(os.path.isfile, filepath):
            return []
        return self.query(filepath, self.hashFile(filepath), languages)

    def query(self, filepath, moviehash, languages=None):
        searchurl = "%s/?action=%s&hash=%s" % (self.server_url, "search", moviehash)
        self.logger.debug(u'Query URL: %s' % searchurl)
        try:
            req = urllib2.Request(searchurl, headers={'User-Agent': self.user_agent})
            page = urllib2.urlopen(req, timeout=self.timeout)
        except urllib2.HTTPError as inst:
            if inst.code == 404:  # no result found
                return []
            self.logger.error(u"Error: %s - %s" % (searchurl, inst))
            return []
        except urllib2.URLError as inst:
            self.logger.error(u"TimeOut: %s" % inst)
            return []
        available_languages = page.readlines()[0].split(',')
        self.logger.debug(u'Available languages: %s' % available_languages)
        subs = []
        for l in available_languages:
            if not languages or l in languages:
                result = {}
                result['release'] = filepath
                result['lang'] = l
                result['link'] = "%s/?action=download&hash=%s&language=%s" % (self.server_url, moviehash, l)
                result['page'] = result['link']
                result['filename'] = filepath
                result['plugin'] = self.getClassName()
                subs.append(result)
        return subs

    def hashFile(self, name):
        """This hash function receives the filename and returns the hash code"""
        readsize = 64 * 1024
        with ek.ek(open, name, 'rb') as f:
            size = ek.ek(os.path.getsize, name)
            data = f.read(readsize)
            f.seek(-readsize, os.SEEK_END)
            data += f.read(readsize)
        return hashlib.md5(data).hexdigest()

    def download(self, subtitle):
        """Main method to call when you want to download a subtitle"""
        suburl = subtitle["link"]
        videofilename = subtitle["filename"]
        srtfilename = videofilename.rsplit(".", 1)[0] + self.getExtension(subtitle)
        self.downloadFile(suburl, srtfilename)
        return srtfilename

    def downloadFile(self, url, srtfilename):
        """Downloads the given url to the given filename"""
        req = urllib2.Request(url)
        req.add_header('User-Agent', self.user_agent)
        f = urllib2.urlopen(req)
        dump = open(srtfilename, "wb")
        dump.write(f.read())
        dump.close()
        f.close()
