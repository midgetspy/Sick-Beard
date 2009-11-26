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



import os.path
import datetime
import sqlite3
import threading
import urllib
import re
import glob
from xml.dom.minidom import Document

from lib.BeautifulSoup import BeautifulStoneSoup, NavigableString, HTMLParseError
from lib.tvdb_api import tvdb_api, tvnamer, tvdb_exceptions

from sickbeard import db
from sickbeard import helpers
from sickbeard import exceptions
from sickbeard import processTV
from sickbeard import classes
from sickbeard import tvrage

from common import *
from logging import *

class TVShow(object):

	def __init__ (self, showdir):
	
		self._location = os.path.normpath(showdir)
		self.name = ""
		self.tvdbid = 0
		self.network = ""
		self.genre = ""
		self.runtime = 0
		self.quality = ANY
		self.predownload = 0
		self.seasonfolders = 0
		
		self.status = ""
		self.airs = ""

		self.db = None
		self.lock = threading.Lock()
		self._isDirGood = False
		
		self.episodes = {}

		# if the location doesn't exist, try the DB
		if not os.path.isdir(self._location):
			
			self._isDirGood = False
			
			Logger().log("The show dir doesn't exist! This show will be inactive until the dir is created.", ERROR)
			
			myDB = db.DBConnection()
			sqlResults = myDB.select("SELECT * FROM tv_shows WHERE location = ?", [self._location])
	
			# if the location is in the DB, load it from the DB only
			if len(sqlResults) > 0:
				self.tvdbid = int(sqlResults[0]["tvdb_id"])
				self.loadFromDB()
			else:
				raise exceptions.NoNFOException("Show folder doesn't exist")
		
		elif not os.path.isfile(os.path.join(self._location, "tvshow.nfo")):
			
			raise exceptions.NoNFOException("No NFO found in show dir")
		
		# if the location does exist then start with the NFO and load extra stuff from the DB
		else:
			
			self._isDirGood = True
			
			self.loadNFO()
			
			myDB = db.DBConnection()
			sqlResults = myDB.select("SELECT * FROM tv_shows WHERE tvdb_id = " + str(self.tvdbid))
			
			if len(sqlResults) > 0:
	
				if self.name == "":
					self.name = sqlResults[0]["name"]
				if self.network == "":
					self.network = sqlResults[0]["network"]
				if self.genre == "":
					self.genre = sqlResults[0]["genre"]
		
				self.runtime = int(sqlResults[0]["runtime"])
				self.quality = int(sqlResults[0]["quality"])
				self.predownload = int(sqlResults[0]["predownload"])
				self.seasonfolders = int(sqlResults[0]["seasonfolders"])
	
		#Logger().log(str(self.tvdbid) + ": Loading extra show info from theTVDB")
		#try:
		#	self.loadFromTVDB()
		#except tvdb_exceptions.tvdb_error as e:
		#	Logger().log("There was a problem loading the details from TVDB (server down?)", ERROR)
		#	if str(e) == "Could not connect to server: <urlopen error timed out>":
		#		sickbeard.LAST_TVDB_TIMEOUT = datetime.datetime.now()

		otherShow = helpers.findCertainShow(sickbeard.showList, self.tvdbid)
		if otherShow != None:
			raise exceptions.MultipleShowObjectsException("Can't create a show if it already exists")
		
		try:
			t = tvdb_api.Tvdb(lastTimeout=sickbeard.LAST_TVDB_TIMEOUT)
			t[self.tvdbid]
		except tvdb_exceptions.tvdb_shownotfound as e:
			raise exceptions.ShowNotFoundException(str(e))
		except tvdb_exceptions.tvdb_error as e:
			Logger().log("Unable to contact theTVDB.com, it might be down: "+str(e), ERROR)
		
		self.saveToDB()
	
	
	def _getLocation(self):
		if self._isDirGood:
			return self._location
		else:
			raise exceptions.NoNFOException("Show folder doesn't exist, you shouldn't be using it")

	def _setLocation(self, newLocation):
		Logger().log("Setter sets location to " + newLocation)
		if os.path.isdir(newLocation) and os.path.isfile(os.path.join(newLocation, "tvshow.nfo")):
			self._location = newLocation
			self._isDirGood = True
		else:
			raise exceptions.NoNFOException("Invalid folder for the show!")

	location = property(_getLocation, _setLocation)

	
	def getEpisode(self, season, episode, forceCreation=False):

		return TVEpisode(self, season, episode)

		if not season in self.episodes:
			self.episodes[season] = {}
		
		ep = None
		
		if not episode in self.episodes[season]:
			if forceCreation == False:
				return None
			
			else:
				Logger().log(str(self.tvdbid) + ": Episode " + str(season) + "x" + str(episode) + " didn't exist, trying to create it", DEBUG)
				ep = None
				try:
					ep = TVEpisode(self, season, episode)
				except (exceptions.EpisodeNotFoundException):
					return None
				
				if ep != None:
					self.episodes[season][episode] = ep

		return self.episodes[season][episode]
	

	def setEpisode(self, season, episode, epObj):
		
		# don't keep it in RAM ever, that's what the DB's for
		epObj.saveToDB()
		return
		
		if not season in self.episodes:
			self.episodes[season] = {}

		self.episodes[season][episode] = epObj
	
	def writeEpisodeNFOs (self):
		
		Logger().log(str(self.tvdbid) + ": Writing NFOs for all episodes")
		
		myDB = db.DBConnection()
		sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = " + str(self.tvdbid) + " AND location != ''")
		
		for epResult in sqlResults:
			Logger().log(str(self.tvdbid) + ": Retrieving/creating episode " + str(epResult["season"]) + "x" + str(epResult["episode"]), DEBUG)
			curEp = self.getEpisode(epResult["season"], epResult["episode"], True)
			curEp.createMetaFiles()


	def loadEpisodesFromDB (self):
		
		Logger().log(str(self.tvdbid) + ": Loading all episodes from the database")
		
		myDB = db.DBConnection()
		sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = " + str(self.tvdbid))

		for epResult in sqlResults:
			Logger().log(str(self.tvdbid) + ": Retrieving/creating episode " + str(epResult["season"]) + "x" + str(epResult["episode"]), DEBUG)
			self.getEpisode(epResult["season"], epResult["episode"], True)

	# find all media files in the show folder and create episodes for as many as possible
	def loadEpisodesFromDir (self, skipDBEps=True):

		Logger().log(str(self.tvdbid) + ": Loading all episodes from the show directory " + self._location)

		# get file list
		files = []
		if not self.seasonfolders:
			files = os.listdir(self._location)
		else:
			for curFile in os.listdir(self._location):
				match = re.match("[Ss]eason (\d+)", curFile)
				if match != None:
					files += [os.path.join(curFile, x) for x in os.listdir(os.path.join(self._location, curFile))]

		# check for season folders
		#Logger().log("Resulting file list: "+str(files))
	
		# find all media files
		mediaFiles = filter(sickbeard.helpers.isMediaFile, files)

		# create TVEpisodes from each media file (if possible)
		for mediaFile in mediaFiles:
			
			if skipDBEps == True:
			
				self._getDB()
				self.db.checkDB()
			
				sqlResults = []
			
				#try:
				#	sql = "SELECT * FROM tv_episodes WHERE showid = " + str(self.tvdbid) + " AND location = \"" + mediaFile + "\""
				#	sqlResults = self.db.connection.execute(sql).fetchall()
				#except sqlite3.DatabaseError as e:
				#	Logger().log("Fatal error executing query '"+sql+"': "+str(e), ERROR)
				#	raise

				#if len(sqlResults) == 0:
				Logger().log(str(self.tvdbid) + ": " + mediaFile + " isn't in the DB, creating a new episode for it", DEBUG)
				curEpisode = self.makeEpFromFile(os.path.join(self._location, mediaFile))
				#else:
				#	Logger().log(str(self.tvdbid)+": "+mediaFile+" is already in the DB, skipping NFO scan", DEBUG)
				#	curEpisode = None
					
			else:
				Logger().log(str(self.tvdbid) + ": " + mediaFile + " isn't in the DB, creating a new episode for it", DEBUG)
				try:
					curEpisode = self.makeEpFromFile(os.path.join(self._location, mediaFile))
				except exceptions.ShowNotFoundException as e:
					Logger().log("Episode "+mediaFile+" returned an exception: "+str(e), ERROR)
					

			# store the reference in the show
			if curEpisode != None:
				curEpisode.saveToDB()
				#self.setEpisode(curEpisode.season, curEpisode.episode, curEpisode)
	

	def loadEpisodesFromTVDB(self, cache=True):
	
		t = tvdb_api.Tvdb(cache=cache, lastTimeout=sickbeard.LAST_TVDB_TIMEOUT)
		
		showObj = t[self.tvdbid]
		
		Logger().log(str(self.tvdbid) + ": Loading all episodes from theTVDB...")
		
		for season in showObj:
			# ignore specials for now
			if season == 0:
				continue
			for episode in showObj[season]:
				if episode == 0:
					continue
				ep = self.getEpisode(season, episode)
				if ep == None:
					Logger().log(str(self.tvdbid) + ": Creating episode object for " + str(season) + "x" + str(episode), DEBUG)
					try:
						ep = TVEpisode(self, season, episode)
					except exceptions.EpisodeNotFoundException:
						Logger().log(str(self.tvdbid) + ": TVDB object for " + str(season) + "x" + str(episode) + " is incomplete, skipping this episode")
						continue
					#self.setEpisode(season, episode, ep)
				else:
					ep.loadFromTVDB()
				
				with ep.lock:
					Logger().log(str(self.tvdbid) + ": Loading info from theTVDB for episode " + str(season) + "x" + str(episode), DEBUG)
					ep.loadFromTVDB(season, episode, cache)
					ep.saveToDB()

	def loadLatestFromTVRage(self):
		
		try:
			# load the tvrage object
			tvr = tvrage.TVRage(self)
			
			# check for sync
			if not tvr.checkSync():
				Logger().log("TVDB and TVRage are out of sync, not using TVRage data")
				return
			
			# store it to db
			tvr.saveToDB()
			
			newEp = tvr.getEpisode()
			
			if newEp != None:
				Logger().log("TVRage gave us an episode object - saving it for now", DEBUG)
				newEp.saveToDB()
				#self.setEpisode(newEp.season, newEp.episode, newEp)
			
			# make an episode out of it
		except exceptions.TVRageException as e:
			Logger().log("Unable to add TVRage info: " + str(e), ERROR)
			


	# make a TVEpisode object from a media file
	def makeEpFromFile(self, file):

		if not os.path.isfile(file):
			Logger().log(str(self.tvdbid) + ": That isn't even a real file dude... " + file)
			return None

		Logger().log(str(self.tvdbid) + ": Creating episode object from " + file, DEBUG)

		result = tvnamer.processSingleName(file)

		showInfo = None

		if result != None:

			# for now lets assume that any show in the show dir belongs to the right place
			showInfo = (self.tvdbid, self.name)
			if 0 == 1:

				try:
					t = tvdb_api.Tvdb(custom_ui=classes.ShowListUI, lastTimeout=sickbeard.LAST_TVDB_TIMEOUT)
					showObj = t[result["file_seriesname"]]
					showInfo = (int(showObj["id"]), showObj["seriesname"])
				except tvdb_exceptions.tvdb_shownotfound:
					Logger().log("Unable to figure out which show this is from the name: "+result["file_seriesname"]+". Assuming it belongs to us.", ERROR)
					try:
						showObj = t[self.tvdbid]
						showInfo = (int(showObj["id"]), showObj["seriesname"])
					except tvdb_exceptions.tvdb_shownotfound:
						raise exceptions.ShowNotFoundException("TVDB returned zero results for show "+result["file_seriesname"])
				except (tvdb_exceptions.tvdb_error, IOError) as e:
					Logger().log("Error connecting to TVDB, trying to search the DB instead: "+ str(e), ERROR)
					
					showInfo = helpers.searchDBForShow(result["file_seriesname"])
				
			if showInfo == None:
				Logger().log("Unable to figure out what show "+result["file_seriesname"] + "is, skipping", ERROR)
				return None
			
			if showInfo[0] != int(self.tvdbid):
				Logger().log("Show doesn't seem to match, assuming it is the show from the folder it belongs to", ERROR)
				raise exceptions.WrongShowException("Expected "+str(self.tvdbid)+" but got "+str(showObj["id"]))
			
			season = int(result["seasno"])
			
			rootEp = None
	
			for curEp in result["epno"]:
	
				episode = int(curEp)
				
				Logger().log(str(self.tvdbid) + ": " + file + " parsed to " + showInfo[1] + " " + str(season) + "x" + str(episode), DEBUG)
	
				curEp = self.getEpisode(season, episode)
				
				if curEp == None:
					try:
						curEp = TVEpisode(self, season, episode, file)
					except exceptions.EpisodeNotFoundException:
						Logger().log(str(self.tvdbid) + ": Unable to figure out what this file is, skipping", ERROR)
						continue
				else:
					with curEp.lock:
						curEp.location = file
						curEp.checkForMetaFiles()
						
				if rootEp == None:
					rootEp = curEp
				else:
					rootEp.relatedEps.append(curEp)

				if sickbeard.helpers.isMediaFile(file):
					with curEp.lock:
						curEp.status = DOWNLOADED
						Logger().log("STATUS: we have an associated file, so setting the status to DOWNLOADED/" + str(DOWNLOADED), DEBUG)
							
				with curEp.lock:
					curEp.saveToDB()
					
				#self.setEpisode(season, episode, curEp)

			# creating metafiles on the root should be good enough
			if rootEp != None:
				with rootEp.lock:
					rootEp.createMetaFiles()


		return None

	
	def _getDB(self):
		self.db = db.DBConnection()
		

	def loadFromDB(self):

		Logger().log(str(self.tvdbid) + ": Loading show info from database")

		myDB = db.DBConnection()
		
		sqlResults = myDB.select("SELECT * FROM tv_shows WHERE tvdb_id = " + str(self.tvdbid))

		if len(sqlResults) > 1:
			raise exceptions.MultipleDBShowsException()
		elif len(sqlResults) == 0:
			Logger().log(str(self.tvdbid) + ": Unable to find the show in the database")
			return
		else:
			if self.name == "":
				self.name = sqlResults[0]["show_name"]
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
			self.quality = int(sqlResults[0]["quality"])
			self.predownload = int(sqlResults[0]["predownload"])
			self.seasonfolders = int(sqlResults[0]["seasonfolders"])
	
	def loadFromTVDB(self, cache=True):

		Logger().log(str(self.tvdbid) + ": Loading show info from theTVDB") 

		t = tvdb_api.Tvdb(cache=cache, lastTimeout=sickbeard.LAST_TVDB_TIMEOUT)
		myEp = t[self.tvdbid]
		
		if myEp["airs_dayofweek"] != None and myEp["airs_time"] != None:
			self.airs = myEp["airs_dayofweek"] + " " + myEp["airs_time"]

		if self.airs == None:
			self.airs = ""

		if myEp["status"] != None:
			self.status = myEp["status"]

		if self.status == None:
			self.status = ""
			
		self.saveToDB()
	
	
	def loadNFO (self):

		Logger().log(str(self.tvdbid) + ": Loading show info from NFO")

		xmlFile = os.path.join(self._location, "tvshow.nfo")
		xmlFileObj = open(xmlFile, "r")
		
		try:
			nfoData = " ".join(xmlFileObj.readlines()).replace("&#x0D;","").replace("&#x0A;","")
			showSoup = BeautifulStoneSoup(nfoData, convertEntities=BeautifulStoneSoup.XML_ENTITIES)
		except HTMLParseError as e:
			Logger().log("There was an error parsing your existing tvshow.nfo file: " + str(e), ERROR)
			Logger().log("Attempting to rename it to tvshow.nfo.old", DEBUG)
			try:
				os.rename(xmlFile, xmlFile + ".old")
			except Exception as e:
				Logger().log("Failed to rename your tvshow.nfo file - you need to delete it or fix it: " + str(e), ERROR)
			raise exceptions.NoNFOException("Invalid info in tvshow.nfo")

		if showSoup.title == None or showSoup.tvdbid == None:
			raise exceptions.NoNFOException("Invalid info in tvshow.nfo (missing name or id)")
		
		self.name = showSoup.title.string
		self.tvdbid = int(showSoup.tvdbid.string)
		if showSoup.studio != None:
			self.network = showSoup.studio.string
		if self.network == None:
			self.network = ""
		if showSoup.genre != None:
			self.genre = showSoup.genre.string
		if self.genre == None:
			self.genre = ""

		# TODO: need to validate the input, I'm assuming it's good until then

		
	def nextEpisode(self):
	
		Logger().log(str(self.tvdbid) + ": Finding the episode which airs next", DEBUG) 

		myDB = db.DBConnection()
		sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = " + str(self.tvdbid) + " AND airdate >= " + str(datetime.date.today().toordinal()) + " AND status = " + str(UNAIRED) + " ORDER BY airdate ASC LIMIT 1")
	
		if sqlResults == None or len(sqlResults) == 0:
			Logger().log(str(self.tvdbid) + ": No episode found... need to implement tvrage and also show status", DEBUG)
			return None
		elif len(sqlResults) > 1:
			Logger().log(str(self.tvdbid) + ": This should never happen, I have LIMIT 1 in the SQL query?!?", ERROR)
			raise Exception("WTF")
		else:
			Logger().log(str(self.tvdbid) + ": Found episode " + str(sqlResults[0]["season"]) + "x" + str(sqlResults[0]["episode"]), DEBUG)
			nextEp = self.getEpisode(int(sqlResults[0]["season"]), int(sqlResults[0]["episode"]), True)
			return nextEp

		# if we didn't get an episode then try getting one from tvrage
		
		# load tvrage info
		
		# extract NextEpisode info
		
		# verify that we don't have it in the DB somehow (ep mismatch)

			
	# clears all my local episode object references, they'll need to be reloaded from the DB
	def flushEpisodes(self):
		self.episodes = {}
			

	def deleteShow(self):
		
		myDB = db.DBConnection()
		myDB.action("DELETE FROM tv_episodes WHERE showid = " + str(self.tvdbid))
		myDB.action("DELETE FROM tv_shows WHERE tvdb_id = " + str(self.tvdbid))
		
		# remove self from show list
		sickbeard.showList = [x for x in sickbeard.showList if x.tvdbid != self.tvdbid]
		
	def refreshDir(self):

		# make sure the show dir is where we think it is
		if not os.path.isdir(self.location):
			return False
		
		# run through all locations from DB, check that they exist
		Logger().log(str(self.tvdbid) + ": Loading all episodes with a location from the database")
		
		myDB = db.DBConnection()
		sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = " + str(self.tvdbid) + " AND location != ''")
		
		for ep in sqlResults:
			curLoc = os.path.normpath(ep["location"]) #TRYIT
			season = int(ep["season"])
			episode = int(ep["episode"])
			
			curEp = self.getEpisode(season, episode, True)
			
			# if the path doesn't exist
			# or if there's no season folders and it's not inside our show dir 
			# or if there are season folders and it's in the main dir:
			# or if it's not in our show dir at all
			if not os.path.isfile(curLoc) or \
			(not self.seasonfolders and os.path.normpath(os.path.dirname(curLoc)) != os.path.normpath(self.location)) or \
			(self.seasonfolders and os.path.normpath(os.path.dirname(curLoc)) == os.path.normpath(self.location)) or \
			os.path.normpath(os.path.commonprefix([os.path.normpath(x) for x in (curLoc, self.location)])) != os.path.normpath(self.location):
			
				Logger().log(str(self.tvdbid) + ": Location for " + str(season) + "x" + str(episode) + " doesn't exist, removing it and changing our status to SKIPPED", DEBUG)
				with curEp.lock:
					curEp.location = ''
					if curEp.status == DOWNLOADED:
						curEp.status = SKIPPED
					curEp.saveToDB()

		
		# load from dir
		self.loadEpisodesFromDir()
			
			
	def fixEpisodeNames(self):
		
		# load episodes from my folder
		self.loadEpisodesFromDir()
		
		Logger().log(str(self.tvdbid) + ": Loading all episodes with a location from the database")
		
		myDB = db.DBConnection()
		sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = " + str(self.tvdbid) + " AND location != ''")
		
		# build list of locations
		fileLocations = {}
		for epResult in sqlResults:
			goodLoc = os.path.normpath(epResult["location"])
			goodSeason = int(epResult["season"])
			goodEpisode = int(epResult["episode"])
			if fileLocations.has_key(goodLoc):
				fileLocations[goodLoc].append((goodSeason, goodEpisode))
			else:
				fileLocations[goodLoc] = [(goodSeason, goodEpisode)]
		
		Logger().log("File results: " + str(fileLocations), DEBUG)

		for curLocation in fileLocations:
			
			epList = fileLocations[curLocation]
			
			# get the root episode and add all related episodes to it
			rootEp = None
			for myEp in epList:
				curEp = self.getEpisode(myEp[0], myEp[1], True)
				if rootEp == None:
					rootEp = curEp
					rootEp.relatedEps = []
				else:
					rootEp.relatedEps.append(curEp)
			
			goodName = rootEp.prettyName()
			actualName = os.path.splitext(os.path.basename(curLocation))

			if goodName == actualName[0]:
				Logger().log(str(self.tvdbid) + ": File " + rootEp.location + " is already named correctly, skipping", DEBUG)
				continue
			
			with rootEp.lock:
				result = processTV.renameFile(rootEp.location, rootEp.prettyName())
				if result != False:
					rootEp.location = result
					for relEp in rootEp.relatedEps:
						relEp.location = result
			
			fileList = glob.glob(os.path.join(rootEp.show.location, actualName[0] + "*"))

			for file in fileList:
				result = processTV.renameFile(file, rootEp.prettyName())
				if result == False:
					Logger().log(str(self.tvdbid) + ": Unable to rename file "+file, ERROR)
			
			for curEp in [rootEp]+rootEp.relatedEps:
				curEp.checkForMetaFiles()
			
			#if os.path.isfile(os.path.join(rootEp.show.location, rootEp.prettyName() + ".nfo")):
			#	Logger().log(str(self.tvdbid) + ": Renamed NFO successfully")
			#	with rootEp.lock:
			#		rootEp.hasnfo = True
			#		for relEp in rootEp.relatedEps:
			#			relEp.hasnfo = True

			#if os.path.isfile(os.path.join(rootEp.show.location, rootEp.prettyName() + ".tbn")):
			#	Logger().log(str(self.tvdbid) + ": Renamed TBN successfully")
			#	with rootEp.lock:
			#		rootEp.hastbn = True
			#		for relEp in rootEp.relatedEps:
			#			relEp.hastbn = True

			with rootEp.lock:
				rootEp.saveToDB()
				for relEp in rootEp.relatedEps:
					relEp.saveToDB()
		
			
	def saveToDB(self):

		Logger().log(str(self.tvdbid) + ": Saving show info to database", DEBUG)

		myDB = db.DBConnection()
		sqlResults = myDB.select("SELECT * FROM tv_shows WHERE tvdb_id = " + str(self.tvdbid))

		# use this list regardless of whether it's in there or not
		sqlValues = [self.name, self.tvdbid, self._location, self.network, self.genre, self.runtime, self.quality, self.predownload, self.airs, self.status, self.seasonfolders]
		
		# if it's not in there then insert it
		if len(sqlResults) == 0:
			sql = "INSERT INTO tv_shows (show_name, tvdb_id, location, network, genre, runtime, quality, predownload, airs, status, seasonfolders) VALUES (?,?,?,?,?,?,?,?,?,?,?)"

		# if it's already there then just change it
		elif len(sqlResults) == 1:
			sql = "UPDATE tv_shows SET show_name=?, tvdb_id=?, location=?, network=?, genre=?, runtime=?, quality=?, predownload=?, airs=?, status=?, seasonfolders=? WHERE tvdb_id=?"
			sqlValues += [self.tvdbid]
		else:
			raise exceptions.MultipleDBShowsException("Multiple records for a single show")
		
		myDB.action(sql, sqlValues)
		
		
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
		toReturn += "genre: " + self.genre + "\n"
		toReturn += "runtime: " + str(self.runtime) + "\n"
		toReturn += "quality: " + str(self.quality) + "\n"
		toReturn += "predownload: " + str(self.predownload) + "\n"
		return toReturn

		
		
		
		
		
		
