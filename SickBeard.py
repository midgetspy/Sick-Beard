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

# Check needed software dependencies to nudge users to fix their setup
import sys
if sys.version_info < (2, 5):
    sys.exit("Sorry, requires Python 2.5, 2.6 or 2.7.")

try:
    import Cheetah
    if Cheetah.Version[0] != '2':
        raise ValueError
except ValueError:
    sys.exit("Sorry, requires Python module Cheetah 2.1.0 or newer.")
except:
    sys.exit("The Python module Cheetah is required")

# We only need this for compiling an EXE and I will just always do that on 2.6+
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
            logger.log(u"There was an error creating the show in " + sqlShow["location"] + ": " + str(e).decode('utf-8'), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)

        # TODO: update the existing shows if the showlist has something in it


def daemonize():
    """
    Fork off as a daemon
    """

    # pylint: disable=E1101
    # Make a non-session-leader child process
    try:
        pid = os.fork()  # @UndefinedVariable - only available in UNIX
        if pid != 0:
            os._exit(0)
    except OSError, e:
        sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

    os.setsid()  # @UndefinedVariable - only available in UNIX

    # Make sure I can read my own files and shut out others
    prev = os.umask(0)
    os.umask(prev and int('077', 8))

    # Make the child a session-leader by detaching from the terminal
    try:
        pid = os.fork()  # @UndefinedVariable - only available in UNIX
        if pid != 0:
            os._exit(0)
    except OSError, e:
        sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

    # Write pid
    if sickbeard.CREATEPID:
        pid = str(os.getpid())
        logger.log(u"Writing PID: " + pid + " to " + str(sickbeard.PIDFILE))
        try:
            file(sickbeard.PIDFILE, 'w').write("%s\n" % pid)
        except IOError, e:
            error_msg = "Unable to write PID file: " + sickbeard.PIDFILE + " Error: " + str(e.strerror) + " [" + str(e.errno) + "]"
            logger.log(u"" + error_msg, logger.ERROR)
            sys.exit(error_msg)

    # Redirect all output
    sys.stdout.flush()
    sys.stderr.flush()

    devnull = getattr(os, 'devnull', '/dev/null')
    stdin = file(devnull, 'r')
    stdout = file(devnull, 'a+')
    stderr = file(devnull, 'a+')
    os.dup2(stdin.fileno(), sys.stdin.fileno())
    os.dup2(stdout.fileno(), sys.stdout.fileno())
    os.dup2(stderr.fileno(), sys.stderr.fileno())


