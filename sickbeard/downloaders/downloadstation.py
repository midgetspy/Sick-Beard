# Author: Brad Allred <bradallred@me.com>
# URL: http://github.com/bradallred/Sick-Beard
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

import urllib, urllib2
import httplib

try:
    import json
except ImportError:
    from lib import simplejson as json

import sickbeard
from sickbeard import logger
from sickbeard.exceptions import ex
from urlparse import urlparse

class DownloadStationAPI(object):
    """Download Station API"""
    def __init__(self, host="localhost", port=5000, username=None, password=None):
        logger.log(u"Creating DownloadStation API object for " + str(host) + " on port " + str(port) + " with credentials " + str(username) + ":" + str(password), logger.DEBUG)
        super(DownloadStationAPI, self).__init__()
        self.sid = None
        self.url = 'http://' + host + ':' + str(port) + '/webapi/'
        logger.log(u"Creating DownloadStation API object for " + self.url, logger.DEBUG)

        post_data = {
			'api' : 'SYNO.API.Auth',
			'method' : 'login',
			'account' : username,
			'passwd' : password,
			'session' : 'DownloadStation',
			'format' : 'sid',
			'version' : 2
        }
        response = self._request('auth.cgi', post_data)
        if response != False:
			logger.log(u"Session ID = " + str(response['sid']), logger.DEBUG)
			self.sid = response['sid']
			self.url = self.url + "DownloadStation/"
        else:
			raise Exception("Unable to get a session from SYNO.API.Auth, check credentials")

    def _request(self, script, post_data):
		logger.log(u"Creating DownloadStation API " + script + " request: " + str(post_data), logger.DEBUG)
		post_data.update({'_sid' : self.sid})
		headers = {'User-agent' : 'sick-beard-downloadstation-client/1.0'}
		request = urllib2.Request(self.url + script, urllib.urlencode(post_data), headers)
		logger.log(u"Request destination: " + self.url + script, logger.DEBUG)
		logger.log(u"Request: " + str(request), logger.DEBUG)
		try:
			open_request = urllib2.urlopen(request)
			response = json.loads(open_request.read())
			logger.log('response: ' + str(json.dumps(response).encode('utf-8')), logger.DEBUG)
			if response['success'] == False:
				logger.log(u"Request Error: " + response['error']['code'], logger.DEBUG)
				return False
			else:
				return True if not 'data' in response else response['data']
		except httplib.InvalidURL, e:
			logger.log(u"Invalid host, check your config " + str(e), logger.ERROR)
		except urllib2.HTTPError, e:
			logger.log(u"DownloadStationAPI HTTPError: " + str(e), logger.ERROR)
		except urllib2.URLError, e:
			logger.log(u"Unable to connect to DownloadStation " + str(e), logger.ERROR)
		return False

    def add_download(self, uri):
        logger.log(u"Adding Download:" + uri, logger.DEBUG)
        post_data = {
            'api' : 'SYNO.DownloadStation.Task',
            'method' : 'create',
            'uri' : uri,
            'version' : 1
        }
        return self._request('task.cgi', post_data)

    def pause_download(self, uri):
        logger.log(u"Pausing Download:" + uri, logger.DEBUG)
        post_data = {
            'api': 'SYNO.DownloadStation.Task',
            'method': 'list',
            'version' : 1
        }
		# the Download Station API doesnt return an ID when we add the torrent
		# list all the download tasks that match our uri and pause them all
        list = self._request('task.cgi', post_data)
        if list:
            post_data['method'] = 'pause'
            tasks = [task['id'] for task in list['tasks'] if task['additional']['detail']['uri'] == uri]
            paused = 0 #number of downloads we successfully pause
            for task in tasks:
				post_data['id'] = task
				if self._request('task.cgi', post_data):
					paused = paused + 1
            logger.log("Paused " + str(paused) + " download tasks", logger.DEBUG)
            return bool(paused)
        return False

def sendDownload(download):
    try:
        host = urlparse(sickbeard.TORRENT_HOST)
    except Exception, e:
        logger.log(u"Host properties are not filled in correctly, port is missing.", logger.ERROR)
        return False

    try:
        ds = DownloadStationAPI(host.hostname, host.port, sickbeard.TORRENT_USERNAME, sickbeard.TORRENT_PASSWORD)
        torrent = ds.add_download(download.url)
        if sickbeard.TORRENT_PAUSED:
			ds.pause_download(download.url)
        return True
    except Exception, e:
        logger.log("Unknown failure sending Torrent to Download Station. Return text is: " + str(e), logger.ERROR)
        return False

def testAuthentication(host, username, password):
	logger.log("Testing authentication to " + str(host) + " TORRENT_HOST=" + str(sickbeard.TORRENT_HOST), logger.DEBUG)
	try:
		host = urlparse(host)
	except Exception, e:
		return False, u"Host properties are not filled in correctly, port is missing."

	try:
		ds = DownloadStationAPI(host.hostname, host.port, username, password)
		return bool(ds.sid), u"Success: Connected and Authenticated."

	except Exception, e:
		return False, u"Error: Unable to connect to Download Station. " + str(e)
