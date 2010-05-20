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
from sickbeard import logger

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

    # don't bother making backlog episodes high priority
    if nzb.episode.status != BACKLOG:
        params['priority'] = 1

    params['pp'] = 3
    
    params['mode'] = 'addurl'
    params['name'] = nzb.url

    url = 'http://' + sickbeard.SAB_HOST + "/sabnzbd/api?" + urllib.urlencode(params)

    logger.log("Sending NZB to SABnzbd")

    logger.log("URL: " + url, logger.DEBUG)

    try:
        f = urllib.urlopen(url)
    except IOError, e:
        logger.log("Unable to connect to SAB: "+str(e), logger.ERROR)
        return False
    
    if f == None:
        logger.log("No data returned from SABnzbd, NZB not sent", logger.ERROR)
        return False
    
    result = f.readlines()

    if len(result) == 0:
        logger.log("No data returned from SABnzbd, NZB not sent", logger.ERROR)
        return False
    
    sabText = result[0].strip()
    
    logger.log("Result text from SAB: " + sabText, logger.DEBUG)
    
    if sabText == "ok":
        logger.log("NZB sent to SAB successfully", logger.DEBUG)
        return True
    elif sabText == "Missing authentication":
        logger.log("Incorrect username/password sent to SAB, NZB not sent", logger.ERROR)
        return False
    else:
        logger.log("Unknown failure sending NZB to sab. Return text is: " + sabText, logger.ERROR)
        return False
