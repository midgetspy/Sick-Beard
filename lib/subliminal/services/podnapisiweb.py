# -*- coding: utf-8 -*-
# Copyright 2011-2012 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of subliminal.
#
# subliminal is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with subliminal.  If not, see <http://www.gnu.org/licenses/>.
from . import ServiceBase
from ..exceptions import DownloadFailedError
from ..language import Language, language_set
from ..subtitles import ResultSubtitle
from ..utils import get_keywords
from ..videos import Episode, Movie
from bs4 import BeautifulSoup
import guessit
import logging
import re
from subliminal.subtitles import get_subtitle_path


logger = logging.getLogger("subliminal")


class PodnapisiWeb(ServiceBase):
    server_url = 'http://simple.podnapisi.net'
    site_url = 'http://www.podnapisi.net'
    api_based = True
    user_agent = 'Subliminal/0.6'
    videos = [Episode, Movie]
    require_video = False
    required_features = ['xml']
    languages = language_set(['Albanian', 'Arabic', 'Spanish (Argentina)', 'Belarusian', 'Bosnian', 'Portuguese (Brazil)', 'Bulgarian', 'Catalan',
                              'Chinese', 'Croatian', 'Czech', 'Danish', 'Dutch', 'English', 'Estonian', 'Persian',
                              'Finnish', 'French', 'German', 'gre', 'Kalaallisut', 'Hebrew', 'Hindi', 'Hungarian',
                              'Icelandic', 'Indonesian', 'Irish', 'Italian', 'Japanese', 'Kazakh', 'Korean', 'Latvian',
                              'Lithuanian', 'Macedonian', 'Malay', 'Norwegian', 'Polish', 'Portuguese', 'Romanian',
                              'Russian', 'Serbian', 'Sinhala', 'Slovak', 'Slovenian', 'Spanish', 'Swedish', 'Thai',
                              'Turkish', 'Ukrainian', 'Vietnamese'])
    language_map = {Language('Albanian'): 29, Language('Arabic'): 12, Language('Spanish (Argentina)'): 14, Language('Belarusian'): 50,
                    Language('Bosnian'): 10, Language('Portuguese (Brazil)'): 48, Language('Bulgarian'): 33, Language('Catalan'): 53,
                    Language('Chinese'): 17, Language('Croatian'): 38, Language('Czech'): 7, Language('Danish'): 24,
                    Language('Dutch'): 23, Language('English'): 2, Language('Estonian'): 20, Language('Persian'): 52,
                    Language('Finnish'): 31, Language('French'): 8, Language('German'): 5, Language('gre'): 16,
                    Language('Kalaallisut'): 57, Language('Hebrew'): 22, Language('Hindi'): 42, Language('Hungarian'): 15,
                    Language('Icelandic'): 6, Language('Indonesian'): 54, Language('Irish'): 49, Language('Italian'): 9,
                    Language('Japanese'): 11, Language('Kazakh'): 58, Language('Korean'): 4, Language('Latvian'): 21,
                    Language('Lithuanian'): 19, Language('Macedonian'): 35, Language('Malay'): 55,
                    Language('Norwegian'): 3, Language('Polish'): 26, Language('Portuguese'): 32, Language('Romanian'): 13,
                    Language('Russian'): 27, Language('Serbian'): 36, Language('Sinhala'): 56, Language('Slovak'): 37,
                    Language('Slovenian'): 1, Language('Spanish'): 28, Language('Swedish'): 25, Language('Thai'): 44,
                    Language('Turkish'): 30, Language('Ukrainian'): 46, Language('Vietnamese'): 51,
                    29: Language('Albanian'), 12: Language('Arabic'), 14: Language('Spanish (Argentina)'), 50: Language('Belarusian'),
                    10: Language('Bosnian'), 48: Language('Portuguese (Brazil)'), 33: Language('Bulgarian'), 53: Language('Catalan'),
                    17: Language('Chinese'), 38: Language('Croatian'), 7: Language('Czech'), 24: Language('Danish'),
                    23: Language('Dutch'), 2: Language('English'), 20: Language('Estonian'), 52: Language('Persian'),
                    31: Language('Finnish'), 8: Language('French'), 5: Language('German'), 16: Language('gre'),
                    57: Language('Kalaallisut'), 22: Language('Hebrew'), 42: Language('Hindi'), 15: Language('Hungarian'),
                    6: Language('Icelandic'), 54: Language('Indonesian'), 49: Language('Irish'), 9: Language('Italian'),
                    11: Language('Japanese'), 58: Language('Kazakh'), 4: Language('Korean'), 21: Language('Latvian'),
                    19: Language('Lithuanian'), 35: Language('Macedonian'), 55: Language('Malay'), 40: Language('Chinese'),
                    3: Language('Norwegian'), 26: Language('Polish'), 32: Language('Portuguese'), 13: Language('Romanian'),
                    27: Language('Russian'), 36: Language('Serbian'), 47: Language('Serbian'), 56: Language('Sinhala'),
                    37: Language('Slovak'), 1: Language('Slovenian'), 28: Language('Spanish'), 25: Language('Swedish'),
                    44: Language('Thai'), 30: Language('Turkish'), 46: Language('Ukrainian'), Language('Vietnamese'): 51}

    def list_checked(self, video, languages):
        if isinstance(video, Movie):
            return self.query(video.path or video.release, languages, video.title, year=video.year,
                              keywords=get_keywords(video.guess))
        if isinstance(video, Episode):
            return self.query(video.path or video.release, languages, video.series, season=video.season,
                              episode=video.episode, keywords=get_keywords(video.guess))

    def query(self, filepath, languages, title, season=None, episode=None, year=None, keywords=None):
        params = {'sXML': 1, 'sK': title, 'sJ': ','.join([str(self.get_code(l)) for l in languages])}
        if season is not None:
            params['sTS'] = season
        if episode is not None:
            params['sTE'] = episode
        if year is not None:
            params['sY'] = year
        if keywords is not None:
            params['sR'] = keywords
        r = self.session.get(self.server_url + '/ppodnapisi/search', params=params)
        if r.status_code != 200:
            logger.error(u'Request %s returned status code %d' % (r.url, r.status_code))
            return []
        subtitles = []
        soup = BeautifulSoup(r.content, self.required_features)
        for sub in soup('subtitle'):
            if 'n' in sub.flags:
                logger.debug(u'Skipping hearing impaired')
                continue
            language = self.get_language(sub.languageId.text)
            confidence = float(sub.rating.text) / 5.0
            sub_keywords = set()
            for release in sub.release.text.split():
                sub_keywords |= get_keywords(guessit.guess_file_info(release + '.srt', 'autodetect'))
            sub_path = get_subtitle_path(filepath, language, self.config.multi)
            subtitle = ResultSubtitle(sub_path, language, self.__class__.__name__.lower(),
                                      sub.url.text, confidence=confidence, keywords=sub_keywords)
            subtitles.append(subtitle)
        return subtitles

    def download(self, subtitle):
        r = self.session.get(subtitle.link)
        if r.status_code != 200:
            raise DownloadFailedError()
        soup = BeautifulSoup(r.content)
        self.download_zip_file(self.server_url + soup.find('a', href=re.compile('download'))['href'], subtitle.path)
        return subtitle


Service = PodnapisiWeb
