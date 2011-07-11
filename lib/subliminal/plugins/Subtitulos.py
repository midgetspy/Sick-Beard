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

from BeautifulSoup import BeautifulSoup
import guessit
import zipfile
import urllib2
import urllib
import logging
import traceback
import httplib
import re
import PluginBase
from subliminal import encodingKludge as ek


class Subtitulos(PluginBase.PluginBase):
    site_url = 'http://www.subtitulos.es'
    site_name = 'Subtitulos'
    server_url = 'http://www.subtitulos.es'
    multi_languages_queries = True
    multi_filename_queries = False
    api_based = False
    _plugin_languages = {u"English (US)": "en",
            u"English (UK)": "en",
            u"English": "en",
            u"French": "fr",
            u"Brazilian": "pt-br",
            u"Portuguese": "pt",
            u"Español (Latinoamérica)": "es",
            u"Español (España)": "es",
            u"Español": "es",
            u"Italian": "it",
            u"Català": "ca"}

    def __init__(self, config_dict=None):
        super(Subtitulos, self).__init__(self._plugin_languages, config_dict, True)
        self.release_pattern = re.compile("Versi&oacute;n (.+) ([0-9]+).([0-9])+ megabytes")

    def list(self, filenames, languages):
        """Main method to call when you want to list subtitles"""
        # as self.multi_filename_queries is false, we won't have multiple filenames in the list so pick the only one
        # once multi-filename queries are implemented, set multi_filename_queries to true and manage a list of multiple filenames here
        if not self.checkLanguages(languages):
            return []
        filepath = filenames[0]
        guess = guessit.guess_file_info(filepath, 'autodetect')
        if guess['type'] != 'episode':
            return []
        # add multiple things to the release group set
        release_group = set()
        if 'releaseGroup' in guess:
            release_group.add(guess['releaseGroup'].lower())
        else:
            if 'title' in guess:
                release_group.add(guess['title'].lower())
            if 'screenSize' in guess:
                release_group.add(guess['screenSize'].lower())
        if len(release_group) == 0:
            return []
        self.release_group = release_group  # used to sort results
        return self.query(guess['series'], guess['season'], guess['episodeNumber'], release_group, filepath, languages)

    def query(self, name, season, episode, release_group, filepath, languages=None):
        """Make a query and returns info about found subtitles"""
        sublinks = []
        searchname = name.lower().replace(" ", "-")
        searchurl = "%s/%s/%sx%.2d" % (self.server_url, searchname, season, episode)
        self.logger.debug(u"Searching in %s" % searchurl)
        try:
            req = urllib2.Request(searchurl, headers={'User-Agent': self.user_agent})
            page = urllib2.urlopen(req, timeout=self.timeout)
        except urllib2.HTTPError as inst:
            self.logger.info(u"Error: %s - %s" % (searchurl, inst))
            return []
        except urllib2.URLError as inst:
            self.logger.info(u"TimeOut: %s" % inst)
            return []
        soup = BeautifulSoup(page.read())
        for subs in soup("div", {"id": "version"}):
            version = subs.find("p", {"class": "title-sub"})
            sub_teams = self.listTeams([self.release_pattern.search("%s" % version.contents[1]).group(1).lower()], [".", "_", " ", "/"])
            if not release_group.intersection(sub_teams):  # On wrong team
                continue
            self.logger.debug(u"Team from website: %s" % sub_teams)
            self.logger.debug(u"Team from file: %s" % release_group)
            for html_language in subs.findAllNext("ul", {"class": "sslist"}):
                sub_language = self.getRevertLanguage(html_language.findNext("li", {"class": "li-idioma"}).find("strong").contents[0].string.strip())
                if languages and not sub_language in languages:  # On wrong language
                    continue
                html_status = html_language.findNext("li", {"class": "li-estado green"})
                sub_status = html_status.contents[0].string.strip()
                if not sub_status == 'Completado':  # On not completed subtitles
                    continue
                sub_link = html_status.findNext("span", {"class": "descargar green"}).find("a")["href"]
                result = {}
                result["release"] = "%s.S%.2dE%.2d.%s" % (name.replace(" ", "."), int(season), int(episode), '.'.join(sub_teams))
                result["lang"] = sub_language
                result["link"] = sub_link
                result["page"] = searchurl
                result["filename"] = filepath
                result["plugin"] = self.getClassName()
                result["teams"] = sub_teams  # used to sort
                sublinks.append(result)
        sublinks.sort(self._cmpTeams)
        return sublinks

    def download(self, subtitle):
        """
        Pass the URL of the sub and the file it matches, will unzip it
        and return the path to the created file
        """
        suburl = subtitle["link"]
        videofilename = subtitle["filename"]
        srtbasefilename = videofilename.rsplit(".", 1)[0]
        srtfilename = srtbasefilename + ".srt"
        self.downloadFile(suburl, srtfilename)
        return srtfilename

    def downloadFile(self, url, filename):
        """Downloads the given url to the given filename"""
        req = urllib2.Request(url, headers={'Referer': url, 'User-Agent': 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.1.3)'})
        f = urllib2.urlopen(req)
        dump = ek.ek(open, filename, "wb")
        dump.write(f.read())
        dump.close()
        f.close()

    def _cmpTeams(self, x, y):
        """Sort based on teams matching"""
        return -cmp(len(x['teams'].intersection(self.release_group)), len(y['teams'].intersection(self.release_group)))
