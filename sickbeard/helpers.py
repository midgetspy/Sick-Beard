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
import urllib, urllib2
import re

import sickbeard

from sickbeard.exceptions import *
from sickbeard import logger
from sickbeard.common import *
from sickbeard import encodingKludge as ek
from sickbeard import db

from lib.tvdb_api import tvdb_api, tvdb_exceptions

import xml.etree.cElementTree as etree

def indentXML(elem, level=0):
	'''
	Does our pretty printing, makes Matt very happy
	'''
	i = "\n" + level*"  "
	if len(elem):
		if not elem.text or not elem.text.strip():
			elem.text = i + "  "
		if not elem.tail or not elem.tail.strip():
			elem.tail = i
		for elem in elem:
			indentXML(elem, level+1)
		if not elem.tail or not elem.tail.strip():
			elem.tail = i
	else:
		# Strip out the newlines from text
		if elem.text:
			elem.text = elem.text.replace('\n', ' ')
		if level and (not elem.tail or not elem.tail.strip()):
			elem.tail = i

def replaceExtension (file, newExt):
	sepFile = file.rpartition(".")
	if sepFile[0] == "":
		return file
	else:
		return sepFile[0] + "." + newExt

def isMediaFile (file):
	sepFile = file.rpartition(".")
	if sepFile[2].lower() in mediaExtensions:
		return True
	else:
		return False

def sanitizeSceneName (name):
	for x in ":()'!":
		name = name.replace(x, "")

	name = name.replace("- ", ".").replace(" ", ".").replace("&", "and")
	name = re.sub("\.\.*", ".", name)	
	
	return name
		
def sanitizeFileName (name):
	for x in ":\\/*":
		name = name.replace(x, "-")
	for x in "\"<>|?":
		name = name.replace(x, "")
	return name
		

def sceneToNormalShowNames(name):
	
	return [name, name.replace(".and.", ".&.")]

def allPossibleShowNames(showData):

	showNames = [showData.name]

	if int(showData.tvdb_id) in sceneExceptions:
		showNames += sceneExceptions[showData.tvdb_id]
	
	# if we have a tvrage name then use it
	#if show.tvrname != "" and show.tvrname != None:
	#	showNames.append(show.tvrname)

	newShowNames = []

	# if we have "Show Name Australia" or "Show Name (Australia)" this will add "Show Name (AU)" for
	# any countries defined in common.countryList
	for curName in showNames:
		for curCountry in countryList:
			if curName.endswith(' '+curCountry):
				logger.log("Show names ends with "+curCountry+", so trying to add ("+countryList[curCountry]+") to it as well", logger.DEBUG)
				newShowNames.append(curName.replace(' '+curCountry, ' ('+countryList[curCountry]+')'))
			elif curName.endswith(' ('+curCountry+')'):
				logger.log("Show names ends with "+curCountry+", so trying to add ("+countryList[curCountry]+") to it as well", logger.DEBUG)
				newShowNames.append(curName.replace(' ('+curCountry+')', ' ('+countryList[curCountry]+')'))

	showNames += newShowNames

	return showNames

def makeSceneShowSearchStrings(show):

	showNames = allPossibleShowNames(show)

	# eliminate duplicates and scenify the names
	return map(sanitizeSceneName, showNames)


def makeSceneSearchString (epData):

	# see if we should use dates instead of episodes
	if "Talk Show" in epData.show_data.genres:
		epString = '.' + str(epData.aired).replace('-', '.')
	else:
		epString = ".S%02iE%02i" % (epData.season, epData.episode)

	showNames = makeSceneShowSearchStrings(epData.show_data)

	toReturn = []

	for curShow in showNames:
		toReturn.append(curShow + epString)

	return toReturn
	
def getGZippedURL (f):
	compressedResponse = f.read()
	compressedStream = StringIO.StringIO(compressedResponse)
	gzipper = gzip.GzipFile(fileobj=compressedStream)
	try:
		data = None
		data = gzipper.read()
	except IOError, e:
		logger.log("Exception encountered trying to read gzip: "+str(e), logger.ERROR)
	return data

def findCertainShow (showList, tvdbid):
	results = filter(lambda x: x.tvdbid == tvdbid, showList)
	if len(results) == 0:
		return None
	elif len(results) > 1:
		raise MultipleShowObjectsException()
	else:
		return results[0]
	
def findCertainTVRageShow (showList, tvrid):

	if tvrid == 0:
		return None

	results = filter(lambda x: x.tvrid == tvrid, showList)

	if len(results) == 0:
		return None
	elif len(results) > 1:
		raise MultipleShowObjectsException()
	else:
		return results[0]
	
	
def makeDir (dir):
	if not os.path.isdir(dir.encode('utf-8')):
		try:
			os.makedirs(dir.encode('utf-8'))
		except OSError:
			return False
	return True

