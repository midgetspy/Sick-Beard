

import unittest
from sickbeard import common, db
from sickbeard.databases import mainDB
import sickbeard

class SceneExceptionTestCase(unittest.TestCase):
    def setUp(self):
        self.old_prog_dir = sickbeard.PROG_DIR
        sickbeard.PROG_DIR = '.'
        db.upgradeDatabase(db.DBConnection(), mainDB.InitialSchema)

    def tearDown(self):
        sickbeard.PROG_DIR = self.old_prog_dir

    def test_sceneExceptionsEmpty(self):
        self.assertEqual(common.getSceneExceptions(0), [])

    def test_sceneExceptionsBabylon5(self):
        self.assertEqual(sorted(common.getSceneExceptions(70726)), ['Babylon 5', 'Babylon5'])

    def test_sceneExceptionByName(self):
        self.assertEqual(common.getSceneExceptionByName('Babylon5'), 70726)
        
    def test_sceneExceptionByNameEmpty(self):
        self.assertEqual(common.getSceneExceptionByName('nothing useful'), None)


