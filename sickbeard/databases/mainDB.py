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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

import sickbeard
import os.path

from sickbeard import db, common, helpers, logger
from sickbeard.providers.generic import GenericProvider

from sickbeard import encodingKludge as ek
from sickbeard.name_parser.parser import NameParser, InvalidNameException

MAX_DB_VERSION = 12


class MainSanityCheck(db.DBSanityCheck):
    def check(self):
        self.fix_duplicate_shows()
        self.fix_duplicate_episodes()
        self.fix_orphan_episodes()

    def fix_duplicate_shows(self):
        sqlResults = self.connection.select("SELECT show_id, tvdb_id, COUNT(tvdb_id) as count FROM tv_shows GROUP BY tvdb_id HAVING count > 1")

        for cur_duplicate in sqlResults:

            logger.log(u"Duplicate show detected! tvdb_id: " + str(cur_duplicate["tvdb_id"]) + u" count: " + str(cur_duplicate["count"]), logger.DEBUG)

            cur_dupe_results = self.connection.select("SELECT show_id, tvdb_id FROM tv_shows WHERE tvdb_id = ? LIMIT ?",
                                           [cur_duplicate["tvdb_id"], int(cur_duplicate["count"]) - 1]
                                           )

            for cur_dupe_id in cur_dupe_results:
                logger.log(u"Deleting duplicate show with tvdb_id: " + str(cur_dupe_id["tvdb_id"]) + u" show_id: " + str(cur_dupe_id["show_id"]))
                self.connection.action("DELETE FROM tv_shows WHERE show_id = ?", [cur_dupe_id["show_id"]])

        else:
            logger.log(u"No duplicate show, check passed")

    def fix_duplicate_episodes(self):
        sqlResults = self.connection.select("SELECT showid, season, episode, COUNT(showid) as count FROM tv_episodes GROUP BY showid, season, episode HAVING count > 1")

        for cur_duplicate in sqlResults:

            logger.log(u"Duplicate episode detected! showid: " + str(cur_duplicate["showid"]) + u" season: " + str(cur_duplicate["season"]) + u" episode: " + str(cur_duplicate["episode"]) + u" count: " + str(cur_duplicate["count"]), logger.DEBUG)

            cur_dupe_results = self.connection.select("SELECT episode_id FROM tv_episodes WHERE showid = ? AND season = ? and episode = ? ORDER BY episode_id DESC LIMIT ?",
                                           [cur_duplicate["showid"], cur_duplicate["season"], cur_duplicate["episode"], int(cur_duplicate["count"]) - 1]
                                           )

            for cur_dupe_id in cur_dupe_results:
                logger.log(u"Deleting duplicate episode with episode_id: " + str(cur_dupe_id["episode_id"]))
                self.connection.action("DELETE FROM tv_episodes WHERE episode_id = ?", [cur_dupe_id["episode_id"]])

        else:
            logger.log(u"No duplicate episode, check passed")

    def fix_orphan_episodes(self):
        sqlResults = self.connection.select("SELECT episode_id, showid, tv_shows.tvdb_id FROM tv_episodes LEFT JOIN tv_shows ON tv_episodes.showid=tv_shows.tvdb_id WHERE tv_shows.tvdb_id is NULL")

        for cur_orphan in sqlResults:
            logger.log(u"Orphan episode detected! episode_id: " + str(cur_orphan["episode_id"]) + " showid: " + str(cur_orphan["showid"]), logger.DEBUG)
            logger.log(u"Deleting orphan episode with episode_id: " + str(cur_orphan["episode_id"]))
            self.connection.action("DELETE FROM tv_episodes WHERE episode_id = ?", [cur_orphan["episode_id"]])

        else:
            logger.log(u"No orphan episode, check passed")


def backupDatabase(version):
    helpers.backupVersionedFile(db.dbFilename(), version)

# ======================
# = Main DB Migrations =
# ======================
# Add new migrations at the bottom of the list; subclass the previous migration.