class TVEpisode:

	def __init__(self, show, season, episode, file=""):
	
		self.name = ""
		self.season = season
		self.episode = episode
		self.description = ""
		self.airdate = datetime.date.fromordinal(1)
		self.hasnfo = False
		self.hastbn = False
		self.status = UNKNOWN
		Logger().log("status starts unknown", DEBUG)

		self.tvdbid = 0

		self.show = show
		self.location = file
		
		self.db = None
		self.lock = threading.Lock()
		
		self._getDB()
		self.specifyEpisode(self.season, self.episode)

		self.relatedEps = []

		self.checkForMetaFiles()

	def checkForMetaFiles(self): 
		
		# check for nfo and tbn
		if os.path.isfile(os.path.join(self.show.location, self.location)):
			if os.path.isfile(os.path.join(self.show.location, helpers.replaceExtension(self.location, 'nfo'))):
				self.hasnfo = True
				
			if os.path.isfile(os.path.join(self.show.location, helpers.replaceExtension(self.location, 'tbn'))):
				self.hastbn = True


		
	def _getDB(self):
		self.db = db.DBConnection()
	
	
	def specifyEpisode(self, season, episode):
		
		sqlResult = self.loadFromDB(season, episode)
		
		if os.path.isfile(self.location):
			try:
				self.loadFromNFO(self.location)
			except exceptions.NoNFOException:
				Logger().log(str(self.show.tvdbid) + ": There was an error loading the NFO for episode " + str(season) + "x" + str(episode), ERROR)
				pass
		
		# if we tried loading it from NFO and didn't find the NFO, use TVDB
		if self.hasnfo == False:
			result = self.loadFromTVDB(season, episode)
			
			# if we failed TVDB, NFO *and* SQL then fail
			if result == False and not sqlResult:
				raise exceptions.EpisodeNotFoundException("Couldn't find episode " + str(season) + "x" + str(episode))
		
		self.saveToDB()
		
	
	def loadFromDB(self, season, episode):

		Logger().log(str(self.show.tvdbid) + ": Loading episode details from DB for episode " + str(season) + "x" + str(episode), DEBUG)

		myDB = db.DBConnection()
		sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = " + str(self.show.tvdbid) + " AND season = " + str(season) + " AND episode = " + str(episode))

		if len(sqlResults) > 1:
			raise exceptions.MultipleDBEpisodesException("Your DB has two records for the same show somehow.")
		elif len(sqlResults) == 0:
			Logger().log(str(self.show.tvdbid) + ": Episode " + str(self.season) + "x" + str(self.episode) + " not found in the database", DEBUG) 
			return False
		else:
			#NAMEIT Logger().log("AAAAA from" + str(self.season)+"x"+str(self.episode) + " -" + self.name + " to " + str(sqlResults[0]["name"]))
			if sqlResults[0]["name"] != None:
				self.name = sqlResults[0]["name"] 
			self.season = season
			self.episode = episode
			self.description = sqlResults[0]["description"]
			if self.description == None:
				self.description = ""
			self.airdate = datetime.date.fromordinal(int(sqlResults[0]["airdate"]))
			Logger().log("1 Status changes from " + str(self.status) + " to " + str(sqlResults[0]["status"]), DEBUG)
			self.status = int(sqlResults[0]["status"])
			
			# don't overwrite my location
			if sqlResults[0]["location"] != "" and sqlResults[0]["location"] != None:
				self.location = os.path.normpath(sqlResults[0]["location"])
			
			self.tvdbid = int(sqlResults[0]["tvdbid"])
			
			return True
	
	
	def loadFromTVDB(self, season=None, episode=None, cache=True):

		if season == None:
			season = self.season
		if episode == None:
			episode = self.episode

		Logger().log(str(self.show.tvdbid) + ": Loading episode details from theTVDB for episode " + str(season) + "x" + str(episode), DEBUG)

		try:
			t = tvdb_api.Tvdb(cache=cache, lastTimeout=sickbeard.LAST_TVDB_TIMEOUT)
			myEp = t[self.show.tvdbid][season][episode]
		except (tvdb_exceptions.tvdb_error, IOError):
			# if the episode is already valid just log it, if not throw it up
			if self.name != "" and self.airdate != datetime.date.fromordinal(1):
				Logger().log("TVDB timed out but we have enough info from other sources, allowing the error", ERROR)
				return
			else:
				Logger().log("TVDB timed out, unable to create the episode", ERROR)
				return False
		except (tvdb_exceptions.tvdb_episodenotfound, tvdb_exceptions.tvdb_seasonnotfound):
			Logger().log("Unable to find the episode on tvdb... has it been removed? Should I delete from db?")
			return
			
		if myEp["episodename"] == None or myEp["firstaired"] == None:
			return False
		
		#NAMEIT Logger().log("BBBBBBBB from " + str(self.season)+"x"+str(self.episode) + " -" +self.name+" to "+myEp["episodename"])
		self.name = myEp["episodename"]
		self.season = season
		self.episode = episode
		self.description = myEp["overview"]
		if self.description == None:
			self.description = ""
		rawAirdate = [int(x) for x in myEp["firstaired"].split("-")]
		self.airdate = datetime.date(rawAirdate[0], rawAirdate[1], rawAirdate[2])
		self.tvdbid = myEp["id"]

		Logger().log(str(self.show.tvdbid) + ": Setting status for " + str(season) + "x" + str(episode) + " based on status " + statusStrings[self.status] + " and existence of " + self.location, DEBUG)
		
		if not os.path.isfile(os.path.join(self.show.location, self.location)):

			# if we don't have the file and it hasn't aired yet set the status to UNAIRED
			if self.airdate >= datetime.date.today() and self.status != SNATCHED and self.status != PREDOWNLOADED:
				Logger().log("2 Status changes from " + str(self.status) + " to " + str(UNAIRED), DEBUG)
				self.status = UNAIRED
				
			else:

				# if we haven't downloaded it then mark it as missed
				if self.status == UNAIRED:
					Logger().log("3 Status changes from " + str(self.status) + " to " + str(MISSED), DEBUG)
					self.status = MISSED

				# if it's an old episode we don't have then assume we SKIPPED it
				elif self.status == UNKNOWN:
					Logger().log("4 Status changes from " + str(self.status) + " to " + str(SKIPPED), DEBUG)
					self.status = SKIPPED

		# if we have a media file then it's downloaded
		elif sickbeard.helpers.isMediaFile(self.location):
			Logger().log("5 Status changes from " + str(self.status) + " to " + str(DOWNLOADED), DEBUG)
			self.status = DOWNLOADED

		# shouldn't get here probably
		else:
			Logger().log("6 Status changes from " + str(self.status) + " to " + str(UNKNOWN), DEBUG)
			self.status = UNKNOWN

		
		# hasnfo, hastbn, status?
		
		
	def loadFromNFO(self, location):

		Logger().log(str(self.show.tvdbid) + ": Loading episode details from the NFO file associated with " + location, DEBUG)

		self.location = location
	
		if self.location != "":
		
			if self.status == UNKNOWN:
				if sickbeard.helpers.isMediaFile(self.location):
					Logger().log("7 Status changes from " + str(self.status) + " to " + str(DOWNLOADED), DEBUG)
					self.status = DOWNLOADED
		
			nfoFile = sickbeard.helpers.replaceExtension(self.location, "nfo")
			Logger().log(str(self.show.tvdbid) + ": Using NFO name " + nfoFile, DEBUG)
			#nfoFile = os.path.join(self.show.location, nfoFilename)
			
			if os.path.isfile(nfoFile):
				nfoFileObj = open(nfoFile, "r")
				try:
					nfoData = " ".join(nfoFileObj.readlines()).replace("&#x0D;","").replace("&#x0A;","")
					showSoup = BeautifulStoneSoup(nfoData, convertEntities=BeautifulStoneSoup.XML_ENTITIES)
				except ValueError as e:
					Logger().log("Error loading the NFO, skipping for now: " + str(e), ERROR) #TODO: figure out what's wrong and fix it
					raise exceptions.NoNFOException("Error in NFO format")

				for epDetails in showSoup.findAll('episodedetails'):
					if isinstance(epDetails, NavigableString):
						continue
				
					if epDetails.season.string == None or int(epDetails.season.string) != self.season or epDetails.episode.string == None or int(epDetails.episode.string) != self.episode:
						Logger().log(str(self.show.tvdbid) + ": NFO has an <episodedetails> block for a different episode - wanted " + str(self.season) + "x" + str(self.episode) + " but got " + str(epDetails.season.string) + "x" + str(epDetails.episode.string), DEBUG)
						continue
				
					if epDetails.title.string == None or epDetails.aired.string == None:
						raise exceptions.NoNFOException("Error in NFO format (missing episode title or airdate)")
				
					if epDetails.title.string != None:
						#NAMEIT Logger().log("CCCCCCC from " + str(self.season)+"x"+str(self.episode) + " -" + str(self.name) + " to " + str(showSoup.title.string))
						self.name = epDetails.title.string
					self.episode = int(epDetails.episode.string)
					self.season = int(epDetails.season.string)
					self.description = epDetails.plot.string
					if self.description == None:
						self.description = ""
					rawAirdate = [int(x) for x in epDetails.aired.string.split("-")]
					self.airdate = datetime.date(rawAirdate[0], rawAirdate[1], rawAirdate[2])
					self.hasnfo = True
			else:
				self.hasnfo = False
			
			if os.path.isfile(sickbeard.helpers.replaceExtension(nfoFile, "tbn")):
				self.hastbn = True
			else:
				self.hastbn = False


	def __str__ (self):

		toReturn = ""
		toReturn += self.show.name + " - " + str(self.season) + "x" + str(self.episode) + " - " + self.name + "\n"
		toReturn += "location: " + os.path.join(self.show.location, self.location) + "\n"
		toReturn += "description: " + self.description + "\n"
		toReturn += "airdate: " + str(self.airdate.toordinal()) + " (" + str(self.airdate) + ")\n"
		toReturn += "hasnfo: " + str(self.hasnfo) + "\n"
		toReturn += "hastbn: " + str(self.hastbn) + "\n"
		toReturn += "status: " + str(self.status) + "\n"
		return toReturn

		
	def createMetaFiles(self, force=False):
		
		if sickbeard.CREATE_METADATA != True:
			return
		
		epsToWrite = [self] + self.relatedEps

		try:
			t = tvdb_api.Tvdb(actors=True, lastTimeout=sickbeard.LAST_TVDB_TIMEOUT)
		except tvdb_exceptions.tvdb_error as o:
			Logger().log("Unable to connect to TVDB while creating meta files - skipping", ERROR)
			return
		
		nfo = Document()
		myShow = t[self.show.tvdbid]

		if len(epsToWrite) > 1:
			dummyNode = nfo.createElement("xbmcmultiepisode")
			nfo.appendChild(dummyNode)
			rootNode = dummyNode
		else:
			rootNode = nfo
		
		needsNFO = not self.hasnfo
		if force:
			needsNFO = True

		# if we're not forcing then we want to make an NFO unless every related ep already has one
		else:
			for curEp in epsToWrite:
				if not curEp.hasnfo:
					break
				needsNFO = False

		thumbFilename = None

		# write an NFO containing info for all matching episodes
		for curEpToWrite in epsToWrite:
		
			try:
				myEp = myShow[curEpToWrite.season][curEpToWrite.episode]
			except tvdb_exceptions.tvdb_episodenotfound:
				Logger().log("Unable to find episode " + str(curEpToWrite.season) + "x" + str(curEpToWrite.episode) + " on tvdb... has it been removed? Should I delete from db?")
				return False
			
			if myEp["episodename"] == None or myEp["firstaired"] == None:
				return False
				
			if curEpToWrite == self:
				thumbFilename = myEp["filename"]
				
			if not needsNFO:
				continue
			
			episode = nfo.createElement("episodedetails")
			rootNode.appendChild(episode)
	
			title = nfo.createElement("title")
			if curEpToWrite.name != None:
				title.appendChild(nfo.createTextNode(curEpToWrite.name))
			episode.appendChild(title)
	
			season = nfo.createElement("season")
			season.appendChild(nfo.createTextNode(str(curEpToWrite.season)))
			episode.appendChild(season)
	
			episodenum = nfo.createElement("episode")
			episodenum.appendChild(nfo.createTextNode(str(curEpToWrite.episode)))
			episode.appendChild(episodenum)
			
			aired = nfo.createElement("aired")
			aired.appendChild(nfo.createTextNode(str(curEpToWrite.airdate)))
			episode.appendChild(aired)
	
			plot = nfo.createElement("plot")
			if curEpToWrite.description != None:
				plot.appendChild(nfo.createTextNode(curEpToWrite.description))
			episode.appendChild(plot)
	
			displayseason = nfo.createElement("displayseason")
			if myEp.has_key('airsbefore_season'):
				displayseason_text = myEp['airsbefore_season']
				if displayseason_text != None:
					displayseason.appendChild(nfo.createTextNode(displayseason_text))
				episode.appendChild(displayseason)
	
			displayepisode = nfo.createElement("displayepisode")
			if myEp.has_key('airsbefore_episode'):
				displayepisode_text = myEp['airsbefore_episode']
				if displayepisode_text != None:
					displayepisode.appendChild(nfo.createTextNode(displayepisode_text))
				episode.appendChild(displayepisode)
	
			thumb = nfo.createElement("thumb")
			thumb_text = myEp['filename']
			if thumb_text != None:
				thumb.appendChild(nfo.createTextNode(thumb_text))
			episode.appendChild(thumb)
	
			watched = nfo.createElement("watched")
			watched.appendChild(nfo.createTextNode('false'))
			episode.appendChild(watched)
	
			credits = nfo.createElement("credits")
			credits_text = myEp['writer']
			if credits_text != None:
				credits.appendChild(nfo.createTextNode(credits_text))
			episode.appendChild(credits)
	
			director = nfo.createElement("director")
			director_text = myEp['director']
			if director_text != None:
				director.appendChild(nfo.createTextNode(director_text))
			episode.appendChild(director)
	
			gueststar_text = myEp['gueststars']
			if gueststar_text != None:
				for actor in gueststar_text.split('|'):
					cur_actor = nfo.createElement("actor")
					cur_actor_name = nfo.createElement("name")
					cur_actor_name.appendChild(nfo.createTextNode(actor))
					cur_actor.appendChild(cur_actor_name)
					episode.appendChild(cur_actor)
	
			for actor in myShow['_actors']:
				cur_actor = nfo.createElement("actor")

				cur_actor_name = nfo.createElement("name")
				cur_actor_name.appendChild(nfo.createTextNode(actor['name']))
				cur_actor.appendChild(cur_actor_name)

				cur_actor_role = nfo.createElement("role")
				cur_actor_role_text = actor['role']
				if cur_actor_role_text != None:
						cur_actor_role.appendChild(nfo.createTextNode(cur_actor_role_text))
				cur_actor.appendChild(cur_actor_role)

				cur_actor_thumb = nfo.createElement("thumb")
				cur_actor_thumb_text = actor['image']
				if cur_actor_thumb_text != None:
						cur_actor_thumb.appendChild(nfo.createTextNode(cur_actor_thumb_text))
				cur_actor.appendChild(cur_actor_thumb)

				episode.appendChild(cur_actor)
					
			Logger().log("Resulting XML episodedetails node: " + str(episode))
		
			if os.path.isfile(self.location):
				nfoFilename = helpers.replaceExtension(self.location, 'nfo')
			else:
				nfoFilename = helpers.sanitizeFileName(self.prettyName() + '.nfo')
	
			Logger().log('Writing nfo to ' + os.path.join(self.show.location, nfoFilename))
			nfo_fh = open(os.path.join(self.show.location, nfoFilename), 'w')
			nfo_fh.write(nfo.toxml(encoding="UTF-8"))
			nfo_fh.close()
			
			for epToWrite in epsToWrite:
				epToWrite.hasnfo = True
		# end if needsNFO

		if not self.hastbn or force:
			if thumbFilename != None:
				if os.path.isfile(self.location):
					tbnFilename = helpers.replaceExtension(self.location, 'tbn')
				else:
					tbnFilename = helpers.sanitizeFileName(self.prettyName() + '.tbn')
				Logger().log('Writing thumb to ' + os.path.join(self.show.location, tbnFilename))
				try:
					urllib.urlretrieve(thumbFilename, os.path.join(self.show.location, tbnFilename))
				except IOError:
					Logger().log("Unable to download thumbnail from "+thumbFilename, ERROR)
					return
				#TODO: check that it worked
				self.hastbn = True


		
	def saveToDB(self):
	
		Logger().log(str(self.show.tvdbid) + ": Saving episode details to database", DEBUG)

		Logger().log("STATUS IS " + str(self.status), DEBUG)
	
		myDB = db.DBConnection()
		sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = " + str(self.show.tvdbid) + " AND episode = " + str(self.episode) + " AND season = " + str(self.season))

		# use this list regardless of whether it's in there or not
		sqlValues = [self.show.tvdbid, self.tvdbid, self.name, self.season, self.episode, self.description, self.airdate.toordinal(), self.hasnfo, self.hastbn, self.status, self.location]
		
		# if it's not in there then insert it
		if len(sqlResults) == 0:
			sql = "INSERT INTO tv_episodes (showid, tvdbid, name, season, episode, description, airdate, hasnfo, hastbn, status, location) VALUES (?,?,?,?,?,?,?,?,?,?,?)"

		# if it's already there then just change it
		elif len(sqlResults) == 1:
			sql = "UPDATE tv_episodes SET showid=?, tvdbid=?, name=?, season=?, episode=?, description=?, airdate=?, hasnfo=?, hastbn=?, status=?, location=? WHERE showid=? AND season=? AND episode=?"
			sqlValues += [self.show.tvdbid, self.season, self.episode]
		else:
			raise sickbeard.exceptions.LaterException("Multiple records for a single episode")
		
		myDB.action(sql, sqlValues)
		
		
	def fullPath (self):
		if self.location == None or self.location == "":
			return None
		else:
			return os.path.join(self.show.location, self.location)
		
	def prettyName (self):
		
		goodName = self.name
		for relEp in self.relatedEps:
			goodName += " & " + relEp.name
		
		goodEpString = "x{0:0>2}".format(self.episode)
		for relEp in self.relatedEps:
			goodEpString += "x{0:0>2}".format(relEp.episode)
		return "{0} - {1}{2} - {3}".format(self.show.name, self.season, goodEpString, unicode(goodName).encode('ascii', 'ignore'))
		
		
		
		
