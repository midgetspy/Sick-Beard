import sickbeard
from sickbeard import db
from sickbeard import common
from sickbeard import logger

from sickbeard import encodingKludge as ek
import shutil, time, os.path, sys

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

        numTries = 0
        while not ek.ek(os.path.isfile, ek.ek(os.path.join, sickbeard.PROG_DIR, 'sickbeard.db.v0')):
            if not ek.ek(os.path.isfile, ek.ek(os.path.join, sickbeard.PROG_DIR, 'sickbeard.db')):
                break

            try:
                logger.log(u"Attempting to back up your sickbeard.db file before migration...")
                shutil.copy(ek.ek(os.path.join, sickbeard.PROG_DIR, 'sickbeard.db'), ek.ek(os.path.join, sickbeard.PROG_DIR, 'sickbeard.db.v0'))
                logger.log(u"Done backup, proceeding with migration.")
                break
            except Exception, e:
                logger.log(u"Error while trying to back up your sickbeard.db: "+str(e).decode('utf-8'))
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
        for curUpdate in toUpdate:

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
