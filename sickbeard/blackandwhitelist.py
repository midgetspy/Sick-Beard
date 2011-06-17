# Author: Dennis Lutter <lad1337@gmail.com>
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

from sickbeard import db, logger

class BlackAndWhiteList(object):
    
    def __init__(self,show_id):
        if not show_id:
            raise BlackWhitelistNoShowIDException()
        self.show_id
        self.myDB = db.DBConnection()
        self.refresh()
       
    def refresh(self):                
        logger.log(u"Building black and white list for "+str(self.show_id), logger.DEBUG)

        self.blacklist = self.load_blacklist()
        self.whitelist = self.load_whitelist()

    def load_blacklist(self):
        return self._load_list("blacklist")
    
    def load_whitelist(self):
        return self._load_list("whitelist")    
    
    def _load_list(self,table):
        sqlResults = self.myDB.select("SELECT range,keyword FROM "+table+" WHERE show_id = ? ", [self.show_id])
        if not sqlResults or not len(sqlResults):
            return []
        
        return self._build_keyword_dict(sqlResults)
    
    def _build_keyword_dict(self,sql_result):
        list = []
        for row in sql_result:
            list.append(BlackWhiteKeyword(row["range"],row["keyword"]))
        return list
    
class BlackWhiteKeyword(object):
    def __init__(self, range, value):
        self.range = range
        self.value = value
        

class BlackWhitelistNoShowIDException(Exception):
    "No show_id was given"
 