class InitialSchema (db.SchemaUpgrade):
    def test(self):
        return self.hasTable("tv_shows")

    def execute(self):
        queries = [
            "CREATE TABLE tv_shows (show_id INTEGER PRIMARY KEY, location TEXT, show_name TEXT, tvdb_id NUMERIC, network TEXT, genre TEXT, runtime NUMERIC, quality NUMERIC, airs TEXT, status TEXT, seasonfolders NUMERIC, paused NUMERIC, startyear NUMERIC);",
            "CREATE TABLE tv_episodes (episode_id INTEGER PRIMARY KEY, showid NUMERIC, tvdbid NUMERIC, name TEXT, season NUMERIC, episode NUMERIC, description TEXT, airdate NUMERIC, hasnfo NUMERIC, hastbn NUMERIC, status NUMERIC, location TEXT);",
            "CREATE TABLE info (last_backlog NUMERIC, last_tvdb NUMERIC);",
            "CREATE TABLE history (action NUMERIC, date NUMERIC, showid NUMERIC, season NUMERIC, episode NUMERIC, quality NUMERIC, resource TEXT, provider NUMERIC);"
        ]
        for query in queries:
            self.connection.action(query)


class AddTvrId (InitialSchema):
    def test(self):
        return self.hasColumn("tv_shows", "tvr_id")

    def execute(self):
        self.addColumn("tv_shows", "tvr_id")


class AddTvrName (AddTvrId):
    def test(self):
        return self.hasColumn("tv_shows", "tvr_name")

    def execute(self):
        self.addColumn("tv_shows", "tvr_name", "TEXT", "")


class AddAirdateIndex (AddTvrName):
    def test(self):
        return self.hasTable("idx_tv_episodes_showid_airdate")

    def execute(self):
        self.connection.action("CREATE INDEX idx_tv_episodes_showid_airdate ON tv_episodes(showid,airdate);")


class NumericProviders (AddAirdateIndex):
    def test(self):
        return self.connection.tableInfo("history")['provider']['type'] == 'TEXT'

    histMap = {-1: 'unknown',
                1: 'newzbin',
                2: 'tvbinz',
                3: 'nzbs',
                4: 'eztv',
                5: 'nzbmatrix',
                6: 'tvnzb',
                7: 'ezrss'}

    def execute(self):
        self.connection.action("ALTER TABLE history RENAME TO history_old")
        self.connection.action("CREATE TABLE history (action NUMERIC, date NUMERIC, showid NUMERIC, season NUMERIC, episode NUMERIC, quality NUMERIC, resource TEXT, provider TEXT);")

        for x in self.histMap.keys():
            self.upgradeHistory(x, self.histMap[x])

    def upgradeHistory(self, number, name):
        oldHistory = self.connection.action("SELECT * FROM history_old").fetchall()
        for curResult in oldHistory:
            sql = "INSERT INTO history (action, date, showid, season, episode, quality, resource, provider) VALUES (?,?,?,?,?,?,?,?)"
            provider = 'unknown'
            try:
                provider = self.histMap[int(curResult["provider"])]
            except ValueError:
                provider = curResult["provider"]
            args = [curResult["action"], curResult["date"], curResult["showid"], curResult["season"], curResult["episode"], curResult["quality"], curResult["resource"], provider]
            self.connection.action(sql, args)


