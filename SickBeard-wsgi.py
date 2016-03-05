#!/usr/bin/env python
# Author: Nic Wolfe <nic@wolfeden.ca>
# Additions by:
__author__ = 'Rob MacKinnon <rob.mackinnon@gmail.com>'
__name__ = 'SickBeard_wsgi'
# URL: http://code.google.com/p/sickbeard/
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

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
    from multiprocessing import freeze_support  # @UnresolvedImport


import locale
import os
import threading
import signal
import time

import sickbeard
from sickbeard import logger
from sickbeard.version import SICKBEARD_VERSION

from sickbeard.webserveInit import app, initWebServer

from lib.configobj import ConfigObj

from SickBeard import daemonize, loadShowsFromDB

signal.signal(signal.SIGINT, sickbeard.sig_handler)
signal.signal(signal.SIGTERM, sickbeard.sig_handler)


def getEnvironmentFlag(flag, default):
    if os.environ[flag] is not None:
        if os.environ[flag] == 1:
            return True
        else:
            return False
    return default


def getEnvironmentStr(flag):
    if os.environ[flag] is not None:
        return os.environ[flag]
    return None


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

    forceUpdate = getEnvironmentFlag('SICKBEARD_UPDATE', False)
    forcedPort = getEnvironmentStr('SICKBEARD_PORT')
    forcedIP = getEnvironmentStr('SICKBEARD_LISTEN')
    noLaunch = True  # The WSGI version should never try to load a browser

    sickbeard.DAEMON = getEnvironmentFlag('SICKBEARD_FORK', False)
    consoleLogging = getEnvironmentFlag('SICKBEARD_CONSOLELOG', True)
    sickbeard.CREATEPID = getEnvironmentFlag('SICKBEARD_CREATEPID', False)
    sickbeard.PIDFILE = getEnvironmentStr('SICKBEARD_PIDFILE')
    sickbeard.NO_RESIZE = getEnvironmentFlag('SICKBEARD_NO_RESIZE', False)

    if getEnvironmentStr('SICKBEARD_DATA_DIR') is not None:
        sickbeard.DATA_DIR = os.path.abspath(getEnvironmentStr('SICKBEARD_DATA_DIR'))

    if getEnvironmentStr('SICKBEARD_CONF') is not None:
        sickbeard.CONFIG_FILE = getEnvironmentStr('SICKBEARD_CONF')
    else:
        sickbeard.CONFIG_FILE = os.path.join(sickbeard.DATA_DIR, "config.ini")

    if getEnvironmentStr('SICKBEARD_LOGDIR') is not None:
        sickbeard.DATA_DIR = os.path.abspath(getEnvironmentStr('SICKBEARD_LOGDIR'))

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

    if sickbeard.WEB_HOST and sickbeard.WEB_HOST != '0.0.0.0':
        webhost = sickbeard.WEB_HOST
    else:
        if sickbeard.WEB_IPV6:
            webhost = '::'
        else:
            webhost = '0.0.0.0'

    if forcedIP is not None:
        webhost = forcedIP

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
