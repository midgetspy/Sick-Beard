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

import os.path
import datetime
import threading
import re
import glob

import sickbeard

import xml.etree.cElementTree as etree

from name_parser.parser import NameParser, InvalidNameException

from lib.tvdb_api import tvdb_api, tvdb_exceptions

from sickbeard import db
from sickbeard import helpers, exceptions, logger
from sickbeard.exceptions import ex
from sickbeard import tvrage
from sickbeard import image_cache
from sickbeard import postProcessor

from sickbeard import encodingKludge as ek

from common import Quality, Overview, statusStrings
from common import DOWNLOADED, SNATCHED, SNATCHED_PROPER, ARCHIVED, IGNORED, UNAIRED, WANTED, SKIPPED, UNKNOWN
from common import NAMING_DUPLICATE, NAMING_EXTEND, NAMING_LIMITED_EXTEND, NAMING_SEPARATED_REPEAT, NAMING_LIMITED_EXTEND_E_PREFIXED


class TVShow(object):

    def __init__(self, tvdbid, lang=""):

        self.tvdbid = tvdbid

        self._location = ""
        self.name = ""
        self.tvrid = 0
        self.tvrname = ""
        self.network = ""
        self.genre = ""
        self.runtime = 0
        self.quality = int(sickbeard.QUALITY_DEFAULT)
        self.flatten_folders = int(sickbeard.FLATTEN_FOLDERS_DEFAULT)

        self.status = ""
        self.airs = ""
        self.startyear = 0
        self.paused = 0
        self.air_by_date = 0
        self.lang = lang
        self.last_update_tvdb = 1

        self.rls_ignore_words = ""
        self.rls_require_words = ""

        self.lock = threading.Lock()
        self._isDirGood = False

        self.episodes = {}

        otherShow = helpers.findCertainShow(sickbeard.showList, self.tvdbid)
        if otherShow != None:
            raise exceptions.MultipleShowObjectsException("Can't create a show if it already exists")

        self.loadFromDB()

    def _getLocation(self):
        # no dir check needed if missing show dirs are created during post-processing
        if sickbeard.CREATE_MISSING_SHOW_DIRS:
            return self._location

        if ek.ek(os.path.isdir, self._location):
            return self._location
        else:
            raise exceptions.ShowDirNotFoundException("Show folder doesn't exist, you shouldn't be using it")

        if self._isDirGood:
            return self._location
        else:
            raise exceptions.NoNFOException("Show folder doesn't exist, you shouldn't be using it")

    def _setLocation(self, newLocation):
        logger.log(u"Setter sets location to " + newLocation, logger.DEBUG)
        # Don't validate dir if user wants to add shows without creating a dir
        if sickbeard.ADD_SHOWS_WO_DIR or ek.ek(os.path.isdir, newLocation):
            self._location = newLocation
            self._isDirGood = True
        else:
            raise exceptions.NoNFOException("Invalid folder for the show!")

    location = property(_getLocation, _setLocation)

    # delete references to anything that's not in the internal lists
    def flushEpisodes(self):

        for curSeason in self.episodes:
            for curEp in self.episodes[curSeason]:
                myEp = self.episodes[curSeason][curEp]
                self.episodes[curSeason][curEp] = None
                del myEp

    def getAllEpisodes(self, season=None, has_location=False):

        myDB = db.DBConnection()

        sql_selection = "SELECT season, episode, "

        # subselection to detect multi-episodes early, share_location > 0
        sql_selection = sql_selection + " (SELECT COUNT (*) FROM tv_episodes WHERE showid = tve.showid AND season = tve.season AND location != '' AND location = tve.location AND episode != tve.episode) AS share_location "

        sql_selection = sql_selection + " FROM tv_episodes tve WHERE showid = " + str(self.tvdbid)

        if season is not None:
            sql_selection = sql_selection + " AND season = " + str(season)
        if has_location:
            sql_selection = sql_selection + " AND location != '' "

        # need ORDER episode ASC to rename multi-episodes in order S01E01-02
        sql_selection = sql_selection + " ORDER BY season ASC, episode ASC"

        results = myDB.select(sql_selection)

        ep_list = []
        for cur_result in results:
            cur_ep = self.getEpisode(int(cur_result["season"]), int(cur_result["episode"]))
            if cur_ep:
                cur_ep.relatedEps = []
                if cur_ep.location:
                    # if there is a location, check if it's a multi-episode (share_location > 0) and put them in relatedEps
                    if cur_result["share_location"] > 0:
                        related_eps_result = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND season = ? AND location = ? AND episode != ? ORDER BY episode ASC", [self.tvdbid, cur_ep.season, cur_ep.location, cur_ep.episode])
                        for cur_related_ep in related_eps_result:
                            related_ep = self.getEpisode(int(cur_related_ep["season"]), int(cur_related_ep["episode"]))
                            if related_ep not in cur_ep.relatedEps:
                                cur_ep.relatedEps.append(related_ep)
                ep_list.append(cur_ep)

        return ep_list

    def getEpisode(self, season, episode, file=None, noCreate=False):

        #return TVEpisode(self, season, episode)

        if not season in self.episodes:
            self.episodes[season] = {}

        ep = None

        if not episode in self.episodes[season] or self.episodes[season][episode] == None:
            if noCreate:
                return None

            logger.log(str(self.tvdbid) + u": An object for episode " + str(season) + "x" + str(episode) + " didn't exist in the cache, trying to create it", logger.DEBUG)

            if file != None:
                ep = TVEpisode(self, season, episode, file)
            else:
                ep = TVEpisode(self, season, episode)

            if ep != None:
                self.episodes[season][episode] = ep

        return self.episodes[season][episode]

    def should_update(self, update_date=datetime.date.today()):

        # if show is not 'Ended' always update (status 'Continuing' or '')
        if self.status != 'Ended':
            return True

        # run logic against the current show latest aired and next unaired data to see if we should bypass 'Ended' status
        cur_tvdbid = self.tvdbid

        graceperiod = datetime.timedelta(days=30)

        myDB = db.DBConnection()
        last_airdate = datetime.date.fromordinal(1)

        # get latest aired episode to compare against today - graceperiod and today + graceperiod
        sql_result = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND season > '0' AND airdate > '1' AND status > '1' ORDER BY airdate DESC LIMIT 1", [cur_tvdbid])

        if sql_result:
            last_airdate = datetime.date.fromordinal(sql_result[0]['airdate'])
            if last_airdate >= (update_date - graceperiod) and last_airdate <= (update_date + graceperiod):
                return True

        # get next upcoming UNAIRED episode to compare against today + graceperiod
        sql_result = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND season > '0' AND airdate > '1' AND status = '1' ORDER BY airdate ASC LIMIT 1", [cur_tvdbid])

        if sql_result:
            next_airdate = datetime.date.fromordinal(sql_result[0]['airdate'])
            if next_airdate <= (update_date + graceperiod):
                return True

        last_update_tvdb = datetime.date.fromordinal(self.last_update_tvdb)

        # in the first year after ended (last airdate), update every 30 days
        if (update_date - last_airdate) < datetime.timedelta(days=450) and (update_date - last_update_tvdb) > datetime.timedelta(days=30):
            return True

        return False

    def writeShowNFO(self):

        result = False

        if not ek.ek(os.path.isdir, self._location):
            logger.log(str(self.tvdbid) + u": Show dir doesn't exist, skipping NFO generation")
            return False

        logger.log(str(self.tvdbid) + u": Writing NFOs for show")
        for cur_provider in sickbeard.metadata_provider_dict.values():
            result = cur_provider.create_show_metadata(self) or result

        return result

    def writeMetadata(self, show_only=False):

        if not ek.ek(os.path.isdir, self._location):
            logger.log(str(self.tvdbid) + u": Show dir doesn't exist, skipping NFO generation")
            return

        self.getImages()

        self.writeShowNFO()

        if not show_only:
            self.writeEpisodeNFOs()

    def writeEpisodeNFOs(self):

        if not ek.ek(os.path.isdir, self._location):
            logger.log(str(self.tvdbid) + u": Show dir doesn't exist, skipping NFO generation")
            return

        logger.log(str(self.tvdbid) + u": Writing NFOs for all episodes")

        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND location != ''", [self.tvdbid])

        for epResult in sqlResults:
            logger.log(str(self.tvdbid) + u": Retrieving/creating episode " + str(epResult["season"]) + u"x" + str(epResult["episode"]), logger.DEBUG)
            curEp = self.getEpisode(epResult["season"], epResult["episode"])
            curEp.createMetaFiles()

    # find all media files in the show folder and create episodes for as many as possible
    def loadEpisodesFromDir(self):

        if not ek.ek(os.path.isdir, self._location):
            logger.log(str(self.tvdbid) + u": Show dir doesn't exist, not loading episodes from disk")
            return

        logger.log(str(self.tvdbid) + u": Loading all episodes from the show directory " + self._location)

        # get file list
        mediaFiles = helpers.listMediaFiles(self._location)

        # create TVEpisodes from each media file (if possible)
        for mediaFile in mediaFiles:

            curEpisode = None

            logger.log(str(self.tvdbid) + u": Creating episode from " + mediaFile, logger.DEBUG)
            try:
                curEpisode = self.makeEpFromFile(ek.ek(os.path.join, self._location, mediaFile))
            except (exceptions.ShowNotFoundException, exceptions.EpisodeNotFoundException), e:
                logger.log(u"Episode " + mediaFile + " returned an exception: " + ex(e), logger.ERROR)
                continue
            except exceptions.EpisodeDeletedException:
                logger.log(u"The episode deleted itself when I tried making an object for it", logger.DEBUG)

            if curEpisode is None:
                continue

            if not curEpisode.release_name:
                ep_file_name = ek.ek(os.path.basename, curEpisode.location)
                ep_base_name = helpers.remove_non_release_groups(helpers.remove_extension(ep_file_name))

                parse_result = None
                try:
                    np = NameParser(False)
                    parse_result = np.parse(ep_base_name)
                except InvalidNameException:
                    pass

                if not ' ' in ep_base_name and parse_result and parse_result.release_group:
                    logger.log(u"Name " + ep_base_name + u" gave release group of " + parse_result.release_group + ", seems valid", logger.DEBUG)
                    curEpisode.release_name = ep_base_name

            # store the reference in the show
            if curEpisode != None:
                curEpisode.saveToDB()

    def loadEpisodesFromDB(self):

        logger.log(u"Loading all episodes from the DB")

        myDB = db.DBConnection()
        sql = "SELECT * FROM tv_episodes WHERE showid = ?"
        sqlResults = myDB.select(sql, [self.tvdbid])

        scannedEps = {}

        ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

        if self.lang:
            ltvdb_api_parms['language'] = self.lang

        t = tvdb_api.Tvdb(**ltvdb_api_parms)

        cachedShow = t[self.tvdbid]
        cachedSeasons = {}

        for curResult in sqlResults:

            deleteEp = False

            curSeason = int(curResult["season"])
            curEpisode = int(curResult["episode"])
            if curSeason not in cachedSeasons:
                try:
                    cachedSeasons[curSeason] = cachedShow[curSeason]
                except tvdb_exceptions.tvdb_seasonnotfound, e:
                    logger.log(u"Error when trying to load the episode from TVDB: " + e.message, logger.WARNING)
                    deleteEp = True

            if not curSeason in scannedEps:
                scannedEps[curSeason] = {}

            logger.log(u"Loading episode " + str(curSeason) + "x" + str(curEpisode) + " from the DB", logger.DEBUG)

            try:
                curEp = self.getEpisode(curSeason, curEpisode)

                # if we found out that the ep is no longer on TVDB then delete it from our database too
                if deleteEp:
                    curEp.deleteEpisode()

                curEp.loadFromDB(curSeason, curEpisode)
                curEp.loadFromTVDB(tvapi=t, cachedSeason=cachedSeasons[curSeason])
                scannedEps[curSeason][curEpisode] = True
            except exceptions.EpisodeDeletedException:
                logger.log(u"Tried loading an episode from the DB that should have been deleted, skipping it", logger.DEBUG)
                continue

        return scannedEps

    def loadEpisodesFromTVDB(self, cache=True):

        # There's gotta be a better way of doing this but we don't wanna
        # change the cache value elsewhere
        ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

        if not cache:
            ltvdb_api_parms['cache'] = False

        if self.lang:
            ltvdb_api_parms['language'] = self.lang

        try:
            t = tvdb_api.Tvdb(**ltvdb_api_parms)
            showObj = t[self.tvdbid]
        except tvdb_exceptions.tvdb_error:
            logger.log(u"TVDB timed out, unable to update episodes from TVDB", logger.ERROR)
            return None

        logger.log(str(self.tvdbid) + u": Loading all episodes from theTVDB...")

        scannedEps = {}

        for season in showObj:
            scannedEps[season] = {}
            for episode in showObj[season]:
                # need some examples of wtf episode 0 means to decide if we want it or not
                if episode == 0:
                    continue
                try:
                    #ep = TVEpisode(self, season, episode)
                    ep = self.getEpisode(season, episode)
                except exceptions.EpisodeNotFoundException:
                    logger.log(str(self.tvdbid) + u": TVDB object for " + str(season) + "x" + str(episode) + " is incomplete, skipping this episode")
                    continue
                else:
                    try:
                        ep.loadFromTVDB(tvapi=t)
                    except exceptions.EpisodeDeletedException:
                        logger.log(u"The episode was deleted, skipping the rest of the load")
                        continue

                with ep.lock:
                    logger.log(str(self.tvdbid) + u": Loading info from theTVDB for episode " + str(season) + "x" + str(episode), logger.DEBUG)
                    ep.loadFromTVDB(season, episode, tvapi=t)
                    if ep.dirty:
                        ep.saveToDB()

                scannedEps[season][episode] = True

        # Done updating save last update date
        self.last_update_tvdb = datetime.date.today().toordinal()
        self.saveToDB()

        return scannedEps

    def setTVRID(self, force=False):

        if self.tvrid != 0 and not force:
            logger.log(u"No need to get the TVRage ID, it's already populated", logger.DEBUG)
            return

        logger.log(u"Attempting to retrieve the TVRage ID", logger.DEBUG)

        try:
            # load the tvrage object, it will set the ID in its constructor if possible
            tvrage.TVRage(self)
            self.saveToDB()
        except exceptions.TVRageException, e:
            logger.log(u"Couldn't get TVRage ID because we're unable to sync TVDB and TVRage: " + ex(e), logger.DEBUG)
            return

    def getImages(self, fanart=None, poster=None):
        fanart_result = poster_result = banner_result = False
        season_posters_result = season_banners_result = season_all_poster_result = season_all_banner_result = False

        for cur_provider in sickbeard.metadata_provider_dict.values():
            # FIXME: Needs to not show this message if the option is not enabled?
            logger.log(u"Running metadata routines for " + cur_provider.name, logger.DEBUG)

            fanart_result = cur_provider.create_fanart(self) or fanart_result
            poster_result = cur_provider.create_poster(self) or poster_result
            banner_result = cur_provider.create_banner(self) or banner_result

            season_posters_result = cur_provider.create_season_posters(self) or season_posters_result
            season_banners_result = cur_provider.create_season_banners(self) or season_banners_result
            season_all_poster_result = cur_provider.create_season_all_poster(self) or season_all_poster_result
            season_all_banner_result = cur_provider.create_season_all_banner(self) or season_all_banner_result

        return fanart_result or poster_result or banner_result or season_posters_result or season_banners_result or season_all_poster_result or season_all_banner_result

    def loadLatestFromTVRage(self):

        try:
            # load the tvrage object
            tvr = tvrage.TVRage(self)

            newEp = tvr.findLatestEp()

            if newEp != None:
                logger.log(u"TVRage gave us an episode object - saving it for now", logger.DEBUG)
                newEp.saveToDB()

            # make an episode out of it
        except exceptions.TVRageException, e:
            logger.log(u"Unable to add TVRage info: " + ex(e), logger.WARNING)

    # make a TVEpisode object from a media file
    def makeEpFromFile(self, file):

        if not ek.ek(os.path.isfile, file):
            logger.log(str(self.tvdbid) + u": That isn't even a real file dude... " + file)
            return None

        logger.log(str(self.tvdbid) + u": Creating episode object from " + file, logger.DEBUG)

        try:
            myParser = NameParser()
            parse_result = myParser.parse(file)
        except InvalidNameException:
            logger.log(u"Unable to parse the filename " + file + " into a valid episode", logger.ERROR)
            return None

        if len(parse_result.episode_numbers) == 0 and not parse_result.air_by_date:
            logger.log(u"parse_result: " + str(parse_result))
            logger.log(u"No episode number found in " + file + ", ignoring it", logger.ERROR)
            return None

        # for now lets assume that any episode in the show dir belongs to that show
        season = parse_result.season_number if parse_result.season_number != None else 1
        episodes = parse_result.episode_numbers
        rootEp = None

        # if we have an air-by-date show then get the real season/episode numbers
        if parse_result.air_by_date:
            try:
                # There's gotta be a better way of doing this but we don't wanna
                # change the cache value elsewhere
                ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

                if self.lang:
                    ltvdb_api_parms['language'] = self.lang

                t = tvdb_api.Tvdb(**ltvdb_api_parms)

                epObj = t[self.tvdbid].airedOn(parse_result.air_date)[0]
                season = int(epObj["seasonnumber"])
                episodes = [int(epObj["episodenumber"])]
            except tvdb_exceptions.tvdb_episodenotfound:
                logger.log(u"Unable to find episode with date " + str(parse_result.air_date) + " for show " + self.name + ", skipping", logger.WARNING)
                return None
            except tvdb_exceptions.tvdb_error, e:
                logger.log(u"Unable to contact TVDB: " + ex(e), logger.WARNING)
                return None

        for curEpNum in episodes:

            episode = int(curEpNum)

            logger.log(str(self.tvdbid) + u": " + file + " parsed to " + self.name + " " + str(season) + "x" + str(episode), logger.DEBUG)

            checkQualityAgain = False
            same_file = False
            curEp = self.getEpisode(season, episode)

            if curEp == None:
                try:
                    curEp = self.getEpisode(season, episode, file)
                except exceptions.EpisodeNotFoundException:
                    logger.log(str(self.tvdbid) + u": Unable to figure out what this file is, skipping", logger.ERROR)
                    continue

            else:
                # if there is a new file associated with this ep then re-check the quality
                if curEp.location and ek.ek(os.path.normpath, curEp.location) != ek.ek(os.path.normpath, file):
                    logger.log(u"The old episode had a different file associated with it, I will re-check the quality based on the new filename " + file, logger.DEBUG)
                    checkQualityAgain = True

                with curEp.lock:
                    old_size = curEp.file_size
                    curEp.location = file
                    # if the sizes are the same then it's probably the same file
                    if old_size and curEp.file_size == old_size:
                        same_file = True
                    else:
                        same_file = False

                    curEp.checkForMetaFiles()

            if rootEp == None:
                rootEp = curEp
            else:
                if curEp not in rootEp.relatedEps:
                    rootEp.relatedEps.append(curEp)

            # if it's a new file then
            if not same_file:
                curEp.release_name = ''

            # if they replace a file on me I'll make some attempt at re-checking the quality unless I know it's the same file
            if checkQualityAgain and not same_file:
                newQuality = Quality.nameQuality(file)
                logger.log(u"Since this file has been renamed, I checked " + file + " and found quality " + Quality.qualityStrings[newQuality], logger.DEBUG)
                if newQuality != Quality.UNKNOWN:
                    curEp.status = Quality.compositeStatus(DOWNLOADED, newQuality)

            # check for status/quality changes as long as it's a new file
            elif not same_file and sickbeard.helpers.isMediaFile(file) and curEp.status not in Quality.DOWNLOADED + [ARCHIVED, IGNORED]:

                oldStatus, oldQuality = Quality.splitCompositeStatus(curEp.status)
                newQuality = Quality.nameQuality(file)
                if newQuality == Quality.UNKNOWN:
                    newQuality = Quality.assumeQuality(file)

                newStatus = None

                # if it was snatched and now exists then set the status correctly
                if oldStatus == SNATCHED and oldQuality <= newQuality:
                    logger.log(u"STATUS: this ep used to be snatched with quality " + Quality.qualityStrings[oldQuality] + " but a file exists with quality " + Quality.qualityStrings[newQuality] + " so I'm setting the status to DOWNLOADED", logger.DEBUG)
                    newStatus = DOWNLOADED

                # if it was snatched proper and we found a higher quality one then allow the status change
                elif oldStatus == SNATCHED_PROPER and oldQuality < newQuality:
                    logger.log(u"STATUS: this ep used to be snatched proper with quality " + Quality.qualityStrings[oldQuality] + " but a file exists with quality " + Quality.qualityStrings[newQuality] + " so I'm setting the status to DOWNLOADED", logger.DEBUG)
                    newStatus = DOWNLOADED

                elif oldStatus not in (SNATCHED, SNATCHED_PROPER):
                    newStatus = DOWNLOADED

                if newStatus != None:
                    with curEp.lock:
                        logger.log(u"STATUS: we have an associated file, so setting the status from " + str(curEp.status) + " to DOWNLOADED/" + str(Quality.statusFromName(file)), logger.DEBUG)
                        curEp.status = Quality.compositeStatus(newStatus, newQuality)

            with curEp.lock:
                curEp.saveToDB()

        return rootEp

    def loadFromDB(self, skipNFO=False):

        logger.log(str(self.tvdbid) + u": Loading show info from database")

        myDB = db.DBConnection()

        sqlResults = myDB.select("SELECT * FROM tv_shows WHERE tvdb_id = ?", [self.tvdbid])

        if len(sqlResults) > 1:
            raise exceptions.MultipleDBShowsException()
        elif len(sqlResults) == 0:
            logger.log(str(self.tvdbid) + u": Unable to find the show in the database")
            return
        else:
            if self.name == "":
                self.name = sqlResults[0]["show_name"]
            self.tvrname = sqlResults[0]["tvr_name"]
            if self.network == "":
                self.network = sqlResults[0]["network"]
            if self.genre == "":
                self.genre = sqlResults[0]["genre"]

            self.runtime = sqlResults[0]["runtime"]

            self.status = sqlResults[0]["status"]
            if self.status == None:
                self.status = ""
            self.airs = sqlResults[0]["airs"]
            if self.airs == None:
                self.airs = ""
            self.startyear = sqlResults[0]["startyear"]
            if self.startyear == None:
                self.startyear = 0

            self.air_by_date = sqlResults[0]["air_by_date"]
            if self.air_by_date == None:
                self.air_by_date = 0

            self.quality = int(sqlResults[0]["quality"])
            self.flatten_folders = int(sqlResults[0]["flatten_folders"])
            self.paused = int(sqlResults[0]["paused"])

            self._location = sqlResults[0]["location"]

            if self.tvrid == 0:
                self.tvrid = int(sqlResults[0]["tvr_id"])

            if self.lang == "":
                self.lang = sqlResults[0]["lang"]

            self.last_update_tvdb = sqlResults[0]["last_update_tvdb"]

            self.rls_ignore_words = sqlResults[0]["rls_ignore_words"]
            self.rls_require_words = sqlResults[0]["rls_require_words"]

    def loadFromTVDB(self, cache=True, tvapi=None, cachedSeason=None):

        logger.log(str(self.tvdbid) + u": Loading show info from theTVDB")

        # There's gotta be a better way of doing this but we don't wanna
        # change the cache value elsewhere
        if tvapi is None:
            ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

            if not cache:
                ltvdb_api_parms['cache'] = False

            if self.lang:
                ltvdb_api_parms['language'] = self.lang

            t = tvdb_api.Tvdb(**ltvdb_api_parms)

        else:
            t = tvapi

        myEp = t[self.tvdbid]

        try:
            self.name = myEp["seriesname"].strip()
        except AttributeError:
            raise tvdb_exceptions.tvdb_attributenotfound("Found %s, but attribute 'seriesname' was empty." % (self.tvdbid))

        self.genre = myEp['genre']
        self.network = myEp['network']

        if myEp["airs_dayofweek"] != None and myEp["airs_time"] != None:
            self.airs = myEp["airs_dayofweek"] + " " + myEp["airs_time"]

        if myEp["firstaired"] != None and myEp["firstaired"]:
            self.startyear = int(myEp["firstaired"].split('-')[0])

        if self.airs == None:
            self.airs = ""

        if myEp["status"] != None:
            self.status = myEp["status"]

        if self.status == None:
            self.status = ""

        self.saveToDB()

    def nextEpisode(self):

        logger.log(str(self.tvdbid) + u": Finding the episode which airs next", logger.DEBUG)

        myDB = db.DBConnection()
        innerQuery = "SELECT airdate FROM tv_episodes WHERE showid = ? AND airdate >= ? AND status = ? ORDER BY airdate ASC LIMIT 1"
        innerParams = [self.tvdbid, datetime.date.today().toordinal(), UNAIRED]
        query = "SELECT * FROM tv_episodes WHERE showid = ? AND airdate >= ? AND airdate <= (" + innerQuery + ") and status = ?"
        params = [self.tvdbid, datetime.date.today().toordinal()] + innerParams + [UNAIRED]
        sqlResults = myDB.select(query, params)

        if sqlResults == None or len(sqlResults) == 0:
            logger.log(str(self.tvdbid) + u": No episode found... need to implement tvrage and also show status", logger.DEBUG)
            return []
        else:
            logger.log(str(self.tvdbid) + u": Found episode " + str(sqlResults[0]["season"]) + "x" + str(sqlResults[0]["episode"]), logger.DEBUG)
            foundEps = []
            for sqlEp in sqlResults:
                curEp = self.getEpisode(int(sqlEp["season"]), int(sqlEp["episode"]))
                foundEps.append(curEp)
            return foundEps

        # if we didn't get an episode then try getting one from tvrage

        # load tvrage info

        # extract NextEpisode info

        # verify that we don't have it in the DB somehow (ep mismatch)

    def deleteShow(self):

        myDB = db.DBConnection()
        myDB.action("DELETE FROM tv_episodes WHERE showid = ?", [self.tvdbid])
        myDB.action("DELETE FROM tv_shows WHERE tvdb_id = ?", [self.tvdbid])

        # remove self from show list
        sickbeard.showList = [x for x in sickbeard.showList if x.tvdbid != self.tvdbid]

        # clear the cache
        image_cache_dir = ek.ek(os.path.join, sickbeard.CACHE_DIR, 'images')
        for cache_file in ek.ek(glob.glob, ek.ek(os.path.join, image_cache_dir, str(self.tvdbid) + '.*')):
            logger.log(u"Deleting cache file " + cache_file)
            os.remove(cache_file)

    def populateCache(self):
        cache_inst = image_cache.ImageCache()

        logger.log(u"Checking & filling cache for show " + self.name)
        cache_inst.fill_cache(self)

    def refreshDir(self):

        # make sure the show dir is where we think it is unless dirs are created on the fly
        if not ek.ek(os.path.isdir, self._location) and not sickbeard.CREATE_MISSING_SHOW_DIRS:
            return False

        # load from dir
        self.loadEpisodesFromDir()

        # run through all locations from DB, check that they exist
        logger.log(str(self.tvdbid) + u": Loading all episodes with a location from the database")

        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND location != ''", [self.tvdbid])

        for ep in sqlResults:
            curLoc = os.path.normpath(ep["location"])
            season = int(ep["season"])
            episode = int(ep["episode"])

            try:
                curEp = self.getEpisode(season, episode)
            except exceptions.EpisodeDeletedException:
                logger.log(u"The episode was deleted while we were refreshing it, moving on to the next one", logger.DEBUG)
                continue

            # if the path doesn't exist or if it's not in our show dir
            if not ek.ek(os.path.isfile, curLoc) or not os.path.normpath(curLoc).startswith(os.path.normpath(self.location)):

                with curEp.lock:
                    # if it used to have a file associated with it and it doesn't anymore then set it to IGNORED
                    if curEp.location and curEp.status in Quality.DOWNLOADED:
                        logger.log(str(self.tvdbid) + u": Location for " + str(season) + "x" + str(episode) + " doesn't exist, removing it and changing our status to IGNORED", logger.DEBUG)
                        curEp.status = IGNORED
                    curEp.location = ''
                    curEp.hasnfo = False
                    curEp.hastbn = False
                    curEp.release_name = ''
                    curEp.saveToDB()

    def saveToDB(self):

        logger.log(str(self.tvdbid) + u": Saving show info to database", logger.DEBUG)

        myDB = db.DBConnection()

        controlValueDict = {"tvdb_id": self.tvdbid}
        newValueDict = {"show_name": self.name,
                        "tvr_id": self.tvrid,
                        "location": self._location,
                        "network": self.network,
                        "genre": self.genre,
                        "runtime": self.runtime,
                        "quality": self.quality,
                        "airs": self.airs,
                        "status": self.status,
                        "flatten_folders": self.flatten_folders,
                        "paused": self.paused,
                        "air_by_date": self.air_by_date,
                        "startyear": self.startyear,
                        "tvr_name": self.tvrname,
                        "lang": self.lang,
                        "last_update_tvdb": self.last_update_tvdb,
                        "rls_ignore_words": self.rls_ignore_words,
                        "rls_require_words": self.rls_require_words
                        }

        myDB.upsert("tv_shows", newValueDict, controlValueDict)

    def __str__(self):
        toReturn = ""
        toReturn += "name: " + self.name + "\n"
        toReturn += "location: " + self._location + "\n"
        toReturn += "tvdbid: " + str(self.tvdbid) + "\n"
        if self.network != None:
            toReturn += "network: " + self.network + "\n"
        if self.airs != None:
            toReturn += "airs: " + self.airs + "\n"
        if self.status != None:
            toReturn += "status: " + self.status + "\n"
        toReturn += "startyear: " + str(self.startyear) + "\n"
        toReturn += "genre: " + self.genre + "\n"
        toReturn += "runtime: " + str(self.runtime) + "\n"
        toReturn += "quality: " + str(self.quality) + "\n"
        return toReturn

    def wantEpisode(self, season, episode, quality, manualSearch=False):

        logger.log(u"Checking if found episode " + str(season) + "x" + str(episode) + " is wanted at quality " + Quality.qualityStrings[quality], logger.DEBUG)

        # if the quality isn't one we want under any circumstances then just say no
        anyQualities, bestQualities = Quality.splitQuality(self.quality)
        logger.log(u"any,best = " + str(anyQualities) + " " + str(bestQualities) + " and found " + str(quality), logger.DEBUG)

        if quality not in anyQualities + bestQualities:
            logger.log(u"Don't want this quality, ignoring found episode", logger.DEBUG)
            return False

        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT status FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?", [self.tvdbid, season, episode])

        if not sqlResults or not len(sqlResults):
            logger.log(u"Unable to find a matching episode in database, ignoring found episode", logger.DEBUG)
            return False

        epStatus = int(sqlResults[0]["status"])
        epStatus_text = statusStrings[epStatus]

        logger.log(u"Existing episode status: " + str(epStatus) + " (" + epStatus_text + ")", logger.DEBUG)

        # if we know we don't want it then just say no
        if epStatus in (SKIPPED, IGNORED, ARCHIVED) and not manualSearch:
            logger.log(u"Existing episode status is skipped/ignored/archived, ignoring found episode", logger.DEBUG)
            return False

        # if it's one of these then we want it as long as it's in our allowed initial qualities
        if quality in anyQualities + bestQualities:
            if epStatus in (WANTED, UNAIRED, SKIPPED):
                logger.log(u"Existing episode status is wanted/unaired/skipped, getting found episode", logger.DEBUG)
                return True
            elif manualSearch:
                logger.log(u"Usually ignoring found episode, but forced search allows the quality, getting found episode", logger.DEBUG)
                return True
            else:
                logger.log(u"Quality is on wanted list, need to check if it's better than existing quality", logger.DEBUG)

        curStatus, curQuality = Quality.splitCompositeStatus(epStatus)

        # if we are re-downloading then we only want it if it's in our bestQualities list and better than what we have
        if curStatus in Quality.DOWNLOADED + Quality.SNATCHED + Quality.SNATCHED_PROPER and quality in bestQualities and quality > curQuality:
            logger.log(u"Episode already exists but the found episode has better quality, getting found episode", logger.DEBUG)
            return True
        else:
            logger.log(u"Episode already exists and the found episode has same/lower quality, ignoring found episode", logger.DEBUG)

        logger.log(u"None of the conditions were met, ignoring found episode", logger.DEBUG)
        return False

    def getOverview(self, epStatus):

        if epStatus == WANTED:
            return Overview.WANTED
        elif epStatus in (UNAIRED, UNKNOWN):
            return Overview.UNAIRED
        elif epStatus in (SKIPPED, IGNORED):
            return Overview.SKIPPED
        elif epStatus == ARCHIVED:
            return Overview.GOOD
        elif epStatus in Quality.DOWNLOADED + Quality.SNATCHED + Quality.SNATCHED_PROPER:

            anyQualities, bestQualities = Quality.splitQuality(self.quality)  # @UnusedVariable
            if bestQualities:
                maxBestQuality = max(bestQualities)
            else:
                maxBestQuality = None

            epStatus, curQuality = Quality.splitCompositeStatus(epStatus)

            if epStatus in (SNATCHED, SNATCHED_PROPER):
                return Overview.SNATCHED
            # if they don't want re-downloads then we call it good if they have anything
            elif maxBestQuality == None:
                return Overview.GOOD
            # if they have one but it's not the best they want then mark it as qual
            elif curQuality < maxBestQuality:
                return Overview.QUAL
            # if it's >= maxBestQuality then it's good
            else:
                return Overview.GOOD