class NewQualitySettings (NumericProviders):
    def test(self):
        return self.hasTable("db_version")

    def execute(self):
        backupDatabase(0)

        # old stuff that's been removed from common but we need it to upgrade
        HD = 1
        SD = 3
        ANY = 2
        BEST = 4

        ACTION_SNATCHED = 1
        ACTION_PRESNATCHED = 2
        ACTION_DOWNLOADED = 3

        PREDOWNLOADED = 3
        MISSED = 6
        BACKLOG = 7
        DISCBACKLOG = 8
        SNATCHED_BACKLOG = 10

        ### Update default quality
        if sickbeard.QUALITY_DEFAULT == HD:
            sickbeard.QUALITY_DEFAULT = common.HD
        elif sickbeard.QUALITY_DEFAULT == SD:
            sickbeard.QUALITY_DEFAULT = common.SD
        elif sickbeard.QUALITY_DEFAULT == ANY:
            sickbeard.QUALITY_DEFAULT = common.ANY
        elif sickbeard.QUALITY_DEFAULT == BEST:
            sickbeard.QUALITY_DEFAULT = common.BEST

        ### Update episode statuses
        toUpdate = self.connection.select("SELECT episode_id, location, status FROM tv_episodes WHERE status IN (?, ?, ?, ?, ?, ?, ?)", [common.DOWNLOADED, common.SNATCHED, PREDOWNLOADED, MISSED, BACKLOG, DISCBACKLOG, SNATCHED_BACKLOG])
        didUpdate = False
        for curUpdate in toUpdate:

            # remember that we changed something
            didUpdate = True

            newStatus = None
            oldStatus = int(curUpdate["status"])
            if oldStatus == common.SNATCHED:
                newStatus = common.Quality.compositeStatus(common.SNATCHED, common.Quality.UNKNOWN)
            elif oldStatus == PREDOWNLOADED:
                newStatus = common.Quality.compositeStatus(common.DOWNLOADED, common.Quality.SDTV)
            elif oldStatus in (MISSED, BACKLOG, DISCBACKLOG):
                newStatus = common.WANTED
            elif oldStatus == SNATCHED_BACKLOG:
                newStatus = common.Quality.compositeStatus(common.SNATCHED, common.Quality.UNKNOWN)

            if newStatus != None:
                self.connection.action("UPDATE tv_episodes SET status = ? WHERE episode_id = ? ", [newStatus, curUpdate["episode_id"]])
                continue

            # if we get here status should be == DOWNLOADED
            if not curUpdate["location"]:
                continue

            newQuality = common.Quality.nameQuality(curUpdate["location"])

            if newQuality == common.Quality.UNKNOWN:
                newQuality = common.Quality.assumeQuality(curUpdate["location"])

            self.connection.action("UPDATE tv_episodes SET status = ? WHERE episode_id = ?", [common.Quality.compositeStatus(common.DOWNLOADED, newQuality), curUpdate["episode_id"]])

        # if no updates were done then the backup is useless
        if didUpdate:
            os.remove(db.dbFilename(suffix='v0'))

        ### Update show qualities
        toUpdate = self.connection.select("SELECT * FROM tv_shows")
        for curUpdate in toUpdate:

            if not curUpdate["quality"]:
                continue

            if int(curUpdate["quality"]) == HD:
                newQuality = common.HD
            elif int(curUpdate["quality"]) == SD:
                newQuality = common.SD
            elif int(curUpdate["quality"]) == ANY:
                newQuality = common.ANY
            elif int(curUpdate["quality"]) == BEST:
                newQuality = common.BEST
            else:
                logger.log(u"Unknown show quality: " + str(curUpdate["quality"]), logger.WARNING)
                newQuality = None

            if newQuality:
                self.connection.action("UPDATE tv_shows SET quality = ? WHERE show_id = ?", [newQuality, curUpdate["show_id"]])

        ### Update history
        toUpdate = self.connection.select("SELECT * FROM history")
        for curUpdate in toUpdate:

            newAction = None
            newStatus = None
            if int(curUpdate["action"] == ACTION_SNATCHED):
                newStatus = common.SNATCHED
            elif int(curUpdate["action"] == ACTION_DOWNLOADED):
                newStatus = common.DOWNLOADED
            elif int(curUpdate["action"] == ACTION_PRESNATCHED):
                newAction = common.Quality.compositeStatus(common.SNATCHED, common.Quality.SDTV)

            if newAction == None and newStatus == None:
                continue

            if not newAction:
                if int(curUpdate["quality"] == HD):
                    newAction = common.Quality.compositeStatus(newStatus, common.Quality.HDTV)
                elif int(curUpdate["quality"] == SD):
                    newAction = common.Quality.compositeStatus(newStatus, common.Quality.SDTV)
                else:
                    newAction = common.Quality.compositeStatus(newStatus, common.Quality.UNKNOWN)

            self.connection.action("UPDATE history SET action = ? WHERE date = ? AND showid = ?", [newAction, curUpdate["date"], curUpdate["showid"]])

        self.connection.action("CREATE TABLE db_version (db_version INTEGER);")
        self.connection.action("INSERT INTO db_version (db_version) VALUES (?)", [1])


