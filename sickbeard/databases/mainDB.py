from sickbeard import db
from sickbeard import common

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
		return len(self.connection.select("SELECT * FROM tv_episodes WHERE status = ?", [common.DOWNLOADED])) == 0

	def execute(self):

		toUpdate = self.connection.select("SELECT episode_id, location, status FROM tv_episodes WHERE status IN (?, ?)", [common.DOWNLOADED, common.SNATCHED])
		
		for curUpdate in toUpdate:

			if int(curUpdate["status"]) == common.SNATCHED:
				self.connection.action("UPDATE tv_episodes SET status = ? WHERE episode_id = ? ", [common.Quality.compositeStatus(common.SNATCHED, common.Quality.UNKNOWN), curUpdate["episode_id"]])
				continue
			
			if not curUpdate["location"]:
				continue
			if curUpdate["location"].endswith(".avi"):
				newQuality = common.Quality.SDTV
			elif curUpdate["location"].endswith(".mkv"):
				newQuality = common.Quality.HDTV
			else:
				newQuality = common.Quality.UNKNOWN

			self.connection.action("UPDATE tv_episodes SET status = ? WHERE episode_id = ?", [common.Quality.compositeStatus(common.DOWNLOADED, newQuality), curUpdate["episode_id"]])


		toUpdate = self.connection.select("SELECT episode_id, location FROM tv_episodes WHERE status = ?", [common.DOWNLOADED])
		
		for curUpdate in toUpdate:
			if not curUpdate["location"]:
				continue

			newQuality = common.Quality.nameQuality(curUpdate["location"])
			
			if newQuality == common.Quality.UNKNOWN:
				newQuality = common.Quality.assumeQuality(curUpdate["location"])

			self.connection.action("UPDATE tv_episodes SET status = ? WHERE episode_id = ?", [common.Quality.compositeStatus(common.DOWNLOADED, newQuality), curUpdate["episode_id"]])
			
			toUpdate = self.connection.select("SELECT * FROM tv_shows")
		
		for curUpdate in toUpdate:
			
			if not curUpdate["quality"]:
				continue
			
			if int(curUpdate["quality"]) == common.HD:
				newQuality = common.Quality.HDTV | common.Quality.HDWEBDL | common.Quality.HDBLURAY | common.Quality.FULLHDBLURAY | common.Quality.ANY 
			elif int(curUpdate["quality"]) == common.SD:
				newQuality = common.Quality.SDTV | common.Quality.SDDVD | common.Quality.ANY 
			elif int(curUpdate["quality"]) == common.ANY:
				newQuality = common.Quality.SDTV | common.Quality.SDDVD | common.Quality.HDTV | common.Quality.HDWEBDL | common.Quality.HDBLURAY | common.Quality.FULLHDBLURAY | common.Quality.ANY
			elif int(curUpdate["quality"]) == common.BEST:
				newQuality = common.Quality.SDTV | common.Quality.SDDVD | common.Quality.HDTV | common.Quality.HDWEBDL | common.Quality.HDBLURAY | common.Quality.FULLHDBLURAY | common.Quality.BEST
			else:
				newQuality = common.Quality.UNKNOWN
			
			self.connection.action("UPDATE tv_shows SET quality = ? WHERE show_id = ?", [newQuality, curUpdate["show_id"]])