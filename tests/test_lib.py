# coding=UTF-8
# Author: Dennis Lutter <lad1337@gmail.com>
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

import unittest

import sqlite3

import sys, os.path
sys.path.append(os.path.abspath('..'))
sys.path.append(os.path.abspath('../lib'))

import sickbeard
import shutil, time
from sickbeard import encodingKludge as ek, providers, tvcache
from sickbeard import db
from sickbeard.databases import mainDB
from sickbeard.databases import cache_db

#=================
# test globals
#=================
TESTDIR = os.path.abspath('.')
TESTDBNAME = "sickbeard.db"
TESTCACHEDBNAME = "cache.db"


SHOWNAME = u"show name"
SEASON = 4
EPISODE = 2
FILENAME = u"show name - s0" + str(SEASON) + "e0" + str(EPISODE) + ".mkv"
FILEDIR = os.path.join(TESTDIR, SHOWNAME)
FILEPATH = os.path.join(FILEDIR, FILENAME)

SHOWDIR = os.path.join(TESTDIR, SHOWNAME+" final")

#sickbeard.logger.sb_log_instance = sickbeard.logger.SBRotatingLogHandler(os.path.join(TESTDIR, 'sickbeard.log'), sickbeard.logger.NUM_LOGS, sickbeard.logger.LOG_SIZE)
sickbeard.logger.SBRotatingLogHandler.log_file = os.path.join(os.path.join(TESTDIR, 'Logs'), 'test_sickbeard.log')

#=================
# prepare env functions
#=================
def createTestLogFolder():
    if not os.path.isdir(sickbeard.LOG_DIR):
        os.mkdir(sickbeard.LOG_DIR)

# call env functions at apropriate time durin sickbeard var setup

#=================
# sickbeard globals
#=================
sickbeard.SYS_ENCODING = 'UTF-8'
sickbeard.showList = []
sickbeard.QUALITY_DEFAULT = 4
sickbeard.SEASON_FOLDERS_DEFAULT = 1
sickbeard.SEASON_FOLDERS_FORMAT = 'Season %02d'

sickbeard.NAMING_SHOW_NAME = 1
sickbeard.NAMING_EP_NAME = 1
sickbeard.NAMING_EP_TYPE = 0
sickbeard.NAMING_MULTI_EP_TYPE = 1
sickbeard.NAMING_SEP_TYPE = 0
sickbeard.NAMING_USE_PERIODS = 0
sickbeard.NAMING_QUALITY = 0
sickbeard.NAMING_DATES = 1

sickbeard.PROVIDER_ORDER = ["sick_beard_index"]
sickbeard.newznabProviderList = providers.getNewznabProviderList("Sick Beard Index|http://momo.sickbeard.com/||1!!!NZBs.org|http://beta.nzbs.org/||0")
sickbeard.providerList = providers.makeProviderList()

sickbeard.PROG_DIR = os.path.abspath('..')
sickbeard.DATA_DIR = sickbeard.PROG_DIR
sickbeard.LOG_DIR = os.path.join(TESTDIR, 'Logs')
createTestLogFolder()
sickbeard.logger.sb_log_instance.initLogging(False)

#=================
# dummy functions
#=================
def _dummy_saveConfig():
    return True
# this overrides the sickbeard save_config which gets called during a db upgrade
# this might be considered a hack
mainDB.sickbeard.save_config = _dummy_saveConfig

# the real one tries to contact tvdb just stop it from getting more info on the ep
def _fake_specifyEP(self, season, episode):
    pass

sickbeard.tv.TVEpisode.specifyEpisode = _fake_specifyEP


#=================
# test classes
#=================
class SickbeardTestDBCase(unittest.TestCase):
    def setUp(self):
        sickbeard.showList = []
        setUp_test_db()
        setUp_test_episode_file()
        setUp_test_show_dir()

    def tearDown(self):
        sickbeard.showList = []
        tearDown_test_db()
        tearDown_test_episode_file()
        tearDown_test_show_dir()


class TestDBConnection(db.DBConnection, object):

    def __init__(self, dbFileName=TESTDBNAME):
        dbFileName = os.path.join(TESTDIR, dbFileName)
        super(TestDBConnection, self).__init__(dbFileName)


class TestCacheDBConnection(TestDBConnection, object):

    def __init__(self, providerName):
        db.DBConnection.__init__(self, os.path.join(TESTDIR, TESTCACHEDBNAME))

        # Create the table if it's not already there
        try:
            sql = "CREATE TABLE "+providerName+" (name TEXT, season NUMERIC, episodes TEXT, tvrid NUMERIC, tvdbid NUMERIC, url TEXT, time NUMERIC, quality TEXT);"
            self.connection.execute(sql)
            self.connection.commit()
        except sqlite3.OperationalError, e:
            if str(e) != "table "+providerName+" already exists":
                raise

        # Create the table if it's not already there
        try:
            sql = "CREATE TABLE lastUpdate (provider TEXT, time NUMERIC);"
            self.connection.execute(sql)
            self.connection.commit()
        except sqlite3.OperationalError, e:
            if str(e) != "table lastUpdate already exists":
                raise

# this will override the normal db connection
sickbeard.db.DBConnection = TestDBConnection
sickbeard.tvcache.CacheDBConnection = TestCacheDBConnection


#=================
# test functions
#=================
def setUp_test_db():
    """upgrades the db to the latest version
    """
    # upgrading the db
    db.upgradeDatabase(db.DBConnection(), mainDB.InitialSchema)
    # fix up any db problems
    db.sanityCheckDatabase(db.DBConnection(), mainDB.MainSanityCheck)
    
    #and for cache.b too
    db.upgradeDatabase(db.DBConnection("cache.db"), cache_db.InitialSchema)


def tearDown_test_db():
    """Deletes the test db
        although this seams not to work on my system it leaves me with an zero kb file
    """
    # uncomment next line so leave the db intact beween test and at the end
    #return False
    if os.path.exists(os.path.join(TESTDIR, TESTDBNAME)):
        os.remove(os.path.join(TESTDIR, TESTDBNAME))
    if os.path.exists(os.path.join(TESTDIR, TESTCACHEDBNAME)):
        os.remove(os.path.join(TESTDIR, TESTCACHEDBNAME))

def setUp_test_episode_file():
    if not os.path.exists(FILEDIR):
        os.makedirs(FILEDIR)

    f = open(FILEPATH, "w")
    f.write("foo bar")
    f.close()


def tearDown_test_episode_file():
    shutil.rmtree(FILEDIR)


def setUp_test_show_dir():
    if not os.path.exists(SHOWDIR):
        os.makedirs(SHOWDIR)


def tearDown_test_show_dir():
    shutil.rmtree(SHOWDIR)

tearDown_test_db()

if __name__ == '__main__':
    print "=================="
    print "Dont call this directly"
    print "=================="
    print "you might want to call"

    dirList = os.listdir(TESTDIR)
    for fname in dirList:
        if (fname.find("_test") > 0) and (fname.find("pyc") < 0):
            print "- " + fname

    print "=================="
    print "or just call all_tests.py"

