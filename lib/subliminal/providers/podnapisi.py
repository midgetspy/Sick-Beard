# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import io
import logging
import re
import xml.etree.ElementTree
import zipfile
import babelfish
import bs4
import guessit
import requests
from . import Provider
from .. import __version__
from ..exceptions import ProviderError
from ..subtitle import Subtitle, fix_line_endings, compute_guess_matches
from ..video import Episode, Movie


logger = logging.getLogger(__name__)
babelfish.language_converters.register('podnapisi = subliminal.converters.podnapisi:PodnapisiConverter')


class PodnapisiSubtitle(Subtitle):
    provider_name = 'podnapisi'

    def __init__(self, language, id, releases, hearing_impaired, page_link, series=None, season=None, episode=None,  # @ReservedAssignment
                 title=None, year=None):
        super(PodnapisiSubtitle, self).__init__(language, hearing_impaired, page_link)
        self.id = id
        self.releases = releases
        self.hearing_impaired = hearing_impaired
        self.series = series
        self.season = season
        self.episode = episode
        self.title = title
        self.year = year

    def compute_matches(self, video):
        matches = set()
        # episode
        if isinstance(video, Episode):
            # series
            if video.series and self.series.lower() == video.series.lower():
                matches.add('series')
            # season
            if video.season and self.season == video.season:
                matches.add('season')
            # episode
            if video.episode and self.episode == video.episode:
                matches.add('episode')
            # guess
            for release in self.releases:
                matches |= compute_guess_matches(video, guessit.guess_episode_info(release + '.mkv'))
        # movie
        elif isinstance(video, Movie):
            # title
            if video.title and self.title.lower() == video.title.lower():
                matches.add('title')
            # guess
            for release in self.releases:
                matches |= compute_guess_matches(video, guessit.guess_movie_info(release + '.mkv'))
        # year
        if self.year == video.year:
            matches.add('year')
        return matches


class PodnapisiProvider(Provider):
    languages = {babelfish.Language.frompodnapisi(l) for l in babelfish.language_converters['podnapisi'].codes}
    video_types = (Episode, Movie)
    server = 'http://simple.podnapisi.net'
    link_re = re.compile('^.*(?P<link>/ppodnapisi/download/i/\d+/k/.*$)')

    def initialize(self):
        self.session = requests.Session()
        self.session.headers = {'User-Agent': 'Subliminal/%s' % __version__.split('-')[0]}

    def terminate(self):
        self.session.close()

    def get(self, url, params=None, is_xml=True):
        """Make a GET request on `url` with the given parameters

        :param string url: part of the URL to reach with the leading slash
        :param dict params: params of the request
        :param bool xml: whether the response content is XML or not
        :return: the response
        :rtype: :class:`xml.etree.ElementTree.Element` or :class:`bs4.BeautifulSoup`

        """
        r = self.session.get(self.server + '/ppodnapisi' + url, params=params, timeout=10)
        if r.status_code != 200:
            raise ProviderError('Request failed with status code %d' % r.status_code)
        if is_xml:
            return xml.etree.ElementTree.fromstring(r.content)
        else:
            return bs4.BeautifulSoup(r.content, ['permissive'])

    def query(self, language, series=None, season=None, episode=None, title=None, year=None):
        params = {'sXML': 1, 'sJ': language.podnapisi}
        if series and season and episode:
            params['sK'] = series
            params['sTS'] = season
            params['sTE'] = episode
        elif title:
            params['sK'] = title
        else:
            raise ValueError('Missing parameters series and season and episode or title')
        if year:
            params['sY'] = year
        logger.debug('Searching episode %r', params)
        subtitles = []
        while True:
            root = self.get('/search', params)
            if not int(root.find('pagination/results').text):
                logger.debug('No subtitle found')
                break
            if series and season and episode:
                subtitles.extend([PodnapisiSubtitle(language, int(s.find('id').text),
                                                    s.find('release').text.split() if s.find('release').text else [],
                                                    'h' in (s.find('flags').text or ''), s.find('url').text,
                                                    series=series, season=season, episode=episode,
                                                    year=s.find('year').text)
                                  for s in root.findall('subtitle')])
            elif title:
                subtitles.extend([PodnapisiSubtitle(language, int(s.find('id').text),
                                                    s.find('release').text.split() if s.find('release').text else [],
                                                    'h' in (s.find('flags').text or ''), s.find('url').text,
                                                    title=title, year=s.find('year').text)
                                  for s in root.findall('subtitle')])
            if int(root.find('pagination/current').text) >= int(root.find('pagination/count').text):
                break
            params['page'] = int(root.find('pagination/current').text) + 1
        return subtitles

    def list_subtitles(self, video, languages):
        if isinstance(video, Episode):
            return [s for l in languages for s in self.query(l, series=video.series, season=video.season,
                                                             episode=video.episode, year=video.year)]
        elif isinstance(video, Movie):
            return [s for l in languages for s in self.query(l, title=video.title, year=video.year)]

    def download_subtitle(self, subtitle):
        soup = self.get(subtitle.page_link[38:], is_xml=False)
        link = soup.find('a', href=self.link_re)
        if not link:
            raise ProviderError('Cannot find the download link')
        r = self.session.get(self.server + self.link_re.match(link['href']).group('link'), timeout=10)
        if r.status_code != 200:
            raise ProviderError('Request failed with status code %d' % r.status_code)
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            if len(zf.namelist()) > 1:
                raise ProviderError('More than one file to unzip')
            subtitle.content = fix_line_endings(zf.read(zf.namelist()[0]))
