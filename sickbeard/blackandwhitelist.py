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
    _tableBlack = "blacklist"
    _tableWhite = "whitelist"
    blackList = []
    whiteList = []
    blackDict = {}
    whiteDict = {}

    last_black_valid_result = None
    last_white_valid_result = None

    def __init__(self, show_id):
        if not show_id:
            raise BlackWhitelistNoShowIDException()
        self.show_id = show_id

        self.myDB = db.DBConnection()
        self.refresh()

    def refresh(self):
        logger.log(u"Building black and white list for " + str(self.show_id), logger.DEBUG)

        (self.blackList, self.blackDict) = self.load_blacklist()
        (self.whiteList, self.whiteDict) = self.load_whitelist()

    def load_blacklist(self):
        return self._load_list(self._tableBlack)

    def load_whitelist(self):
        return self._load_list(self._tableWhite)

    def get_black_keywords_for(self, range):
        if range in self.blackDict:
            return self.blackDict[range]
        else:
            return []

    def get_white_keywords_for(self, range):
        if range in self.whiteDict:
            return self.whiteDict[range]
        else:
            return []

    def set_black_keywords(self, range, values):
        self._del_all_black_keywords()
        self._add_keywords(self._tableBlack, range, values)

    def set_white_keywords(self, range, values):
        self._del_all_white_keywords()
        self._add_keywords(self._tableWhite, range, values)

    def set_black_keywords_for(self, range, values):
        self._del_all_black_keywords_for(range)
        self._add_keywords(self._tableBlack, range, values)

    def set_white_keywords_for(self, range, values):
        self._del_all_white_keywords_for(range)
        self._add_keywords(self._tableWhite, range, values)

    def add_black_keyword(self, range, value):
        self._add_keywords(self._tableBlack, range, [value])

    def add_white_keyword(self, range, value):
        self._add_keywords(self._tableWhite, range, [value])

    def get_last_result_msg(self):
        blackResult = whiteResult = "Untested"
        if self.last_black_valid_result == True:
            blackResult = "Valid"
        elif self.last_black_valid_result == False:
            blackResult = "Invalid"

        if self.last_white_valid_result == True:
            whiteResult = "Valid"
        elif self.last_white_valid_result == False:
            whiteResult = "Invalid"

        return "Blacklist: " + blackResult + ", Whitelist: " + whiteResult

    def _add_keywords(self, table, range, values):
        for value in values:
            self.myDB.action("INSERT INTO " + table + " (show_id, range , keyword) VALUES (?,?,?)", [self.show_id, range, value])
        self.refresh()

    def _del_all_black_keywords(self):
        self._del_all_keywords(self._tableBlack)

    def _del_all_white_keywords(self):
        self._del_all_keywords(self._tableWhite)

    def _del_all_black_keywords_for(self, range):
        self._del_all_keywords_for(self._tableBlack, range)

    def _del_all_white_keywords_for(self, range):
        self._del_all_keywords_for(self._tableWhite, range)

    def _del_all_keywords(self, table):
        logger.log(u"Deleting all " + table + " keywords for " + str(self.show_id), logger.DEBUG)
        self.myDB.action("DELETE FROM " + table + " WHERE show_id = ?", [self.show_id])
        self.refresh()

    def _del_all_keywords_for(self, table, range):
        logger.log(u"Deleting all " + range + " " + table + " keywords for " + str(self.show_id), logger.DEBUG)
        self.myDB.action("DELETE FROM " + table + " WHERE show_id = ? and range = ?", [self.show_id, range])
        self.refresh()

    def _load_list(self, table):
        sqlResults = self.myDB.select("SELECT range,keyword FROM " + table + " WHERE show_id = ? ", [self.show_id])
        if not sqlResults or not len(sqlResults):
            return ([], {})

        list, dict = self._build_keyword_dict(sqlResults)
        logger.log("BWL: " + str(self.show_id) + " loaded keywords from " + table + ": " + str(dict), logger.DEBUG)
        return list, dict

    def _build_keyword_dict(self, sql_result):
        list = []
        dict = {}
        for row in sql_result:
            list.append(row["keyword"])
            if row["range"] in dict:
                dict[row["range"]].append(row["keyword"])
            else:
                dict[row["range"]] = [row["keyword"]]

        return (list, dict)

    def is_valid_for_black(self, haystack):
        logger.log(u"BWL: " + str(self.show_id) + " is valid black", logger.DEBUG)
        result = self._is_valid_for(self.blackDict, False, haystack)
        self.last_black_valid_result = result
        return result

    def is_valid_for_white(self, haystack):
        logger.log(u"BWL: " + str(self.show_id) + " is valid white", logger.DEBUG)
        result = self._is_valid_for(self.whiteDict, True, haystack)
        self.last_white_valid_result = result
        return result

    def is_valid(self, haystack):
        return self.is_valid_for_black(haystack) and self.is_valid_for_white(haystack)

    def _is_valid_for(self, list, mood, haystack):
        if not len(list):
            return True

        results = []
        for range in list:
            for keyword in list[range]:
                string = None
                if range == "global":
                    string = haystack.name
                elif range in haystack.__dict__:
                    string = haystack.__dict__[range]
                elif not range in haystack.__dict__:
                    results.append((not mood))
                else:
                    results.append(False)

                if string:
                    results.append(self._is_keyword_in_string(string, keyword) == mood)

        # black: mood = False
        # white: mood = True
        if mood in results:
            return mood
        else:
            return (not mood)

    def _is_keyword_in_string(self, fromPost, fromBWList):
        """
        will return true if fromBWList is found in fromPost
        for now a basic find is used
        """
        fromPost = fromPost.lower()
        fromBWList = fromBWList.lower()
        logger.log(u"BWL: " + str(self.show_id) + " comparing fromPost: " + fromPost + " vs fromBWlist: " + fromBWList, logger.DEBUG)
        return (fromPost.find(fromBWList) >= 0)

class BlackWhiteKeyword(object):
    range = ""
    value = []

    def __init__(self, range, values):
        self.range = range # "global" or a parser group
        self.value = values # a list of values may contain only one item (still a list)


class BlackWhitelistNoShowIDException(Exception):
    "No show_id was given"
