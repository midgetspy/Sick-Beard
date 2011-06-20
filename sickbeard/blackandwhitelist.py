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
    _tabeBlack = "blacklist"
    _tabeWhite = "whitelist"
    blackList = []
    whiteList = []
    blackDict = {}
    whiteDict = {}
    
    def __init__(self,show_id):
        if not show_id:
            raise BlackWhitelistNoShowIDException()
        self.show_id = show_id
        self.myDB = db.DBConnection()
        self.refresh()
       
    def refresh(self):                
        logger.log(u"Building black and white list for "+str(self.show_id), logger.DEBUG)

        (self.blackList,self.blackDict) = self.load_blacklist()
        (self.whiteList,self.whiteDict) = self.load_whitelist()

    def load_blacklist(self):
        return self._load_list(self._tabeBlack)
    
    def load_whitelist(self):
        return self._load_list(self._tabeWhite)    
    
    def set_black_keywords(self,range,values):
        self._del_all_black_keywors()
        self._add_keywords(self._tabeBlack, range, values)

    def set_white_keywords(self,range,values):
        self._del_all_white_keywors()
        self._add_keywords(self._tabeWhite, range, values)
  
    def set_black_keywords_for(self,range,values):
        self._del_all_black_keywors_for(range)
        self._add_keywords(self._tabeBlack, range, values)

    def set_white_keywords_for(self,range,values):
        self._del_all_white_keywors_for(range)
        self._add_keywords(self._tabeWhite, range, values)
    
    def add_black_keyword(self,range,value):
        self._add_keywords(self._tabeBlack, range, [value])
        
    def add_white_keyword(self,range,value):
        self._add_keywords(self._tabeWhite, range, [value])
    
    def _add_keywords(self,table,range,values):
        for value in values:
            self.myDB.action("INSERT INTO "+table+" (show_id, range , keyword) VALUES (?,?,?)", [self.show_id,range,value])        
        self.refresh()
        
    def _del_all_black_keywors(self):
        self._del_all_keywords(self._tabeBlack)
    
    def _del_all_white_keywors(self):
        self._del_all_keywords(self._tabeWhite)
        
    def _del_all_black_keywors_for(self,range):
        self._del_all_keywords_for(self._tabeBlack,range)
    
    def _del_all_white_keywors_for(self,range):
        self._del_all_keywords_for(self._tabeWhite.range)
    
    def _del_all_keywords(self,table):
        logger.log(u"Deleting all "+table+" keywords for "+str(self.show_id), logger.DEBUG)
        self.myDB.action("DELETE FROM "+table+" WHERE show_id = ?", [self.show_id])
        self.refresh()
    
    def _del_all_keywords_for(self,table,range):
        logger.log(u"Deleting all "+range+" "+table+" keywords for "+str(self.show_id), logger.DEBUG)
        self.myDB.action("DELETE FROM "+table+" WHERE show_id = ? and range = ?", [self.show_id,range])
        self.refresh()
        
    def _load_list(self,table):
        sqlResults = self.myDB.select("SELECT range,keyword FROM "+table+" WHERE show_id = ? ", [self.show_id])
        if not sqlResults or not len(sqlResults):
            return ([],{})
        
        return self._build_keyword_dict(sqlResults)
    
    def _build_keyword_dict(self,sql_result):
        list = []
        dict = {}
        for row in sql_result:
            list.append(BlackWhiteKeyword(row["range"],[row["keyword"]]))
            if(dict.has_key(row["range"])):
                dict[row["range"]].append(row["keyword"])
            else:
                dict[row["range"]] = [row["keyword"]]
        for range in dict:
            dict[range] = BlackWhiteKeyword(range,dict[range])
        return (list,dict)
    
class BlackWhiteKeyword(object):
    range = ""
    value = []
    def __init__(self, range, values):
        self.range = range # "global" or a parser group
        self.value = values # a list of values may contain only one item (still a list)
        

class BlackWhitelistNoShowIDException(Exception):
    "No show_id was given"
