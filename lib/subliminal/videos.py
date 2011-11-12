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


import struct
import os
import hashlib
import guessit
import subprocess
import subtitles
import utils


EXTENSIONS = ['.mkv', '.avi', '.mpg'] #TODO: Complete..
MIMETYPES = ['video/mpeg', 'video/mp4', 'video/quicktime', 'video/x-ms-wmv', 'video/x-msvideo', 'video/x-flv', 'video/x-matroska', 'video/x-matroska-3d']


class Video(object):
    """Base class for videos"""
    def __init__(self, release, guess):
        self.release = release
        self.guess = guess
        self.tvdbid = None
        self.imdbid = None
        self._path = None
        self.hashes = {}
        if os.path.exists(release):
            self.path = release

    def __eq__(self, other):
        return self.release == other.release and self.path == other.path

    @property
    def exists(self):
        if self._path:
            return os.path.exists(self._path)
        return False

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        if not os.path.exists(value):
            raise ValueError('Path does not exists')
        self._path = value
        self.size = os.path.getsize(self._path)
        self._computeHashes()

    def _computeHashes(self):
        self.hashes['OpenSubtitles'] = self._computeHashOpenSubtitles()
        self.hashes['TheSubDB'] = self._computeHashTheSubDB()

    def _computeHashOpenSubtitles(self):
        """Hash a file like OpenSubtitles"""
        longlongformat = 'q'  # long long
        bytesize = struct.calcsize(longlongformat)
        f = open(self.path, 'rb')
        filesize = os.path.getsize(self.path)
        hash = filesize
        if filesize < 65536 * 2:
            return []
        for _ in range(65536 / bytesize):
            buffer = f.read(bytesize)
            (l_value,) = struct.unpack(longlongformat, buffer)
            hash += l_value
            hash = hash & 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number
        f.seek(max(0, filesize - 65536), 0)
        for _ in range(65536 / bytesize):
            buffer = f.read(bytesize)
            (l_value,) = struct.unpack(longlongformat, buffer)
            hash += l_value
            hash = hash & 0xFFFFFFFFFFFFFFFF
        f.close()
        returnedhash = '%016x' % hash
        return returnedhash

    def _computeHashTheSubDB(self):
        """Hash a file like TheSubDB"""
        readsize = 64 * 1024
        with open(self.path, 'rb') as f:
            data = f.read(readsize)
            f.seek(-readsize, os.SEEK_END)
            data += f.read(readsize)
        return hashlib.md5(data).hexdigest()

    def mkvmerge(self, subtitles, out=None, mkvmerge_bin='mkvmerge', title=None):
        """Merge the video with subtitles"""
        if not out:
            out = self.path + '.merged.mkv'
        args = [mkvmerge_bin, '-o', out, self.path]
        if title:
            args += ['--title', title]
        for subtitle in subtitles:
            if subtitle.language:
                args += ['--language', '0:' + subtitle.language, subtitle.path]
            continue
            args += [subtitle.path]
        p = subprocess.Popen(args)
        p.wait()

    def scan(self):
        """Scan and return associated Subtitles"""
        if not self.exists:
            return []
        scan_result = scan(self.path, max_depth=0)
        if len(scan_result) != 1:
            return []
        _, languages, single = scan_result[0]
        results = []
        if single:
            for ext in subtitles.EXTENSIONS:
                filepath = os.path.splitext(self.path)[0] + ext
                if os.path.exists(filepath):
                    subtitle = subtitles.factory(filepath)
                    results.append(subtitle)
                    break
        for language in languages:
            for ext in subtitles.EXTENSIONS:
                filepath = os.path.splitext(self.path)[0] + '.' + language + ext
                if os.path.exists(filepath):
                    subtitle = subtitles.factory(filepath)
                    results.append(subtitle)
                    break
        return results


class Episode(Video):
    """Episode class"""
    def __init__(self, release, series, season, episode, title=None, guess=None):
        super(Episode, self).__init__(release, guess)
        self.series = series
        self.title = title
        self.season = season
        self.episode = episode


class Movie(Video):
    """Movie class"""
    def __init__(self, release, title, year=None, guess=None):
        super(Movie, self).__init__(release, guess)
        self.title = title
        self.year = year


class UnknownVideo(Video):
    """Unknown video"""
    def __init__(self, release, guess):
        super(UnknownVideo, self).__init__(release, guess)
        self.guess = guess


def factory(entry):
    """Create a Video object guessing all informations from the given release/path"""
    guess = guessit.guess_file_info(entry, 'autodetect')
    if guess['type'] == 'episode' and 'series' in guess and 'season' in guess and 'episodeNumber' in guess:
        title = None
        if 'title' in guess:
            title = guess['title']
        return Episode(entry, guess['series'], guess['season'], guess['episodeNumber'], title, guess)
    if guess['type'] == 'movie' and 'title' in guess:
        year = None
        if 'year' in guess:
            year = guess['year']
        return Movie(entry, guess['title'], year, guess)
    return UnknownVideo(entry, guess)

def scan(entry, max_depth=3, depth=0):
    """Scan a path and return a list of tuples (filepath, set(languages), has single)"""
    if depth > max_depth and max_depth != 0:  # we do not want to search the whole file system except if max_depth = 0
        return []
    if depth == 0:
        entry = os.path.abspath(entry)
    if os.path.isfile(entry):  # a file? scan it
        if depth != 0:  # trust the user: only check for valid format if recursing
            if mimetypes.guess_type(entry)[0] not in MIMETYPES and os.path.splitext(entry)[1] not in EXTENSIONS:
                return []
        # check for .lg.ext and .ext
        available_languages = set()
        has_single = False
        basepath = os.path.splitext(entry)[0]
        for l in utils.LANGUAGES:
            for e in subtitles.EXTENSIONS:
                if os.path.exists(basepath + '.%s%s' % (l, e)):
                    available_languages.add(l)
                if os.path.exists(basepath + '%s' % e):
                    has_single = True
        return [(os.path.normpath(entry), available_languages, has_single)]
    if os.path.isdir(entry):  # a dir? recurse
        result = []
        for e in os.listdir(entry):
            result.extend(scan(os.path.join(entry, e), maxdepth, depth + 1))
        return result
    return []  # anything else
