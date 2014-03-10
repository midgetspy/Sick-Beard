# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import babelfish
import bs4
import requests
from . import Provider
from .. import __version__
#from ..cache import region, SHOW_EXPIRATION_TIME
from ..exceptions import ConfigurationError, AuthenticationError, DownloadLimitExceeded, ProviderError
from ..subtitle import Subtitle, fix_line_endings, compute_guess_properties_matches
from ..video import Episode


logger = logging.getLogger(__name__)
babelfish.language_converters.register('addic7ed = subliminal.converters.addic7ed:Addic7edConverter')


class Addic7edSubtitle(Subtitle):
    provider_name = 'addic7ed'

    def __init__(self, language, series, season, episode, title, year, version, hearing_impaired, download_link,
                 page_link):
        super(Addic7edSubtitle, self).__init__(language, hearing_impaired, page_link)
        self.series = series
        self.season = season
        self.episode = episode
        self.title = title
        self.year = year
        self.version = version
        self.download_link = download_link

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
        # title
        if video.title and self.title.lower() == video.title.lower():
            matches.add('title')
        # year
        if self.year == video.year:
            matches.add('year')
        # release_group
        if video.release_group and self.version and video.release_group.lower() in self.version.lower():
            matches.add('release_group')
        """
        # resolution
        if video.resolution and self.version and video.resolution in self.version.lower():
            matches.add('resolution')
        # format
        if video.format and self.version and video.format in self.version.lower:
            matches.add('format')
        """
        # we don't have the complete filename, so we need to guess the matches separately
        # guess resolution (screenSize in guessit)
        matches |= compute_guess_properties_matches(video, self.version, 'screenSize')
        # guess format
        matches |= compute_guess_properties_matches(video, self.version, 'format')
        return matches


class Addic7edProvider(Provider):
    languages = {babelfish.Language('por', 'BR')} | {babelfish.Language(l)
                 for l in ['ara', 'aze', 'ben', 'bos', 'bul', 'cat', 'ces', 'dan', 'deu', 'ell', 'eng', 'eus', 'fas',
                           'fin', 'fra', 'glg', 'heb', 'hrv', 'hun', 'hye', 'ind', 'ita', 'jpn', 'kor', 'mkd', 'msa',
                           'nld', 'nor', 'pol', 'por', 'ron', 'rus', 'slk', 'slv', 'spa', 'sqi', 'srp', 'swe', 'tha',
                           'tur', 'ukr', 'vie', 'zho']}
    video_types = (Episode,)
    server = 'http://www.addic7ed.com'

    def __init__(self, username=None, password=None):
        if username is not None and password is None or username is None and password is not None:
            raise ConfigurationError('Username and password must be specified')
        self.username = username
        self.password = password
        self.logged_in = False

    def initialize(self):
        self.session = requests.Session()
        self.session.headers = {'User-Agent': 'Subliminal/%s' % __version__.split('-')[0]}
        # login
        if self.username is not None and self.password is not None:
            logger.debug('Logging in')
            data = {'username': self.username, 'password': self.password, 'Submit': 'Log in'}
            r = self.session.post(self.server + '/dologin.php', data, timeout=10, allow_redirects=False)
            if r.status_code == 302:
                logger.info('Logged in')
                self.logged_in = True
            else:
                raise AuthenticationError(self.username)

    def terminate(self):
        # logout
        if self.logged_in:
            r = self.session.get(self.server + '/logout.php', timeout=10)
            logger.info('Logged out')
            if r.status_code != 200:
                raise ProviderError('Request failed with status code %d' % r.status_code)
        self.session.close()

    def get(self, url, params=None):
        """Make a GET request on `url` with the given parameters

        :param string url: part of the URL to reach with the leading slash
        :param params: params of the request
        :return: the response
        :rtype: :class:`bs4.BeautifulSoup`

        """
        r = self.session.get(self.server + url, params=params, timeout=10)
        if r.status_code != 200:
            raise ProviderError('Request failed with status code %d' % r.status_code)
        return bs4.BeautifulSoup(r.content, ['permissive'])

    #@region.cache_on_arguments(expiration_time=SHOW_EXPIRATION_TIME)
    def get_show_ids(self):
        """Load the shows page with default series to show ids mapping

        :return: series to show ids
        :rtype: dict

        """
        soup = self.get('/shows.php')
        show_ids = {}
        for html_show in soup.select('td.version > h3 > a[href^="/show/"]'):
            show_ids[html_show.string.lower()] = int(html_show['href'][6:])
        return show_ids

    #@region.cache_on_arguments(expiration_time=SHOW_EXPIRATION_TIME)
    def find_show_id(self, series, year=None):
        """Find the show id from the `series` with optional `year`

        Use this only if the show id cannot be found with :meth:`get_show_ids`

        :param string series: series of the episode in lowercase
        :param year: year of the series, if any
        :type year: int or None
        :return: the show id, if any
        :rtype: int or None

        """
        series_year = series
        if year is not None:
            series_year += ' (%d)' % year
        params = {'search': series_year, 'Submit': 'Search'}
        logger.debug('Searching series %r', params)
        suggested_shows = self.get('/search.php', params).select('span.titulo > a[href^="/show/"]')
        if not suggested_shows:
            logger.info('Series %r not found', series_year)
            return None
        return int(suggested_shows[0]['href'][6:])

    def query(self, series, season, year=None):
        show_ids = self.get_show_ids()
        show_id = None
        if year is not None:  # search with the year
            series_year = '%s (%d)' % (series.lower(), year)
            if series_year in show_ids:
                show_id = show_ids[series_year]
            else:
                show_id = self.find_show_id(series.lower(), year)
        if show_id is None:  # search without the year
            year = None
            if series.lower() in show_ids:
                show_id = show_ids[series.lower()]
            else:
                show_id = self.find_show_id(series.lower())
        if show_id is None:
            return []
        params = {'show_id': show_id, 'season': season}
        logger.debug('Searching subtitles %r', params)
        link = '/show/{show_id}&season={season}'.format(**params)
        soup = self.get(link)
        subtitles = []
        for row in soup('tr', class_='epeven completed'):
            cells = row('td')
            if cells[5].string != 'Completed':
                continue
            if not cells[3].string:
                continue
            subtitles.append(Addic7edSubtitle(babelfish.Language.fromaddic7ed(cells[3].string), series, season,
                                              int(cells[1].string), cells[2].string, year, cells[4].string,
                                              bool(cells[6].string), cells[9].a['href'],
                                              self.server + cells[2].a['href']))
        return subtitles

    def list_subtitles(self, video, languages):
        return [s for s in self.query(video.series, video.season, video.year)
                if s.language in languages and s.episode == video.episode]

    def download_subtitle(self, subtitle):
        r = self.session.get(self.server + subtitle.download_link, timeout=10, headers={'Referer': subtitle.page_link})
        if r.status_code != 200:
            raise ProviderError('Request failed with status code %d' % r.status_code)
        if r.headers['Content-Type'] == 'text/html':
            raise DownloadLimitExceeded
        subtitle.content = fix_line_endings(r.content)
