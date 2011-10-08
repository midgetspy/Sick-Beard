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
import urllib2
import re
import guessit
from subliminal.classes import Subtitle


class SubsWiki(PluginBase.PluginBase):
    site_url = 'http://www.subswiki.com'
    site_name = 'SubsWiki'
    server_url = 'http://www.subswiki.com'
    api_based = False
    _plugin_languages = {u'English (US)': 'en',
            u'English (UK)': 'en',
            u'English': 'en',
            u'French': 'fr',
            u'Brazilian': 'pt-br',
            u'Portuguese': 'pt',
            u'Español (Latinoamérica)': 'es',
            u'Español (España)': 'es',
            u'Español': 'es',
            u'Italian': 'it',
            u'Català': 'ca'}

    def __init__(self, config_dict=None):
        super(SubsWiki, self).__init__(self._plugin_languages, config_dict, True)
        self.release_pattern = re.compile('\nVersion (.+), ([0-9]+).([0-9])+ MBs')

    def list(self, filepath, languages):
        possible_languages = self.possible_languages(languages)
        if not possible_languages:
            return []
        guess = guessit.guess_file_info(filepath, 'autodetect')
        if guess['type'] != 'episode':
            self.logger.debug(u'Not an episode')
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
        if 'series' not in guess or len(release_group) == 0:
            self.logger.debug(u'Not enough information to proceed')
            return []
        self.release_group = release_group  # used to sort results
        return self.query(guess['series'], guess['season'], guess['episodeNumber'], release_group, filepath, possible_languages)

    def query(self, name, season, episode, release_group, filepath, languages):
        sublinks = []
        searchname = name.lower().replace(' ', '_')
        if isinstance(searchname, unicode):
            searchname = searchname.encode('utf-8')
        searchurl = '%s/serie/%s/%s/%s/' % (self.server_url, urllib2.quote(searchname), season, episode)
        self.logger.debug(u'Searching in %s' % searchurl)
        try:
            req = urllib2.Request(searchurl, headers={'User-Agent': self.user_agent})
            page = urllib2.urlopen(req, timeout=self.timeout)
        except urllib2.HTTPError as inst:
            self.logger.info(u'Error: %s - %s' % (searchurl, inst))
            return []
        except urllib2.URLError as inst:
            self.logger.info(u'TimeOut: %s' % inst)
            return []
        soup = BeautifulSoup(page.read())
        for subs in soup('td', {'class': 'NewsTitle'}):
            sub_teams = self.listTeams([self.release_pattern.search('%s' % subs.contents[1]).group(1).lower()], ['.', '_', ' ', '/', '-'])
            if not release_group.intersection(sub_teams):  # On wrong team
                continue
            self.logger.debug(u'Team from website: %s' % sub_teams)
            self.logger.debug(u'Team from file: %s' % release_group)
            for html_language in subs.parent.parent.findAll('td', {'class': 'language'}):
                sub_language = self.getRevertLanguage(html_language.string.strip())
                self.logger.debug(u'Subtitle reverted language: %s' % sub_language)
                if not sub_language in languages:  # On wrong language
                    continue
                html_status = html_language.findNextSibling('td')
                sub_status = html_status.find('strong').string.strip()
                if not sub_status == 'Completed':  # On not completed subtitles
                    continue
                sub_link = html_status.findNext('td').find('a')['href']
                result = Subtitle(filepath, self.getSubtitlePath(filepath, sub_language), self.__class__.__name__, sub_language, self.server_url + sub_link, teams=sub_teams)
                sublinks.append(result)
        sublinks.sort(self._cmpReleaseGroup)
        return sublinks

    def download(self, subtitle):
        self.downloadFile(subtitle.link, subtitle.path)
        return subtitle

