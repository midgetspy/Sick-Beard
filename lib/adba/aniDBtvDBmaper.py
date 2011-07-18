#!/usr/bin/env python
#
# This file is part of aDBa.
#
# aDBa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# aDBa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with aDBa.  If not, see <http://www.gnu.org/licenses/>.

import os
import xml.etree.cElementTree as etree
import aniDBfileInfo as fileInfo



class TvDBMap():
    
    def __init__(self,filePath=None):
        self.xmlMap = fileInfo.read_tvdb_map_xml(filePath)
        
    def get_tvdb_for_anidb(self,anidb_id):
        return self._get_x_for_y(anidb_id,"anidbid","tvdbid")
            
    def get_anidb_for_tvdb(self,tvdb_id):
        return self._get_x_for_y(tvdb_id,"tvdbid","anidbid")
        

    def _get_x_for_y(self,xValue,x,y):
        #print("searching "+x+" with the value "+str(xValue)+" and want to give back "+y)
        xValue = str(xValue)
        for anime in self.xmlMap.findall("anime"):
            try:
                if anime.get(x,False) == xValue:
                    return int(anime.get(y,0))
            except ValueError, e:
                continue
        return 0
            
            
    def get_season_episode_for_anidb_absoluteNumber(self,anidb_id,absoluteNumber):
        # NOTE: this cant be done without the length of each season from thetvdb
        #TODO: implement
        season = 0
        episode = 0
        
        for anime in self.xmlMap.findall("anime"):
            if int(anime.get("anidbid",False)) == anidb_id:
                defaultSeason = int(anime.get("defaulttvdbseason",1))
        
        
        return (season,episode)
            
    def get_season_episode_for_tvdb_absoluteNumber(self,anidb_id,absoluteNumber):
        #TODO: implement
        season = 0
        episode = 0
        return (season,episode)