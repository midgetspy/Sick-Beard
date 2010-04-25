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
import datetime

from sickbeard import logger

from sickbeard import tvclasses
from sickbeard.tvapi import safestore
from sickbeard.tvapi import tvapi_classes
from sickbeard.tvapi.tvdb import tvdb_classes
from sickbeard.tvapi.tvrage import tvrage_classes

from lib.tvdb_api import tvdb_api, tvdb_exceptions

from storm.locals import And 

import sickbeard

def _findShowDataFromName(showName, year=None):
    conds = [tvdb_classes.TVShowData_TVDB.name.like(showName)]
    if year:
        #conds.append(tvdb_classes.TVShowData_TVDB.firstaired.year == int(year))
        conds.append(tvdb_classes.TVShowData_TVDB.firstaired >= datetime.date(2010, 01, 01))
        conds.append(tvdb_classes.TVShowData_TVDB.firstaired <= datetime.date(2010, 12, 31))
    showDataList_TVDB = safestore.safe_list(sickbeard.storeManager.safe_store("find",
                                                                              tvdb_classes.TVShowData_TVDB,
                                                                              And(*conds)))

    conds = [tvrage_classes.TVShowData_TVRage.name.like(showName)]
    if year:
        conds.append(tvrage_classes.TVShowData_TVRage.firstaired >= datetime.date(2010, 01, 01))
        conds.append(tvrage_classes.TVShowData_TVRage.firstaired <= datetime.date(2010, 12, 31))
    showDataList_TVRage = safestore.safe_list(sickbeard.storeManager.safe_store("find",
                                                                                tvrage_classes.TVShowData_TVRage,
                                                                                And(*conds)))

    return showDataList_TVDB + showDataList_TVRage

def searchDBForShow(regShowName):
    
    showNames = set([regShowName+'%', regShowName.replace(' ','_')+'%'])
    
    yearRegex = "(.*?)\s*([(]?)(\d{4})(?(2)[)]?).*"

    for showName in showNames:
    
        #sqlResults = myDB.select("SELECT * FROM tv_shows WHERE show_name LIKE ? OR tvr_name LIKE ?", [showName, showName])
        showDataList = _findShowDataFromName(showName)
        
        if len(showDataList) == 1:
            return (int(showDataList[0].tvdb_id), showDataList[0].name)

        else:
    
            # if we didn't get exactly one result then try again with the year stripped off if possible
            match = re.match(yearRegex, showName)
            if match:
                logger.log("Unable to match original name but trying to manually strip and specify show year", logger.DEBUG)
                showDataList = _findShowDataFromName(match.group(1)+'%', match.group(3))
    
            if len(showDataList) == 0:
                logger.log("Unable to match a record in the DB for "+showName, logger.DEBUG)
                continue
            elif len(showDataList) > 1:
                logger.log("Multiple results for "+showName+" in the DB, unable to match show name", logger.DEBUG)
                continue
            else:
                return (int(showDataList[0].tvdb_id), showDataList[0].name)

    
    return None