def makeShowNFO(showID, showDir):

	logger.log("Making NFO for show "+str(showID)+" in dir "+showDir, logger.DEBUG)

	if not makeDir(showDir):
		logger.log("Unable to create show dir, can't make NFO", logger.ERROR)
		return False

	t = tvdb_api.Tvdb(actors=True, **sickbeard.TVDB_API_PARMS)
	
	tvNode = etree.Element( "tvshow" )
	for ns in XML_NSMAP.keys():
		tvNode.set(ns, XML_NSMAP[ns])

	try:
		myShow = t[int(showID)]
	except tvdb_exceptions.tvdb_shownotfound:
 		logger.log("Unable to find show with id " + str(showID) + " on tvdb, skipping it", logger.ERROR)
		raise

	except tvdb_exceptions.tvdb_error:
 		logger.log("TVDB is down, can't use its data to add this show", logger.ERROR)
 		raise

	# check for title and id
	try:
		if myShow["seriesname"] == None or myShow["seriesname"] == "" or myShow["id"] == None or myShow["id"] == "":
 			logger.log("Incomplete info for show with id " + str(showID) + " on tvdb, skipping it", logger.ERROR)

			return False
	except tvdb_exceptions.tvdb_attributenotfound:
 		logger.log("Incomplete info for show with id " + str(showID) + " on tvdb, skipping it", logger.ERROR)

		return False
	
	title = etree.SubElement( tvNode, "title" )
	if myShow["seriesname"] != None:
		title.text = myShow["seriesname"]
		
	rating = etree.SubElement( tvNode, "rating" )
	if myShow["rating"] != None:
		rating.text = myShow["rating"]

	plot = etree.SubElement( tvNode, "plot" )
	if myShow["overview"] != None:
		plot.text = myShow["overview"]

	episodeguide = etree.SubElement( tvNode, "episodeguide" )
	episodeguideurl = etree.SubElement( episodeguide, "url" )
	if myShow["id"] != None:
		showurl = sickbeard.TVDB_BASE_URL + '/series/' + myShow["id"] + '/all/en.zip'
		episodeguideurl.text = showurl
		
	mpaa = etree.SubElement( tvNode, "mpaa" )
	if myShow["contentrating"] != None:
		mpaa.text = myShow["contentrating"]

	tvdbid = etree.SubElement( tvNode, "id" )
	if myShow["id"] != None:
		tvdbid.text = myShow["id"]
		
	genre = etree.SubElement( tvNode, "genre" )
	if myShow["genre"] != None:
		genre.text = " / ".join([x for x in myShow["genre"].split('|') if x != ''])
		
	premiered = etree.SubElement( tvNode, "premiered" )
	if myShow["firstaired"] != None:
		premiered.text = myShow["firstaired"]
		
	studio = etree.SubElement( tvNode, "studio" )
	if myShow["network"] != None:
		studio.text = myShow["network"]
	
	for actor in myShow['_actors']:

		cur_actor = etree.SubElement( tvNode, "actor" )

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

 	logger.log("Writing NFO to "+os.path.join(showDir, "tvshow.nfo"), logger.DEBUG)


	# Make it purdy
	indentXML( tvNode )

	nfo_fh = open(os.path.join(showDir, "tvshow.nfo").encode('utf-8'), 'w')
	nfo = etree.ElementTree( tvNode )
	nfo.write( nfo_fh, encoding="utf-8" )
	nfo_fh.close()

	return True



def findLatestBuild():

	regex = "http\://sickbeard\.googlecode\.com/files/SickBeard\-win32\-build(\d+)\.zip"
	
	svnFile = urllib.urlopen("http://code.google.com/p/sickbeard/downloads/list")
	
	for curLine in svnFile.readlines():
		match = re.search(regex, curLine)
		if match:
			groups = match.groups()
			return int(groups[0])

	return None


def getShowImage(url, imgNum=None):
	
	imgFile = None
	imgData = None
	
	if url == None:
		return None
	
	# if they provided a fanart number try to use it instead
	if imgNum != None:
		tempURL = url.split('-')[0] + "-" + str(imgNum) + ".jpg"
	else:
		tempURL = url

	logger.log("Getting show image at "+tempURL, logger.DEBUG)
	try:
		imgFile = urllib2.urlopen(tempURL)
	except urllib2.URLError, e:
		logger.log("There was an error trying to retrieve the image, aborting", logger.ERROR)
		return None
	except urllib2.HTTPError, e:
		logger.log("Unable to access image at "+tempURL+", assuming it doesn't exist: "+str(e), logger.ERROR)
		return None

	if imgFile == None:
		logger.log("Something bad happened and we have no URL data somehow", logger.ERROR)
		return None

	# get the image
	try:
		imgData = imgFile.read()		
	except (urllib2.URLError, urllib2.HTTPError), e:
		logger.log("There was an error trying to retrieve the image, skipping download: " + str(e), logger.ERROR)
		return None

	return imgData

def guessSceneEpisodeQuality(name):
	if '720p' in name or '1080p' in name:
		return HD
	else:
		return SD

def listMediaFiles(dir):
	if not dir or not ek.ek(os.path.isdir, dir):
		return []
	
	files = []
	for curFile in ek.ek(os.listdir, dir):
		fullCurFile = ek.ek(os.path.join, dir, curFile)
		
		# if it's a dir do it recursively
		if ek.ek(os.path.isdir, fullCurFile):
			files += listMediaFiles(fullCurFile)
		
		else:
			if isMediaFile(curFile):
				files.append(fullCurFile)
	
	return files
		
