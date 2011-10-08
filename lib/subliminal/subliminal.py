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

import threading
from itertools import groupby
from classes import DownloadTask, ListTask, StopTask, LanguageError, PluginError, BadStateError, WrongTaskError, DownloadFailedError
import Queue
import logging
import mimetypes
import os
import plugins


# be nice
try:
    from logging import NullHandler
except ImportError:

    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
logger = logging.getLogger('subliminal')
logger.addHandler(NullHandler())

# const
FORMATS = ['video/x-msvideo', 'video/quicktime', 'video/x-matroska', 'video/mp4']
EXTENSIONS = set(['srt', 'sub'])
LANGUAGES = set(['aa', 'ab', 'ae', 'af', 'ak', 'am', 'an', 'ar', 'as', 'av', 'ay', 'az', 'ba', 'be', 'bg', 'bh', 'bi',
                 'bm', 'bn', 'bo', 'br', 'bs', 'ca', 'ce', 'ch', 'co', 'cr', 'cs', 'cu', 'cv', 'cy', 'da', 'de', 'dv',
                 'dz', 'ee', 'el', 'en', 'eo', 'es', 'et', 'eu', 'fa', 'ff', 'fi', 'fj', 'fo', 'fr', 'fy', 'ga', 'gd',
                 'gl', 'gn', 'gu', 'gv', 'ha', 'he', 'hi', 'ho', 'hr', 'ht', 'hu', 'hy', 'hz', 'ia', 'id', 'ie', 'ig',
                 'ii', 'ik', 'io', 'is', 'it', 'iu', 'ja', 'jv', 'ka', 'kg', 'ki', 'kj', 'kk', 'kl', 'km', 'kn', 'ko',
                 'kr', 'ks', 'ku', 'kv', 'kw', 'ky', 'la', 'lb', 'lg', 'li', 'ln', 'lo', 'lt', 'lu', 'lv', 'mg', 'mh',
                 'mi', 'mk', 'ml', 'mn', 'mo', 'mr', 'ms', 'mt', 'my', 'na', 'nb', 'nd', 'ne', 'ng', 'nl', 'nn', 'no',
                 'nr', 'nv', 'ny', 'oc', 'oj', 'om', 'or', 'os', 'pa', 'pi', 'pl', 'ps', 'pt', 'qu', 'rm', 'rn', 'ro',
                 'ru', 'rw', 'sa', 'sc', 'sd', 'se', 'sg', 'si', 'sk', 'sl', 'sm', 'sn', 'so', 'sq', 'sr', 'ss', 'st',
                 'su', 'sv', 'sw', 'ta', 'te', 'tg', 'th', 'ti', 'tk', 'tl', 'tn', 'to', 'tr', 'ts', 'tt', 'tw', 'ty',
                 'ug', 'uk', 'ur', 'uz', 've', 'vi', 'vo', 'wa', 'wo', 'xh', 'yi', 'yo', 'za', 'zh', 'zu'])  # ISO 639-1
PLUGINS = ['BierDopje', 'OpenSubtitles', 'SubsWiki', 'Subtitulos', 'TheSubDB']
API_PLUGINS = filter(lambda p: getattr(plugins, p).api_based, PLUGINS)
IDLE = 0
RUNNING = 1
PAUSED = 2


