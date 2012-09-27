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

from lib import subliminal

SINGLE = 'und'
def sortedServiceList():
    servicesMapping = dict([(x.lower(), x) for x in subliminal.core.SERVICES])

    newList = []

    # add all services in the priority list, in order
    curIndex = 0
    for curService in sickbeard.SUBTITLES_SERVICES_LIST:
        if curService in servicesMapping:
            curServiceDict = {'id': curService, 'image': curService+'.png', 'name': servicesMapping[curService], 'enabled': sickbeard.SUBTITLES_SERVICES_ENABLED[curIndex] == 1, 'api_based': servicesMapping[curService] in subliminal.SERVICES, 'url': __import__('lib.subliminal.services.' + curService, globals=globals(), locals=locals(), fromlist=['Service'], level=-1).Service.site_url}
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
    for lang in subliminal.language.LANGUAGES:
        if selectLang == lang[0]:
            return lang[3]
    return 'Error'

def wantedLanguages(sqlLike = False):
    if sickbeard.SUBTITLES_MULTI:
        wantedLanguages = sorted(sickbeard.SUBTITLES_LANGUAGES)
    else:
        wantedLanguages = [SINGLE]
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
            languages.add(subtitle.language)
        else:
            languages.add(SINGLE)
    return list(languages)


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
        sqlResults = myDB.select('SELECT s.show_name, e.showid, e.season, e.episode, e.subtitles_searchcount AS searchcount, e.subtitles_lastsearch AS lastsearch, e.location, (? - e.airdate) AS airdate_daydiff FROM tv_episodes AS e INNER JOIN tv_shows AS s ON (e.showid = s.tvdb_id) WHERE s.subtitles = 1 AND e.subtitles NOT LIKE (?) AND ((e.subtitles_searchcount <= 2 AND (? - e.airdate) > 7) OR (e.subtitles_searchcount <= 7 AND (? - e.airdate) <= 7)) AND (e.status IN ('+','.join([str(x) for x in Quality.DOWNLOADED + [ARCHIVED]])+') OR (e.status IN ('+','.join([str(x) for x in Quality.SNATCHED + Quality.SNATCHED_PROPER])+') AND e.location != ""))', [today, wantedLanguages(True), today, today])
        locations = []
        toRefresh = []
        rules = self._getRules()
        now = datetime.datetime.now()
        for epToSub in sqlResults:
            if not ek.ek(os.path.isfile, epToSub['location']):
                logger.log('Episode file does not exist, cannot download subtitles for episode %dx%d of show %s' % (epToSub['season'], epToSub['episode'], epToSub['show_name']), logger.DEBUG)
                continue
            # Old shows rule
            if epToSub['airdate_daydiff'] > 7 and epToSub['searchcount'] < 2 and now - datetime.datetime.strptime(epToSub['lastsearch'], '%Y-%m-%d %H:%M:%S') > datetime.timedelta(hours=rules['old'][epToSub['searchcount']]):
                logger.log('Downloading subtitles for episode %dx%d of show %s' % (epToSub['season'], epToSub['episode'], epToSub['show_name']), logger.DEBUG)
                locations.append(epToSub['location'])
                toRefresh.append((epToSub['showid'], epToSub['season'], epToSub['episode']))
                continue
            # Recent shows rule
            if epToSub['airdate_daydiff'] <= 7 and epToSub['searchcount'] < 7 and now - datetime.datetime.strptime(epToSub['lastsearch'], '%Y-%m-%d %H:%M:%S') > datetime.timedelta(hours=rules['new'][epToSub['searchcount']]):
                logger.log('Downloading subtitles for episode %dx%d of show %s' % (epToSub['season'], epToSub['episode'], epToSub['show_name']), logger.DEBUG)
                locations.append(epToSub['location'])
                toRefresh.append((epToSub['showid'], epToSub['season'], epToSub['episode']))
                continue
            # Not matching my rules
            #logger.log('Do not match criteria to get downloaded: %s - %dx%d' % (epToSub['showid'], epToSub['season'], epToSub['episode']), logger.DEBUG)

        # stop here if we don't have subtitles to download
        if not locations:
            logger.log('No subtitles to download', logger.MESSAGE)
            return

        # download subtitles
        subtitles = subliminal.download_subtitles(locations, cache_dir=sickbeard.CACHE_DIR, multi=sickbeard.SUBTITLES_MULTI, languages=sickbeard.SUBTITLES_LANGUAGES, services=sickbeard.subtitles.getEnabledServiceList())

        if sickbeard.SUBTITLES_SUBDIR:
            for video in subtitles:
                subsDir = ek.ek(os.path.join, os.path.dirname(video.path), sickbeard.SUBTITLES_SUBDIR)
                if not ek.ek(os.path.isdir, subsDir):
                    ek.ek(os.mkdir, subsDir)
                
                for subtitle in subtitles.get(video):                    
                    new_file_path = ek.ek(os.path.join,subsDir, os.path.basename(subtitle.path))
                    helpers.moveFile(subtitle.path, new_file_path)

        if subtitles:
            logger.log('Downloaded %d subtitles' % len(subtitles), logger.MESSAGE)
            
            for video in subtitles:
                notifiers.notify_subtitle_download(self.makeEpFromFile(video.path).prettyName(True), ",".join([subtitle.language.alpha3 for subtitle in subtitles]))
        else:
            logger.log('No subtitles found', logger.MESSAGE)

        # refresh each show
        self._refreshShows(toRefresh, now)

    def _getRules(self):
        """
        Define the hours to wait between 2 subtitles search depending on:
        - the episode: new or old
        - the number of searches done so far (searchcount), represented by the index of the list
        """
        return {'old': [0, 24], 'new': [0, 4, 8, 16, 24, 24, 24]}

    def _refreshShows(self, toRefresh, now):
        """Refresh episodes with new subtitles"""
        for (showid, season, episode) in toRefresh:
            show = helpers.findCertainShow(sickbeard.showList, showid)
            episode = show.getEpisode(season, episode)
            episode.subtitles_searchcount = episode.subtitles_searchcount + 1
            episode.subtitles_lastsearch = now
            episode.refreshSubtitles()
            episode.saveToDB()

