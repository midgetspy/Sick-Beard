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

import re

from sickbeard import helpers
from sickbeard import name_cache
from sickbeard import logger
from sickbeard import db


def get_scene_exceptions(tvdb_id):
    """
    Given a tvdb_id, return a list of all the scene exceptions.
    """

    myDB = db.DBConnection("cache.db")
    exceptions = myDB.select("SELECT DISTINCT show_name FROM scene_exceptions WHERE tvdb_id = ?", [tvdb_id])
    return [cur_exception["show_name"] for cur_exception in exceptions]


def get_scene_exception_by_name(show_name):
    """
    Given a show name, return the tvdbid of the exception, None if no exception
    is present.
    """

    myDB = db.DBConnection("cache.db")

    # try the obvious case first
    exception_result = myDB.select("SELECT tvdb_id FROM scene_exceptions WHERE LOWER(show_name) = ?", [show_name.lower()])
    if exception_result:
        return int(exception_result[0]["tvdb_id"])

    all_exception_results = myDB.select("SELECT DISTINCT show_name, tvdb_id FROM scene_exceptions")
    for cur_exception in all_exception_results:

        cur_exception_name = cur_exception["show_name"]
        cur_tvdb_id = int(cur_exception["tvdb_id"])

        if show_name.lower() in (cur_exception_name.lower(), helpers.sanitizeSceneName(cur_exception_name).lower().replace('.', ' ')):
            logger.log(u"Scene exception lookup got tvdb id " + str(cur_tvdb_id) + u", using that", logger.DEBUG)
            return cur_tvdb_id

    return None


def retrieve_exceptions():
    """
    Looks up the exceptions on github, parses them into a dict, and inserts them into the
    scene_exceptions table in cache.db. Also clears the scene name cache.
    """

    provider = 'sb_tvdb_scene_exceptions'
    remote_exception_dict = {}
    local_exception_dict = {}
    query_list = []

    # remote exceptions are stored on github pages
    url = 'http://midgetspy.github.io/sb_tvdb_scene_exceptions/exceptions.txt'

    logger.log(u"Check scene exceptions update")

    # get remote exceptions
    url_data = helpers.getURL(url)

    if not url_data:
        # when url_data is None, trouble connecting to github
        logger.log(u"Check scene exceptions update failed. Unable to get URL: " + url, logger.ERROR)
        return False

    else:
        # each exception is on one line with the format tvdb_id: 'show name 1', 'show name 2', etc
        for cur_line in url_data.splitlines():
            cur_line = cur_line.decode('utf-8')
            tvdb_id, sep, aliases = cur_line.partition(':')  # @UnusedVariable

            if not aliases:
                continue

            cur_tvdb_id = int(tvdb_id)

            # regex out the list of shows, taking \' into account
            alias_list = [re.sub(r'\\(.)', r'\1', x) for x in re.findall(r"'(.*?)(?<!\\)',?", aliases)]

            remote_exception_dict[cur_tvdb_id] = alias_list

        # get local exceptions
        myDB = db.DBConnection("cache.db", row_type="dict")
        sql_result = myDB.select("SELECT tvdb_id, show_name FROM scene_exceptions WHERE provider=?;", [provider])

        for cur_result in sql_result:
            cur_tvdb_id = cur_result["tvdb_id"]
            if cur_tvdb_id not in local_exception_dict:
                local_exception_dict[cur_tvdb_id] = []
            local_exception_dict[cur_tvdb_id].append(cur_result["show_name"])

        # check remote against local for added exceptions
        for cur_tvdb_id in remote_exception_dict:
            if cur_tvdb_id not in local_exception_dict:
                local_exception_dict[cur_tvdb_id] = []

            for cur_exception_name in remote_exception_dict[cur_tvdb_id]:
                if cur_exception_name not in local_exception_dict[cur_tvdb_id]:
                    query_list.append(["INSERT INTO scene_exceptions (tvdb_id,show_name,provider) VALUES (?,?,?);", [cur_tvdb_id, cur_exception_name, provider]])

        # check local against remote for removed exceptions
        for cur_tvdb_id in local_exception_dict:
            if cur_tvdb_id not in remote_exception_dict:
                query_list.append(["DELETE FROM scene_exceptions WHERE tvdb_id=? AND provider=?;", [cur_tvdb_id, provider]])

            else:
                for cur_exception_name in local_exception_dict[cur_tvdb_id]:
                    if cur_exception_name not in remote_exception_dict[cur_tvdb_id]:
                        query_list.append(["DELETE FROM scene_exceptions WHERE tvdb_id= ? AND show_name=? AND provider=?;", [cur_tvdb_id, cur_exception_name, provider]])

        if query_list:
            logger.log(u"Updating scene exceptions")
            myDB.mass_action(query_list, logTransaction=True)

            logger.log(u"Clear name cache")
            name_cache.clearCache()

            logger.log(u"Performing a vacuum on database: " + myDB.filename)
            myDB.action("VACUUM")

        else:
            logger.log(u"No scene exceptions update needed")

    return True
