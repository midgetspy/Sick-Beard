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

from __future__ import with_statement

import sickbeard

from sickbeard import search_queue

import threading

class CurrentSearcher():

    def __init__(self):
        self.lock = threading.Lock()

        self.amActive = False

    def run(self):
        search_queue_item = search_queue.RSSSearchQueueItem()
        sickbeard.searchQueueScheduler.action.add_item(search_queue_item) #@UndefinedVariable
