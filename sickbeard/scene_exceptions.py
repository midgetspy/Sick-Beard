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
import peewee

from sickbeard import helpers
from sickbeard import name_cache
from sickbeard import logger
from sickbeard.db_peewee import SceneException

def get_scene_exceptions(tvdb_id):
    """
    Given a tvdb_id, return a list of all the scene exceptions.
    """

    return [exception.show_name for exception in
            SceneException.select().where(SceneException.tvdb_id == tvdb_id)]


def get_scene_exception_by_name(show_name):
    """
    Given a show name, return the tvdbid of the exception, None if no exception
    is present.
    """

    # try the obvious case first
    exception_result = SceneException.select().where(
        peewee.fn.Lower(SceneException.show_name == show_name.lower())).first()

    if exception_result is not None:
        return exception_result.tvdb_id

    for cur_exception in SceneException.select():
        cur_exception_name = cur_exception.show_name
        cur_tvdb_id = cur_exception.tvdb_id

        if show_name.lower() in (cur_exception_name.lower(), helpers.sanitizeSceneName(cur_exception_name).lower().replace('.', ' ')):
            logger.log(u"Scene exception lookup got tvdb id "+str(cur_tvdb_id)+u", using that", logger.DEBUG)
            return cur_tvdb_id

    return None


def retrieve_exceptions():
    """
    Looks up the exceptions on github, parses them into a dict, and inserts them into the
    scene_exceptions table in cache.db. Also clears the scene name cache.
    """

    exception_dict = {}

    # exceptions are stored on github pages
    url = 'http://midgetspy.github.com/sb_tvdb_scene_exceptions/exceptions.txt'

    logger.log(u"Check scene exceptions update")
    url_data = helpers.getURL(url)

    if url_data is None:
        # When urlData is None, trouble connecting to github
        logger.log(u"Check scene exceptions update failed. Unable to get URL: " + url, logger.ERROR)
        return

    else:
        # each exception is on one line with the format tvdb_id: 'show name 1', 'show name 2', etc
        for cur_line in url_data.splitlines():
            cur_line = cur_line.decode('utf-8')
            tvdb_id, sep, aliases = cur_line.partition(':') #@UnusedVariable

            if not aliases:
                continue

            tvdb_id = int(tvdb_id)

            # regex out the list of shows, taking \' into account
            alias_list = [re.sub(r'\\(.)', r'\1', x) for x in re.findall(r"'(.*?)(?<!\\)',?", aliases)]

            exception_dict[tvdb_id] = alias_list

        changed_exceptions = False

        # write all the exceptions we got off the net into the database
        for cur_tvdb_id in exception_dict:
            existing_exceptions = [s.show_name for s in SceneException.select(
                SceneException.show_name).where(
                    SceneException.tvdb_id == cur_tvdb_id)]

            for cur_exception in exception_dict[cur_tvdb_id]:
                # if this exception isn't already in the DB then add it
                if cur_exception not in existing_exceptions:
                    SceneException(
                        tvdb_id=cur_tvdb_id,
                        show_name=cur_exception).save()
                    changed_exceptions = True

        # since this could invalidate the results of the cache we clear
        # it out after updating
        if changed_exceptions:
            logger.log(u"Updated scene exceptions")
            name_cache.clearCache()
        else:
            logger.log(u"No scene exceptions update needed")
