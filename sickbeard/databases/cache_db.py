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
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

from sickbeard import db
from sickbeard import db_peewee

# Add new migrations at the bottom of the list; subclass the previous migration.
class InitialSchema (db.SchemaUpgrade):
    def test(self):
        return self.hasTable("lastUpdate")

    def execute(self):
        with db_peewee.cachedb.transaction():
            tables = [db_peewee.Lastupdate, db_peewee.DbVersion]
            for t in tables:
                t.create_table()
            db_peewee.DbVersion(db_version=1).save(force_insert=True)


class AddSceneExceptions(InitialSchema):
    def test(self):
        return self.hasTable("scene_exceptions")

    def execute(self):
        db_peewee.SceneException.create_table()


class AddSceneNameCache(AddSceneExceptions):
    def test(self):
        return (
            self.hasTable("scene_names") and
            self.hasColumn("scene_names", "id"))

    def execute(self):
        db_peewee.SceneName.drop_table(fail_silently=True)
        db_peewee.SceneName.create_table()
