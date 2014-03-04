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


# Add new migrations at the bottom of the list; subclass the previous migration.
class InitialSchema (db.SchemaUpgrade):
    def test(self):
        return self.hasTable("lastUpdate")

    def execute(self):

        queries = [
            ("CREATE TABLE lastUpdate (provider TEXT, time NUMERIC);",),
            ("CREATE TABLE db_version (db_version INTEGER);",),
            ("INSERT INTO db_version (db_version) VALUES (?)", 1),
        ]
        for query in queries:
            if len(query) == 1:
                self.connection.action(query[0])
            else:
                self.connection.action(query[0], query[1:])


class AddSceneExceptions(InitialSchema):
    def test(self):
        return self.hasTable("scene_exceptions")

    def execute(self):
        self.connection.action("CREATE TABLE scene_exceptions (exception_id INTEGER PRIMARY KEY, tvdb_id INTEGER KEY, show_name TEXT, provider TEXT)")


class AddSceneNameCache(AddSceneExceptions):
    def test(self):
        return self.hasTable("scene_names")

    def execute(self):
        self.connection.action("CREATE TABLE scene_names (tvdb_id INTEGER, name TEXT)")


class AddSceneExceptionsProvider(AddSceneNameCache):
    def test(self):
        return self.hasColumn("scene_exceptions", "provider")

    def execute(self):
        if not self.hasColumn("scene_exceptions", "provider"):
            self.addColumn("scene_exceptions", "provider", data_type='TEXT', default='sb_tvdb_scene_exceptions')