class Subliminal(object):
    """Main Subliminal class"""

    def __init__(self, cache_dir=None, workers=4, multi=False, force=False, max_depth=3, files_mode=-1):
        self.multi = multi
        self.force = force
        self.max_depth = max_depth
        self.cache_dir = None
        self.taskQueue = Queue.PriorityQueue()
        self.listResultQueue = Queue.Queue()
        self.downloadResultQueue = Queue.Queue()
        self._languages = []
        self._plugins = API_PLUGINS
        self.workers = workers
        self.files_mode = files_mode
        self.state = IDLE
        try:
            if cache_dir:
                self.cache_dir = cache_dir
                if not os.path.isdir(self.cache_dir):
                    os.makedirs(self.cache_dir)
                    logger.debug(u'Creating cache directory: %r' % self.cache_dir)
        except:
            self.cache_dir = None
            logger.error(u'Failed to use the cache directory, continue without it')

    @property
    def languages(self):
        """Getter for languages"""
        return self._languages

    @languages.setter
    def languages(self, languages):
        """Setter for languages"""
        logger.debug(u'Setting languages to %r' % languages)
        self._languages = []
        for l in languages:
            if l not in LANGUAGES:
                raise LanguageError(l)
            if not l in self._languages:
                self._languages.append(l)

    @property
    def plugins(self):
        """Getter for plugins"""
        return self._plugins

    @plugins.setter
    def plugins(self, plugins):
        """Setter for plugins"""
        logger.debug(u'Setting plugins to %r' % plugins)
        self._plugins = []
        for p in plugins:
            if p not in PLUGINS:
                raise PluginError(p)
            if not p in self._plugins:
                self._plugins.append(p)

    def listSubtitles(self, entries, auto=True):
        """
        Search subtitles within the plugins and return all found subtitles in a list of Subtitle object.

        Attributes:
            entries -- filepath or folderpath of video file or a list of that
            auto    -- automaticaly manage workers"""
        if auto:
            if self.state != IDLE:
                raise BadStateError(self.state, IDLE)
            self.startWorkers()
        if isinstance(entries, basestring):
            entries = [entries]
        scan_result = []
        for e in entries:
            if not isinstance(e, unicode):
                logger.warning(u'Entry %r is not unicode' % e)
            if not os.path.exists(e):
                scan_result.append((e, set(), False))
                continue
            scan_result.extend(scan(e))
        task_count = 0
        for filepath, languages, has_single in scan_result:
            wanted_languages = set(self._languages)
            if not wanted_languages:
                wanted_languages = LANGUAGES
            if not self.force and self.multi:
                wanted_languages = set(wanted_languages) - languages
                if not wanted_languages:
                    logger.debug(u'No need to list multi subtitles %r for %r because %r subtitles detected' % (self._languages, filepath, languages))
                    continue
            if not self.force and not self.multi and has_single:
                logger.debug(u'No need to list single subtitles %r for %r because one detected' % (self._languages, filepath))
                continue
            logger.debug(u'Listing subtitles %r for %r with %r' % (wanted_languages, filepath, self._plugins))
            for plugin in self._plugins:
                self.taskQueue.put((5, ListTask(filepath, wanted_languages, plugin, self.getConfigDict())))
                task_count += 1
        subtitles = []
        for _ in range(task_count):
            subtitles.extend(self.listResultQueue.get())
        if auto:
            self.stopWorkers()
        return subtitles

    def downloadSubtitles(self, entries, auto=True):
        """
        Download subtitles using the plugins preferences and languages. Also use internal algorithm to find
        the best match inside a plugin.

        Attributes:
            entries -- filepath or folderpath of video file or a list of that
            auto    -- automaticaly manage workers"""
        if auto:
            if self.state != IDLE:
                raise BadStateError(self.state, IDLE)
            self.startWorkers()
        subtitles = self.listSubtitles(entries, False)
        task_count = 0
        for _, subsByVideoPath in groupby(sorted(subtitles, key=lambda x: x.video_path), lambda x: x.video_path):
            if not self.multi:
                self.taskQueue.put((5, DownloadTask(sorted(list(subsByVideoPath), cmp=self.cmpSubtitles))))
                task_count += 1
                continue
            for __, subsByVideoPathByLanguage in groupby(sorted(subsByVideoPath, key=lambda x: x.language), lambda x: x.language):
                self.taskQueue.put((5, DownloadTask(sorted(list(subsByVideoPathByLanguage), cmp=self.cmpSubtitles))))
                task_count += 1
        downloaded = []
        for _ in range(task_count):
            downloaded.extend(self.downloadResultQueue.get())
        if auto:
            self.stopWorkers()
        return downloaded

    def cmpSubtitles(self, x, y):
        """Compares 2 subtitles elements x and y using video_path, languages and plugin"""
        video_paths = sorted([x.video_path, y.video_path])
        if x.video_path != y.video_path and video_paths.index(x.video_path) < video_paths(y.video_path):
            return - 1
        if x.video_path != y.video_path and video_paths.index(x.video_path) > video_paths(y.video_path):
            return 1
        if self._languages and self._languages.index(x.language) < self._languages.index(y.language):
            return - 1
        if self._languages and self._languages.index(x.language) > self._languages.index(y.language):
            return 1
        if self._plugins.index(x.plugin) < self._plugins.index(y.plugin):
            return - 1
        if self._plugins.index(x.plugin) > self._plugins.index(y.plugin):
            return 1
        return 0

    def startWorkers(self):
        """Create a pool of workers and start them"""
        self.pool = []
        for _ in range(self.workers):
            worker = PluginWorker(self.taskQueue, self.listResultQueue, self.downloadResultQueue)
            worker.start()
            self.pool.append(worker)
            logger.debug(u'Worker %s added to the pool' % worker.name)
        self.state = RUNNING

    def stopWorkers(self):
        """Stop workers using a lowest priority stop signal and wait for them to terminate properly"""
        for _ in range(self.workers):
            self.taskQueue.put((10, StopTask()))
        for worker in self.pool:
            worker.join()
        self.state = IDLE

    def pauseWorkers(self):
        """Pause workers using a highest priority stop signal and wait for them to terminate properly"""
        for _ in range(self.workers):
            self.taskQueue.put((0, StopTask()))
        for worker in self.pool:
            worker.join()
        self.state = PAUSED
        if self.taskQueue.empty():
            self.state = STOPPED

    def getConfigDict(self):
        """Produce a dict with configuration items. Used by plugins to read configuration"""
        config = {}
        config['multi'] = self.multi
        config['cache_dir'] = self.cache_dir
        config['files_mode'] = self.files_mode
        return config

    def addTask(self, task):
        if not isinstance(task, Task) or isinstance(task, StopTask):
            raise WrongTaskError()
        self.taskQueue.put((5, task))


