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


import urllib2

from hashlib import sha1

try:
    import json
except ImportError:
    from lib import simplejson as json

import sickbeard

from sickbeard import logger, exceptions, helpers

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree #@UnusedImport

class TraktNotifier:

    def notify_snatch(self, ep_name):
        pass

    def notify_download(self, ep_name):
        pass
    
    def notify_delete(self, tvdb_id, season, episode):
        logger.log(u"Starting Trakt removal", logger.DEBUG)
        
        show_obj = None
        
        logger.log(u"Loading show object for tvdb_id " + str(tvdb_id), logger.DEBUG)
        # find the show in the showlist
        try:
            show_obj = helpers.findCertainShow(sickbeard.showList, tvdb_id)
        except exceptions.MultipleShowObjectsException:
            raise #TODO: later I'll just log this, for now I want to know about it ASAP
        
        ep_obj = None
        logger.log(u"Retrieving episode object for " + str(season) + "x" + str(episode), logger.DEBUG)
        try:
            ep_obj = show_obj.getEpisode(season, episode)
        except exceptions.EpisodeNotFoundException, e:
            logger.log(u"Unable to find episode: " + ex(e), logger.WARNING)
            
        if ep_obj != None:
            logger.log(u"Removing " + ep_obj.show.name + " " + str(ep_obj.season) + "x" + str(ep_obj.episode) + " from Trakt collection", logger.DEBUG)
            self.update_library(ep_obj, True)
        else:
            logger.log(u"No episode could be found to be removed from your Trakt collection", logger.WARNING)

    def update_library(self, ep_obj, delete=False):
        if sickbeard.USE_TRAKT:
            method = "show/episode/unlibrary/" if delete else "show/episode/library/"
            method += "%API%"
            
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
                self._notifyTrakt(method, None, None, None, data)

    def test_notify(self, api, username, password):
        method = "account/test/"
        method += "%API%"
        return self._notifyTrakt(method, api, username, password, {})

    def _username(self):
        return sickbeard.TRAKT_USERNAME

    def _password(self):
        return sickbeard.TRAKT_PASSWORD

    def _api(self):
        return sickbeard.TRAKT_API

    def _use_me(self):
        return sickbeard.USE_TRAKT

    def _notifyTrakt(self, method, api, username, password, data={}):
        logger.log("trakt_notifier: Call method " + method, logger.DEBUG)

        if not api:
            api = self._api()
        if not username:
            username = self._username()
        if not password:
            password = self._password()
        password = sha1(password).hexdigest()

        method = method.replace("%API%", api)

        data["username"] = username
        data["password"] = password

        encoded_data = json.dumps(data);

        try:
            logger.log("trakt_notifier: Calling method http://api.trakt.tv/" + method + ", with data" + encoded_data, logger.DEBUG)
            stream = urllib2.urlopen("http://api.trakt.tv/" + method, encoded_data)
            resp = stream.read()

            resp = json.loads(resp)
            
            if ("error" in resp):
                raise Exception(resp["error"])
        except (IOError):
            logger.log("trakt_notifier: Failed calling method", logger.ERROR)
            return False

        if (resp["status"] == "success"):
            logger.log("trakt_notifier: Succeeded calling method. Result: " + resp["message"], logger.DEBUG)
            return True

        logger.log("trakt_notifier: Failed calling method", logger.ERROR)
        return False

notifier = TraktNotifier
