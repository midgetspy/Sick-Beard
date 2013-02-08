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
from sickbeard.db_peewee import *

# Add new migrations at the bottom of the list; subclass the previous migration.
class InitialSchema (db.SchemaUpgrade):
    cache_tables = [
        ProviderCache,
        Lastupdate,
        CacheDbVersion,
        SceneException,
        SceneName
    ]
    def test(self):
        for t in self.cache_tables:
            if not t.table_exists():
                return False
        return True

    def execute(self):
        ProviderCache.create_table(fail_silently=True)
        Lastupdate.create_table(fail_silently=True)
        DbVersion.create_table(fail_silently=True)
        SceneException.create_table(fail_silently=True)
        SceneName.create_table(fail_silently=True)

        DbVersion(db_version=1).save(force_insert=True)
