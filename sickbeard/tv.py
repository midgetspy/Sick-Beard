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

import sickbeard

import xml.etree.cElementTree as etree

from lib.BeautifulSoup import BeautifulStoneSoup, NavigableString, SGMLParseError
from lib.tvdb_api import tvdb_api, tvnamer, tvdb_exceptions
from lib.tvnamer.utils import FileParser
from lib.tvnamer import tvnamer_exceptions

from sickbeard import db
from sickbeard import helpers
from sickbeard import exceptions
from sickbeard import processTV
from sickbeard import classes
from sickbeard import tvrage

from common import *
from sickbeard import logger

class TVShow(object):

	def __init__ (self, showdir):
	
		self._location = os.path.normpath(showdir)
		self.name = ""
		self.tvdbid = 0
		self.tvrid = 0
		self.network = ""
		self.genre = ""
		self.runtime = 0
		self.quality = int(sickbeard.QUALITY_DEFAULT)
		self.seasonfolders = int(sickbeard.SEASON_FOLDERS_DEFAULT)
		
		self.status = ""
		self.airs = ""
		self.startyear = 0
		self.paused = 0

		self.lock = threading.Lock()
		self._isDirGood = False
		
		self.episodes = {}

		# if the location doesn't exist, try the DB
		if not os.path.isdir(self._location):
			
			self._isDirGood = False
			
			logger.log("The show dir doesn't exist! This show will be inactive until the dir is created.", logger.ERROR)
			
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

			self.loadFromDB()
	
		#logger.log(str(self.tvdbid) + ": Loading extra show info from theTVDB")
		#try:
		#	self.loadFromTVDB()
		#except tvdb_exceptions.tvdb_error as e:
		#	logger.log("There was a problem loading the details from TVDB (server down?)", logger.ERROR)
		#	if str(e) == "Could not connect to server: <urlopen error timed out>":
		#		sickbeard.LAST_TVDB_TIMEOUT = datetime.datetime.now()

		otherShow = helpers.findCertainShow(sickbeard.showList, self.tvdbid)
		if otherShow != None:
			raise exceptions.MultipleShowObjectsException("Can't create a show if it already exists")
		
		try:
			t = tvdb_api.Tvdb(lastTimeout=sickbeard.LAST_TVDB_TIMEOUT, apikey=sickbeard.TVDB_API_KEY)
			t[self.tvdbid]
		except tvdb_exceptions.tvdb_shownotfound as e:
			raise exceptions.ShowNotFoundException(str(e))
		except tvdb_exceptions.tvdb_error as e:
			logger.log("Unable to contact theTVDB.com, it might be down: "+str(e), logger.ERROR)
		
		self.saveToDB()
	
	
	def _getLocation(self):
		if os.path.isdir(self._location):
			return self._location
		else:
			raise exceptions.ShowDirNotFoundException("Show folder doesn't exist, you shouldn't be using it")
		
		if self._isDirGood:
			return self._location
		else:
			raise exceptions.NoNFOException("Show folder doesn't exist, you shouldn't be using it")

	def _setLocation(self, newLocation):
		logger.log("Setter sets location to " + newLocation)
		if os.path.isdir(newLocation) and os.path.isfile(os.path.join(newLocation, "tvshow.nfo")):
			self._location = newLocation
			self._isDirGood = True
		else:
			raise exceptions.NoNFOException("Invalid folder for the show!")

	location = property(_getLocation, _setLocation)

	# delete references to anything that's not in the internal lists
	def flushEpisodes(self):
		
		for curSeason in self.episodes:
			for curEp in self.episodes[curSeason]:
				myEp = self.episodes[curSeason][curEp]
				if myEp not in sickbeard.comingList and \
				myEp not in sickbeard.airingList and \
				myEp not in sickbeard.missingList:
					self.episodes[curSeason][curEp] = None
					del myEp
			
	
	def getEpisode(self, season, episode, file=None, noCreate=False):

		#return TVEpisode(self, season, episode)
	
		if not season in self.episodes:
			self.episodes[season] = {}
		
		ep = None
		
		if not episode in self.episodes[season] or self.episodes[season][episode] == None:
			if noCreate:
				return None
			
			logger.log(str(self.tvdbid) + ": An object for episode " + str(season) + "x" + str(episode) + " didn't exist in the cache, trying to create it", logger.DEBUG)

			if file != None:
				ep = TVEpisode(self, season, episode, file)
			else:
				ep = TVEpisode(self, season, episode)
			
			if ep != None:
				self.episodes[season][episode] = ep
		
		return self.episodes[season][episode]


	def writeEpisodeNFOs (self):
		
		if not os.path.isdir(self._location):
			logger.log(str(self.tvdbid) + ": Show dir doesn't exist, skipping NFO generation")
			return
		
		logger.log(str(self.tvdbid) + ": Writing NFOs for all episodes")
		
		myDB = db.DBConnection()
		sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = " + str(self.tvdbid) + " AND location != ''")
		
		for epResult in sqlResults:
			logger.log(str(self.tvdbid) + ": Retrieving/creating episode " + str(epResult["season"]) + "x" + str(epResult["episode"]), logger.DEBUG)
			curEp = self.getEpisode(epResult["season"], epResult["episode"])
			curEp.createMetaFiles()


	# find all media files in the show folder and create episodes for as many as possible
	def loadEpisodesFromDir (self):

		if not os.path.isdir(self._location):
			logger.log(str(self.tvdbid) + ": Show dir doesn't exist, not loading episodes from disk")
			return
		
		logger.log(str(self.tvdbid) + ": Loading all episodes from the show directory " + self._location)

		# get file list
		files = []
		if not self.seasonfolders:
			files = os.listdir(unicode(self._location))
		else:
			for curFile in os.listdir(unicode(self._location)):
				if not os.path.isdir(os.path.join(self._location, curFile)):
					continue
				match = re.match("[Ss]eason\s*(\d+)", curFile)
				if match != None:
					files += [os.path.join(curFile, x) for x in os.listdir(unicode(os.path.join(self._location, curFile)))]

		# check for season folders
		#logger.log("Resulting file list: "+str(files))
	
		# find all media files
		mediaFiles = filter(sickbeard.helpers.isMediaFile, files)

		# create TVEpisodes from each media file (if possible)
		for mediaFile in mediaFiles:
			
			curEpisode = None
			
			logger.log(str(self.tvdbid) + ": Creating episode from " + mediaFile, logger.DEBUG)
			try:
				curEpisode = self.makeEpFromFile(os.path.join(self._location, mediaFile))
			except (exceptions.ShowNotFoundException, exceptions.EpisodeNotFoundException) as e:
				logger.log("Episode "+mediaFile+" returned an exception: "+str(e), logger.ERROR)
			except exceptions.EpisodeDeletedException:
				logger.log("The episode deleted itself when I tried making an object for it", logger.DEBUG)
					

			# store the reference in the show
			if curEpisode != None:
				curEpisode.saveToDB()
	
	
	def loadEpisodesFromDB(self):
	
		logger.log("Loading all episodes from the DB")
	
		myDB = db.DBConnection()
		sql = "SELECT * FROM tv_episodes WHERE showid="+str(self.tvdbid)
		sqlResults = myDB.select(sql)
		
		scannedEps = {}
		
		for curResult in sqlResults:
			
			curSeason = int(curResult["season"])
			curEpisode = int(curResult["episode"])
			
			if not curSeason in scannedEps:
				scannedEps[curSeason] = {}
			
			logger.log("Loading episode "+str(curSeason)+"x"+str(curEpisode)+" from the DB", logger.DEBUG)
			
			try:
				curEp = self.getEpisode(curSeason, curEpisode)
				curEp.loadFromDB(curSeason, curEpisode)
				curEp.loadFromTVDB()
				scannedEps[curSeason][curEpisode] = True
			except exceptions.EpisodeDeletedException:
				logger.log("Tried loading an episode from the DB that should have been deleted, skipping it", logger.DEBUG)
				continue

		return scannedEps
	

	def loadEpisodesFromTVDB(self, cache=True):
	
		try:
			t = tvdb_api.Tvdb(cache=cache, lastTimeout=sickbeard.LAST_TVDB_TIMEOUT, apikey=sickbeard.TVDB_API_KEY)
		except tvdb_exceptions.tvdb_error:
			logger.log("TVDB timed out, unable to update episodes from TVDB", logger.ERROR)
			return None
		
		showObj = t[self.tvdbid]
		
		logger.log(str(self.tvdbid) + ": Loading all episodes from theTVDB...")
		
		scannedEps = {}
		
		for season in showObj:
			scannedEps[season] = {}
			for episode in showObj[season]:
				# need some examples of wtf episode 0 means to decide if we want it or not
				if episode == 0:
					continue
				try:
					#ep = TVEpisode(self, season, episode)
					ep = self.getEpisode(season, episode)
				except exceptions.EpisodeNotFoundException:
					logger.log(str(self.tvdbid) + ": TVDB object for " + str(season) + "x" + str(episode) + " is incomplete, skipping this episode")
					continue
				else:
					try:
						ep.loadFromTVDB()
					except exceptions.EpisodeDeletedException:
						logger.log("The episode was deleted, skipping the rest of the load")
						continue
				
				with ep.lock:
					logger.log(str(self.tvdbid) + ": Loading info from theTVDB for episode " + str(season) + "x" + str(episode), logger.DEBUG)
					ep.loadFromTVDB(season, episode, cache)
					ep.saveToDB()
				
				scannedEps[season][episode] = True

		return scannedEps

	def setTVRID(self, force=False):
		
		if self.tvrid != 0 and not force:
			logger.log("No need to get the TVRage ID, it's already populated", logger.DEBUG)
			return

		logger.log("Attempting to retrieve the TVRage ID", logger.DEBUG)

		tvrID = None
		
		# load the tvrage object
		tvr = tvrage.TVRage(self)
		
		# check for sync
		try:
			if not tvr.checkSync():
				raise exceptions.TVRageException("The latest episodes on TVDB and TVRage are out of sync, trying to sync with earlier episodes")
			tvrID = tvr.getTVRID()
		except exceptions.TVRageException as e:
			logger.log("TVRage error: "+str(e), logger.DEBUG)
			try:
				if not tvr.confirmShow():
					raise exceptions.TVRageException("Show episodes don't match - maybe the search is giving the wrong show?")
				tvrID = tvr.getTVRID()
			except exceptions.TVRageException as e:
				logger.log("Couldn't get TVRage ID because we're unable to sync TVDB and TVRage: "+str(e), logger.DEBUG)
				return

		if tvrID != None:
			logger.log("Setting TVRage ID for show "+self.name+" to "+str(tvrID))
			self.tvrid = tvrID
			self.saveToDB()
		else:
			logger.log("No TVRage ID was found, not setting it", logger.DEBUG)
		

	def loadLatestFromTVRage(self):
		
		try:
			# load the tvrage object
			tvr = tvrage.TVRage(self)
			
			# check for sync
			if not tvr.checkSync():
				logger.log("TVDB and TVRage are out of sync, not using TVRage data")
				return
			
			# store it to db
			tvr.saveToDB()
			
			newEp = tvr.getEpisode()
			
			if newEp != None:
				logger.log("TVRage gave us an episode object - saving it for now", logger.DEBUG)
				newEp.saveToDB()
			
			# make an episode out of it
		except exceptions.TVRageException as e:
			logger.log("Unable to add TVRage info: " + str(e), logger.ERROR)
			


	# make a TVEpisode object from a media file
	def makeEpFromFile(self, file):

		if not os.path.isfile(file):
			logger.log(str(self.tvdbid) + ": That isn't even a real file dude... " + file)
			return None

		logger.log(str(self.tvdbid) + ": Creating episode object from " + file, logger.DEBUG)

		try:
			myParser = FileParser(file)
			epInfo = myParser.parse()
		except tvnamer_exceptions.InvalidFilename:
			logger.log("Unable to parse the filename "+file+" into a valid episode", logger.ERROR)
			return None

		# for now lets assume that any episode in the show dir belongs to that show
		season = epInfo.seasonnumber
		rootEp = None

		# TODO: tvnamer should really just return a list always
		if not isinstance(epInfo.episodenumber, list):
			epList = [epInfo.episodenumber]
		else:
			epList = epInfo.episodenumber

		for curEp in epList:

			episode = int(curEp)
			
			logger.log(str(self.tvdbid) + ": " + file + " parsed to " + self.name + " " + str(season) + "x" + str(episode), logger.DEBUG)

			curEp = self.getEpisode(season, episode)
			
			if curEp == None:
				try:
					curEp = self.getEpisode(season, episode, file)
				except exceptions.EpisodeNotFoundException:
					logger.log(str(self.tvdbid) + ": Unable to figure out what this file is, skipping", logger.ERROR)
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
					logger.log("STATUS: we have an associated file, so setting the status to DOWNLOADED/" + str(DOWNLOADED), logger.DEBUG)
						
			with curEp.lock:
				curEp.saveToDB()
				
		# creating metafiles on the root should be good enough
		if rootEp != None:
			with rootEp.lock:
				rootEp.createMetaFiles()

		return None

	
	def loadFromDB(self, skipNFO=False):

		logger.log(str(self.tvdbid) + ": Loading show info from database")

		myDB = db.DBConnection()
		
		sqlResults = myDB.select("SELECT * FROM tv_shows WHERE tvdb_id = " + str(self.tvdbid))

		if len(sqlResults) > 1:
			raise exceptions.MultipleDBShowsException()
		elif len(sqlResults) == 0:
			logger.log(str(self.tvdbid) + ": Unable to find the show in the database")
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
			self.startyear = sqlResults[0]["startyear"]
			if self.startyear == None:
				self.startyear = 0

			self.quality = int(sqlResults[0]["quality"])
			self.seasonfolders = int(sqlResults[0]["seasonfolders"])
			self.paused = int(sqlResults[0]["paused"])

			if self.tvdbid == 0:
				self.tvdbid = int(sqlResults[0]["tvdb_id"])
				
			if self.tvrid == 0:
				self.tvrid = int(sqlResults[0]["tvr_id"])
	
	def loadFromTVDB(self, cache=True):

		logger.log(str(self.tvdbid) + ": Loading show info from theTVDB") 

		t = tvdb_api.Tvdb(cache=cache, lastTimeout=sickbeard.LAST_TVDB_TIMEOUT, apikey=sickbeard.TVDB_API_KEY)
		myEp = t[self.tvdbid]
		
		if myEp["airs_dayofweek"] != None and myEp["airs_time"] != None:
			self.airs = myEp["airs_dayofweek"] + " " + myEp["airs_time"]

		if myEp["firstaired"] != None and myEp["firstaired"]:
			self.startyear = int(myEp["firstaired"].split('-')[0])

		if self.airs == None:
			self.airs = ""

		if myEp["status"] != None:
			self.status = myEp["status"]

		if self.status == None:
			self.status = ""
			
		self.saveToDB()
	
	
	def loadNFO (self):

		if not os.path.isdir(self._location):
			logger.log(str(self.tvdbid) + ": Show dir doesn't exist, can't load NFO")
			raise exceptions.NoNFOException("The show dir doesn't exist, no NFO could be loaded")
		
		logger.log(str(self.tvdbid) + ": Loading show info from NFO")

		xmlFile = os.path.join(self._location, "tvshow.nfo")
		xmlFileObj = open(xmlFile, "r")
		
		try:
			nfoData = " ".join(xmlFileObj.readlines()).replace("&#x0D;","").replace("&#x0A;","")
			showSoup = BeautifulStoneSoup(nfoData, convertEntities=BeautifulStoneSoup.XML_ENTITIES)
		except SGMLParseError as e:
			logger.log("There was an error parsing your existing tvshow.nfo file: " + str(e), logger.ERROR)
			logger.log("Attempting to rename it to tvshow.nfo.old", logger.DEBUG)
			xmlFileObj.close()
			try:
				os.rename(xmlFile, xmlFile + ".old")
			except Exception as e:
				logger.log("Failed to rename your tvshow.nfo file - you need to delete it or fix it: " + str(e), logger.ERROR)
			raise exceptions.NoNFOException("Invalid info in tvshow.nfo")

		if showSoup.title == None or (showSoup.tvdbid == None and showSoup.id == None):
			raise exceptions.NoNFOException("Invalid info in tvshow.nfo (missing name or id): "+str(showSoup.title)+" "+str(showSoup.tvdbid)+" "+str(showSoup.id))
		
		self.name = showSoup.title.string
		if showSoup.tvdbid != None:
			self.tvdbid = int(showSoup.tvdbid.string)
		elif showSoup.id != None:
			self.tvdbid = int(showSoup.id.string)
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
	
		logger.log(str(self.tvdbid) + ": Finding the episode which airs next", logger.DEBUG) 

		myDB = db.DBConnection()
		innerQuery = "SELECT airdate FROM tv_episodes WHERE showid = " + str(self.tvdbid) + " AND airdate >= " + str(datetime.date.today().toordinal()) + " AND status = " + str(UNAIRED) + " ORDER BY airdate ASC LIMIT 1"
		query = "SELECT * FROM tv_episodes WHERE showid = " + str(self.tvdbid) + " AND airdate >= " + str(datetime.date.today().toordinal()) + " AND airdate <= ("+innerQuery+") and status = " + str(UNAIRED)
		sqlResults = myDB.select(query)
	
		if sqlResults == None or len(sqlResults) == 0:
			logger.log(str(self.tvdbid) + ": No episode found... need to implement tvrage and also show status", logger.DEBUG)
			return []
		else:
			logger.log(str(self.tvdbid) + ": Found episode " + str(sqlResults[0]["season"]) + "x" + str(sqlResults[0]["episode"]), logger.DEBUG)
			foundEps = []
			for sqlEp in sqlResults:
				curEp = self.getEpisode(int(sqlEp["season"]), int(sqlEp["episode"]))
				foundEps.append(curEp)
			return foundEps

		# if we didn't get an episode then try getting one from tvrage
		
		# load tvrage info
		
		# extract NextEpisode info
		
		# verify that we don't have it in the DB somehow (ep mismatch)

			
	def deleteShow(self):
		
		myDB = db.DBConnection()
		myDB.action("DELETE FROM tv_episodes WHERE showid = " + str(self.tvdbid))
		myDB.action("DELETE FROM tv_shows WHERE tvdb_id = " + str(self.tvdbid))
		
		# remove self from show list
		sickbeard.showList = [x for x in sickbeard.showList if x.tvdbid != self.tvdbid]
		
	def refreshDir(self):

		# make sure the show dir is where we think it is
		if not os.path.isdir(self._location):
			return False
		
		# run through all locations from DB, check that they exist
		logger.log(str(self.tvdbid) + ": Loading all episodes with a location from the database")
		
		myDB = db.DBConnection()
		sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = " + str(self.tvdbid) + " AND location != ''")
		
		for ep in sqlResults:
			curLoc = os.path.normpath(ep["location"])
			season = int(ep["season"])
			episode = int(ep["episode"])
			
			try:
				curEp = self.getEpisode(season, episode)
			except exceptions.EpisodeDeletedException:
				logger.log("The episode was deleted while we were refreshing it, moving on to the next one", logger.DEBUG)
				continue
			
			# if the path doesn't exist
			# or if there's no season folders and it's not inside our show dir 
			# or if there are season folders and it's in the main dir:
			# or if it's not in our show dir at all
			if not os.path.isfile(curLoc) or \
			(not self.seasonfolders and os.path.normpath(os.path.dirname(curLoc)) != os.path.normpath(self.location)) or \
			(self.seasonfolders and os.path.normpath(os.path.dirname(curLoc)) == os.path.normpath(self.location)) or \
			os.path.normpath(os.path.commonprefix([os.path.normpath(x) for x in (curLoc, self.location)])) != os.path.normpath(self.location):
			
				logger.log(str(self.tvdbid) + ": Location for " + str(season) + "x" + str(episode) + " doesn't exist, removing it and changing our status to SKIPPED", logger.DEBUG)
				with curEp.lock:
					curEp.location = ''
					if curEp.status == DOWNLOADED:
						curEp.status = SKIPPED
					curEp.saveToDB()

		
		# load from dir
		self.loadEpisodesFromDir()
			
			
	def fixEpisodeNames(self):

		if not os.path.isdir(self._location):
			logger.log(str(self.tvdbid) + ": Show dir doesn't exist, can't rename episodes")
			return
				
		# load episodes from my folder
		self.loadEpisodesFromDir()
		
		logger.log(str(self.tvdbid) + ": Loading all episodes with a location from the database")
		
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
		
		logger.log("File results: " + str(fileLocations), logger.DEBUG)

		for curLocation in fileLocations:
			
			epList = fileLocations[curLocation]
			
			# get the root episode and add all related episodes to it
			rootEp = None
			for myEp in epList:
				curEp = self.getEpisode(myEp[0], myEp[1])
				if rootEp == None:
					rootEp = curEp
					rootEp.relatedEps = []
				else:
					rootEp.relatedEps.append(curEp)
			
			goodName = rootEp.prettyName()
			actualName = os.path.splitext(os.path.basename(curLocation))
			curEpDir = os.path.dirname(curLocation)

			if goodName == actualName[0]:
				logger.log(str(self.tvdbid) + ": File " + rootEp.location + " is already named correctly, skipping", logger.DEBUG)
				continue
			
			with rootEp.lock:
				result = processTV.renameFile(rootEp.location, rootEp.prettyName())
				if result != False:
					rootEp.location = result
					for relEp in rootEp.relatedEps:
						relEp.location = result
			
			fileList = glob.glob(os.path.join(curEpDir, actualName[0] + "*").replace("[","*").replace("]","*"))

			for file in fileList:
				result = processTV.renameFile(file, rootEp.prettyName())
				if result == False:
					logger.log(str(self.tvdbid) + ": Unable to rename file "+file, logger.ERROR)
			
			for curEp in [rootEp]+rootEp.relatedEps:
				curEp.checkForMetaFiles()
			
			with rootEp.lock:
				rootEp.saveToDB()
				for relEp in rootEp.relatedEps:
					relEp.saveToDB()
		
			
	def saveToDB(self):

		logger.log(str(self.tvdbid) + ": Saving show info to database", logger.DEBUG)

		myDB = db.DBConnection()
		sqlResults = myDB.select("SELECT * FROM tv_shows WHERE tvdb_id = " + str(self.tvdbid))

		# use this list regardless of whether it's in there or not
		sqlValues = [self.name, self.tvdbid, self.tvrid, self._location, self.network, self.genre, self.runtime, self.quality, self.airs, self.status, self.seasonfolders, self.paused, self.startyear]
		
		# if it's not in there then insert it
		if len(sqlResults) == 0:
			sql = "INSERT INTO tv_shows (show_name, tvdb_id, tvr_id, location, network, genre, runtime, quality,  airs, status, seasonfolders, paused, startyear) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"

		# if it's already there then just change it
		elif len(sqlResults) == 1:
			sql = "UPDATE tv_shows SET show_name=?, tvdb_id=?, tvr_id=?, location=?, network=?, genre=?, runtime=?, quality=?, airs=?, status=?, seasonfolders=?, paused=?, startyear=? WHERE tvdb_id=?"
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
		toReturn += "startyear: " + str(self.startyear) + "\n"
		toReturn += "genre: " + self.genre + "\n"
		toReturn += "runtime: " + str(self.runtime) + "\n"
		toReturn += "quality: " + str(self.quality) + "\n"
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
		logger.log("status starts unknown", logger.DEBUG)

		self.tvdbid = 0

		self.show = show
		self.location = file
		
		self.lock = threading.Lock()
		
		self.specifyEpisode(self.season, self.episode)

		self.relatedEps = []

		self.checkForMetaFiles()

	def checkForMetaFiles(self): 
		
		# check for nfo and tbn
		if os.path.isfile(self.location):
			if os.path.isfile(os.path.join(self.show.location, helpers.replaceExtension(self.location, 'nfo'))):
				self.hasnfo = True
			else:
				self.hasnfo = False
				
			if os.path.isfile(os.path.join(self.show.location, helpers.replaceExtension(self.location, 'tbn'))):
				self.hastbn = True
			else:
				self.hastbn = False


		
	def specifyEpisode(self, season, episode):
		
		sqlResult = self.loadFromDB(season, episode)
		
		# only load from NFO if we didn't load from DB
		if os.path.isfile(self.location) and self.name == "":
			try:
				self.loadFromNFO(self.location)
			except exceptions.NoNFOException:
				logger.log(str(self.show.tvdbid) + ": There was an error loading the NFO for episode " + str(season) + "x" + str(episode), logger.ERROR)
				pass
		
		# if we tried loading it from NFO and didn't find the NFO, use TVDB
		if self.hasnfo == False:
			try:
				result = self.loadFromTVDB(season, episode)
			except exceptions.EpisodeDeletedException:
				result = False
			
			# if we failed TVDB, NFO *and* SQL then fail
			if result == False and not sqlResult:
				raise exceptions.EpisodeNotFoundException("Couldn't find episode " + str(season) + "x" + str(episode))
		
		self.saveToDB()
		
	
	def loadFromDB(self, season, episode):

		logger.log(str(self.show.tvdbid) + ": Loading episode details from DB for episode " + str(season) + "x" + str(episode), logger.DEBUG)

		myDB = db.DBConnection()
		sqlResults = myDB.select("SELECT * FROM tv_episodes WHERE showid = " + str(self.show.tvdbid) + " AND season = " + str(season) + " AND episode = " + str(episode))

		if len(sqlResults) > 1:
			raise exceptions.MultipleDBEpisodesException("Your DB has two records for the same show somehow.")
		elif len(sqlResults) == 0:
			logger.log(str(self.show.tvdbid) + ": Episode " + str(self.season) + "x" + str(self.episode) + " not found in the database", logger.DEBUG) 
			return False
		else:
			#NAMEIT logger.log("AAAAA from" + str(self.season)+"x"+str(self.episode) + " -" + self.name + " to " + str(sqlResults[0]["name"]))
			if sqlResults[0]["name"] != None:
				self.name = sqlResults[0]["name"] 
			self.season = season
			self.episode = episode
			self.description = sqlResults[0]["description"]
			if self.description == None:
				self.description = ""
			self.airdate = datetime.date.fromordinal(int(sqlResults[0]["airdate"]))
			logger.log("1 Status changes from " + str(self.status) + " to " + str(sqlResults[0]["status"]), logger.DEBUG)
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

		logger.log(str(self.show.tvdbid) + ": Loading episode details from theTVDB for episode " + str(season) + "x" + str(episode), logger.DEBUG)

		try:
			t = tvdb_api.Tvdb(cache=cache, lastTimeout=sickbeard.LAST_TVDB_TIMEOUT, apikey=sickbeard.TVDB_API_KEY)
			myEp = t[self.show.tvdbid][season][episode]
		except (tvdb_exceptions.tvdb_error, IOError):
			# if the episode is already valid just log it, if not throw it up
			if self.name != "" and self.airdate != datetime.date.fromordinal(1):
				logger.log("TVDB timed out but we have enough info from other sources, allowing the error", logger.ERROR)
				return
			else:
				logger.log("TVDB timed out, unable to create the episode", logger.ERROR)
				return False
		except (tvdb_exceptions.tvdb_episodenotfound, tvdb_exceptions.tvdb_seasonnotfound):
			logger.log("Unable to find the episode on tvdb... has it been removed? Should I delete from db?")
			# if I'm no longer on TVDB but I once was then delete myself from the DB
			if self.tvdbid != -1:
				self.deleteEpisode()
			return

			
		if myEp["firstaired"] == None and season == 0:
			myEp["firstaired"] = str(datetime.date.fromordinal(1))
			
		if myEp["episodename"] == None or myEp["episodename"] == "":
			logger.log("The episode has no name on TVDB")
			# if I'm incomplete on TVDB but I once was complete then just delete myself from the DB for now
			if self.tvdbid != -1:
				self.deleteEpisode()
			return False

		if myEp["firstaired"] == None or myEp["firstaired"] == "":
			logger.log("The episode has no air date on TVDB")
			return False
		
		#NAMEIT logger.log("BBBBBBBB from " + str(self.season)+"x"+str(self.episode) + " -" +self.name+" to "+myEp["episodename"])
		self.name = myEp["episodename"]
		self.season = season
		self.episode = episode
		self.description = myEp["overview"]
		if self.description == None:
			self.description = ""
		rawAirdate = [int(x) for x in myEp["firstaired"].split("-")]
		self.airdate = datetime.date(rawAirdate[0], rawAirdate[1], rawAirdate[2])
		self.tvdbid = myEp["id"]

		if not os.path.isdir(self.show._location):
			logger.log("The show dir is missing, not bothering to change the episode statuses since it'd probably be invalid")
			return

		logger.log(str(self.show.tvdbid) + ": Setting status for " + str(season) + "x" + str(episode) + " based on status " + statusStrings[self.status] + " and existence of " + self.location, logger.DEBUG)
		
		if not os.path.isfile(self.location):

			# if we don't have the file and it hasn't aired yet set the status to UNAIRED
			if self.airdate >= datetime.date.today() and self.status != SNATCHED and self.status != PREDOWNLOADED:
				logger.log("2 Status changes from " + str(self.status) + " to " + str(UNAIRED), logger.DEBUG)
				self.status = UNAIRED
				
			else:

				# if we haven't downloaded it then mark it as missed
				if self.status == UNAIRED:
					logger.log("3 Status changes from " + str(self.status) + " to " + str(MISSED), logger.DEBUG)
					self.status = MISSED

				# if it's an old episode we don't have then assume we SKIPPED it
				elif self.status == UNKNOWN:
					logger.log("4 Status changes from " + str(self.status) + " to " + str(SKIPPED), logger.DEBUG)
					self.status = SKIPPED

		# if we have a media file then it's downloaded
		elif sickbeard.helpers.isMediaFile(self.location):
			logger.log("5 Status changes from " + str(self.status) + " to " + str(DOWNLOADED), logger.DEBUG)
			self.status = DOWNLOADED

		# shouldn't get here probably
		else:
			logger.log("6 Status changes from " + str(self.status) + " to " + str(UNKNOWN), logger.DEBUG)
			self.status = UNKNOWN

		
		# hasnfo, hastbn, status?
		
		
	def loadFromNFO(self, location):

		if not os.path.isdir(self.show._location):
			logger.log(str(self.show.tvdbid) + ": The show dir is missing, not bothering to try loading the episode NFO")
			return

		logger.log(str(self.show.tvdbid) + ": Loading episode details from the NFO file associated with " + location, logger.DEBUG)

		self.location = location
	
		if self.location != "":
		
			if self.status == UNKNOWN:
				if sickbeard.helpers.isMediaFile(self.location):
					logger.log("7 Status changes from " + str(self.status) + " to " + str(DOWNLOADED), logger.DEBUG)
					self.status = DOWNLOADED
		
			nfoFile = sickbeard.helpers.replaceExtension(self.location, "nfo")
			logger.log(str(self.show.tvdbid) + ": Using NFO name " + nfoFile, logger.DEBUG)
			#nfoFile = os.path.join(self.show.location, nfoFilename)
			
			if os.path.isfile(nfoFile):
				nfoFileObj = open(nfoFile, "r")
				try:
					nfoData = " ".join(nfoFileObj.readlines()).replace("&#x0D;","").replace("&#x0A;","")
					showSoup = BeautifulStoneSoup(nfoData, convertEntities=BeautifulStoneSoup.XML_ENTITIES)
				except (SGMLParseError, ValueError) as e:
					logger.log("Error loading the NFO, backing up the NFO and skipping for now: " + str(e), logger.ERROR) #TODO: figure out what's wrong and fix it
					nfoFileObj.close()
					try:
						os.rename(nfoFile, nfoFile + ".old")
					except Exception as e:
						logger.log("Failed to rename your episode's NFO file - you need to delete it or fix it: " + str(e), logger.ERROR)
					raise exceptions.NoNFOException("Error in NFO format")

				for epDetails in showSoup.findAll('episodedetails'):
					if isinstance(epDetails, NavigableString):
						continue
				
					if epDetails.season.string == None or int(epDetails.season.string) != self.season or epDetails.episode.string == None or int(epDetails.episode.string) != self.episode:
						logger.log(str(self.show.tvdbid) + ": NFO has an <episodedetails> block for a different episode - wanted " + str(self.season) + "x" + str(self.episode) + " but got " + str(epDetails.season.string) + "x" + str(epDetails.episode.string), logger.DEBUG)
						continue
				
					if epDetails.title.string == None or epDetails.aired.string == None:
						raise exceptions.NoNFOException("Error in NFO format (missing episode title or airdate)")
				
					if epDetails.title.string != None:
						#NAMEIT logger.log("CCCCCCC from " + str(self.season)+"x"+str(self.episode) + " -" + str(self.name) + " to " + str(showSoup.title.string))
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
		toReturn += "location: " + self.location + "\n"
		toReturn += "description: " + self.description + "\n"
		toReturn += "airdate: " + str(self.airdate.toordinal()) + " (" + str(self.airdate) + ")\n"
		toReturn += "hasnfo: " + str(self.hasnfo) + "\n"
		toReturn += "hastbn: " + str(self.hastbn) + "\n"
		toReturn += "status: " + str(self.status) + "\n"
		return toReturn

		
	def createMetaFiles(self, force=False):
		
		if not os.path.isdir(self.show._location):
			logger.log(str(self.show.tvdbid) + ": The show dir is missing, not bothering to try to create metadata")
			return

		if sickbeard.CREATE_METADATA != True:
			return
		
		self.checkForMetaFiles()
		
		epsToWrite = [self] + self.relatedEps

		try:
			t = tvdb_api.Tvdb(actors=True,
							  lastTimeout=sickbeard.LAST_TVDB_TIMEOUT,
							  apikey=sickbeard.TVDB_API_KEY)
			myShow = t[self.show.tvdbid]
		except tvdb_exceptions.tvdb_shownotfound as e:
			raise exceptions.ShowNotFoundException(str(e))
		except tvdb_exceptions.tvdb_error as e:
			logger.log("Unable to connect to TVDB while creating meta files - skipping - "+str(e), logger.ERROR)
			return

		if len(epsToWrite) > 1:
			rootNode = etree.Element( "xbmcmultiepisode" )
		else:
			rootNode = etree.Element( "episodedetails" )

		# Set our namespace correctly
		for ns in XML_NSMAP.keys():
			rootNode.set(ns, XML_NSMAP[ns])
		
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
			except (tvdb_exceptions.tvdb_episodenotfound, tvdb_exceptions.tvdb_seasonnotfound):
				logger.log("Unable to find episode " + str(curEpToWrite.season) + "x" + str(curEpToWrite.episode) + " on tvdb... has it been removed? Should I delete from db?")
				return False
			
			if myEp["firstaired"] == None and self.season == 0:
				myEp["firstaired"] = str(datetime.date.fromordinal(1))
			
			if myEp["episodename"] == None or myEp["firstaired"] == None:
				return False
				
			if curEpToWrite == self:
				thumbFilename = myEp["filename"]
				
			if not needsNFO:
				logger.log("Skipping metadata generation for myself ("+str(self.season)+"x"+str(self.episode)+")", logger.DEBUG)
				continue
			else:
				logger.log("Creating metadata for myself ("+str(self.season)+"x"+str(self.episode)+")", logger.DEBUG)
			
			if len(epsToWrite) > 1:
			    episode = etree.SubElement( rootNode, "episodedetails" )
			else:
			    episode = rootNode

			title = etree.SubElement( episode, "title" )
			if curEpToWrite.name != None:
				title.text = curEpToWrite.name

			season = etree.SubElement( episode, "season" )
			season.text = str(curEpToWrite.season)
	
			episodenum = etree.SubElement( episode, "episode" )
			episodenum.text = str(curEpToWrite.episode)
			
			aired = etree.SubElement( episode, "aired" )
			aired.text = str(curEpToWrite.airdate)
	
			plot = etree.SubElement( episode, "plot" )
			if curEpToWrite.description != None:
				plot.text = curEpToWrite.description
	
			displayseason = etree.SubElement( episode, "displayseason" )
			if myEp.has_key('airsbefore_season'):
				displayseason_text = myEp['airsbefore_season']
				if displayseason_text != None:
					displayseason.text = displayseason_text
	
			displayepisode = etree.SubElement( episode, "displayepisode" )
			if myEp.has_key('airsbefore_episode'):
				displayepisode_text = myEp['airsbefore_episode']
				if displayepisode_text != None:
					displayepisode.text = displayepisode_text
	
			thumb = etree.SubElement( episode, "thumb" )
			thumb_text = myEp['filename']
			if thumb_text != None:
				thumb.text = thumb_text
	
			watched = etree.SubElement( episode, "watched" )
			watched.text = 'false'
	
			credits = etree.SubElement( episode, "credits" )
			credits_text = myEp['writer']
			if credits_text != None:
				credits.text = credits_text
	
			director = etree.SubElement( episode, "director" )
			director_text = myEp['director']
			if director_text != None:
				director.text = director_text
	
			gueststar_text = myEp['gueststars']
			if gueststar_text != None:
				for actor in gueststar_text.split('|'):
					cur_actor = etree.SubElement( episode, "actor" )
					cur_actor_name = etree.SubElement(
						cur_actor, "name"
						)
					cur_actor_name.text = actor
	
			for actor in myShow['_actors']:
				cur_actor = etree.SubElement( episode, "actor" )

				cur_actor_name = etree.SubElement( cur_actor, "name" )
				cur_actor_name.text = actor['name']

				cur_actor_role = etree.SubElement( cur_actor, "role" )
				cur_actor_role_text = actor['role']
				if cur_actor_role_text != None:
					cur_actor_role.text = cur_actor_role_text

				cur_actor_thumb = etree.SubElement( cur_actor, "thumb" )
				cur_actor_thumb_text = actor['image']
				if cur_actor_thumb_text != None:
					cur_actor_thumb.text = cur_actor_thumb_text
					
			if os.path.isfile(self.location):
				nfoFilename = helpers.replaceExtension(self.location, 'nfo')
			else:
				nfoFilename = helpers.sanitizeFileName(self.prettyName() + '.nfo')
	
			logger.log('Writing nfo to ' + os.path.join(self.show.location, nfoFilename))
			#
			# Make it purdy
			helpers.indentXML( rootNode )

			nfo = etree.ElementTree( rootNode )
			nfo_fh = open(os.path.join(self.show.location, nfoFilename), 'w')
			nfo.write( nfo_fh, encoding="utf-8" ) 
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
				logger.log('Writing thumb to ' + os.path.join(self.show.location, tbnFilename))
				try:
					urllib.urlretrieve(thumbFilename, os.path.join(self.show.location, tbnFilename))
				except IOError:
					logger.log("Unable to download thumbnail from "+thumbFilename, logger.ERROR)
					return
				#TODO: check that it worked
				self.hastbn = True

		# save our new NFO statuses to the DB
		self.saveToDB()


	def deleteEpisode(self):

		logger.log("Deleting "+self.show.name+" "+str(self.season)+"x"+str(self.episode))
		
		# remove myself from the show dictionary
		if self.show.getEpisode(self.season, self.episode, noCreate=True) == self:
			logger.log("Removing myself from my show's list", logger.DEBUG)
			del self.show.episodes[self.season][self.episode]
		
		# make sure it's not in any ep lists
		if self in sickbeard.airingList:
			logger.log("Removing myself from the airing list", logger.DEBUG)
			sickbeard.airingList.remove(self)
		if self in sickbeard.comingList:
			logger.log("Removing myself from the coming list", logger.DEBUG)
			sickbeard.comingList.remove(self)
		if self in sickbeard.missingList:
			logger.log("Removing myself from the missing list", logger.DEBUG)
			sickbeard.missingList.remove(self)
		
		# delete myself from the DB
		logger.log("Deleting myself from the database", logger.DEBUG)
		myDB = db.DBConnection()
		sql = "DELETE FROM tv_episodes WHERE showid="+str(self.show.tvdbid)+" AND season="+str(self.season)+" AND episode="+str(self.episode)
		myDB.action(sql)
		
		raise exceptions.EpisodeDeletedException()
		
	def saveToDB(self):
	
		logger.log(str(self.show.tvdbid) + ": Saving episode details to database", logger.DEBUG)

		logger.log("STATUS IS " + str(self.status), logger.DEBUG)
	
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
		
		regex = "(.*) \(\d\)"


		if len(self.relatedEps) == 0:
			goodName = self.name

		elif len(self.relatedEps) > 1:
			goodName = ''

		else:
			singleName = True
			curGoodName = None

			for curName in [self.name]+[x.name for x in self.relatedEps]:
				match = re.match(regex, curName)
				if not match:
					singleName = False
					break
	
				if curGoodName == None:
					curGoodName = match.group(1)
				else:
					if curGoodName != match.group(1):
						singleName = False
						break


			if singleName:
				goodName = curGoodName
			else:
				goodName = self.name
				for relEp in self.relatedEps:
					goodName += " & " + relEp.name
		
		goodEpString = "x{0:0>2}".format(self.episode)
		for relEp in self.relatedEps:
			goodEpString += "x{0:0>2}".format(relEp.episode)
		
		if goodName != '':
			goodName = ' - ' + goodName

		return self.show.name + ' - ' + str(self.season) + goodEpString + goodName
		#return "{0} - {1}{2} - {3}".format(self.show.name, self.season, goodEpString, unicode(goodName).encode('utf-8', 'ignore'))
		
		
		
		
