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



import urllib

import sickbeard

from sickbeard.common import *
from sickbeard.logging import *

def sendNZB(nzb):
    
    params = {}
    
    if sickbeard.SAB_USERNAME != None:
        params['ma_username'] = sickbeard.SAB_USERNAME
    if sickbeard.SAB_PASSWORD != None:
        params['ma_password'] = sickbeard.SAB_PASSWORD
    if sickbeard.SAB_APIKEY != None:
        params['apikey'] = sickbeard.SAB_APIKEY
    if sickbeard.SAB_CATEGORY != None:
        params['cat'] = sickbeard.SAB_CATEGORY
    
    params['priority'] = 1
    params['pp'] = 3
    
    if nzb.provider == NEWZBIN:
        params['mode'] = 'addid'
        params['name'] = nzb.extraInfo[0]
    elif nzb.provider in (TVBINZ, NZBS, NZBMATRIX):
        params['mode'] = 'addurl'
        params['name'] = nzb.url

    url = 'http://' + sickbeard.SAB_HOST + "/sabnzbd/api?" + urllib.urlencode(params)

    Logger().log("Sending NZB to SABnzbd")

    Logger().log("URL: " + url, DEBUG)

    f = urllib.urlopen(url)
    
    if f == None:
        Logger().log("No data returned from SABnzbd, NZB not sent", ERROR)
        return False
    
    result = f.readlines()

    if len(result) == 0:
        Logger().log("No data returned from SABnzbd, NZB not sent", ERROR)
        return False
    
    sabText = result[0].strip()
    
    Logger().log("Result text from SAB: " + sabText, DEBUG)
    
    if sabText == "ok":
        Logger().log("NZB sent to SAB successfully", DEBUG)
        return True
    elif sabText == "Missing authentication":
        Logger().log("Incorrect username/password sent to SAB, NZB not sent", ERROR)
        return False
    else:
        Logger().log("Unknown failure sending NZB to sab. Return text is: " + sabText, ERROR)
        return False
