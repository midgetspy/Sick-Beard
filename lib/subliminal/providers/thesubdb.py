# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import babelfish
import requests
from . import Provider
from .. import __version__
from ..exceptions import ProviderError
from ..subtitle import Subtitle, fix_line_endings


logger = logging.getLogger(__name__)


class TheSubDBSubtitle(Subtitle):
    provider_name = 'thesubdb'

    def __init__(self, language, hash):  # @ReservedAssignment
        super(TheSubDBSubtitle, self).__init__(language)
        self.hash = hash

    def compute_matches(self, video):
        matches = set()
        # hash
        if 'thesubdb' in video.hashes and video.hashes['thesubdb'] == self.hash:
            matches.add('hash')
        return matches


class TheSubDBProvider(Provider):
    languages = {babelfish.Language.fromalpha2(l) for l in ['en', 'es', 'fr', 'it', 'nl', 'pl', 'pt', 'ro', 'sv', 'tr']}
    required_hash = 'thesubdb'

    def initialize(self):
        self.session = requests.Session()
        self.session.headers = {'User-Agent': 'SubDB/1.0 (subliminal/%s; https://github.com/Diaoul/subliminal)' %
                                __version__.split('-')[0]}

    def terminate(self):
        self.session.close()

    def get(self, params):
        """Make a GET request on the server with the given parameters

        :param params: params of the request
        :return: the response
        :rtype: :class:`requests.Response`

        """
        return self.session.get('http://api.thesubdb.com', params=params, timeout=10)

    def query(self, hash):  # @ReservedAssignment
        params = {'action': 'search', 'hash': hash}
        logger.debug('Searching subtitles %r', params)
        r = self.get(params)
        if r.status_code == 404:
            logger.debug('No subtitle found')
            return []
        elif r.status_code != 200:
            raise ProviderError('Request failed with status code %d' % r.status_code)
        return [TheSubDBSubtitle(language, hash) for language in
                {babelfish.Language.fromalpha2(l) for l in r.content.decode('utf-8').split(',')}]

    def list_subtitles(self, video, languages):
        return [s for s in self.query(video.hashes['thesubdb']) if s.language in languages]

    def download_subtitle(self, subtitle):
        params = {'action': 'download', 'hash': subtitle.hash, 'language': subtitle.language.alpha2}
        r = self.get(params)
        if r.status_code != 200:
            raise ProviderError('Request failed with status code %d' % r.status_code)
        subtitle.content = fix_line_endings(r.content)