class DropOldHistoryTable(NewQualitySettings):
    def test(self):
        return self.checkDBVersion() >= 2

    def execute(self):
        self.connection.action("DROP TABLE history_old")
        self.incDBVersion()


class UpgradeHistoryForGenericProviders(DropOldHistoryTable):
    def test(self):
        return self.checkDBVersion() >= 3

    def execute(self):
        providerMap = {'NZBs': 'NZBs.org',
                       'BinReq': 'Bin-Req',
                       'NZBsRUS': '''NZBs'R'US''',
                       'EZTV': 'EZTV@BT-Chat'}

        for oldProvider in providerMap:
            self.connection.action("UPDATE history SET provider = ? WHERE provider = ?", [providerMap[oldProvider], oldProvider])

        self.incDBVersion()


class AddAirByDateOption(UpgradeHistoryForGenericProviders):
    def test(self):
        return self.checkDBVersion() >= 4

    def execute(self):
        self.connection.action("ALTER TABLE tv_shows ADD air_by_date NUMERIC")
        self.incDBVersion()


class ChangeSabConfigFromIpToHost(AddAirByDateOption):
    def test(self):
        return self.checkDBVersion() >= 5

    def execute(self):
        sickbeard.SAB_HOST = 'http://' + sickbeard.SAB_HOST + '/sabnzbd/'
        self.incDBVersion()


class FixSabHostURL(ChangeSabConfigFromIpToHost):
    def test(self):
        return self.checkDBVersion() >= 6

    def execute(self):
        if sickbeard.SAB_HOST.endswith('/sabnzbd/'):
            sickbeard.SAB_HOST = sickbeard.SAB_HOST.replace('/sabnzbd/', '/')
        sickbeard.save_config()
        self.incDBVersion()


class AddLang (FixSabHostURL):
    def test(self):
        return self.hasColumn("tv_shows", "lang")

    def execute(self):
        self.addColumn("tv_shows", "lang", "TEXT", "en")


class PopulateRootDirs (AddLang):
    def test(self):
        return self.checkDBVersion() >= 7

    def execute(self):
        dir_results = self.connection.select("SELECT location FROM tv_shows")

        dir_counts = {}
        for cur_dir in dir_results:
            cur_root_dir = ek.ek(os.path.dirname, ek.ek(os.path.normpath, cur_dir["location"]))
            if cur_root_dir not in dir_counts:
                dir_counts[cur_root_dir] = 1
            else:
                dir_counts[cur_root_dir] += 1

        logger.log(u"Dir counts: " + str(dir_counts), logger.DEBUG)

        if not dir_counts:
            self.incDBVersion()
            return

        default_root_dir = dir_counts.values().index(max(dir_counts.values()))

        new_root_dirs = str(default_root_dir) + '|' + '|'.join(dir_counts.keys())
        logger.log(u"Setting ROOT_DIRS to: " + new_root_dirs, logger.DEBUG)

        sickbeard.ROOT_DIRS = new_root_dirs

        sickbeard.save_config()

        self.incDBVersion()


class SetNzbTorrentSettings(PopulateRootDirs):
    def test(self):
        return self.checkDBVersion() >= 8

    def execute(self):
        use_torrents = False
        use_nzbs = False

        for cur_provider in sickbeard.providers.sortedProviderList():
            if cur_provider.isEnabled():
                if cur_provider.providerType == GenericProvider.NZB:
                    use_nzbs = True
                    logger.log(u"Provider " + cur_provider.name + " is enabled, enabling NZBs in the upgrade")
                    break
                elif cur_provider.providerType == GenericProvider.TORRENT:
                    use_torrents = True
                    logger.log(u"Provider " + cur_provider.name + " is enabled, enabling Torrents in the upgrade")
                    break

        sickbeard.USE_TORRENTS = use_torrents
        sickbeard.USE_NZBS = use_nzbs

        sickbeard.save_config()

        self.incDBVersion()


