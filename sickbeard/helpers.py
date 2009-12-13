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


import StringIO
import gzip
import os.path
import os
import sqlite3
import codecs
import urllib
import re

from sickbeard.exceptions import *
from sickbeard.logging import *
from sickbeard.common import mediaExtensions

from sickbeard import db

from lib.tvdb_api import tvdb_api, tvdb_exceptions

from xml.dom.minidom import Document

def replaceExtension (file, newExt):
	sepFile = file.rpartition(".")
	if sepFile[0] == "":
		return file
	else:
		return sepFile[0] + "." + newExt

def isMediaFile (file):
	sepFile = file.rpartition(".")
	if sepFile[2] in mediaExtensions:
		return True
	else:
		return False

def sanitizeSceneName (name):
	for x in ":()'":
		name = name.replace(x, "")
	return name
		
def sanitizeFileName (name):
	for x in ":\\/":
		name = name.replace(x, "-")
	for x in "\"<>|?":
		name = name.replace(x, "")
	return name
		
def makeSceneSearchString (episode):

	epString = ".S{0:0>2}E{1:0>2}".format(episode.season, episode.episode)
	showName = episode.show.name.replace(" ", ".").replace("&", "and")

	if not showName.endswith(")") and episode.show.startyear > 1900:
		showName += ".(" + str(episode.show.startyear) + ")"

	results = []
	toReturn = []

	results.append(showName + epString)

	if showName.find("(") != -1:
		showNameNoBrackets = showName.rpartition(".(")[0]
		results.append(showNameNoBrackets + epString)

	for x in results:
		toReturn.append(sanitizeSceneName(x))

	return toReturn
	
def getGZippedURL (f):
	compressedResponse = f.read()
	compressedStream = StringIO.StringIO(compressedResponse)
	gzipper = gzip.GzipFile(fileobj=compressedStream)
	return gzipper.read()

def findCertainShow (showList, tvdbid):
	results = filter(lambda x: x.tvdbid == tvdbid, showList)
	if len(results) == 0:
		return None
	elif len(results) > 1:
		raise MultipleShowObjectsException()
	else:
		return results[0]
	
	
def makeDir (dir):
	if not os.path.isdir(dir):
		try:
			os.makedirs(dir)
		except OSError:
			return False
	return True

def makeShowNFO(showID, showDir):

	Logger().log("Making NFO for show "+str(showID)+" in dir "+showDir, DEBUG)

	if not makeDir(showDir):
		Logger().log("Unable to create show dir, can't make NFO", ERROR)
		return False

	t = tvdb_api.Tvdb()
	
	nfo = Document()

	tvNode = nfo.createElement("tvshow")
	nfo.appendChild(tvNode)
	
	try:
		myShow = t[int(showID)]
	except tvdb_exceptions.tvdb_shownotfound:
		Logger().log("Unable to find show with id " + str(showID) + " on tvdb, skipping it", ERROR)
		raise
		return False

	# check for title and id
	try:
		if myShow["seriesname"] == None or myShow["seriesname"] == "" or myShow["id"] == None or myShow["id"] == "":
			Logger().log("Incomplete info for show with id " + str(showID) + " on tvdb, skipping it", ERROR)
			return False
	except tvdb_exceptions.tvdb_attributenotfound:
		Logger().log("Incomplete info for show with id " + str(showID) + " on tvdb, skipping it", ERROR)
		return False
		
	title = nfo.createElement("title")
	if myShow["seriesname"] != None:
		title.appendChild(nfo.createTextNode(myShow["seriesname"]))
	tvNode.appendChild(title)
		
	rating = nfo.createElement("rating")
	if myShow["rating"] != None:
		rating.appendChild(nfo.createTextNode(myShow["rating"]))
	tvNode.appendChild(rating)

	plot = nfo.createElement("plot")
	if myShow["overview"] != None:
		plot.appendChild(nfo.createTextNode(myShow["overview"]))
	tvNode.appendChild(plot)
		
	mpaa = nfo.createElement("mpaa")
	if myShow["contentrating"] != None:
		mpaa.appendChild(nfo.createTextNode(myShow["contentrating"]))
	tvNode.appendChild(mpaa)


	id = nfo.createElement("id")
	if myShow["imdb_id"] != None:
		id.appendChild(nfo.createTextNode(myShow["imdb_id"]))
	tvNode.appendChild(id)
		
	tvdbid = nfo.createElement("tvdbid")
	if myShow["id"] != None:
		tvdbid.appendChild(nfo.createTextNode(myShow["id"]))
	tvNode.appendChild(tvdbid)
		
	genre = nfo.createElement("genre")
	if myShow["genre"] != None:
		genre.appendChild(nfo.createTextNode(" / ".join([x for x in myShow["genre"].split('|') if x != ''])))
	tvNode.appendChild(genre)
		
	premiered = nfo.createElement("premiered")
	if myShow["firstaired"] != None:
		premiered.appendChild(nfo.createTextNode(myShow["firstaired"]))
	tvNode.appendChild(premiered)
		
	studio = nfo.createElement("studio")
	if myShow["network"] != None:
		studio.appendChild(nfo.createTextNode(myShow["network"]))
	tvNode.appendChild(studio)
	
	Logger().log("Writing NFO to "+os.path.join(showDir, "tvshow.nfo"), DEBUG)
	nfo_fh = open(os.path.join(showDir, "tvshow.nfo"), 'w')
	nfo_fh.write(nfo.toxml(encoding="UTF-8"))
	nfo_fh.close()

	return True


def searchDBForShow(showName):
	
	# if tvdb fails then try looking it up in the db
	myDB = db.DBConnection()
	sqlResults = myDB.select("SELECT * FROM tv_shows WHERE show_name LIKE ?", [showName+'%'])
	
	if len(sqlResults) != 1:
		if len(sqlResults) == 0:
			Logger().log("Unable to match a record in the DB for "+showName, DEBUG)
		else:
			Logger().log("Multiple results for "+showName+" in the DB, unable to match show name", DEBUG)
		return None
	
	return (int(sqlResults[0]["tvdb_id"]), sqlResults[0]["show_name"])

def findLatestRev():

	regex = "http\://sickbeard\.googlecode\.com/files/SickBeard\-r(\d+)\.zip"
	
	svnFile = urllib.urlopen("http://code.google.com/p/sickbeard/downloads/list")
	
	for curLine in svnFile.readlines():
		match = re.search(regex, curLine)
		if match:
			groups = match.groups()
			return int(groups[0])

	return None