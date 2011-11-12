# -*- coding: utf-8 -*-
#
# Subliminal - Subtitles, faster than your thoughts
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


import os.path
from exceptions import InvalidLanguageError
from utils import LANGUAGES


EXTENSIONS = ['.srt', '.sub', '.txt']


class Subtitle(object):
    """Subtitle class"""

    def __init__(self, path, plugin=None, language=None, link=None, release=None, confidence=1, keywords=set()):
        self.path = path
        self.plugin = plugin
        self.language = language
        self.link = link
        self.release = release
        self.keywords = keywords
        self.confidence = confidence

    @property
    def exists(self):
        if self.path:
            return os.path.exists(self.path)
        return False

    def __repr__(self):
        return repr({'path': self.path, 'plugin': self.plugin, 'language': self.language, 'link': self.link, 'release': self.release, 'keywords': self.keywords, 'confidence': self.confidence})


def get_subtitle_path(video_path, language, multi):
    """Create the subtitle path from the given video path using language if multi"""
    if not os.path.exists(video_path):
        path = os.path.splitext(os.path.basename(video_path))[0]
    else:
        path = os.path.splitext(video_path)[0]
    if multi and language:
        return path + '.%s%s' % (language, EXTENSIONS[0])
    return path + '%s' % EXTENSIONS[0]

def factory(path):
    extension = ''
    for e in EXTENSIONS:
        if path.endswith(e):
            extension = e
            break
    if not extension:
        raise ValueError('Not a supported subtitle extension')
    language = os.path.splitext(path[:len(path) - len(extension)])[1][1:]
    if not language in LANGUAGES:
        language = None
    return Subtitle(path, language=language)
