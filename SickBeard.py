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

# we only need this for compiling an EXE and I will just always do that on 2.6+
if sys.hexversion >= 0x020600F0:
	from multiprocessing import Process, freeze_support


import os
import os.path
import threading
import time
import signal
import sqlite3
import traceback
import getopt

import sickbeard

from sickbeard import db
from sickbeard.tv import TVShow
from sickbeard import logger
from sickbeard.common import *
from sickbeard.version import SICKBEARD_VERSION

from sickbeard.webserveInit import initWebServer

from lib.configobj import ConfigObj

signal.signal(signal.SIGINT, sickbeard.sig_handler)
signal.signal(signal.SIGTERM, sickbeard.sig_handler)

def loadShowsFromDB():

	myDB = db.DBConnection()
	sqlResults = myDB.select("SELECT * FROM tv_shows")
	
	myShowList = []
	
	for sqlShow in sqlResults:
		try:
			curShow = TVShow(sqlShow["location"])
			curShow.saveToDB()
			sickbeard.showList.append(curShow)
		except Exception, e:
			logger.log("There was an error creating the show in "+sqlShow["location"]+": "+str(e), logger.ERROR)
			logger.log(traceback.format_exc(), logger.DEBUG)
			
		#TODO: make it update the existing shows if the showlist has something in it

def main():

	# do some preliminary stuff
	sickbeard.MY_FULLNAME = os.path.normpath(os.path.abspath(sys.argv[0]))
	sickbeard.MY_NAME = os.path.basename(sickbeard.MY_FULLNAME)
	sickbeard.PROG_DIR = os.path.dirname(sickbeard.MY_FULLNAME)

	config_file = os.path.join(sickbeard.PROG_DIR, "config.ini")

	# need console logging for SickBeard.py and SickBeard-console.exe
	consoleLogging = (not hasattr(sys, "frozen")) or (sickbeard.MY_NAME.lower().find('-console') > 0)

	# rename the main thread
	threading.currentThread().name = "MAIN"

	try:
		opts, args = getopt.getopt(sys.argv[1:], "qfp:", ['quiet', 'force-update', 'port=', 'tvbinz'])
	except getopt.GetoptError:
		print "Available options: --quiet, --forceupdate, --port"
		sys.exit()
	
	forceUpdate = False
	forcedPort = None
	
	for o, a in opts:
		# for now we'll just silence the logging
		if (o in ('-q', '--quiet')):
			consoleLogging = False
		# for now we'll just silence the logging
		if (o in ('--tvbinz')):
			sickbeard.SHOW_TVBINZ = True
	
		# should we update right away?
		if (o in ('-f', '--forceupdate')):
			forceUpdate = True
	
		# should we update right away?
		if (o in ('-p', '--port')):
			forcedPort = int(a)
	
	if consoleLogging:
		print "Starting up Sick Beard "+SICKBEARD_VERSION+" from " + config_file
	
	# load the config and publish it to the sickbeard package
	if not os.path.isfile(config_file):
		logger.log("Unable to find config.ini, all settings will be default", logger.ERROR)

	sickbeard.CFG = ConfigObj(config_file)

	# initialize the config and our threads
	sickbeard.initialize(consoleLogging=consoleLogging)

	sickbeard.showList = []
	
	if forcedPort:
		logger.log("Forcing web server to port "+str(forcedPort))
		startPort = forcedPort
	else:
		startPort = sickbeard.WEB_PORT
	
	logger.log("Starting Sick Beard on http://localhost:"+str(startPort))

	try:
		initWebServer({
		        'port':      startPort,
		        'data_root': os.path.join(sickbeard.PROG_DIR, 'data'),
		        'web_root':  sickbeard.WEB_ROOT,
		        'log_dir':   sickbeard.LOG_DIR if sickbeard.WEB_LOG else None,
		        'username':  sickbeard.WEB_USERNAME,
		        'password':  sickbeard.WEB_PASSWORD,
		})
	except IOError:
		logger.log("Unable to start web server, is something else running on port %d?" % sickbeard.WEB_PORT, logger.ERROR)
		if sickbeard.LAUNCH_BROWSER:
			logger.log("Launching browser and exiting", logger.ERROR)
			sickbeard.launchBrowser()
		sys.exit()

	# build from the DB to start with
	logger.log("Loading initial show list")
	loadShowsFromDB()

	# set up the lists
	sickbeard.updateAiringList()
	sickbeard.updateComingList()
	sickbeard.updateMissingList()
	
	# fire up all our threads
	sickbeard.start()

	# launch browser if we're supposed to
	if sickbeard.LAUNCH_BROWSER:
		sickbeard.launchBrowser()

	# start an update if we're supposed to
	if forceUpdate:
		sickbeard.showUpdateScheduler.action.run(force=True)

	# stay alive while my threads do the work
	while (True):
		
		time.sleep(1)
	
	return
		
if __name__ == "__main__":
	if sys.hexversion >= 0x020600F0:
		freeze_support()
	main()
