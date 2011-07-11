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
import PluginBase
import zipfile
import urllib2
import urllib
import logging
import traceback
import httplib
import re
import guessit
from subliminal import encodingKludge as ek


class SubsWiki(PluginBase.PluginBase):
    site_url = 'http://www.subswiki.com'
    site_name = 'SubsWiki'
    server_url = 'http://www.subswiki.com'
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
        super(SubsWiki, self).__init__(self._plugin_languages, config_dict, True)
        self.release_pattern = re.compile("\nVersion (.+), ([0-9]+).([0-9])+ MBs")

    def list(self, filenames, languages):
        """Main method to call when you want to list subtitles"""
        # as self.multi_filename_queries is false, we won't have multiple filenames in the list so pick the only one
        # once multi-filename queries are implemented, set multi_filename_queries to true and manage a list of multiple filenames here
        filepath = filenames[0]
        if not self.checkLanguages(languages):
            return []
        guess = guessit.guess_file_info(filepath, 'autodetect')
        if guess['type'] != 'episode':
            return []
        # add multiple things to the release group set
        release_group = set()
        if 'releaseGroup' in guess:
            release_group.add(guess['releaseGroup'])
        else:
            if 'title' in guess:
                release_group.add(guess['title'])
            if 'screenSize' in guess:
                release_group.add(guess['screenSize'])
        if len(release_group) == 0:
            return []
        self.release_group = release_group  # used to sort results
        return self.query(guess['series'], guess['season'], guess['episodeNumber'], release_group, filepath, languages)

    def query(self, name, season, episode, release_group, filepath, languages=None):
        """Make a query and returns info about found subtitles"""
        sublinks = []
        searchname = name.lower().replace(" ", "_")
        searchurl = "%s/serie/%s/%s/%s/" % (self.server_url, searchname, season, episode)
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
        for subs in soup("td", {"class": "NewsTitle"}):
            sub_teams = self.listTeams([self.release_pattern.search("%s" % subs.contents[1]).group(1)], [".", "_", " ", "/", "-"])
            if not release_group.intersection(sub_teams):  # On wrong team
                continue
            self.logger.debug(u"Team from website: %s" % sub_teams)
            self.logger.debug(u"Team from file: %s" % release_group)
            for html_language in subs.parent.parent.findAll("td", {"class": "language"}):
                sub_language = self.getRevertLanguage(html_language.string.strip())
                self.logger.debug(u"Subtitle reverted language: %s" % sub_language)
                if languages and not sub_language in languages:  # On wrong language
                    continue
                html_status = html_language.findNextSibling('td')
                sub_status = html_status.find('strong').string.strip()
                if not sub_status == 'Completed':  # On not completed subtitles
                    continue
                sub_link = html_status.findNext("td").find("a")["href"]
                result = {}
                result["release"] = "%s.S%.2dE%.2d.%s" % (name.replace(" ", "."), int(season), int(episode), '.'.join(sub_teams))
                result["lang"] = sub_language
                result["link"] = self.server_url + sub_link
                result["page"] = searchurl
                result["filename"] = filepath
                result["plugin"] = self.getClassName()
                result["teams"] = sub_teams  # used to sort
                sublinks.append(result)
        sublinks.sort(self._cmpTeams)
        return sublinks

    def download(self, subtitle):
        """Main method to call when you want to download a subtitle"""
        subtitleFilename = subtitle["filename"].rsplit(".", 1)[0] + self.getExtension(subtitle)
        self.downloadFile(subtitle["link"], subtitleFilename)
        return subtitleFilename

    def listTeams(self, subteams, separators):
        teams = []
        for sep in separators:
            subteams = self.splitTeam(subteams, sep)
        return set(subteams)

    def splitTeam(self, subteams, sep):
        teams = []
        for t in subteams:
            teams += t.split(sep)
        return teams

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
