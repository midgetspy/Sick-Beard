import os.path
import sqlite3

import sickbeard

from lib.tvdb_api import tvdb_api

class DBConnection:
		def __init__(self):
			self.connection = sqlite3.connect(os.path.join(sickbeard.PROG_DIR, "sickbeard.db"), 20)
			self.connection.row_factory = sqlite3.Row
		
		def checkDB(self):
			# Create the table if it's not already there
			try:
				sql = "CREATE TABLE tv_shows (show_id INTEGER PRIMARY KEY, location TEXT, show_name TEXT, tvdb_id NUMERIC, network TEXT, genre TEXT, runtime NUMERIC, quality NUMERIC, predownload NUMERIC, airs TEXT, status TEXT, seasonfolders NUMERIC);"
				self.connection.execute(sql)
				self.connection.commit()
			except sqlite3.OperationalError as e:
				if str(e) != "table tv_shows already exists":
					raise

			# Create the table if it's not already there
			try:
				sql = "CREATE TABLE tv_episodes (episode_id INTEGER PRIMARY KEY, showid NUMERIC, tvdbid NUMERIC, name TEXT, season NUMERIC, episode NUMERIC, description TEXT, airdate NUMERIC, hasnfo NUMERIC, hastbn NUMERIC, status NUMERIC, location TEXT);"
				self.connection.execute(sql)
				self.connection.commit()
			except sqlite3.OperationalError as e:
				if str(e) != "table tv_episodes already exists":
					raise

			# Create the table if it's not already there
			try:
				sql = "CREATE TABLE info (last_backlog NUMERIC, last_tvdb NUMERIC);"
				self.connection.execute(sql)
				self.connection.commit()
			except sqlite3.OperationalError as e:
				if str(e) != "table info already exists":
					raise

