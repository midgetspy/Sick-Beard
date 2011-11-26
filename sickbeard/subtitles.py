# Author: Antoine Bertin <diaoulael@gmail.com>
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
from sickbeard import logger
from sickbeard import helpers
from sickbeard import encodingKludge as ek
from sickbeard import db


try:
    import subliminal
    SUBLIMINAL_SUPPORT = True
except ImportError:
    SUBLIMINAL_SUPPORT = False

SINGLE = 'und'
def sortedPluginList():
    pluginsMapping = dict([(x.lower(), x) for x in subliminal.PLUGINS])

    newList = []

    # add all plugins in the priority list, in order
    curIndex = 0
    for curPlugin in sickbeard.SUBTITLES_PLUGINS_LIST:
        if curPlugin in pluginsMapping:
            curPluginDict = {'id': curPlugin, 'image': curPlugin+'.png', 'name': pluginsMapping[curPlugin], 'enabled': sickbeard.SUBTITLES_PLUGINS_ENABLED[curIndex] == 1,
                'api_based': pluginsMapping[curPlugin] in subliminal.API_PLUGINS, 'url': getattr(subliminal.plugins, pluginsMapping[curPlugin]).site_url}
            newList.append(curPluginDict)
        curIndex += 1

    # add any plugins that are missing from that list
    for curPlugin in pluginsMapping.keys():
        if curPlugin not in [x['id'] for x in newList]:
            curPluginDict = {'id': curPlugin, 'image': curPlugin+'.png', 'name': pluginsMapping[curPlugin], 'enabled': False,
                'api_based': pluginsMapping[curPlugin] in subliminal.API_PLUGINS, 'url': getattr(subliminal.plugins, pluginsMapping[curPlugin]).site_url}
            newList.append(curPluginDict)

    return newList
    
def getEnabledPluginList():
    return [x['name'] for x in sortedPluginList() if x['enabled']]
    
def isValidLanguage(language):
    return language in subliminal.languages.list_languages(1)

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
    video = subliminal.videos.Video.fromPath(video_path)
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
        if not SUBLIMINAL_SUPPORT or not sickbeard.USE_SUBTITLES:
            logger.log(u'No subtitles support of subtitles support disabled', logger.DEBUG)
            return
        if len(sickbeard.subtitles.getEnabledPluginList()) < 2:
            logger.log(u'Not enough plugins selected. At least 2 plugins are required to search subtitles in the background', logger.ERROR)
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
            if epToSub['airdate_daydiff'] > 7 and epToSub['searchcount'] < 2 and now - epToSub['lastsearch'] > datetime.timedelta(hours=rules['old'][epToSub['searchcount']]):
                logger.log('Downloading subtitles for episode %dx%d of show %s' % (epToSub['season'], epToSub['episode'], epToSub['show_name']), logger.DEBUG)
                locations.append(epToSub['location'])
                toRefresh.append((epToSub['showid'], epToSub['season'], epToSub['episode']))
                continue
            # Recent shows rule
            if epToSub['airdate_daydiff'] <= 7 and epToSub['searchcount'] < 7 and now - epToSub['lastsearch'] > datetime.timedelta(hours=rules['new'][epToSub['searchcount']]):
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
        with subliminal.Subliminal(cache_dir=sickbeard.CACHE_DIR, workers=2, multi=sickbeard.SUBTITLES_MULTI, force=False, max_depth=3,
                                   languages=sickbeard.SUBTITLES_LANGUAGES, plugins=sickbeard.subtitles.getEnabledPluginList()) as subli:
            subtitles = subli.downloadSubtitles(locations)
        for subtitle in subtitles:
            helpers.chmodAsParent(subtitle.path)
        if subtitles:
            logger.log('Downloaded %d subtitles' % len(subtitles), logger.MESSAGE)
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

