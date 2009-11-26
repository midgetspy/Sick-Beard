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



import os
import os.path
import threading
import time
import signal
import sqlite3
import sys

import cherrypy
import cherrypy.lib.auth_basic

import sickbeard

from sickbeard import db, webserve
from sickbeard.tv import TVShow
from sickbeard.logging import *
from sickbeard.common import *

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
			myShowList.append(curShow)
		except Exception as e:
			Logger().log("There was an error creating the show in "+sqlShow["location"]+": "+str(e), ERROR)
		#TODO: make it update the existing shows if the showlist has something in it
	
	return myShowList

	

def main():

	# do some preliminary stuff
	sickbeard.PROG_DIR = os.path.dirname(os.path.normpath(os.path.abspath(sys.argv[0])))
	sickbeard.CONFIG_FILE = "config.ini"

	# rename the main thread
	threading.currentThread().name = "MAIN"
	
	Logger().log("Starting up Sick Beard from " + os.path.join(sickbeard.PROG_DIR, sickbeard.CONFIG_FILE))
	
	# load the config and publish it to the sickbeard package
	if not os.path.isfile(os.path.join(sickbeard.PROG_DIR, sickbeard.CONFIG_FILE)):
		Logger().log("Unable to find config.ini - aborting", ERROR)
		sys.exit()
	sickbeard.CFG = ConfigObj(os.path.join(sickbeard.PROG_DIR, sickbeard.CONFIG_FILE))

	# initialize the config and our threads
	sickbeard.initialize()

	# build from the DB to start with
	Logger().log("Loading initial show list")
	sickbeard.showList = loadShowsFromDB()

	# setup cherrypy logging
	if os.path.isdir(sickbeard.LOG_DIR) and sickbeard.WEB_LOG:
		cherry_log = os.path.join(sickbeard.LOG_DIR, "cherrypy.log")
		Logger().log("Using " + cherry_log + " for cherrypy log")
	else:
		cherry_log = None

	# cherrypy setup
	webRoot = webserve.WebInterface()
	cherrypy.config.update({
						    'server.socket_port': sickbeard.WEB_PORT,
						    'server.socket_host': '0.0.0.0',
						    'log.screen': False,
						    'log.access_file': cherry_log
	})
	
	userpassdict = {sickbeard.WEB_USERNAME: sickbeard.WEB_PASSWORD}
	checkpassword = cherrypy.lib.auth_basic.checkpassword_dict(userpassdict)
	
	if sickbeard.WEB_USERNAME == "" or sickbeard.WEB_PASSWORD == "":
		useAuth = False
	else:
		useAuth = True 
	
	conf = {'/': {
				  'tools.staticdir.root': os.path.join(sickbeard.PROG_DIR, 'data'),
				  'tools.auth_basic.on': useAuth,
				  'tools.auth_basic.realm': 'SickBeard',
				  'tools.auth_basic.checkpassword': checkpassword},
		    '/images': {'tools.staticdir.on': True,
				    'tools.staticdir.dir': 'images'},
			'/js': {'tools.staticdir.on': True,
				    'tools.staticdir.dir': 'js'},
			'/css': {'tools.staticdir.on': True,
					 'tools.staticdir.dir': 'css'},
	}

	cherrypy.tree.mount(webRoot, '/', conf)

	# launch a browser if we need to
	browserURL = 'http://localhost:' + str(sickbeard.WEB_PORT) + '/'

	try:
		cherrypy.server.start()
		cherrypy.server.wait()
	except IOError:
		Logger().log("Unable to start web server, is something else running?", ERROR)
		Logger().log("Launching browser and exiting", ERROR)
		sickbeard.launchBrowser(browserURL)
		sys.exit()

	# fire up all our threads
	sickbeard.start()

	# launch browser if we're supposed to
	if sickbeard.LAUNCH_BROWSER:
		sickbeard.launchBrowser(browserURL)

	# stay alive while my threads do the work
	while (True):
		
		time.sleep(1)
	
	return
		

if __name__ == "__main__":
	main()