class FixAirByDateSetting(SetNzbTorrentSettings):
    def test(self):
        return self.checkDBVersion() >= 9

    def execute(self):
        shows = self.connection.select("SELECT * FROM tv_shows")

        for cur_show in shows:
            if cur_show["genre"] and "talk show" in cur_show["genre"].lower():
                self.connection.action("UPDATE tv_shows SET air_by_date = ? WHERE tvdb_id = ?", [1, cur_show["tvdb_id"]])

        self.incDBVersion()


class AddSizeAndSceneNameFields(FixAirByDateSetting):
    def test(self):
        return self.checkDBVersion() >= 10

    def execute(self):
        backupDatabase(10)

        if not self.hasColumn("tv_episodes", "file_size"):
            self.addColumn("tv_episodes", "file_size")

        if not self.hasColumn("tv_episodes", "release_name"):
            self.addColumn("tv_episodes", "release_name", "TEXT", "")

        ep_results = self.connection.select("SELECT episode_id, location, file_size FROM tv_episodes")

        logger.log(u"Adding file size to all episodes in DB, please be patient")
        for cur_ep in ep_results:
            if not cur_ep["location"]:
                continue

            # if there is no size yet then populate it for us
            if (not cur_ep["file_size"] or not int(cur_ep["file_size"])) and ek.ek(os.path.isfile, cur_ep["location"]):
                cur_size = ek.ek(os.path.getsize, cur_ep["location"])
                self.connection.action("UPDATE tv_episodes SET file_size = ? WHERE episode_id = ?", [cur_size, int(cur_ep["episode_id"])])

        # check each snatch to see if we can use it to get a release name from
        history_results = self.connection.select("SELECT * FROM history WHERE provider != -1 ORDER BY date ASC")

        logger.log(u"Adding release name to all episodes still in history")
        for cur_result in history_results:
            # find the associated download, if there isn't one then ignore it
            download_results = self.connection.select("SELECT resource FROM history WHERE provider = -1 AND showid = ? AND season = ? AND episode = ? AND date > ?",
                                                    [cur_result["showid"], cur_result["season"], cur_result["episode"], cur_result["date"]])
            if not download_results:
                logger.log(u"Found a snatch in the history for " + cur_result["resource"] + " but couldn't find the associated download, skipping it", logger.DEBUG)
                continue

            nzb_name = cur_result["resource"]
            file_name = ek.ek(os.path.basename, download_results[0]["resource"])

            # take the extension off the filename, it's not needed
            if '.' in file_name:
                file_name = file_name.rpartition('.')[0]

            # find the associated episode on disk
            ep_results = self.connection.select("SELECT episode_id, status FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ? AND location != ''",
                                                [cur_result["showid"], cur_result["season"], cur_result["episode"]])
            if not ep_results:
                logger.log(u"The episode " + nzb_name + " was found in history but doesn't exist on disk anymore, skipping", logger.DEBUG)
                continue

            # get the status/quality of the existing ep and make sure it's what we expect
            ep_status, ep_quality = common.Quality.splitCompositeStatus(int(ep_results[0]["status"]))
            if ep_status != common.DOWNLOADED:
                continue

            if ep_quality != int(cur_result["quality"]):
                continue

            # make sure this is actually a real release name and not a season pack or something
            for cur_name in (nzb_name, file_name):
                logger.log(u"Checking if " + cur_name + " is actually a good release name", logger.DEBUG)
                try:
                    np = NameParser(False)
                    parse_result = np.parse(cur_name)
                except InvalidNameException:
                    continue

                if parse_result.series_name and parse_result.season_number != None and parse_result.episode_numbers and parse_result.release_group:
                    # if all is well by this point we'll just put the release name into the database
                    self.connection.action("UPDATE tv_episodes SET release_name = ? WHERE episode_id = ?", [cur_name, ep_results[0]["episode_id"]])
                    break

        # check each snatch to see if we can use it to get a release name from
        empty_results = self.connection.select("SELECT episode_id, location FROM tv_episodes WHERE release_name = ''")

        logger.log(u"Adding release name to all episodes with obvious scene filenames")
        for cur_result in empty_results:

            ep_file_name = ek.ek(os.path.basename, cur_result["location"])
            ep_file_name = os.path.splitext(ep_file_name)[0]

            # only want to find real scene names here so anything with a space in it is out
            if ' ' in ep_file_name:
                continue

            try:
                np = NameParser(False)
                parse_result = np.parse(ep_file_name)
            except InvalidNameException:
                continue

            if not parse_result.release_group:
                continue

            logger.log(u"Name " + ep_file_name + " gave release group of " + parse_result.release_group + ", seems valid", logger.DEBUG)
            self.connection.action("UPDATE tv_episodes SET release_name = ? WHERE episode_id = ?", [ep_file_name, cur_result["episode_id"]])

        self.incDBVersion()


