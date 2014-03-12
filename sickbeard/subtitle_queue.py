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

import datetime
import time

import sickbeard
from sickbeard import db, logger, common, exceptions, helpers
from sickbeard import generic_queue
from sickbeard import search
import os.path
from sickbeard import encodingKludge as ek
from lib import subliminal
from lib.babelfish import Language
from subliminal.video import Episode
import random
import sys
import traceback

SUBTITLE_SEARCH = 35
SUBTITLE_SERVICES = ['opensubtitles', 'addic7ed', 'tvsubtitles', 'thesubdb', 'podnapisi']

class SubtitleQueue(generic_queue.GenericQueue):
    
    def __init__(self):
        generic_queue.GenericQueue.__init__(self)
        self.queue_name = "SUBTITLEQUEUE"

    def is_ep_in_queue(self, ep_obj):
        for cur_item in self.queue:
            if isinstance(cur_item, SubtitleQueueItem) and cur_item.ep_obj == ep_obj:
                return True
        return False

    def add_item(self, item):

        if isinstance(item, SubtitleQueueItem) and not self.is_ep_in_queue(item.ep_obj):
            generic_queue.GenericQueue.add_item(self, item)
        else:
            logger.log(u"Not adding item, it's already in the queue", logger.DEBUG)

class SubtitleQueueItem(generic_queue.QueueItem):
    def __init__(self, ep_obj, force):
        generic_queue.QueueItem.__init__(self, 'Search', SUBTITLE_SEARCH)
        self.priority = generic_queue.QueuePriorities.NORMAL
        
        self.ep_obj = ep_obj
        self.force = force
        
        self.success = None

    def execute(self):
        generic_queue.QueueItem.execute(self)
        
        ep_obj = self.ep_obj
        force = self.force
        
        random.shuffle(SUBTITLE_SERVICES)
        logger.log("Searching subtitles for " + ep_obj.prettyName())

        if not ek.ek(os.path.isfile, ep_obj.location):
            logger.log("Can't download subtitles for " + ep_obj.prettyName() + ". Episode file doesn't exist.", logger.DEBUG)
            return
        
        epName = ep_obj.location.rpartition(".")[0]
        subLanguages = []
        if sickbeard.SUBTITLE_LANGUAGES <> '':
            subLanguages = sickbeard.SUBTITLE_LANGUAGES.split(",")
        if len(subLanguages) < 1 and ep_obj.show.lang:
            subLanguages.append(ep_obj.show.lang)
        
        if len(subLanguages) < 1:
            logger.log("Can't download subtitles for " + ep_obj.prettyName() + ". Configure the language to search at post processing options.", logger.DEBUG)
            return
        #for lang in subLanguages:
            #langS = lang.split("-")
            #if len(langS) > 1:
                #subLanguages.append(langS[0])
        try:
            sublimLangs = set()
            for sub in subLanguages:
                bLang = Language.fromietf(sub)
                sublimLangs.add(bLang)
            sublimEpisode = set()
            sublimEpisode.add(Episode.fromname(ep_obj.location))
            downloadedSubs = subliminal.download_best_subtitles(
                videos=sublimEpisode,
                languages=sublimLangs,
                providers=SUBTITLE_SERVICES)

            subliminal.save_subtitles(downloadedSubs, directory = os.path.dirname(ep_obj.location))
            subCount = 0
            for video, video_subtitles in downloadedSubs.items():
                for sub in video_subtitles:
                    subPath = subliminal.subtitle.get_subtitle_path(ep_obj.location, sub.language)
                    helpers.chmodAsParent(subPath)
                    subCount += 1
        except Exception, e:
            logger.log("Error while downloading subtitles for %s: %s" % (ep_obj.prettyName(), str(e)), logger.ERROR)
            traceback.print_exc()
            return False
                
        if subCount > 0:
            ep_obj.checkForMetaFiles()
            ep_obj.saveToDB(forceSave = True)
            logger.log("Downloaded subtitle for %s." % ep_obj.prettyName())
            self.success = True
        else:
            logger.log("No subtitles downloaded for %s." % ep_obj.prettyName())
            self.success = False

    def finish(self):
        # don't let this linger if something goes wrong
        if self.success == None:
            self.success = False
        generic_queue.QueueItem.finish(self)
