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

from xml.dom import minidom
import guessit
import PluginBase
import os
try:
    import cPickle as pickle
except ImportError:
    import pickle
import urllib2
from subliminal.classes import Subtitle


class BierDopje(PluginBase.PluginBase):
    site_url = 'http://bierdopje.com'
    site_name = 'BierDopje'
    server_url = 'http://api.bierdopje.com/A2B638AC5D804C2E/'
    api_based = True
    exceptions = {'the office': 10358,
        'the office us': 10358,
        'greys anatomy': 3733,
        'sanctuary us': 7904,
        'human target 2010': 12986,
        'csi miami': 2187,
        'castle 2009': 12708,
        'chase 2010': 14228,
        'the defenders 2010': 14225,
        'hawaii five-0 2010': 14211}
    _plugin_languages = {'en': 'en', 'nl': 'nl'}

    def __init__(self, config_dict=None):
        super(BierDopje, self).__init__(self._plugin_languages, config_dict)
        #http://api.bierdopje.com/23459DC262C0A742/GetShowByName/30+Rock
        #http://api.bierdopje.com/23459DC262C0A742/GetAllSubsFor/94/5/1/en (30 rock, season 5, episode 1)
        if config_dict and config_dict['cache_dir']:
            self.showid_cache = os.path.join(config_dict['cache_dir'], 'bierdopje_showid.cache')
            with self.lock:
                if not os.path.exists(self.showid_cache):
                    if not os.path.exists(os.path.dirname(self.showid_cache)):
                        raise Exception('Cache directory does not exist')
                    f = open(self.showid_cache, 'w')
                    pickle.dump({}, f)
                    f.close()
                f = open(self.showid_cache, 'r')
                self.showids = pickle.load(f)
                self.logger.debug(u'Reading showids from cache: %s' % self.showids)
                f.close()

    def list(self, filepath, languages):
        if not self.config_dict['cache_dir']:
            raise Exception('Cache directory is required for this plugin')
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

    def download(self, subtitle):
        self.downloadFile(subtitle.link, subtitle.path)
        return subtitle

    def query(self, name, season, episode, release_group, filepath, languages):
        sublinks = []
        # get the show id
        show_name = name.lower()
        if show_name in self.exceptions:  # get it from exceptions
            show_id = self.exceptions[show_name]
        elif show_name in self.showids:  # get it from cache
            show_id = self.showids[show_name]
        else:  # retrieve it
            show_name_encoded = show_name
            if isinstance(show_name_encoded, unicode):
                show_name_encoded = show_name_encoded.encode('utf-8')
            show_id_url = '%sGetShowByName/%s' % (self.server_url, urllib2.quote(show_name_encoded))
            self.logger.debug(u'Retrieving show id from web at %s' % show_id_url)
            page = urllib2.urlopen(show_id_url)
            dom = minidom.parse(page)
            if not dom or len(dom.getElementsByTagName('showid')) == 0:  # no proper result
                page.close()
                return []
            show_id = dom.getElementsByTagName('showid')[0].firstChild.data
            self.showids[show_name] = show_id
            with self.lock:
                f = open(self.showid_cache, 'w')
                self.logger.debug(u'Writing showid %s to cache file' % show_id)
                pickle.dump(self.showids, f)
                f.close()
            page.close()

        # get the subs for the show id we have
        for language in languages:
            subs_url = '%sGetAllSubsFor/%s/%s/%s/%s' % (self.server_url, show_id, season, episode, language)
            self.logger.debug(u'Getting subtitles at %s' % subs_url)
            page = urllib2.urlopen(subs_url)
            dom = minidom.parse(page)
            page.close()
            for sub in dom.getElementsByTagName('result'):
                sub_release = sub.getElementsByTagName('filename')[0].firstChild.data
                if sub_release.endswith('.srt'):
                    sub_release = sub_release[:-4]
                sub_release = sub_release + '.avi'  # put a random extension for guessit not to fail guessing that file
                # guess information from subtitle
                sub_guess = guessit.guess_file_info(sub_release, 'episode')
                sub_release_group = set()
                if 'releaseGroup' in sub_guess:
                    sub_release_group.add(sub_guess['releaseGroup'].lower())
                else:
                    if 'title' in sub_guess:
                        sub_release_group.add(sub_guess['title'].lower())
                    if 'screenSize' in sub_guess:
                        sub_release_group.add(sub_guess['screenSize'].lower())
                sub_link = sub.getElementsByTagName('downloadlink')[0].firstChild.data
                result = Subtitle(filepath, self.getSubtitlePath(filepath, language), self.__class__.__name__, language, sub_link, sub_release, sub_release_group)
                sublinks.append(result)
        sublinks.sort(self._cmpReleaseGroup)
        return sublinks

