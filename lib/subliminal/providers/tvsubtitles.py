# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import io
import logging
import re
import zipfile
import babelfish
import bs4
import requests
from . import Provider
from .. import __version__
#from ..cache import region, SHOW_EXPIRATION_TIME, EPISODE_EXPIRATION_TIME
from ..exceptions import ProviderError
from ..subtitle import Subtitle, fix_line_endings, compute_guess_properties_matches
from ..video import Episode


logger = logging.getLogger(__name__)
babelfish.language_converters.register('tvsubtitles = subliminal.converters.tvsubtitles:TVsubtitlesConverter')


class TVsubtitlesSubtitle(Subtitle):
    provider_name = 'tvsubtitles'

    def __init__(self, language, series, season, episode, year, id, rip, release, page_link):  # @ReservedAssignment
        super(TVsubtitlesSubtitle, self).__init__(language, page_link=page_link)
        self.series = series
        self.season = season
        self.episode = episode
        self.year = year
        self.id = id
        self.rip = rip
        self.release = release

    def compute_matches(self, video):
        matches = set()
        # series
        if video.series and self.series == video.series:
            matches.add('series')
        # season
        if video.season and self.season == video.season:
            matches.add('season')
        # episode
        if video.episode and self.episode == video.episode:
            matches.add('episode')
        # year
        if self.year == video.year:
            matches.add('year')
        # release_group
        if video.release_group and self.release and video.release_group.lower() in self.release.lower():
            matches.add('release_group')
        """
        # video_codec
        if video.video_codec and self.release and (video.video_codec in self.release.lower()
                                                   or video.video_codec == 'h264' and 'x264' in self.release.lower()):
            matches.add('video_codec')
        # resolution
        if video.resolution and self.rip and video.resolution in self.rip.lower():
            matches.add('resolution')
        # format
        if video.format and self.rip and video.format in self.rip.lower():
            matches.add('format')
        """
        # we don't have the complete filename, so we need to guess the matches separately
        # guess video_codec (videoCodec in guessit)
        matches |= compute_guess_properties_matches(video, self.release, 'videoCodec')
        # guess resolution (screenSize in guessit)
        matches |= compute_guess_properties_matches(video, self.rip, 'screenSize')
        # guess format
        matches |= compute_guess_properties_matches(video, self.rip, 'format')
        return matches


class TVsubtitlesProvider(Provider):
    languages = {babelfish.Language('por', 'BR')} | {babelfish.Language(l)
                 for l in ['ara', 'bul', 'ces', 'dan', 'deu', 'ell', 'eng', 'fin', 'fra', 'hun', 'ita', 'jpn', 'kor',
                           'nld', 'pol', 'por', 'ron', 'rus', 'spa', 'swe', 'tur', 'ukr', 'zho']}
    video_types = (Episode,)
    server = 'http://www.tvsubtitles.net'
    episode_id_re = re.compile('^episode-\d+\.html$')
    subtitle_re = re.compile('^\/subtitle-\d+\.html$')
    link_re = re.compile('^(?P<series>[A-Za-z0-9 \'.]+).*\((?P<first_year>\d{4})-\d{4}\)$')

    def initialize(self):
        self.session = requests.Session()
        self.session.headers = {'User-Agent': 'Subliminal/%s' % __version__.split('-')[0]}

    def terminate(self):
        self.session.close()

    def request(self, url, params=None, data=None, method='GET'):
        """Make a `method` request on `url` with the given parameters

        :param string url: part of the URL to reach with the leading slash
        :param dict params: params of the request
        :param dict data: data of the request
        :param string method: method of the request
        :return: the response
        :rtype: :class:`bs4.BeautifulSoup`

        """
        r = self.session.request(method, self.server + url, params=params, data=data, timeout=10)
        if r.status_code != 200:
            raise ProviderError('Request failed with status code %d' % r.status_code)
        return bs4.BeautifulSoup(r.content, ['permissive'])

    #@region.cache_on_arguments(expiration_time=SHOW_EXPIRATION_TIME)
    def find_show_id(self, series, year=None):
        """Find the show id from the `series` with optional `year`

        :param string series: series of the episode in lowercase
        :param year: year of the series, if any
        :type year: int or None
        :return: the show id, if any
        :rtype: int or None

        """
        data = {'q': series}
        logger.debug('Searching series %r', data)
        soup = self.request('/search.php', data=data, method='POST')
        links = soup.select('div.left li div a[href^="/tvshow-"]')
        if not links:
            logger.info('Series %r not found', series)
            return None
        matched_links = [link for link in links if self.link_re.match(link.string)]
        for link in matched_links:  # first pass with exact match on series
            match = self.link_re.match(link.string)
            if match.group('series').lower().replace('.', ' ').strip() == series:
                if year is not None and int(match.group('first_year')) != year:
                    continue
                return int(link['href'][8:-5])
        for link in matched_links:  # less selective second pass
            match = self.link_re.match(link.string)
            if match.group('series').lower().replace('.', ' ').strip().startswith(series):
                if year is not None and int(match.group('first_year')) != year:
                    continue
                return int(link['href'][8:-5])
        return None

    #@region.cache_on_arguments(expiration_time=EPISODE_EXPIRATION_TIME)
    def find_episode_ids(self, show_id, season):
        """Find episode ids from the show id and the season

        :param int show_id: show id
        :param int season: season of the episode
        :return: episode ids per episode number
        :rtype: dict

        """
        params = {'show_id': show_id, 'season': season}
        logger.debug('Searching episodes %r', params)
        soup = self.request('/tvshow-{show_id}-{season}.html'.format(**params))
        episode_ids = {}
        for row in soup.select('table#table5 tr'):
            if not row('a', href=self.episode_id_re):
                continue
            cells = row('td')
            episode_ids[int(cells[0].string.split('x')[1])] = int(cells[1].a['href'][8:-5])
        return episode_ids

    def query(self, series, season, episode, year=None):
        show_id = self.find_show_id(series.lower(), year)
        if show_id is None:
            return []
        episode_ids = self.find_episode_ids(show_id, season)
        if episode not in episode_ids:
            logger.info('Episode %d not found', episode)
            return []
        params = {'episode_id': episode_ids[episode]}
        logger.debug('Searching episode %r', params)
        link = '/episode-{episode_id}.html'.format(**params)
        soup = self.request(link)
        return [TVsubtitlesSubtitle(babelfish.Language.fromtvsubtitles(row.h5.img['src'][13:-4]), series, season,
                                    episode, year if year and show_id != self.find_show_id(series.lower()) else None,
                                    int(row['href'][10:-5]), row.find('p', title='rip').text.strip() or None,
                                    row.find('p', title='release').text.strip() or None,
                                    self.server + '/subtitle-%d.html' % int(row['href'][10:-5]))
                for row in soup('a', href=self.subtitle_re)]

    def list_subtitles(self, video, languages):
        return [s for s in self.query(video.series, video.season, video.episode, video.year) if s.language in languages]

    def download_subtitle(self, subtitle):
        r = self.session.get(self.server + '/download-{subtitle_id}.html'.format(subtitle_id=subtitle.id),
                             timeout=10)
        if r.status_code != 200:
            raise ProviderError('Request failed with status code %d' % r.status_code)
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            if len(zf.namelist()) > 1:
                raise ProviderError('More than one file to unzip')
            subtitle.content = fix_line_endings(zf.read(zf.namelist()[0]))