def help_message():
    """
    print help message for commandline options
    """
    help_msg = "\n"
    help_msg += "Usage: " + sickbeard.MY_FULLNAME + " <option> <another option>\n"
    help_msg += "\n"
    help_msg += "Options:\n"
    help_msg += "\n"
    help_msg += "    -h          --help              Prints this message\n"
    help_msg += "    -f          --forceupdate       Force update all shows in the DB (from tvdb) on startup\n"
    help_msg += "    -q          --quiet             Disables logging to console\n"
    help_msg += "                --nolaunch          Suppress launching web browser on startup\n"

    if sys.platform == 'win32':
        help_msg += "    -d          --daemon            Running as real daemon is not supported on Windows\n"
        help_msg += "                                    On Windows, --daemon is substituted with: --quiet --nolaunch\n"
    else:
        help_msg += "    -d          --daemon            Run as double forked daemon (includes options --quiet --nolaunch)\n"
        help_msg += "                --pidfile=<path>    Combined with --daemon creates a pidfile (full path including filename)\n"

    help_msg += "    -p <port>   --port=<port>       Override default/configured port to listen on\n"
    help_msg += "                --datadir=<path>    Override folder (full path) as location for\n"
    help_msg += "                                    storing database, configfile, cache, logfiles \n"
    help_msg += "                                    Default: " + sickbeard.PROG_DIR + "\n"
    help_msg += "                --config=<path>     Override config filename (full path including filename)\n"
    help_msg += "                                    to load configuration from \n"
    help_msg += "                                    Default: config.ini in " + sickbeard.PROG_DIR + " or --datadir location\n"
    help_msg += "                --noresize          Prevent resizing of the banner/posters even if PIL is installed\n"

    return help_msg


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
    sickbeard.DAEMON = False
    sickbeard.CREATEPID = False

    sickbeard.SYS_ENCODING = None

    try:
        locale.setlocale(locale.LC_ALL, "")
        sickbeard.SYS_ENCODING = locale.getpreferredencoding()
    except (locale.Error, IOError):
        pass

    # For OSes that are poorly configured I'll just randomly force UTF-8
    if not sickbeard.SYS_ENCODING or sickbeard.SYS_ENCODING in ('ANSI_X3.4-1968', 'US-ASCII', 'ASCII'):
        sickbeard.SYS_ENCODING = 'UTF-8'

    if not hasattr(sys, "setdefaultencoding"):
        reload(sys)

    try:
        # pylint: disable=E1101
        # On non-unicode builds this will raise an AttributeError, if encoding type is not valid it throws a LookupError
        sys.setdefaultencoding(sickbeard.SYS_ENCODING)
    except:
        sys.exit("Sorry, you MUST add the Sick Beard folder to the PYTHONPATH environment variable\n" +
            "or find another way to force Python to use " + sickbeard.SYS_ENCODING + " for string encoding.")

    # Need console logging for SickBeard.py and SickBeard-console.exe
    consoleLogging = (not hasattr(sys, "frozen")) or (sickbeard.MY_NAME.lower().find('-console') > 0)

    # Rename the main thread
    threading.currentThread().name = "MAIN"

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hfqdp::", ['help', 'forceupdate', 'quiet', 'nolaunch', 'daemon', 'pidfile=', 'port=', 'datadir=', 'config=', 'noresize'])  # @UnusedVariable
    except getopt.GetoptError:
        sys.exit(help_message())

    forceUpdate = False
    forcedPort = None
    noLaunch = False

    for o, a in opts:

        # Prints help message
        if o in ('-h', '--help'):
            sys.exit(help_message())

        # Should we update (from tvdb) all shows in the DB right away?
        if o in ('-f', '--forceupdate'):
            forceUpdate = True

        # Disables logging to console
        if o in ('-q', '--quiet'):
            consoleLogging = False

        # Suppress launching web browser
        # Needed for OSes without default browser assigned
        # Prevent duplicate browser window when restarting in the app
        if o in ('--nolaunch',):
            noLaunch = True

        # Run as a double forked daemon
        if o in ('-d', '--daemon'):
            sickbeard.DAEMON = True
            # When running as daemon disable consoleLogging and don't start browser
            consoleLogging = False
            noLaunch = True

            if sys.platform == 'win32':
                sickbeard.DAEMON = False

        # Write a pidfile if requested
        if o in ('--pidfile',):
            sickbeard.CREATEPID = True
            sickbeard.PIDFILE = str(a)

            # If the pidfile already exists, sickbeard may still be running, so exit
            if os.path.exists(sickbeard.PIDFILE):
                sys.exit("PID file: " + sickbeard.PIDFILE + " already exists. Exiting.")

        # Override default/configured port
        if o in ('-p', '--port'):
            try:
                forcedPort = int(a)
            except ValueError:
                sys.exit("Port: " + str(a) + " is not a number. Exiting.")

        # Specify folder to use as data dir (storing database, configfile, cache, logfiles)
        if o in ('--datadir',):
            sickbeard.DATA_DIR = os.path.abspath(a)

        # Specify filename to load the config information from
        if o in ('--config',):
            sickbeard.CONFIG_FILE = os.path.abspath(a)

        # Prevent resizing of the banner/posters even if PIL is installed
        if o in ('--noresize',):
            sickbeard.NO_RESIZE = True

    # The pidfile is only useful in daemon mode, make sure we can write the file properly
    if sickbeard.CREATEPID:
        if sickbeard.DAEMON:
            pid_dir = os.path.dirname(sickbeard.PIDFILE)
            if not os.access(pid_dir, os.F_OK):
                sys.exit("PID dir: " + pid_dir + " doesn't exist. Exiting.")
            if not os.access(pid_dir, os.W_OK):
                sys.exit("PID dir: " + pid_dir + " must be writable (write permissions). Exiting.")

        else:
            if consoleLogging:
                sys.stdout.write("Not running in daemon mode. PID file creation disabled.\n")

            sickbeard.CREATEPID = False

    # If they don't specify a config file then put it in the data dir
    if not sickbeard.CONFIG_FILE:
        sickbeard.CONFIG_FILE = os.path.join(sickbeard.DATA_DIR, "config.ini")

    # Make sure that we can create the data dir
    if not os.access(sickbeard.DATA_DIR, os.F_OK):
        try:
            os.makedirs(sickbeard.DATA_DIR, 0744)
        except os.error:
            sys.exit("Unable to create data directory: " + sickbeard.DATA_DIR + " Exiting.")

    # Make sure we can write to the data dir
    if not os.access(sickbeard.DATA_DIR, os.W_OK):
        sys.exit("Data directory: " + sickbeard.DATA_DIR + " must be writable (write permissions). Exiting.")

    # Make sure we can write to the config file
    if not os.access(sickbeard.CONFIG_FILE, os.W_OK):
        if os.path.isfile(sickbeard.CONFIG_FILE):
            sys.exit("Config file: " + sickbeard.CONFIG_FILE + " must be writeable (write permissions). Exiting.")
        elif not os.access(os.path.dirname(sickbeard.CONFIG_FILE), os.W_OK):
            sys.exit("Config file directory: " + os.path.dirname(sickbeard.CONFIG_FILE) + " must be writeable (write permissions). Exiting")

    os.chdir(sickbeard.DATA_DIR)

    if consoleLogging:
        sys.stdout.write("Starting up Sick Beard " + SICKBEARD_VERSION + "\n")
        if not os.path.isfile(sickbeard.CONFIG_FILE):
            sys.stdout.write("Unable to find '" + sickbeard.CONFIG_FILE + "' , all settings will be default!" + "\n")

    # Load the config and publish it to the sickbeard package
    sickbeard.CFG = ConfigObj(sickbeard.CONFIG_FILE)

    # Initialize the config and our threads
    sickbeard.initialize(consoleLogging=consoleLogging)

    sickbeard.showList = []

    if sickbeard.DAEMON:
        daemonize()

    # Use this PID for everything
    sickbeard.PID = os.getpid()

    if forcedPort:
        logger.log(u"Forcing web server to port " + str(forcedPort))
        startPort = forcedPort
    else:
        startPort = sickbeard.WEB_PORT

    if sickbeard.WEB_LOG:
        log_dir = sickbeard.LOG_DIR
    else:
        log_dir = None

    # sickbeard.WEB_HOST is available as a configuration value in various
    # places but is not configurable. It is supported here for historic reasons.
    if sickbeard.WEB_HOST and sickbeard.WEB_HOST != '0.0.0.0':
        webhost = sickbeard.WEB_HOST
    else:
        if sickbeard.WEB_IPV6:
            webhost = '::'
        else:
            webhost = '0.0.0.0'

    try:
        initWebServer({
                      'port': startPort,
                      'host': webhost,
                      'data_root': os.path.join(sickbeard.PROG_DIR, 'data'),
                      'web_root': sickbeard.WEB_ROOT,
                      'log_dir': log_dir,
                      'username': sickbeard.WEB_USERNAME,
                      'password': sickbeard.WEB_PASSWORD,
                      'enable_https': sickbeard.ENABLE_HTTPS,
                      'https_cert': sickbeard.HTTPS_CERT,
                      'https_key': sickbeard.HTTPS_KEY,
                      })
    except IOError:
        logger.log(u"Unable to start web server, is something else running on port: " + str(startPort), logger.ERROR)
        if sickbeard.LAUNCH_BROWSER and not sickbeard.DAEMON:
            logger.log(u"Launching browser and exiting", logger.ERROR)
            sickbeard.launchBrowser(startPort)
        sys.exit("Unable to start web server, is something else running on port: " + str(startPort))

    # Build from the DB to start with
    logger.log(u"Loading initial show list")
    loadShowsFromDB()

    # Fire up all our threads
    sickbeard.start()

    # Launch browser if we're supposed to
    if sickbeard.LAUNCH_BROWSER and not noLaunch and not sickbeard.DAEMON:
        sickbeard.launchBrowser(startPort)

    # Start an update if we're supposed to
    if forceUpdate:
        sickbeard.showUpdateScheduler.action.run(force=True)  # @UndefinedVariable

    # Stay alive while my threads do the work
    while (True):

        if sickbeard.invoked_command:
            sickbeard.invoked_command()
            sickbeard.invoked_command = None

        time.sleep(1)

    return

if __name__ == "__main__":
    if sys.hexversion >= 0x020600F0:
        freeze_support()
    main()
