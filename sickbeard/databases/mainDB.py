from sickbeard import db
from sickbeard import common
from sickbeard import logger


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
				6: 'tvnzb'}

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
		# if there are any download statuses then we need to migrate the DB
		if len(self.connection.select("SELECT * FROM tv_episodes WHERE status = ?", [common.DOWNLOADED])) == 0:
			return False

	def execute(self):
		
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
				logger.log("Unknown show quality: "+str(curUpdate["quality"]), logger.WARNING)
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

			