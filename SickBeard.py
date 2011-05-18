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
    from multiprocessing import freeze_support

import locale
import os
import threading
import time
import signal
import traceback
import getopt

import sickbeard

from sickbeard import db
from sickbeard.tv import TVShow
from sickbeard import logger
from sickbeard.version import SICKBEARD_VERSION

from sickbeard.webserveInit import initWebServer

from lib.configobj import ConfigObj

signal.signal(signal.SIGINT, sickbeard.sig_handler)
signal.signal(signal.SIGTERM, sickbeard.sig_handler)

def loadShowsFromDB():
    """
    Populates the showList with shows from the database
    """

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
    """
    Fork off as a daemon
    """

    # Make a non-session-leader child process
    try:
        pid = os.fork() #@UndefinedVariable - only available in UNIX
        if pid != 0:
            sys.exit(0)
    except OSError, e:
        raise RuntimeError("1st fork failed: %s [%d]" %
                   (e.strerror, e.errno))

    os.setsid() #@UndefinedVariable - only available in UNIX

    # Make sure I can read my own files and shut out others
    prev = os.umask(0)
    os.umask(prev and int('077', 8))

    # Make the child a session-leader by detaching from the terminal
    try:
        pid = os.fork() #@UndefinedVariable - only available in UNIX
        if pid != 0:
            sys.exit(0)
    except OSError, e:
        raise RuntimeError("2st fork failed: %s [%d]" %
                   (e.strerror, e.errno))

    dev_null = file('/dev/null', 'r')
    os.dup2(dev_null.fileno(), sys.stdin.fileno())

    if sickbeard.CREATEPID:
        pid = str(os.getpid())
        logger.log(u"Writing PID " + pid + " to " + str(sickbeard.PIDFILE))
        file(sickbeard.PIDFILE, 'w').write("%s\n" % pid)

def main():
    """
    TV for me
    """

    # do some preliminary stuff
    sickbeard.MY_FULLNAME = os.path.normpath(os.path.abspath(__file__))
    sickbeard.MY_NAME = os.path.basename(sickbeard.MY_FULLNAME)
    sickbeard.PROG_DIR = os.path.dirname(sickbeard.MY_FULLNAME)
    sickbeard.DATA_DIR = sickbeard.PROG_DIR
    sickbeard.MY_ARGS = sys.argv[1:]
    sickbeard.CREATEPID = False

    sickbeard.SYS_ENCODING = None

    try:
        locale.setlocale(locale.LC_ALL, "")
        sickbeard.SYS_ENCODING = locale.getpreferredencoding()
    except (locale.Error, IOError):
        pass

    # for OSes that are poorly configured I'll just force UTF-8
    if not sickbeard.SYS_ENCODING or sickbeard.SYS_ENCODING in ('ANSI_X3.4-1968', 'US-ASCII', 'ASCII'):
        sickbeard.SYS_ENCODING = 'UTF-8'

    # need console logging for SickBeard.py and SickBeard-console.exe
    consoleLogging = (not hasattr(sys, "frozen")) or (sickbeard.MY_NAME.lower().find('-console') > 0)

    # rename the main thread
    threading.currentThread().name = "MAIN"

    try:
        opts, args = getopt.getopt(sys.argv[1:], "qfdp::", ['quiet', 'forceupdate', 'daemon', 'port=', 'pidfile=', 'nolaunch', 'config=', 'datadir=']) #@UnusedVariable
    except getopt.GetoptError:
        print "Available options: --quiet, --forceupdate, --port, --daemon, --pidfile, --config, --datadir"
        sys.exit()

    forceUpdate = False
    forcedPort = None
    noLaunch = False

    for o, a in opts:
        # for now we'll just silence the logging
        if o in ('-q', '--quiet'):
            consoleLogging = False

        # should we update right away?
        if o in ('-f', '--forceupdate'):
            forceUpdate = True

        # should we update right away?
        if o in ('--nolaunch',):
            noLaunch = True

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

        # config file
        if o in ('--config',):
            sickbeard.CONFIG_FILE = os.path.abspath(a)

        # datadir
        if o in ('--datadir',):
            sickbeard.DATA_DIR = os.path.abspath(a)

        # write a pidfile if requested
        if o in ('--pidfile',):
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
    
    # if they don't specify a config file then put it in the data dir
    if not sickbeard.CONFIG_FILE:
        sickbeard.CONFIG_FILE = os.path.join(sickbeard.DATA_DIR, "config.ini")

    # make sure that we can create the data dir
    if not os.access(sickbeard.DATA_DIR, os.F_OK):
        try:
            os.makedirs(sickbeard.DATA_DIR, 0744)
        except os.error, e:
            raise SystemExit("Unable to create datadir '" + sickbeard.DATA_DIR + "'")

    # make sure we can write to the data dir
    if not os.access(sickbeard.DATA_DIR, os.W_OK):
        raise SystemExit("Data dir must be writeable '" + sickbeard.DATA_DIR + "'")

    # make sure we can write to the config file
    if not os.access(sickbeard.CONFIG_FILE, os.W_OK):
        if os.path.isfile(sickbeard.CONFIG_FILE):
            raise SystemExit("Config file '" + sickbeard.CONFIG_FILE + "' must be writeable")
        elif not os.access(os.path.dirname(sickbeard.CONFIG_FILE), os.W_OK):
            raise SystemExit("Config file root dir '" + os.path.dirname(sickbeard.CONFIG_FILE) + "' must be writeable") 
        
    os.chdir(sickbeard.DATA_DIR)
    
    if consoleLogging:
        print "Starting up Sick Beard "+SICKBEARD_VERSION+" from " + sickbeard.CONFIG_FILE

    # load the config and publish it to the sickbeard package
    if not os.path.isfile(sickbeard.CONFIG_FILE):
        logger.log(u"Unable to find " + sickbeard.CONFIG_FILE + " , all settings will be default", logger.WARNING)

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
                'ip_whitelist': sickbeard.WEB_IP_WHITELIST
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
    if sickbeard.LAUNCH_BROWSER and not noLaunch:
        sickbeard.launchBrowser(startPort)

    # start an update if we're supposed to
    if forceUpdate:
        sickbeard.showUpdateScheduler.action.run(force=True) #@UndefinedVariable

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
