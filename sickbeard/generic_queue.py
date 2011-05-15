# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import threading

from sickbeard import logger

class QueuePriorities:
    LOW = 10
    NORMAL = 20
    HIGH = 30

class GenericQueue(object):

    def __init__(self):

        self.currentItem = None
        self.queue = []

        self.thread = None

        self.queue_name = "QUEUE"

        self.min_priority = 0
        
        self.currentItem = None

    def pause(self):
        logger.log(u"Pausing queue")
        self.min_priority = 999999999999
    
    def unpause(self):
        logger.log(u"Unpausing queue")
        self.min_priority = 0

    def add_item(self, item):
        item.added = datetime.datetime.now()
        self.queue.append(item)
        
        return item

    def run(self):

        # only start a new task if one isn't already going
        if self.thread == None or self.thread.isAlive() == False:

            # if the thread is dead then the current item should be finished
            if self.currentItem != None:
                self.currentItem.finish()
                self.currentItem = None

            # if there's something in the queue then run it in a thread and take it out of the queue
            if len(self.queue) > 0:

                # sort by priority
                def sorter(x,y):
                    """
                    Sorts by priority descending then time ascending
                    """
                    if x.priority == y.priority:
                        if y.added == x.added:
                            return 0
                        elif y.added < x.added:
                            return 1
                        elif y.added > x.added:
                            return -1
                    else:
                        return y.priority-x.priority

                self.queue.sort(cmp=sorter)
                
                queueItem = self.queue[0]

                if queueItem.priority < self.min_priority:
                    return

                # launch the queue item in a thread
                # TODO: improve thread name
                threadName = self.queue_name + '-' + queueItem.get_thread_name()
                self.thread = threading.Thread(None, queueItem.execute, threadName)
                self.thread.start()

                self.currentItem = queueItem

                # take it out of the queue
                del self.queue[0]

class QueueItem:
    def __init__(self, name, action_id = 0):
        self.name = name

        self.inProgress = False

        self.priority = QueuePriorities.NORMAL

        self.thread_name = None

        self.action_id = action_id
        
        self.added = None

    def get_thread_name(self):
        if self.thread_name:
            return self.thread_name
        else:
            return self.name.replace(" ","-").upper()

    def execute(self):
        """Implementing classes should call this"""

        self.inProgress = True

    def finish(self):
        """Implementing Classes should call this"""

        self.inProgress = False


