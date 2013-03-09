# Author: Nyaran <nyayukko@gmail.com>, based on Antoine Bertin <diaoulael@gmail.com> work
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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import sickbeard
from sickbeard.common import *
from sickbeard import notifiers
from sickbeard import logger
from sickbeard import helpers
from sickbeard import encodingKludge as ek
from sickbeard import db
from sickbeard import history
from lib import subliminal

SINGLE = 'und'
def sortedServiceList():
    servicesMapping = dict([(x.lower(), x) for x in subliminal.core.SERVICES])

    newList = []

    # add all services in the priority list, in order
    curIndex = 0
    for curService in sickbeard.SUBTITLES_SERVICES_LIST:
        if curService in servicesMapping:
            curServiceDict = {'id': curService, 'image': curService+'.png', 'name': servicesMapping[curService], 'enabled': sickbeard.SUBTITLES_SERVICES_ENABLED[curIndex] == 1, 'api_based': __import__('lib.subliminal.services.' + curService, globals=globals(), locals=locals(), fromlist=['Service'], level=-1).Service.api_based, 'url': __import__('lib.subliminal.services.' + curService, globals=globals(), locals=locals(), fromlist=['Service'], level=-1).Service.site_url}
            newList.append(curServiceDict)
        curIndex += 1

    # add any services that are missing from that list
    for curService in servicesMapping.keys():
        if curService not in [x['id'] for x in newList]:
            curServiceDict = {'id': curService, 'image': curService+'.png', 'name': servicesMapping[curService], 'enabled': False, 'api_based': servicesMapping[curService] in subliminal.SERVICES, 'url': ''}
            newList.append(curServiceDict)

    return newList
    
def getEnabledServiceList():
    return [x['name'] for x in sortedServiceList() if x['enabled']]
    
def isValidLanguage(language):
    return subliminal.language.language_list(language)

def getLanguageName(selectLang):
    return subliminal.language.Language(selectLang).name

def wantedLanguages(sqlLike = False):
    wantedLanguages = sorted(sickbeard.SUBTITLES_LANGUAGES)
    if sqlLike:
        return '%' + ','.join(wantedLanguages) + '%'
    return wantedLanguages

def subtitlesLanguages(video_path):
    """Return a list detected subtitles for the given video file"""
    video = subliminal.videos.Video.from_path(video_path)
    subtitles = video.scan()
    languages = set()
    for subtitle in subtitles:
        if subtitle.language:
            languages.add(subtitle.language.alpha2)
        else:
            languages.add(SINGLE)
    return list(languages)

# Return a list with languages that have alpha2 code
def subtitleLanguageFilter():
    return [language for language in subliminal.language.LANGUAGES if language[2] != ""]

class SubtitlesFinder():
    """
    The SubtitlesFinder will be executed every hour but will not necessarly search
    and download subtitles. Only if the defined rule is true
    """
    def run(self):
        # TODO: Put that in the __init__ before starting the thread?
        if not sickbeard.USE_SUBTITLES:
            logger.log(u'Subtitles support disabled', logger.DEBUG)
            return
        if len(sickbeard.subtitles.getEnabledServiceList()) < 1:
            logger.log(u'Not enough services selected. At least 1 service is required to search subtitles in the background', logger.ERROR)
            return

        logger.log(u'Checking for subtitles', logger.MESSAGE)

        # get episodes on which we want subtitles
        # criteria is: 
        #  - show subtitles = 1
        #  - episode subtitles != config wanted languages or SINGLE (depends on config multi)
        #  - search count < 2 and diff(airdate, now) > 1 week : now -> 1d
        #  - search count < 7 and diff(airdate, now) <= 1 week : now -> 4h -> 8h -> 16h -> 1d -> 1d -> 1d
        
        myDB = db.DBConnection()
        today = datetime.date.today().toordinal()
        # you have 5 minutes to understand that one. Good luck
        sqlResults = myDB.select('SELECT s.show_name, e.showid, e.season, e.episode, e.status, e.subtitles, e.subtitles_searchcount AS searchcount, e.subtitles_lastsearch AS lastsearch, e.location, (? - e.airdate) AS airdate_daydiff FROM tv_episodes AS e INNER JOIN tv_shows AS s ON (e.showid = s.tvdb_id) WHERE s.subtitles = 1 AND e.subtitles NOT LIKE (?) AND ((e.subtitles_searchcount <= 2 AND (? - e.airdate) > 7) OR (e.subtitles_searchcount <= 7 AND (? - e.airdate) <= 7)) AND (e.status IN ('+','.join([str(x) for x in Quality.DOWNLOADED + [ARCHIVED]])+') OR (e.status IN ('+','.join([str(x) for x in Quality.SNATCHED + Quality.SNATCHED_PROPER])+') AND e.location != ""))', [today, wantedLanguages(True), today, today])
        if len(sqlResults) == 0:
            logger.log('No subtitles to download', logger.MESSAGE)
            return
        
        rules = self._getRules()
        now = datetime.datetime.now();
        for epToSub in sqlResults:
            if not ek.ek(os.path.isfile, epToSub['location']):
                logger.log('Episode file does not exist, cannot download subtitles for episode %dx%d of show %s' % (epToSub['season'], epToSub['episode'], epToSub['show_name']), logger.DEBUG)
                continue
            
            # Old shows rule
            if ((epToSub['airdate_daydiff'] > 7 and epToSub['searchcount'] < 2 and now - datetime.datetime.strptime(epToSub['lastsearch'], '%Y-%m-%d %H:%M:%S') > datetime.timedelta(hours=rules['old'][epToSub['searchcount']])) or
                # Recent shows rule 
                (epToSub['airdate_daydiff'] <= 7 and epToSub['searchcount'] < 7 and now - datetime.datetime.strptime(epToSub['lastsearch'], '%Y-%m-%d %H:%M:%S') > datetime.timedelta(hours=rules['new'][epToSub['searchcount']]))):
                logger.log('Downloading subtitles for episode %dx%d of show %s' % (epToSub['season'], epToSub['episode'], epToSub['show_name']), logger.DEBUG)
                helpers.findCertainShow(sickbeard.showList, int(epToSub['showid'])).getEpisode(int(epToSub["season"]), int(epToSub["episode"])).downloadSubtitles()
            

    def _getRules(self):
        """
        Define the hours to wait between 2 subtitles search depending on:
        - the episode: new or old
        - the number of searches done so far (searchcount), represented by the index of the list
        """
        return {'old': [0, 24], 'new': [0, 4, 8, 4, 16, 24, 24]}
