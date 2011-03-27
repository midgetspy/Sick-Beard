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

import db
import datetime

from sickbeard.common import SNATCHED, Quality

dateFormat = "%Y%m%d%H%M%S"

def _logHistoryItem(action, showid, season, episode, quality, resource, provider):

    logDate = datetime.datetime.today().strftime(dateFormat)

    myDB = db.DBConnection()
    myDB.action("INSERT INTO history (action, date, showid, season, episode, quality, resource, provider) VALUES (?,?,?,?,?,?,?,?)",
                [action, logDate, showid, season, episode, quality, resource, provider])


def logSnatch(searchResult):

    for curEpObj in searchResult.episodes:

        showid = int(curEpObj.show.tvdbid)
        season = int(curEpObj.season)
        episode = int(curEpObj.episode)
        quality = searchResult.quality

        providerClass = searchResult.provider
        if providerClass != None:
            provider = providerClass.name
        else:
            provider = "unknown"

        action = Quality.compositeStatus(SNATCHED, searchResult.quality)

        resource = searchResult.name

        _logHistoryItem(action, showid, season, episode, quality, resource, provider)

def logDownload(episode, filename, new_ep_quality, release_group=None):

    showid = int(episode.show.tvdbid)
    season = int(episode.season)
    epNum = int(episode.episode)

    quality = new_ep_quality
    
    # store the release group as the provider if possible
    if release_group:
        provider = release_group
    else:
        provider = -1

    action = episode.status

    _logHistoryItem(action, showid, season, epNum, quality, filename, provider)

