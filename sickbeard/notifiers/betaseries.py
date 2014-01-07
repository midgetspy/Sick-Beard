# Author: Gregoire Astruc <gregoire.astruc@gmail.com>
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
import urllib2

from hashlib import md5

try:
    import json
except ImportError:
    from lib import simplejson as json

import sickbeard

from sickbeard import logger

class BetaSeriesNotifier:
    """
    A "notifier" for betaseries.com which keeps track of what has and hasn't been added to your library.
    """

    def notify_snatch(self, ep_name):
        pass

    def notify_download(self, ep_name):
        pass

    def update_library(self, ep_obj):
        """
        Sends a request to betaseries indicating that the given episode is part of our library.

        ep_obj: The TVEpisode object to add to betaseries
        """
        if not sickbeard.USE_BETASERIES:
            return

        # TODO: Figure out if the show is present, and eventually add it.

        self._notifyBetaSeries('episodes/downloaded', {'thetvdb_id': ep_obj.show.tvdbid})

    def test_notify(self, username, password):
        """
        Sends a test notification to trakt with the given authentication info and returns a boolean
        representing success.

        api: The api string to use
        username: The username to use
        password: The password to use

        Returns: True if the request succeeded, False otherwise
        """

        method = "timeline/home"
        return self._notifyBetaSeries(method, login=username, password=password)

    def _username(self):
        return sickbeard.BETASERIES_USERNAME

    def _password(self):
        return sickbeard.BETASERIES_PASSWORD

    def _api(self):
        return sickbeard.BETASERIES_API

    def _use_me(self):
        return sickbeard.USE_BETASERIES

    def _notifyBetaSeries(self, method, data = {}, login = None, password = None):
        """
        A generic method for communicating with trakt. Uses the method and data provided along
        with the auth info to send the command.

        method: The URL to use at trakt, relative, no leading slash.
        api: The API string to provide to trakt
        username: The username to use when logging in
        password: The unencrypted password to use when logging in

        Returns: A boolean representing success
        """
        logger.log("betaseries_notifier: Call method " + method, logger.DEBUG)

        # if the username isn't given then use the config username
        if not login:
            login = self._login()

        # if the password isn't given then use the config password
        if not password:
            password = self._password()

        password = md5(password).hexdigest()
        token = None

        try:
            stream = urllib2.urlopen(_requestBetaSeries('members/auth', {"login": login, "password": password}))
            auth_resp = stream.read()
            auth_resp = json.loads(auth_resp)

            token = auth_resp["token"]
        except urllib2.URLError, e:
            error = ''.join(e.readlines())
            logger.log("betaseries_notifier: Failed authenticating: {0} ({1})".format(e, error), logger.ERROR)
            return False
        except IOError, e:
            logger.log("betaseries_notifier: Failed authenticating: {0}".format(e), logger.ERROR)
            return False


        # request the URL from trakt and parse the result as json
        try:
            logger.log("betaseries_notifier: Calling method https://api.betaseries.com/{0}, with data: {1}".format(method, encoded_data), logger.DEBUG)
            stream = urllib2.urlopen(_requestBetaSeries(method, data, token))
            resp = stream.read()

            resp = json.loads(resp)

            if resp["errors"]:
                raise Exception(resp["errors"])

        except (IOError):
            logger.log("betaseries_notifier: Failed calling method", logger.ERROR)
            return False

        if not resp["errors"]:
            logger.log("betaseries_notifier: Succeeded calling method. Result: {0}".format(resp), logger.DEBUG)
            return True

        #TODO: Destroy token.

        logger.log("betaseries_notifier: Failed calling method", logger.ERROR)
        return False

    def _requestBetaSeries(self, method, data, token = None, version = "2.2"):
        request = urllib2.Request(
                url="https://api.betaseries.com/{0}",
                data=urllib.urlencode(data),
                headers=[
                    ("User-Agent", "Sickbeard/1.0"),
                    ("X-BetaSeries-Version", "2.2"),
                    ("X-BetaSeries-Key", self._api())])

        if token:
            request.add_header("X-BetaSeries-Token", token)

        return request

notifier = BetaSeriesNotifier