def dirty_setter(attr_name):
    def wrapper(self, val):
        if getattr(self, attr_name) != val:
            setattr(self, attr_name, val)
            self.dirty = True
    return wrapper


class TVEpisode(object):

    def __init__(self, show, season, episode, file=""):

        self._name = ""
        self._season = season
        self._episode = episode
        self._description = ""
        self._airdate = datetime.date.fromordinal(1)
        self._hasnfo = False
        self._hastbn = False
        self._status = UNKNOWN
        self._tvdbid = 0
        self._file_size = 0
        self._release_name = ''

        # setting any of the above sets the dirty flag
        self.dirty = True

        self.show = show
        self._location = file

        self.lock = threading.Lock()

        self.specifyEpisode(self.season, self.episode)

        self.relatedEps = []

        self.checkForMetaFiles()

    name = property(lambda self: self._name, dirty_setter("_name"))
    season = property(lambda self: self._season, dirty_setter("_season"))
    episode = property(lambda self: self._episode, dirty_setter("_episode"))
    description = property(lambda self: self._description, dirty_setter("_description"))
    airdate = property(lambda self: self._airdate, dirty_setter("_airdate"))
    hasnfo = property(lambda self: self._hasnfo, dirty_setter("_hasnfo"))
    hastbn = property(lambda self: self._hastbn, dirty_setter("_hastbn"))
    status = property(lambda self: self._status, dirty_setter("_status"))
    tvdbid = property(lambda self: self._tvdbid, dirty_setter("_tvdbid"))
    #location = property(lambda self: self._location, dirty_setter("_location"))
    file_size = property(lambda self: self._file_size, dirty_setter("_file_size"))
    release_name = property(lambda self: self._release_name, dirty_setter("_release_name"))

    def _set_location(self, new_location):
        logger.log(u"Setter sets location to " + new_location, logger.DEBUG)

        #self._location = newLocation
        dirty_setter("_location")(self, new_location)

        if new_location and ek.ek(os.path.isfile, new_location):
            self.file_size = ek.ek(os.path.getsize, new_location)
        else:
            self.file_size = 0

    location = property(lambda self: self._location, _set_location)

    def checkForMetaFiles(self):

        oldhasnfo = self.hasnfo
        oldhastbn = self.hastbn

        cur_nfo = False
        cur_tbn = False

        # check for nfo and tbn
        if ek.ek(os.path.isfile, self.location):
            for cur_provider in sickbeard.metadata_provider_dict.values():
                if cur_provider.episode_metadata:
                    new_result = cur_provider._has_episode_metadata(self)
                else:
                    new_result = False
                cur_nfo = new_result or cur_nfo

                if cur_provider.episode_thumbnails:
                    new_result = cur_provider._has_episode_thumb(self)
                else:
                    new_result = False
                cur_tbn = new_result or cur_tbn

        self.hasnfo = cur_nfo
        self.hastbn = cur_tbn

        # if either setting has changed return true, if not return false
        return oldhasnfo != self.hasnfo or oldhastbn != self.hastbn

    def specifyEpisode(self, season, episode):

        sqlResult = self.loadFromDB(season, episode)

        if not sqlResult:
            # only load from NFO if we didn't load from DB
            if ek.ek(os.path.isfile, self.location):
                try:
                    self.loadFromNFO(self.location)
                except exceptions.NoNFOException:
                    logger.log(str(self.show.tvdbid) + u": There was an error loading the NFO for episode " + str(season) + "x" + str(episode), logger.ERROR)
                    pass

                # if we tried loading it from NFO and didn't find the NFO, use TVDB
                if self.hasnfo == False:
                    try:
                        result = self.loadFromTVDB(season, episode)
                    except exceptions.EpisodeDeletedException:
                        result = False

                    # if we failed SQL *and* NFO, TVDB then fail
                    if result == False:
                        raise exceptions.EpisodeNotFoundException("Couldn't find episode " + str(season) + "x" + str(episode))

        # don't update if not needed
        if self.dirty:
            self.saveToDB()

    def loadFromDB(self, season, episode):

        logger.log(str(self.show.tvdbid) + u": Loading episode details from DB for episode " + str(season) + "x" + str(episode), logger.DEBUG)

        myDB = db.DBConnection()
        sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?", [self.show.tvdbid, season, episode])

        if len(sqlResults) > 1:
            raise exceptions.MultipleDBEpisodesException("Your DB has two records for the same show somehow.")
        elif len(sqlResults) == 0:
            logger.log(str(self.show.tvdbid) + u": Episode " + str(self.season) + "x" + str(self.episode) + " not found in the database", logger.DEBUG)
            return False
        else:
            #NAMEIT logger.log(u"AAAAA from" + str(self.season)+"x"+str(self.episode) + " -" + self.name + " to " + str(sqlResults[0]["name"]))
            if sqlResults[0]["name"] != None:
                self.name = sqlResults[0]["name"]
            self.season = season
            self.episode = episode
            self.description = sqlResults[0]["description"]
            if self.description == None:
                self.description = ""
            self.airdate = datetime.date.fromordinal(int(sqlResults[0]["airdate"]))
            #logger.log(u"1 Status changes from " + str(self.status) + " to " + str(sqlResults[0]["status"]), logger.DEBUG)
            self.status = int(sqlResults[0]["status"])

            # don't overwrite my location
            if sqlResults[0]["location"] != "" and sqlResults[0]["location"] != None:
                self.location = os.path.normpath(sqlResults[0]["location"])
            if sqlResults[0]["file_size"]:
                self.file_size = int(sqlResults[0]["file_size"])
            else:
                self.file_size = 0

            self.tvdbid = int(sqlResults[0]["tvdbid"])

            if sqlResults[0]["release_name"] != None:
                self.release_name = sqlResults[0]["release_name"]

            self.dirty = False
            return True

    def loadFromTVDB(self, season=None, episode=None, cache=True, tvapi=None, cachedSeason=None):

        if season == None:
            season = self.season
        if episode == None:
            episode = self.episode

        logger.log(str(self.show.tvdbid) + u": Loading episode details from theTVDB for episode " + str(season) + "x" + str(episode), logger.DEBUG)

        tvdb_lang = self.show.lang

        try:
            if cachedSeason is None:
                if tvapi is None:
                    # There's gotta be a better way of doing this but we don't wanna
                    # change the cache value elsewhere
                    ltvdb_api_parms = sickbeard.TVDB_API_PARMS.copy()

                    if not cache:
                        ltvdb_api_parms['cache'] = False

                    if tvdb_lang:
                            ltvdb_api_parms['language'] = tvdb_lang

                    t = tvdb_api.Tvdb(**ltvdb_api_parms)
                else:
                    t = tvapi
                myEp = t[self.show.tvdbid][season][episode]
            else:
                myEp = cachedSeason[episode]

        except (tvdb_exceptions.tvdb_error, IOError), e:
            logger.log(u"TVDB threw up an error: " + ex(e), logger.DEBUG)
            # if the episode is already valid just log it, if not throw it up
            if self.name:
                logger.log(u"TVDB timed out but we have enough info from other sources, allowing the error", logger.DEBUG)
                return
            else:
                logger.log(u"TVDB timed out, unable to create the episode", logger.ERROR)
                return False
        except (tvdb_exceptions.tvdb_episodenotfound, tvdb_exceptions.tvdb_seasonnotfound):
            logger.log(u"Unable to find the episode on tvdb... has it been removed? Should I delete from db?", logger.DEBUG)
            # if I'm no longer on TVDB but I once was then delete myself from the DB
            if self.tvdbid != -1:
                self.deleteEpisode()
            return

        if not myEp["firstaired"] or myEp["firstaired"] == "0000-00-00":
            myEp["firstaired"] = str(datetime.date.fromordinal(1))

        if myEp["episodename"] == None or myEp["episodename"] == "":
            logger.log(u"This episode (" + self.show.name + " - " + str(season) + "x" + str(episode) + ") has no name on TVDB")
            # if I'm incomplete on TVDB but I once was complete then just delete myself from the DB for now
            if self.tvdbid != -1:
                self.deleteEpisode()
            return False

        #NAMEIT logger.log(u"BBBBBBBB from " + str(self.season)+"x"+str(self.episode) + " -" +self.name+" to "+myEp["episodename"])
        self.name = myEp["episodename"]
        self.season = season
        self.episode = episode
        tmp_description = myEp["overview"]
        if tmp_description == None:
            self.description = ""
        else:
            self.description = tmp_description
        rawAirdate = [int(x) for x in myEp["firstaired"].split("-")]
        try:
            self.airdate = datetime.date(rawAirdate[0], rawAirdate[1], rawAirdate[2])
        except ValueError:
            logger.log(u"Malformed air date retrieved from TVDB (" + self.show.name + " - " + str(season) + "x" + str(episode) + ")", logger.ERROR)
            # if I'm incomplete on TVDB but I once was complete then just delete myself from the DB for now
            if self.tvdbid != -1:
                self.deleteEpisode()
            return False

        #early conversion to int so that episode doesn't get marked dirty
        self.tvdbid = int(myEp["id"])

        # don't update show status if show dir is missing, unless it's missing on purpose
        if not ek.ek(os.path.isdir, self.show._location) and not sickbeard.CREATE_MISSING_SHOW_DIRS and not sickbeard.ADD_SHOWS_WO_DIR:
            logger.log(u"The show dir is missing, not bothering to change the episode statuses since it'd probably be invalid")
            return

        logger.log(str(self.show.tvdbid) + u": Setting status for " + str(season) + "x" + str(episode) + " based on status " + str(self.status) + " and existence of " + self.location, logger.DEBUG)

        # if we don't have the file
        if not ek.ek(os.path.isfile, self.location):

            # if it hasn't aired yet set the status to UNAIRED
            if self.airdate >= datetime.date.today() and self.status in [SKIPPED, UNAIRED, UNKNOWN, WANTED]:
                logger.log(u"Episode airs in the future, marking it " + str(UNAIRED), logger.DEBUG)
                self.status = UNAIRED

            # if there's no airdate then set it to skipped (and respect ignored)
            elif self.airdate == datetime.date.fromordinal(1):
                if self.status == IGNORED:
                    logger.log(u"Episode has no air date, but it's already marked as ignored", logger.DEBUG)
                else:
                    logger.log(u"Episode has no air date, automatically marking it skipped", logger.DEBUG)
                    self.status = SKIPPED

            # if we don't have the file and the airdate is in the past
            else:
                if self.status == UNAIRED:
                    self.status = WANTED

                # if we somehow are still UNKNOWN then just skip it
                elif self.status == UNKNOWN:
                    self.status = SKIPPED

                else:
                    logger.log(u"Not touching status because we have no ep file, the airdate is in the past, and the status is " + str(self.status), logger.DEBUG)

        # if we have a media file then it's downloaded
        elif sickbeard.helpers.isMediaFile(self.location):
            # leave propers alone, you have to either post-process them or manually change them back
            if self.status not in Quality.SNATCHED_PROPER + Quality.DOWNLOADED + Quality.SNATCHED + [ARCHIVED]:
                logger.log(u"5 Status changes from " + str(self.status) + " to " + str(Quality.statusFromName(self.location)), logger.DEBUG)
                self.status = Quality.statusFromName(self.location)

        # shouldn't get here probably
        else:
            logger.log(u"6 Status changes from " + str(self.status) + " to " + str(UNKNOWN), logger.DEBUG)
            self.status = UNKNOWN

        # hasnfo, hastbn, status?

    def loadFromNFO(self, location):

        if not ek.ek(os.path.isdir, self.show._location):
            logger.log(str(self.show.tvdbid) + u": The show dir is missing, not bothering to try loading the episode NFO")
            return

        logger.log(str(self.show.tvdbid) + u": Loading episode details from the NFO file associated with " + location, logger.DEBUG)

        self.location = location

        if self.location != "":

            if self.status == UNKNOWN:
                if sickbeard.helpers.isMediaFile(self.location):
                    logger.log(u"7 Status changes from " + str(self.status) + " to " + str(Quality.statusFromName(self.location)), logger.DEBUG)
                    self.status = Quality.statusFromName(self.location)

            nfoFile = sickbeard.helpers.replaceExtension(self.location, "nfo")
            logger.log(str(self.show.tvdbid) + u": Using NFO name " + nfoFile, logger.DEBUG)

            if ek.ek(os.path.isfile, nfoFile):
                try:
                    showXML = etree.ElementTree(file=nfoFile)
                except (SyntaxError, ValueError), e:
                    logger.log(u"Error loading the NFO, backing up the NFO and skipping for now: " + ex(e), logger.ERROR)  # TODO: figure out what's wrong and fix it
                    try:
                        ek.ek(os.rename, nfoFile, nfoFile + ".old")
                    except Exception, e:
                        logger.log(u"Failed to rename your episode's NFO file - you need to delete it or fix it: " + ex(e), logger.ERROR)
                    raise exceptions.NoNFOException("Error in NFO format")

                for epDetails in showXML.getiterator('episodedetails'):
                    if epDetails.findtext('season') == None or int(epDetails.findtext('season')) != self.season or \
                       epDetails.findtext('episode') == None or int(epDetails.findtext('episode')) != self.episode:
                        logger.log(str(self.show.tvdbid) + u": NFO has an <episodedetails> block for a different episode - wanted " + str(self.season) + "x" + str(self.episode) + " but got " + str(epDetails.findtext('season')) + "x" + str(epDetails.findtext('episode')), logger.DEBUG)
                        continue

                    if epDetails.findtext('title') == None or epDetails.findtext('aired') == None:
                        raise exceptions.NoNFOException("Error in NFO format (missing episode title or airdate)")

                    self.name = epDetails.findtext('title')
                    self.episode = int(epDetails.findtext('episode'))
                    self.season = int(epDetails.findtext('season'))

                    self.description = epDetails.findtext('plot')
                    if self.description == None:
                        self.description = ""

                    if epDetails.findtext('aired'):
                        rawAirdate = [int(x) for x in epDetails.findtext('aired').split("-")]
                        self.airdate = datetime.date(rawAirdate[0], rawAirdate[1], rawAirdate[2])
                    else:
                        self.airdate = datetime.date.fromordinal(1)

                    self.hasnfo = True
            else:
                self.hasnfo = False

            if ek.ek(os.path.isfile, sickbeard.helpers.replaceExtension(nfoFile, "tbn")):
                self.hastbn = True
            else:
                self.hastbn = False

    def __str__(self):

        toReturn = ""
        toReturn += str(self.show.name) + " - " + str(self.season) + "x" + str(self.episode) + " - " + str(self.name) + "\n"
        toReturn += "location: " + str(self.location) + "\n"
        toReturn += "description: " + str(self.description) + "\n"
        toReturn += "airdate: " + str(self.airdate.toordinal()) + " (" + str(self.airdate) + ")\n"
        toReturn += "hasnfo: " + str(self.hasnfo) + "\n"
        toReturn += "hastbn: " + str(self.hastbn) + "\n"
        toReturn += "status: " + str(self.status) + "\n"
        return toReturn

    def createMetaFiles(self, force=False):

        if not ek.ek(os.path.isdir, self.show._location):
            logger.log(str(self.show.tvdbid) + u": The show dir is missing, not bothering to try to create metadata")
            return

        self.createNFO(force)
        self.createThumbnail(force)

        if self.checkForMetaFiles():
            self.saveToDB()

    def createNFO(self, force=False):

        result = False

        for cur_provider in sickbeard.metadata_provider_dict.values():
            result = cur_provider.create_episode_metadata(self) or result

        return result

    def createThumbnail(self, force=False):

        result = False

        for cur_provider in sickbeard.metadata_provider_dict.values():
            result = cur_provider.create_episode_thumb(self) or result

        return result

    def deleteEpisode(self):

        logger.log(u"Deleting " + self.show.name + " " + str(self.season) + "x" + str(self.episode) + " from the DB", logger.DEBUG)

        # remove myself from the show dictionary
        if self.show.getEpisode(self.season, self.episode, noCreate=True) == self:
            logger.log(u"Removing myself from my show's list", logger.DEBUG)
            del self.show.episodes[self.season][self.episode]

        # delete myself from the DB
        logger.log(u"Deleting myself from the database", logger.DEBUG)
        myDB = db.DBConnection()
        sql = "DELETE FROM tv_episodes WHERE showid=" + str(self.show.tvdbid) + " AND season=" + str(self.season) + " AND episode=" + str(self.episode)
        myDB.action(sql)

        raise exceptions.EpisodeDeletedException()

    def saveToDB(self, forceSave=False):
        """
        Saves this episode to the database if any of its data has been changed since the last save.

        forceSave: If True it will save to the database even if no data has been changed since the
                    last save (aka if the record is not dirty).
        """

        if not self.dirty and not forceSave:
            logger.log(str(self.show.tvdbid) + u": Not saving episode to db - record is not dirty", logger.DEBUG)
            return

        logger.log(str(self.show.tvdbid) + u": Saving episode details to database", logger.DEBUG)

        logger.log(u"STATUS IS " + str(self.status), logger.DEBUG)

        myDB = db.DBConnection()
        newValueDict = {"tvdbid": self.tvdbid,
                        "name": self.name,
                        "description": self.description,
                        "airdate": self.airdate.toordinal(),
                        "hasnfo": self.hasnfo,
                        "hastbn": self.hastbn,
                        "status": self.status,
                        "location": self.location,
                        "file_size": self.file_size,
                        "release_name": self.release_name}
        controlValueDict = {"showid": self.show.tvdbid,
                            "season": self.season,
                            "episode": self.episode}

        # use a custom update/insert method to get the data into the DB
        myDB.upsert("tv_episodes", newValueDict, controlValueDict)

    def fullPath(self):
        if self.location == None or self.location == "":
            return None
        else:
            return ek.ek(os.path.join, self.show.location, self.location)

    def prettyName(self):
        """
        Returns the name of this episode in a "pretty" human-readable format. Used for logging
        and notifications and such.

        Returns: A string representing the episode's name and season/ep numbers
        """

        return self._format_pattern('%SN - %Sx%0E - %EN')

    def _ep_name(self):
        """
        Returns the name of the episode to use during renaming. Combines the names of related episodes.
        Eg. "Ep Name (1)" and "Ep Name (2)" becomes "Ep Name"
            "Ep Name" and "Other Ep Name" becomes "Ep Name & Other Ep Name"
        """

        multiNameRegex = "(.*) \(\d{1,2}\)"

        self.relatedEps = sorted(self.relatedEps, key=lambda x: x.episode)

        if len(self.relatedEps) == 0:
            goodName = self.name

        else:
            goodName = ''

            singleName = True
            curGoodName = None

            for curName in [self.name] + [x.name for x in self.relatedEps]:
                match = re.match(multiNameRegex, curName)
                if not match:
                    singleName = False
                    break

                if curGoodName == None:
                    curGoodName = match.group(1)
                elif curGoodName != match.group(1):
                    singleName = False
                    break

            if singleName:
                goodName = curGoodName
            else:
                goodName = self.name
                for relEp in self.relatedEps:
                    goodName += " & " + relEp.name

        return goodName

    def _replace_map(self):
        """
        Generates a replacement map for this episode which maps all possible custom naming patterns to the correct
        value for this episode.

        Returns: A dict with patterns as the keys and their replacement values as the values.
        """

        ep_name = self._ep_name()

        def dot(name):
            return helpers.sanitizeSceneName(name)

        def us(name):
            return re.sub('[ -]', '_', name)

        def release_name(name):
            if name:
                name = helpers.remove_non_release_groups(helpers.remove_extension(name))
            return name

        def release_group(name):

            if name:
                name = helpers.remove_non_release_groups(helpers.remove_extension(name))
            else:
                return ""

            np = NameParser(False)

            try:
                parse_result = np.parse(name)
            except InvalidNameException, e:
                logger.log(u"Unable to get parse release_group: " + ex(e), logger.DEBUG)
                return ""

            if not parse_result.release_group:
                return ""

            return parse_result.release_group

        epStatus, epQual = Quality.splitCompositeStatus(self.status)  # @UnusedVariable

        return {
                   '%SN': self.show.name,
                   '%S.N': dot(self.show.name),
                   '%S_N': us(self.show.name),
                   '%EN': ep_name,
                   '%E.N': dot(ep_name),
                   '%E_N': us(ep_name),
                   '%QN': Quality.qualityStrings[epQual],
                   '%Q.N': dot(Quality.qualityStrings[epQual]),
                   '%Q_N': us(Quality.qualityStrings[epQual]),
                   '%S': str(self.season),
                   '%0S': '%02d' % self.season,
                   '%E': str(self.episode),
                   '%0E': '%02d' % self.episode,
                   '%RN': release_name(self.release_name),
                   '%RG': release_group(self.release_name),
                   '%AD': str(self.airdate).replace('-', ' '),
                   '%A.D': str(self.airdate).replace('-', '.'),
                   '%A_D': us(str(self.airdate)),
                   '%A-D': str(self.airdate),
                   '%Y': str(self.airdate.year),
                   '%M': str(self.airdate.month),
                   '%D': str(self.airdate.day),
                   '%0M': '%02d' % self.airdate.month,
                   '%0D': '%02d' % self.airdate.day,
                   }

    def _format_string(self, pattern, replace_map):
        """
        Replaces all template strings with the correct value
        """

        result_name = pattern

        # do the replacements
        for cur_replacement in sorted(replace_map.keys(), reverse=True):
            result_name = result_name.replace(cur_replacement, helpers.sanitizeFileName(replace_map[cur_replacement]))
            result_name = result_name.replace(cur_replacement.lower(), helpers.sanitizeFileName(replace_map[cur_replacement].lower()))

        return result_name

    def _format_pattern(self, pattern=None, multi=None):
        """
        Manipulates an episode naming pattern and then fills the template in
        """

        if pattern == None:
            pattern = sickbeard.NAMING_PATTERN

        if multi == None:
            multi = sickbeard.NAMING_MULTI_EP

        replace_map = self._replace_map()

        result_name = pattern

        # if there's no release group then replace it with a reasonable facsimile
        if not replace_map['%RN']:
            if self.show.air_by_date:
                result_name = result_name.replace('%RN', '%S.N.%A.D.%E.N-SiCKBEARD')
                result_name = result_name.replace('%rn', '%s.n.%A.D.%e.n-sickbeard')

            else:
                result_name = result_name.replace('%RN', '%S.N.S%0SE%0E.%E.N-SiCKBEARD')
                result_name = result_name.replace('%rn', '%s.n.s%0se%0e.%e.n-sickbeard')

            logger.log(u"Episode has no release name, replacing it with a generic one: " + result_name, logger.DEBUG)

        if not replace_map['%RG']:
            result_name = result_name.replace('%RG', 'SiCKBEARD')
            result_name = result_name.replace('%rg', 'sickbeard')
            logger.log(u"Episode has no release group, replacing it with a generic one: " + result_name, logger.DEBUG)

        # split off ep name part only
        name_groups = re.split(r'[\\/]', result_name)

        # figure out the double-ep numbering style for each group, if applicable
        for cur_name_group in name_groups:

            season_format = sep = ep_sep = ep_format = None

            season_ep_regex = '''
                                (?P<pre_sep>[ _.-]*)
                                ((?:s(?:eason|eries)?\s*)?%0?S(?![._]?N))
                                (.*?)
                                (%0?E(?![._]?N))
                                (?P<post_sep>[ _.-]*)
                              '''
            ep_only_regex = '(E?%0?E(?![._]?N))'

            # try the normal way
            season_ep_match = re.search(season_ep_regex, cur_name_group, re.I | re.X)
            ep_only_match = re.search(ep_only_regex, cur_name_group, re.I | re.X)

            # if we have a season and episode then collect the necessary data
            if season_ep_match:
                season_format = season_ep_match.group(2)
                ep_sep = season_ep_match.group(3)
                ep_format = season_ep_match.group(4)
                sep = season_ep_match.group('pre_sep')
                if not sep:
                    sep = season_ep_match.group('post_sep')
                if not sep:
                    sep = ' '

                # force 2-3-4 format if they chose to extend
                if multi in (NAMING_EXTEND, NAMING_LIMITED_EXTEND, NAMING_LIMITED_EXTEND_E_PREFIXED):
                    ep_sep = '-'

                regex_used = season_ep_regex

            # if there's no season then there's not much choice so we'll just force them to use 03-04-05 style
            elif ep_only_match:
                season_format = ''
                ep_sep = '-'
                ep_format = ep_only_match.group(1)
                sep = ''
                regex_used = ep_only_regex

            else:
                continue

            # we need at least this much info to continue
            if not ep_sep or not ep_format:
                continue

            # start with the ep string, eg. E03
            ep_string = self._format_string(ep_format.upper(), replace_map)
            for other_ep in self.relatedEps:

                # for limited extend we only append the last ep
                if multi in (NAMING_LIMITED_EXTEND, NAMING_LIMITED_EXTEND_E_PREFIXED) and other_ep != self.relatedEps[-1]:
                    continue

                elif multi == NAMING_DUPLICATE:
                    # add " - S01"
                    ep_string += sep + season_format

                elif multi == NAMING_SEPARATED_REPEAT:
                    ep_string += sep

                # add "E04"
                ep_string += ep_sep

                if multi == NAMING_LIMITED_EXTEND_E_PREFIXED:
                    ep_string += 'E'

                ep_string += other_ep._format_string(ep_format.upper(), other_ep._replace_map())

            if season_ep_match:
                regex_replacement = r'\g<pre_sep>\g<2>\g<3>' + ep_string + r'\g<post_sep>'
            elif ep_only_match:
                regex_replacement = ep_string

            # fill out the template for this piece and then insert this piece into the actual pattern
            cur_name_group_result = re.sub('(?i)(?x)' + regex_used, regex_replacement, cur_name_group)
            #cur_name_group_result = cur_name_group.replace(ep_format, ep_string)
            #logger.log(u"found "+ep_format+" as the ep pattern using "+regex_used+" and replaced it with "+regex_replacement+" to result in "+cur_name_group_result+" from "+cur_name_group, logger.DEBUG)
            result_name = result_name.replace(cur_name_group, cur_name_group_result)

        result_name = self._format_string(result_name, replace_map)

        logger.log(u"formatting pattern: " + pattern + " -> " + result_name, logger.DEBUG)

        return result_name

    def proper_path(self):
        """
        Figures out the path where this episode SHOULD live according to the renaming rules, relative from the show dir
        """

        result = self.formatted_filename()

        # if they want us to flatten it and we're allowed to flatten it then we will
        if self.show.flatten_folders and not sickbeard.NAMING_FORCE_FOLDERS:
            return result

        # if not we append the folder on and use that
        else:
            result = ek.ek(os.path.join, self.formatted_dir(), result)

        return result

    def formatted_dir(self, pattern=None, multi=None):
        """
        Just the folder name of the episode
        """

        if pattern == None:
            # we only use ABD if it's enabled, this is an ABD show, AND this is not a multi-ep
            if self.show.air_by_date and sickbeard.NAMING_CUSTOM_ABD and not self.relatedEps:
                pattern = sickbeard.NAMING_ABD_PATTERN
            else:
                pattern = sickbeard.NAMING_PATTERN

        # split off the dirs only, if they exist
        name_groups = re.split(r'[\\/]', pattern)

        if len(name_groups) == 1:
            return ''
        else:
            return self._format_pattern(os.sep.join(name_groups[:-1]), multi)

    def formatted_filename(self, pattern=None, multi=None):
        """
        Just the filename of the episode, formatted based on the naming settings
        """

        if pattern == None:
            # we only use ABD if it's enabled, this is an ABD show, AND this is not a multi-ep
            if self.show.air_by_date and sickbeard.NAMING_CUSTOM_ABD and not self.relatedEps:
                pattern = sickbeard.NAMING_ABD_PATTERN
            else:
                pattern = sickbeard.NAMING_PATTERN

        # split off the filename only, if they exist
        name_groups = re.split(r'[\\/]', pattern)

        return self._format_pattern(name_groups[-1], multi)

    def rename(self):
        """
        Renames an episode file and all related files to the location and filename as specified
        in the naming settings.
        """

        if not ek.ek(os.path.isfile, self.location):
            logger.log(u"Can't perform rename on " + self.location + " when it doesn't exist, skipping", logger.WARNING)
            return

        proper_path = self.proper_path()
        absolute_proper_path = ek.ek(os.path.join, self.show.location, proper_path)
        absolute_current_path_no_ext, file_ext = ek.ek(os.path.splitext, self.location)
        absolute_current_path_no_ext_length = len(absolute_current_path_no_ext)

        current_path = absolute_current_path_no_ext

        if absolute_current_path_no_ext.startswith(self.show.location):
            current_path = absolute_current_path_no_ext[len(self.show.location):]

        logger.log(u"Renaming/moving episode from the base path " + self.location + " to " + absolute_proper_path, logger.DEBUG)

        # if it's already named correctly then don't do anything
        if proper_path == current_path:
            logger.log(str(self.tvdbid) + u": File " + self.location + " is already named correctly, skipping", logger.DEBUG)
            return

        related_files = postProcessor.PostProcessor(self.location).list_associated_files(self.location, base_name_only=True)
        logger.log(u"Files associated to " + self.location + ": " + str(related_files), logger.DEBUG)

        # move the ep file
        result = helpers.rename_ep_file(self.location, absolute_proper_path, absolute_current_path_no_ext_length)

        # move related files
        for cur_related_file in related_files:
            cur_result = helpers.rename_ep_file(cur_related_file, absolute_proper_path, absolute_current_path_no_ext_length)
            if cur_result == False:
                logger.log(str(self.tvdbid) + u": Unable to rename file " + cur_related_file, logger.ERROR)

        # save the ep
        with self.lock:
            if result != False:
                self.location = absolute_proper_path + file_ext
                for relEp in self.relatedEps:
                    relEp.location = absolute_proper_path + file_ext

        # in case something changed with the metadata just do a quick check
        for curEp in [self] + self.relatedEps:
            curEp.checkForMetaFiles()

        # save any changes to the database
        with self.lock:
            self.saveToDB()
            for relEp in self.relatedEps:
                relEp.saveToDB()
