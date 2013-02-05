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

from sickbeard.db_peewee import SceneName
from sickbeard.helpers import sanitizeSceneName

def addNameToCache(name, tvdb_id):
    """
    Adds the show & tvdb id to the scene_names table in cache.db.

    name: The show name to cache
    tvdb_id: The tvdb id that this show should be cached with (can be None/0
        for unknown)
    """

    # standardize the name we're using to account for small differences
    # in providers (aka NZBMatrix sucks)
    name = sanitizeSceneName(name)

    if not tvdb_id:
        tvdb_id = 0

    SceneName(tvdb_id=tvdb_id, name=name).save(force_insert=True)


def retrieveNameFromCache(name):
    """
    Looks up the given name in the scene_names table in cache.db.

    name: The show name to look up.

    Returns: the tvdb id that resulted from the cache lookup or None if
    the show wasn't found in the cache
    """

    # standardize the name we're using to account for small differences
    # in providers (aka NZBMatrix sucks)
    name = sanitizeSceneName(name)

    result = SceneName.select().where(SceneName.name == name).first()
    if not result:
        return None

    return result.tvdb_id


def clearCache():
    """
    Deletes all "unknown" entries from the cache (names with tvdb_id of 0).
    """
    SceneName.delete().where(SceneName.tvdb_id == 0).execute()
