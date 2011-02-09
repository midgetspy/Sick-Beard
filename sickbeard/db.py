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
import re
import sqlite3
import time
import threading

import sickbeard

from sickbeard import logger

db_lock = threading.Lock()

class DBConnection:
	def __init__(self, dbFileName="sickbeard.db"):

		self.dbFileName = dbFileName

		self.connection = sqlite3.connect(os.path.join(sickbeard.PROG_DIR, self.dbFileName), 20)
		self.connection.row_factory = sqlite3.Row

 	def action(self, query, args=None):

 		with db_lock:

			if query == None:
				return
	
			sqlResult = None
			attempt = 0
	
			while attempt < 5:
				try:
					if args == None:
						logger.log(self.dbFileName+": "+query, logger.DEBUG)
						sqlResult = self.connection.execute(query)
					else:
						logger.log(self.dbFileName+": "+query+" with args "+str(args), logger.DEBUG)
						sqlResult = self.connection.execute(query, args)
					self.connection.commit()
					# get out of the connection attempt loop since we were successful
					break
				except sqlite3.OperationalError, e:
					if "unable to open database file" in str(e) or "database is locked" in str(e):
						logger.log(u"DB error: "+str(e).decode('utf-8'), logger.WARNING)
						attempt += 1
						time.sleep(1)
					else:
						logger.log(u"DB error: "+str(e).decode('utf-8'), logger.ERROR)
						raise
				except sqlite3.DatabaseError, e:
					logger.log(u"Fatal error executing query: " + str(e), logger.ERROR)
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

def sanityCheckDatabase(connection, sanity_check):
	sanity_check(connection).check()

class DBSanityCheck(object):
	def __init__(self, connection):
		self.connection = connection

	def check(self):
		pass

# ===============
# = Upgrade API =
# ===============

def upgradeDatabase(connection, schema):
	logger.log(u"Checking database structure...", logger.MESSAGE)
	_processUpgrade(connection, schema)

def prettyName(str):
	return ' '.join([x.group() for x in re.finditer("([A-Z])([a-z0-9]+)", str)])

def _processUpgrade(connection, upgradeClass):
	instance = upgradeClass(connection)
	logger.log(u"Checking " + prettyName(upgradeClass.__name__) + " database upgrade", logger.DEBUG)
	if not instance.test():
		logger.log(u"Database upgrade required: " + prettyName(upgradeClass.__name__), logger.MESSAGE)
		try:
			instance.execute()
		except sqlite3.DatabaseError, e:
			print "Error in " + str(upgradeClass.__name__) + ": " + str(e)
			raise
		logger.log(upgradeClass.__name__ + " upgrade completed", logger.DEBUG)
	else:
		logger.log(upgradeClass.__name__ + " upgrade not required", logger.DEBUG)

	for upgradeSubClass in upgradeClass.__subclasses__():
		_processUpgrade(connection, upgradeSubClass)

# Base migration class. All future DB changes should be subclassed from this class
class SchemaUpgrade (object):
	def __init__(self, connection):
		self.connection = connection

	def hasTable(self, tableName):
		return len(self.connection.action("SELECT 1 FROM sqlite_master WHERE name = ?;", (tableName, )).fetchall()) > 0

	def hasColumn(self, tableName, column):
		return column in self.connection.tableInfo(tableName)

	def addColumn(self, table, column, type="NUMERIC", default=0):
		self.connection.action("ALTER TABLE %s ADD %s %s" % (table, column, type))
		self.connection.action("UPDATE %s SET %s = ?" % (table, column), (default,))

	def checkDBVersion(self):
		result = self.connection.select("SELECT db_version FROM db_version")
		if result:
			return int(result[0]["db_version"])
		else:
			return 0

	def incDBVersion(self):
		curVersion = self.checkDBVersion()
		self.connection.action("UPDATE db_version SET db_version = ?", [curVersion+1])
		return curVersion+1