class RenameSeasonFolders(AddSizeAndSceneNameFields):
    def test(self):
        return self.checkDBVersion() >= 11

    def execute(self):
        # rename the column
        self.connection.action("ALTER TABLE tv_shows RENAME TO tmp_tv_shows")
        self.connection.action("CREATE TABLE tv_shows (show_id INTEGER PRIMARY KEY, location TEXT, show_name TEXT, tvdb_id NUMERIC, network TEXT, genre TEXT, runtime NUMERIC, quality NUMERIC, airs TEXT, status TEXT, flatten_folders NUMERIC, paused NUMERIC, startyear NUMERIC, tvr_id NUMERIC, tvr_name TEXT, air_by_date NUMERIC, lang TEXT)")
        sql = "INSERT INTO tv_shows(show_id, location, show_name, tvdb_id, network, genre, runtime, quality, airs, status, flatten_folders, paused, startyear, tvr_id, tvr_name, air_by_date, lang) SELECT show_id, location, show_name, tvdb_id, network, genre, runtime, quality, airs, status, seasonfolders, paused, startyear, tvr_id, tvr_name, air_by_date, lang FROM tmp_tv_shows"
        self.connection.action(sql)

        # flip the values to be opposite of what they were before
        self.connection.action("UPDATE tv_shows SET flatten_folders = 2 WHERE flatten_folders = 1")
        self.connection.action("UPDATE tv_shows SET flatten_folders = 1 WHERE flatten_folders = 0")
        self.connection.action("UPDATE tv_shows SET flatten_folders = 0 WHERE flatten_folders = 2")
        self.connection.action("DROP TABLE tmp_tv_shows")

        self.incDBVersion()


