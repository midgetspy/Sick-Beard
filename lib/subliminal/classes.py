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


class Error(Exception):
    """Base class for exceptions in subliminal"""
    pass


class BadStateError(Error):
    """Exception raised when an invalid action is asked

    Attributes:
        current  -- current state of Subliminal instance
        expected -- expected state of Subliminal instance
    """
    def __init__(self, current, expected):
        self.current = current
        self.expected = expected

    def __str__(self):
        return 'Expected state %d but current state is %d' % (self.expected, self.current)


class LanguageError(Error):
    """Exception raised when invalid language is submitted

    Attributes:
        language -- language that cause the error
    """
    def __init__(self, language):
        self.language = language

    def __str__(self):
        return self.language


class PluginError(Error):
    """"Exception raised when invalid plugin is submitted

    Attributes:
        plugin -- plugin that cause the error
    """
    def __init__(self, plugin):
        self.plugin = plugin

    def __str__(self):
        return self.plugin


class WrongTaskError(Error):
    """"Exception raised when invalid task is submitted"""
    pass


class DownloadFailedError(Error):
    """"Exception raised when a download task has failed in plugin"""
    pass


class Subtitle(object):
    """Subtitle class

    Attributes:
        video_path -- path to the video file
        path       -- path to the subtitle file
        plugin     -- plugin used
        language   -- language of the subtitle
        link       -- download link
        release    -- release group identified by guessit
        teams      -- identified by subliminal
    """
    def __init__(self, video_path=None, path=None, plugin=None, language=None, link=None, release=None, teams=None):
        self.video_path = video_path
        self.path = path
        self.plugin = plugin
        self.language = language
        self.link = link
        self.release = release
        self.teams = teams

    def __repr__(self):
        return repr({'video_path': self.video_path, 'path': self.path, 'plugin': self.plugin,
            'language': self.language, 'link': self.link, 'release': self.release, 'teams': self.teams})


class Task(object):
    """Base class for tasks to use in subliminal"""
    pass


class ListTask(Task):
    """List task to list subtitles"""
    def __init__(self, filepath, languages, plugin, config):
        self.filepath = filepath
        self.plugin = plugin
        self.languages = languages
        self.config = config


class DownloadTask(Task):
    """Download task to download subtitles"""
    def __init__(self, subtitles):
        self.subtitles = subtitles


class StopTask(Task):
    """Stop task to stop workers"""
    pass
