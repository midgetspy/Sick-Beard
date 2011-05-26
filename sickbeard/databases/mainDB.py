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
import shutil, time, os.path, sys

from sickbeard import db
from sickbeard import common
from sickbeard import logger
from sickbeard.providers.generic import GenericProvider

from sickbeard import encodingKludge as ek
from sickbeard.exceptions import ex

class MainSanityCheck(db.DBSanityCheck):

    def check(self):
        self.fix_duplicate_episodes()

    def fix_duplicate_episodes(self):
    
        sqlResults = self.connection.select("SELECT showid, season, episode, COUNT(*) as count FROM tv_episodes GROUP BY showid, season, episode HAVING COUNT(*) > 1")
    
        for cur_duplicate in sqlResults:
    
            logger.log(u"Duplicate episode detected! showid: "+str(cur_duplicate["showid"])+" season: "+str(cur_duplicate["season"])+" episode: "+str(cur_duplicate["episode"])+" count: "+str(cur_duplicate["count"]), logger.DEBUG)
    
            cur_dupe_results = self.connection.select("SELECT episode_id FROM tv_episodes WHERE showid = ? AND season = ? and episode = ? LIMIT ?",
                                           [cur_duplicate["showid"], cur_duplicate["season"], cur_duplicate["episode"], int(cur_duplicate["count"])-1]
                                           )
            
            for cur_dupe_id in cur_dupe_results:
                logger.log(u"Deleting episode with id "+str(cur_dupe_id["episode_id"]))
                self.connection.action("DELETE FROM tv_episodes WHERE episode_id = ?", [cur_dupe_id["episode_id"]])
        
        else:
            logger.log(u"No duplicate episode, check passed")
        
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
                7: 'ezrss',
                8: 'thepiratebay'}

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

        numTries = 0
        while not ek.ek(os.path.isfile, db.dbFilename(suffix='v0')):
            if not ek.ek(os.path.isfile, db.dbFilename()):
                break

            try:
                logger.log(u"Attempting to back up your sickbeard.db file before migration...")
                shutil.copy(db.dbFilename(), db.dbFilename(suffix='v0'))
                logger.log(u"Done backup, proceeding with migration.")
                break
            except Exception, e:
                logger.log(u"Error while trying to back up your sickbeard.db: "+ex(e))
                numTries += 1
                time.sleep(1)
                logger.log(u"Trying again.")

            if numTries >= 10:
                logger.log(u"Unable to back up your sickbeard.db file, please do it manually.")
                sys.exit(1)

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
                logger.log(u"Unknown show quality: "+str(curUpdate["quality"]), logger.WARNING)
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
            sickbeard.SAB_HOST = sickbeard.SAB_HOST.replace('/sabnzbd/','/')
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
        
        logger.log(u"Dir counts: "+str(dir_counts), logger.DEBUG)
        
        if not dir_counts:
            self.incDBVersion()
            return
        
        default_root_dir = dir_counts.values().index(max(dir_counts.values()))
        
        new_root_dirs = str(default_root_dir)+'|'+'|'.join(dir_counts.keys())
        logger.log(u"Setting ROOT_DIRS to: "+new_root_dirs, logger.DEBUG)
        
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
                    logger.log(u"Provider "+cur_provider.name+" is enabled, enabling NZBs in the upgrade")
                    break
                elif cur_provider.providerType == GenericProvider.TORRENT:
                    use_torrents = True
                    logger.log(u"Provider "+cur_provider.name+" is enabled, enabling Torrents in the upgrade")
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
