import unittest

import sqlite3

import sys, os.path
sys.path.append(os.path.abspath('..'))
sys.path.append(os.path.abspath('../lib'))

import sickbeard
import shutil, time, os.path, sys
from sickbeard import encodingKludge as ek 
from sickbeard import db
from sickbeard.databases import mainDB




#=================
# sickbeard globals
#=================
sickbeard.SYS_ENCODING = 'UTF-8'
sickbeard.showList = []
sickbeard.QUALITY_DEFAULT = 4
sickbeard.SEASON_FOLDERS_DEFAULT = 1
sickbeard.SEASON_FOLDERS_FORMAT = 'Season %02d'


sickbeard.PROG_DIR = os.path.abspath('..')
sickbeard.DATA_DIR = sickbeard.PROG_DIR

#=================
# test globals
#=================
TESTDIR = os.path.abspath('.')
TESTDBNAME = "test_sickbeard.db"

SHOWNAME = u"show name"
SEASON = 4
EPISODE = 2
FILENAME = u"show name - s0"+str(SEASON)+"e0"+str(EPISODE)+".mkv"
FILEPATH = u"/user/name/dir/"+SHOWNAME+"/"+FILENAME

#=================
# dummy functions
#=================
def _dummy_saveConfig():
    return True
# this overrides the sickbeard save_config which gets called during a db upgrade
# this might be considered a hack
mainDB.sickbeard.save_config = _dummy_saveConfig


#=================
# test classes
#=================
class SickbeardTestDBCase(unittest.TestCase):
    def setUp(self):
        sickbeard.showList = []
        setUp_test_db()
    
    def tearDown(self):
        sickbeard.showList = []
        tearDown_test_db() 

class TestDBConnection(db.DBConnection,object):
    def __init__(self, dbFileName=TESTDBNAME):
        dbFileName = os.path.join(TESTDIR, dbFileName)
        super(TestDBConnection, self).__init__(dbFileName)
        
# this will override the normal db connection
sickbeard.db.DBConnection = TestDBConnection


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
    
       
def tearDown_test_db():
    """Deletes the test db
        although this seams not to work on my system it leaves me with an zero kb file
    """
    os.remove(ek.ek(os.path.join, TESTDIR, TESTDBNAME))

def setUp_test_episode():
    f = open('/anyfile','w')
    f.write("foo bar")
    f.close()

if __name__ == '__main__':
    print "=================="
    print "Dont call this directly"
    print "=================="
    print "you might want to call"
    
    dirList=os.listdir(TESTDIR)
    for fname in dirList:
        if (fname.find("_test") > 0) and (fname.find("pyc") < 0):
            print "- "+fname
    
    print "=================="
    print "or just call all_tests.py"