class Add1080pAndRawHDQualities(RenameSeasonFolders):
    """Add support for 1080p related qualities along with RawHD

    Quick overview of what the upgrade needs to do:

           quality   | old  | new
        --------------------------
        hdwebdl      | 1<<3 | 1<<5
        hdbluray     | 1<<4 | 1<<7
        fullhdbluray | 1<<5 | 1<<8
        --------------------------
        rawhdtv      |      | 1<<3
        fullhdtv     |      | 1<<4
        fullhdwebdl  |      | 1<<6
    """

    def test(self):
        return self.checkDBVersion() >= 12

    def _update_status(self, old_status):
        (status, quality) = common.Quality.splitCompositeStatus(old_status)
        return common.Quality.compositeStatus(status, self._update_quality(quality))

    def _update_quality(self, old_quality):
        """Update bitwise flags to reflect new quality values

        Check flag bits (clear old then set their new locations) starting
        with the highest bits so we dont overwrite data we need later on
        """

        result = old_quality
        # move fullhdbluray from 1<<5 to 1<<8 if set
        if(result & (1<<5)):
            result = result & ~(1<<5)
            result = result | (1<<8)
        # move hdbluray from 1<<4 to 1<<7 if set
        if(result & (1<<4)):
            result = result & ~(1<<4)
            result = result | (1<<7)
        # move hdwebdl from 1<<3 to 1<<5 if set
        if(result & (1<<3)):
            result = result & ~(1<<3)
            result = result | (1<<5)

        return result

    def _update_composite_qualities(self, status):
        """Unpack, Update, Return new quality values

        Unpack the composite archive/initial values.
        Update either qualities if needed.
        Then return the new compsite quality value.
        """

        best = (status & (0xffff << 16)) >> 16
        initial = status & (0xffff)

        best = self._update_quality(best)
        initial = self._update_quality(initial)

        result = ((best << 16) | initial)
        return result

    def execute(self):
        backupDatabase(self.checkDBVersion())

        # update the default quality so we dont grab the wrong qualities after migration
        sickbeard.QUALITY_DEFAULT = self._update_composite_qualities(sickbeard.QUALITY_DEFAULT)
        sickbeard.save_config()

        # upgrade previous HD to HD720p -- shift previous qualities to new placevalues
        old_hd = common.Quality.combineQualities([common.Quality.HDTV, common.Quality.HDWEBDL >> 2, common.Quality.HDBLURAY >> 3], [])
        new_hd = common.Quality.combineQualities([common.Quality.HDTV, common.Quality.HDWEBDL, common.Quality.HDBLURAY], [])

        # update ANY -- shift existing qualities and add new 1080p qualities, note that rawHD was not added to the ANY template
        old_any = common.Quality.combineQualities([common.Quality.SDTV, common.Quality.SDDVD, common.Quality.HDTV, common.Quality.HDWEBDL >> 2, common.Quality.HDBLURAY >> 3, common.Quality.UNKNOWN], [])
        new_any = common.Quality.combineQualities([common.Quality.SDTV, common.Quality.SDDVD, common.Quality.HDTV, common.Quality.FULLHDTV, common.Quality.HDWEBDL, common.Quality.FULLHDWEBDL, common.Quality.HDBLURAY, common.Quality.FULLHDBLURAY, common.Quality.UNKNOWN], [])

        # update qualities (including templates)
        logger.log(u"[1/4] Updating pre-defined templates and the quality for each show...", logger.MESSAGE)
        ql = []
        shows = self.connection.select("SELECT * FROM tv_shows")
        for cur_show in shows:
            if cur_show["quality"] == old_hd:
                new_quality = new_hd
            elif cur_show["quality"] == old_any:
                new_quality = new_any
            else:
                new_quality = self._update_composite_qualities(cur_show["quality"])
            ql.append(["UPDATE tv_shows SET quality = ? WHERE show_id = ?", [new_quality, cur_show["show_id"]]])
        self.connection.mass_action(ql)

        # update status that are are within the old hdwebdl (1<<3 which is 8) and better -- exclude unknown (1<<15 which is 32768)
        logger.log(u"[2/4] Updating the status for the episodes within each show...", logger.MESSAGE)
        ql = []
        episodes = self.connection.select("SELECT * FROM tv_episodes WHERE status < 3276800 AND status >= 800")
        for cur_episode in episodes:
            ql.append(["UPDATE tv_episodes SET status = ? WHERE episode_id = ?", [self._update_status(cur_episode["status"]), cur_episode["episode_id"]]])
        self.connection.mass_action(ql)

        # make two seperate passes through the history since snatched and downloaded (action & quality) may not always coordinate together

        # update previous history so it shows the correct action
        logger.log(u"[3/4] Updating history to reflect the correct action...", logger.MESSAGE)
        ql = []
        historyAction = self.connection.select("SELECT * FROM history WHERE action < 3276800 AND action >= 800")
        for cur_entry in historyAction:
            ql.append(["UPDATE history SET action = ? WHERE showid = ? AND date = ?", [self._update_status(cur_entry["action"]), cur_entry["showid"], cur_entry["date"]]])
        self.connection.mass_action(ql)

        # update previous history so it shows the correct quality
        logger.log(u"[4/4] Updating history to reflect the correct quality...", logger.MESSAGE)
        ql = []
        historyQuality = self.connection.select("SELECT * FROM history WHERE quality < 32768 AND quality >= 8")
        for cur_entry in historyQuality:
            ql.append(["UPDATE history SET quality = ? WHERE showid = ? AND date = ?", [self._update_quality(cur_entry["quality"]), cur_entry["showid"], cur_entry["date"]]])
        self.connection.mass_action(ql)

        self.incDBVersion()

        # cleanup and reduce db if any previous data was removed
        logger.log(u"Performing a vacuum on the database.", logger.DEBUG)
        self.connection.action("VACUUM")
