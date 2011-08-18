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
import plugins
import logging
import traceback


class PluginWorker(threading.Thread):
    """Threaded plugin worker"""
    def __init__(self, taskQueue, resultQueue):
        threading.Thread.__init__(self)
        self.taskQueue = taskQueue
        self.resultQueue = resultQueue
        self.logger = logging.getLogger('subliminal.worker')

    def run(self):
        while True:
            task = self.taskQueue.get()
            result = None
            try:
                if not task:  # this is a poison pill
                    break
                elif task['task'] == 'list':  # the task is a listing
                    # get the corresponding plugin
                    plugin = getattr(plugins, task['plugin'])(task['config'])
                    # split tasks if the plugin can't handle multi queries
                    splitedTasks = plugin.splitTask(task)
                    myTask = splitedTasks.pop()
                    for st in splitedTasks:
                        self.taskQueue.put(st)
                    result = plugin.list(myTask['filenames'], myTask['languages'])
                elif task['task'] == 'download':  # the task is to download
                    result = None
                    while task['subtitle']:
                        subtitle = task['subtitle'].pop(0)
                        # get the corresponding plugin
                        plugin = getattr(plugins, subtitle['plugin'])(task['config'])
                        path = plugin.download(subtitle)
                        if path:
                            subtitle['subtitlepath'] = path
                            result = subtitle
                            break
                else:
                    self.logger.error(u'Unknown task %s submited to worker %s' % (task['task'], self.name))
            except:
                self.logger.debug(traceback.print_exc())
                self.logger.error(u"Worker couldn't do the job %s, continue anyway" % task['task'])
            finally:
                self.resultQueue.put(result)
                self.taskQueue.task_done()
        self.logger.debug(u'Thread %s terminated' % self.name)