class PluginWorker(threading.Thread):
    """Threaded plugin worker"""
    def __init__(self, taskQueue, listResultQueue, downloadResultQueue):
        threading.Thread.__init__(self)
        self.taskQueue = taskQueue
        self.listResultQueue = listResultQueue
        self.downloadResultQueue = downloadResultQueue
        self.logger = logging.getLogger('subliminal.worker')

    def run(self):
        while True:
            task = self.taskQueue.get()[1]
            if isinstance(task, StopTask):
                self.logger.debug(u'Poison pill received, terminating thread %s' % self.name)
                self.taskQueue.task_done()
                break
            result = []
            try:
                if isinstance(task, ListTask):
                    plugin = getattr(plugins, task.plugin)(task.config)
                    result = plugin.list(task.filepath, task.languages)
                elif isinstance(task, DownloadTask):
                    for subtitle in task.subtitles:
                        plugin = getattr(plugins, subtitle.plugin)()
                        try:
                            result = [plugin.download(subtitle)]
                            break
                        except DownloadFailedError as e:
                            self.logger.warning(u'Could not download subtitle %r, trying next' % subtitle)
                            continue
                    if not result:
                        self.logger.error(u'No subtitles could be downloaded for file %r' % subtitle.video_path)
            except:
                self.logger.error(u'Exception raised in worker %s' % self.name, exc_info=True)
            finally:
                if isinstance(task, ListTask):
                    self.listResultQueue.put(result)
                elif isinstance(task, DownloadTask):
                    self.downloadResultQueue.put(result)
                self.taskQueue.task_done()
        self.logger.debug(u'Thread %s terminated' % self.name)


def scan(entry, depth=0, max_depth=3):
    """Scan a path and return a list of tuples (filepath, set(languages), has single)"""
    if depth > max_depth and max_depth != 0:  # we do not want to search the whole file system except if max_depth = 0
        return []
    if depth == 0:
        entry = os.path.abspath(entry)
    if os.path.isfile(entry):  # a file? scan it
        if depth != 0:  # trust the user: only check for valid format if recursing
            mimetypes.add_type('video/x-matroska', '.mkv')
            if mimetypes.guess_type(entry)[0] not in FORMATS:
                return []
        # check for .lg.ext and .ext
        available_languages = set()
        has_single = False
        basepath = os.path.splitext(entry)[0]
        for l in LANGUAGES:
            for e in EXTENSIONS:
                if os.path.exists(basepath + '.%s.%s' % (l, e)):
                    available_languages.add(l)
                if os.path.exists(basepath + '.%s' % e):
                    has_single = True
        return [(os.path.normpath(entry), available_languages, has_single)]
    if os.path.isdir(entry):  # a dir? recurse
        result = []
        for e in os.listdir(entry):
            result.extend(scan(os.path.join(entry, e), depth + 1))
        return result
    return []  # anything else
