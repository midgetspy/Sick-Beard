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



import sickbeard

class ProgressIndicator():

    def __init__(self, percentComplete=0, currentStatus={'title': ''}):
        self.percentComplete = percentComplete
        self.currentStatus = currentStatus

class ProgressIndicators():
    _pi = {'massUpdate': [],
           'massAdd': [],
           'dailyUpdate': []
           }

    @staticmethod
    def getIndicator(name):
        if name not in ProgressIndicators._pi:
            return []

        # if any of the progress indicators are done take them off the list
        for curPI in ProgressIndicators._pi[name]:
            if curPI != None and curPI.percentComplete() == 100:
                ProgressIndicators._pi[name].remove(curPI)

        # return the list of progress indicators associated with this name
        return ProgressIndicators._pi[name]

    @staticmethod
    def setIndicator(name, indicator):
        ProgressIndicators._pi[name].append(indicator)

class QueueProgressIndicator():
    """
    A class used by the UI to show the progress of the queue or a part of it.
    """
    def __init__(self, name, queueItemList):
        self.queueItemList = queueItemList
        self.name = name

    def numTotal(self):
        return len(self.queueItemList)

    def numFinished(self):
        return len([x for x in self.queueItemList if not x.isInQueue()])

    def numRemaining(self):
        return len([x for x in self.queueItemList if x.isInQueue()])

    def nextName(self):
        for curItem in [sickbeard.showQueueScheduler.action.currentItem]+sickbeard.showQueueScheduler.action.queue: #@UndefinedVariable
            if curItem in self.queueItemList:
                return curItem.name

        return "Unknown"

    def percentComplete(self):
        numFinished = self.numFinished()
        numTotal = self.numTotal()

        if numTotal == 0:
            return 0
        else:
            return int(float(numFinished)/float(numTotal)*100)

class LoadingTVShow():
    def __init__(self, dir):
        self.dir = dir
        self.show = None

class Flash:
    _messages = []
    _errors = []

    def message(self, title, detail=''):
        Flash._messages.append((title, detail))

    def error(self, title, detail=''):
        Flash._errors.append((title, detail))

    def messages(self):
        tempMessages = Flash._messages
        Flash._messages = []
        return tempMessages

    def errors(self):
        tempErrors = Flash._errors
        Flash._errors = []
        return tempErrors

flash = Flash()

