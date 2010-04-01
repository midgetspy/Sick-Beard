from sickbeard import db

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
