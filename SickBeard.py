#!/usr/bin/env python
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

import locale
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

    for sqlShow in sqlResults:
        try:
            curShow = TVShow(int(sqlShow["tvdb_id"]))
            sickbeard.showList.append(curShow)
        except Exception, e:
            logger.log(u"There was an error creating the show in "+sqlShow["location"]+": "+str(e).decode('utf-8'), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)

        #TODO: make it update the existing shows if the showlist has something in it

def daemonize():
    # Make a non-session-leader child process
    try:
        pid = os.fork()
        if pid != 0:
            sys.exit(0)
    except OSError, e:
        raise RuntimeError("1st fork failed: %s [%d]" %
                   (e.strerror, e.errno))

    os.chdir(sickbeard.PROG_DIR)
    os.setsid()

    # Make sure I can read my own files and shut out others
    prev = os.umask(0)
    os.umask(prev and int('077',8))

    # Make the child a session-leader by detaching from the terminal
    try:
        pid = os.fork()
        if pid != 0:
            sys.exit(0)
    except OSError, e:
        raise RuntimeError("2st fork failed: %s [%d]" %
                   (e.strerror, e.errno))
        raise Exception, "%s [%d]" % (e.strerror, e.errno)

    dev_null = file('/dev/null', 'r')
    os.dup2(dev_null.fileno(), sys.stdin.fileno())

    if sickbeard.CREATEPID:
        pid = str(os.getpid())
        logger.log(u"Writing PID " + pid + " to " + str(sickbeard.PIDFILE))
        file(sickbeard.PIDFILE, 'w').write("%s\n" % pid)

def main():

    # do some preliminary stuff
    sickbeard.MY_FULLNAME = os.path.normpath(os.path.abspath(sys.argv[0]))
    sickbeard.MY_NAME = os.path.basename(sickbeard.MY_FULLNAME)
    sickbeard.PROG_DIR = os.path.dirname(sickbeard.MY_FULLNAME)
    sickbeard.MY_ARGS = sys.argv[1:]
    sickbeard.CREATEPID = False

    try:
        locale.setlocale(locale.LC_ALL, "")
    except (locale.Error, IOError):
        pass
    sickbeard.SYS_ENCODING = locale.getpreferredencoding()
    
    # for OSes that are poorly configured I'll just force UTF-8
    if not sickbeard.SYS_ENCODING or sickbeard.SYS_ENCODING in ('ANSI_X3.4-1968', 'US-ASCII'):
        sickbeard.SYS_ENCODING = 'UTF-8'

    sickbeard.CONFIG_FILE = os.path.join(sickbeard.PROG_DIR, "config.ini")

    # need console logging for SickBeard.py and SickBeard-console.exe
    consoleLogging = (not hasattr(sys, "frozen")) or (sickbeard.MY_NAME.lower().find('-console') > 0)

    # rename the main thread
    threading.currentThread().name = "MAIN"

    try:
        opts, args = getopt.getopt(sys.argv[1:], "qfdp::", ['quiet', 'forceupdate', 'daemon', 'port=', 'tvbinz', 'pidfile='])
    except getopt.GetoptError:
        print "Available options: --quiet, --forceupdate, --port, --daemon --pidfile"
        sys.exit()

    forceUpdate = False
    forcedPort = None

    for o, a in opts:
        # for now we'll just silence the logging
        if o in ('-q', '--quiet'):
            consoleLogging = False
        # for now we'll just silence the logging
        if o in ('--tvbinz'):
            sickbeard.SHOW_TVBINZ = True

        # should we update right away?
        if o in ('-f', '--forceupdate'):
            forceUpdate = True

        # use a different port
        if o in ('-p', '--port'):
            forcedPort = int(a)

        # Run as a daemon
        if o in ('-d', '--daemon'):
            if sys.platform == 'win32':
                print "Daemonize not supported under Windows, starting normally"
            else:
                consoleLogging = False
                sickbeard.DAEMON = True

        # write a pidfile if requested
        if o in ('--pidfile'):
            sickbeard.PIDFILE = str(a)

            # if the pidfile already exists, sickbeard may still be running, so exit
            if os.path.exists(sickbeard.PIDFILE):
                sys.exit("PID file " + sickbeard.PIDFILE + " already exists. Exiting.")

            # a pidfile is only useful in daemon mode
            # also, test to make sure we can write the file properly
            if sickbeard.DAEMON:
                sickbeard.CREATEPID = True
                try:
                    file(sickbeard.PIDFILE, 'w').write("pid\n")
                except IOError, e:
                    raise SystemExit("Unable to write PID file: %s [%d]" % (e.strerror, e.errno))
            else:
                logger.log(u"Not running in daemon mode. PID file creation disabled.")

    if consoleLogging:
        print "Starting up Sick Beard "+SICKBEARD_VERSION+" from " + sickbeard.CONFIG_FILE

    # load the config and publish it to the sickbeard package
    if not os.path.isfile(sickbeard.CONFIG_FILE):
        logger.log(u"Unable to find config.ini, all settings will be default", logger.ERROR)

    sickbeard.CFG = ConfigObj(sickbeard.CONFIG_FILE)

    # initialize the config and our threads
    sickbeard.initialize(consoleLogging=consoleLogging)

    sickbeard.showList = []

    if sickbeard.DAEMON:
        daemonize()
    
    # use this pid for everything
    sickbeard.PID = os.getpid()

    if forcedPort:
        logger.log(u"Forcing web server to port "+str(forcedPort))
        startPort = forcedPort
    else:
        startPort = sickbeard.WEB_PORT

    logger.log(u"Starting Sick Beard on http://localhost:"+str(startPort))

    if sickbeard.WEB_LOG:
        log_dir = sickbeard.LOG_DIR
    else:
        log_dir = None

    # sickbeard.WEB_HOST is available as a configuration value in various
    # places but is not configurable. It is supported here for historic
    # reasons.
    if sickbeard.WEB_HOST and sickbeard.WEB_HOST != '0.0.0.0':
        webhost = sickbeard.WEB_HOST
    else:
        if sickbeard.WEB_IPV6:
            webhost = '::'
        else:
            webhost = '0.0.0.0'

    try:
        initWebServer({
                'port':      startPort,
                'host':      webhost,
                'data_root': os.path.join(sickbeard.PROG_DIR, 'data'),
                'web_root':  sickbeard.WEB_ROOT,
                'log_dir':   log_dir,
                'username':  sickbeard.WEB_USERNAME,
                'password':  sickbeard.WEB_PASSWORD,
        })
    except IOError:
        logger.log(u"Unable to start web server, is something else running on port %d?" % startPort, logger.ERROR)
        if sickbeard.LAUNCH_BROWSER:
            logger.log(u"Launching browser and exiting", logger.ERROR)
            sickbeard.launchBrowser(startPort)
        sys.exit()

    # build from the DB to start with
    logger.log(u"Loading initial show list")
    loadShowsFromDB()

    # fire up all our threads
    sickbeard.start()

    # launch browser if we're supposed to
    if sickbeard.LAUNCH_BROWSER:
        sickbeard.launchBrowser(startPort)

    # start an update if we're supposed to
    if forceUpdate:
        sickbeard.showUpdateScheduler.action.run(force=True)

    # stay alive while my threads do the work
    while (True):

        if sickbeard.invoked_command:
            logger.log(u"Executing invoked command: "+repr(sickbeard.invoked_command))
            sickbeard.invoked_command()
            sickbeard.invoked_command = None

        time.sleep(1)

    return

if __name__ == "__main__":
    if sys.hexversion >= 0x020600F0:
        freeze_support()
    main()
