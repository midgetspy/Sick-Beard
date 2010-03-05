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


import sys
import os.path
import sqlite3

import sickbeard
from sickbeard import logger
from sickbeard import dbSetup

class DBConnection:
	def __init__(self, dbFileName="sickbeard.db"):
		
		self.dbFileName = dbFileName
		
		self.connection = sqlite3.connect(os.path.join(sickbeard.PROG_DIR, self.dbFileName), 20)
		self.connection.row_factory = sqlite3.Row

	def action(self, query, args=None):
		
		if query == None:
			return

		sqlResult = None

		try:
			if args == None:
				logger.log(self.dbFileName+": "+query, logger.DEBUG)
				sqlResult = self.connection.execute(query)
			else:
				logger.log(self.dbFileName+": "+query+" with args "+str(args), logger.DEBUG)
				sqlResult = self.connection.execute(query, args)
			self.connection.commit()
		except sqlite3.OperationalError, e:
			logger.log("DB error: "+str(e), logger.ERROR)
			raise
		except sqlite3.DatabaseError, e:
			logger.log("Fatal error executing query: " + str(e), logger.ERROR)
			raise
		
		return sqlResult
		

	def select(self, query, args=None):

		sqlResults = self.action(query, args).fetchall()

		if sqlResults == None:
			return []
		
		return sqlResults
	
	def upsert(self, tableName, valueDict, keyDict):
		
		changesBefore = self.connection.total_changes
		
		genParams = lambda myDict : [x + " = ?" for x in myDict.keys()]
		
		query = "UPDATE "+tableName+" SET " + ", ".join(genParams(valueDict)) + " WHERE " + " AND ".join(genParams(keyDict))
		
		self.action(query, valueDict.values() + keyDict.values())

		if self.connection.total_changes == changesBefore:
			query = "INSERT INTO "+tableName+" (" + ", ".join(valueDict.keys() + keyDict.keys()) + ")" + \
			         " VALUES (" + ", ".join(["?"] * len(valueDict.keys() + keyDict.keys())) + ")" 
			self.action(query, valueDict.values() + keyDict.values())

	def tableInfo(self, tableName):
		# FIXME ? binding is not supported here, but I cannot find a way to escape a string manually
		cursor = self.connection.execute("PRAGMA table_info(%s)" % tableName)
		columns = {}
		for column in cursor:
			columns[column['name']] = { 'type': column['type'] }
		return columns
