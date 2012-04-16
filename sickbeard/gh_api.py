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

try:
    import json
except ImportError:
    from lib import simplejson as json

import urllib

class GitHub(object):
    """
    Simple api wrapper for the Github API v3. Currently only supports the small thing that SB
    needs it for - list of cimmots.
    """
    
    def _access_API(self, path, params=None):
        """
        Access the API at the path given and with the optional params given.
        
        path: A list of the path elements to use (eg. ['repos', 'midgetspy', 'Sick-Beard', 'commits'])
        params: Optional dict of name/value pairs for extra params to send. (eg. {'per_page': 10})
        
        Returns a deserialized json object of the result. Doesn't do any error checking (hope it works).
        """
        
        url = 'https://api.github.com/' + '/'.join(path)
        
        if params and type(params) is dict:
            url += '?' + '&'.join([str(x) + '=' + str(params[x]) for x in params.keys()])
        
        return json.load(urllib.urlopen(url)) 
    
    def commits(self, user, repo, branch='master'):
        """
        Uses the API to get a list of the 100 most recent commits from the specified user/repo/branch, starting from HEAD.
        
        user: The github username of the person whose repo you're querying
        repo: The repo name to query
        branch: Optional, the branch name to show commits from
        
        Returns a deserialized json object containing the commit info. See http://developer.github.com/v3/repos/commits/
        """
        return self._access_API(['repos', user, repo, 'commits'], {'per_page': 100, 'branch': branch})
