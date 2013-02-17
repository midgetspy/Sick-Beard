# Author: Dieter Blomme <dieterblomme@gmail.com>
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

import sickbeard
from sickbeard import logger
from lib.trakt import *

class TraktNotifier:
    """
    A "notifier" for trakt.tv which keeps track of what has and hasn't been added to your library.
    """

    def notify_snatch(self, ep_name):
        pass

    def notify_download(self, ep_name):
        pass
    
    def notify_subtitle_download(self, ep_name, lang):
        pass

    def update_library(self, ep_obj):
        """
        Sends a request to trakt indicating that the given episode is part of our library.
        
        ep_obj: The TVEpisode object to add to trakt
        """
        
        if sickbeard.USE_TRAKT:
            
            # URL parameters
            data = {
                'tvdb_id': ep_obj.show.tvdbid,
                'title': ep_obj.show.name,
                'year': ep_obj.show.startyear,
                'episodes': [ {
                    'season': ep_obj.season,
                    'episode': ep_obj.episode
                    } ]
                }
            
            if data is not None:
                TraktCall("show/episode/library/%API%", self._api(), self._username(), self._password(), data)
                if sickbeard.TRAKT_REMOVE_WATCHLIST:
                    TraktCall("show/episode/unwatchlist/%API%", self._api(), self._username(), self._password(), data)

    def test_notify(self, api, username, password):
        """
        Sends a test notification to trakt with the given authentication info and returns a boolean
        representing success.
        
        api: The api string to use
        username: The username to use
        password: The password to use
        
        Returns: True if the request succeeded, False otherwise
        """
        
        data = TraktCall("account/test/%API%", api, username, password, {})
        if data["status"] == "success":
            return True

    def _username(self):
        return sickbeard.TRAKT_USERNAME

    def _password(self):
        return sickbeard.TRAKT_PASSWORD

    def _api(self):
        return sickbeard.TRAKT_API

    def _use_me(self):
        return sickbeard.USE_TRAKT


notifier = TraktNotifier
