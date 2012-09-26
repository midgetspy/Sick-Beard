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
from .core import (get_defaults, create_list_tasks, consume_task,
    create_download_tasks, group_by_video, key_subtitles)
from .language import language_set, language_list
import logging


__all__ = ['consume_task_list', 'list_subtitles', 'download_subtitles']
logger = logging.getLogger(__name__)


def consume_task_list(tasks):
    """Consume the given list of tasks, single-threaded mode.

    :param tasks: the list of tasks to consume
    :type tasks: list of :class:`~subliminal.tasks.ListTask` or :class:`~subliminal.tasks.DownloadTask`
    :return: resulting subtitles (either list of subtitles to download or downloaded subtitles, depending on the tasks type
    :rtype: dict of :class:`~subliminal.videos.Video` => [:class:`~subliminal.subtitles.ResultSubtitle`]

    """
    results = []
    service_instances = {}
    for task in tasks:
        try:
            result = consume_task(task, service_instances)
            results.append((task.video, result))
        except:
            logger.error(u'Error consuming task %r' % task, exc_info=True)
    for service_instance in service_instances.itervalues():
        service_instance.terminate()
    return group_by_video(results)


def list_subtitles(paths, languages=None, services=None, force=True, multi=False, cache_dir=None, max_depth=3, scan_filter=None):
    """List subtitles in given paths according to the criteria

    :param paths: path(s) to video file or folder
    :type paths: string or list
    :param languages: languages to search for, in preferred order
    :type languages: list of :class:`~subliminal.language.Language` or string
    :param list services: services to use for the search, in preferred order
    :param bool force: force searching for subtitles even if some are detected
    :param bool multi: search multiple languages for the same video
    :param string cache_dir: path to the cache directory to use
    :param int max_depth: maximum depth for scanning entries
    :param function scan_filter: filter function that takes a path as argument and returns a boolean indicating whether it has to be filtered out (``True``) or not (``False``)
    :return: found subtitles
    :rtype: dict of :class:`~subliminal.videos.Video` => [:class:`~subliminal.subtitles.ResultSubtitle`]

    """
    paths, languages, services, _ = get_defaults(paths, languages, services, None,
                                                 languages_as=language_set)
    tasks = create_list_tasks(paths, languages, services, force, multi, cache_dir, max_depth, scan_filter)
    return consume_task_list(tasks)


def download_subtitles(paths, languages=None, services=None, force=True, multi=False, cache_dir=None, max_depth=3, scan_filter=None, order=None):
    """Download subtitles in given paths according to the criteria

    :param paths: path(s) to video file or folder
    :type paths: string or list
    :param languages: languages to search for, in preferred order
    :type languages: list of :class:`~subliminal.language.Language` or string
    :param list services: services to use for the search, in preferred order
    :param bool force: force searching for subtitles even if some are detected
    :param bool multi: search multiple languages for the same video
    :param string cache_dir: path to the cache directory to use
    :param int max_depth: maximum depth for scanning entries
    :param function scan_filter: filter function that takes a path as argument and returns a boolean indicating whether it has to be filtered out (``True``) or not (``False``)
    :param order: preferred order for subtitles sorting
    :type list: list of :data:`~subliminal.core.LANGUAGE_INDEX`, :data:`~subliminal.core.SERVICE_INDEX`, :data:`~subliminal.core.SERVICE_CONFIDENCE`, :data:`~subliminal.core.MATCHING_CONFIDENCE`
    :return: downloaded subtitles
    :rtype: dict of :class:`~subliminal.videos.Video` => [:class:`~subliminal.subtitles.ResultSubtitle`]

    .. note::

        If you use ``multi=True``, :data:`~subliminal.core.LANGUAGE_INDEX` has to be the first item of the ``order`` list
        or you might get unexpected results.

    """
    paths, languages, services, order = get_defaults(paths, languages, services, order,
                                                     languages_as=language_list)
    subtitles_by_video = list_subtitles(paths, languages, services, force, multi, cache_dir, max_depth, scan_filter)
    for video, subtitles in subtitles_by_video.iteritems():
        subtitles.sort(key=lambda s: key_subtitles(s, video, languages, services, order), reverse=True)
    tasks = create_download_tasks(subtitles_by_video, languages, multi)
    return consume_task_list(tasks)
