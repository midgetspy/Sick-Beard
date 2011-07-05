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

from time import time,sleep
import aniDBfileInfo as fileInfo
from aniDBmaper import AniDBMaper


class aniDBabstractObject(object):
    
    def __init__(self,aniDB,load=False):
        self.aniDB = aniDB
        self.log = self.aniDB.log
        self.laoded = False
        if load:
            self.load_data()
        
    
    def _fill(self,dataline):
        for key in dataline:
            try:
                tmpList = dataline[key].split("'")
                if len(tmpList) > 1:
                    newList=[]
                    for i in tmpList:
                        try:
                            newList.append(int(i))
                        except:
                            newList.append(unicode(i, "utf-8"))
                    self.__dict__[key] = newList
                    continue
            except:
                pass
            try:
                self.__dict__[key] = int(dataline[key])
            except:
                self.__dict__[key] = unicode(dataline[key], "utf-8")
            key = property(lambda x: dataline[key])

    def __getattr__(self, name):
        try:
            return object.__getattribute__(self, name)
        except:
            return None
    
    def _build_names(self):
        names = []
        names = self._easy_extend(names,self.english_name)
        names = self._easy_extend(names,self.short_name_list)
        names = self._easy_extend(names,self.synonym_list)
        names = self._easy_extend(names,self.other_name)
            
        self.allNames = names
    
    def _easy_extend(self,initialList,item):
        if item:
            if isinstance(item, list):
                initialList.extend(item)
            elif isinstance(item, basestring):
                initialList.append(item)
            
        return initialList
         
    
    def load_data(self):
        return False
    
    def add_notification(self):
        """
        type - Type of notification: type=>  0=all, 1=new, 2=group, 3=complete
        priority - low = 0, medium = 1, high = 2 (unconfirmed)
        
        """
        if(self.aid):
            self.aniDB.notifyadd(aid=self.aid,type=1, priority=1)
    
    
class Anime(aniDBabstractObject):
    def __init__(self,aniDB,name=None,aid=None,paramsA=None,load=False):
        if not (name or aid):
            raise AniDBIncorrectParameterError,"Anime error"
        self.maper = AniDBMaper() 
        self.name = name
        self.aid = aid
        
        if not paramsA:
            self.bitCode = "b2f0e0fc000000"
            self.params = self.maper.getAnimeCodesA(self.bitCode)
        else:
            self.paramsA = paramsA
            self.bitCode = self.maper.getAnimeBitsA(self.paramsA)
        
        super(Anime, self).__init__(aniDB,load)
        
    def load_data(self):
        """load the data from anidb"""
        
        self.rawData = self.aniDB.anime(aid=self.aid,aname=self.name,amask=self.bitCode)
        self._fill(self.rawData.datalines[0])
        self._builPreSequal()
        self.laoded = True
    
    def get_groups(self):
        self.rawData = self.aniDB.groupstatus(aid=self.aid)
        self.release_groups = []
        for line in self.rawData.datalines:
            self.release_groups.append(unicode(line["name"], "utf-8"))
        return self.release_groups
    
    def _builPreSequal(self):
        if self.related_aid_list and self.related_aid_type:
            try:
                for i in range(len(self.related_aid_list)):
                    if self.related_aid_type[i] == 2:
                        self.__dict__["prequal"] = self.related_aid_list[i]
                    elif self.related_aid_type[i] == 1:
                        self.__dict__["sequal"] = self.related_aid_list[i]
            except:
                if self.related_aid_type == 2:
                    self.__dict__["prequal"] = self.related_aid_list
                elif self.str_related_aid_type == 1:
                    self.__dict__["sequal"] = self.related_aid_list
    
                  
                    
class Episode(aniDBabstractObject):
    
    def __init__(self,aniDB,number=None,epid=None,filePath=None,fid=None,epno=None,paramsA=None,paramsF=None,load=False,calculate=False):
        if not aniDB and not number and not epid and not file and not fid:
            return None
        
        self.maper = AniDBMaper()
        self.epid = epid
        self.filePath = filePath
        self.fid = fid
        self.epno = epno
        if calculate:
            (self.ed2k, self.size) = self._calculate_file_stuff(self.filePath)
        
        
        if not paramsA:
            self.bitCodeA = "C000F0C0"
            self.paramsA = self.maper.getFileCodesA(self.bitCodeA)
        else:
            self.paramsA = paramsA
            self.bitCodeA = self.maper.getFileBitsA(self.paramsA)
        
        if not paramsF:
            self.bitCodeF = "7FF8FEF8"
            self.paramsF = self.maper.getFileCodesF(self.bitCodeF)
        else:
            self.paramsF = paramsF
            self.bitCodeF = self.maper.getFileBitsF(self.paramsF)
        
        super(Episode, self).__init__(aniDB,load)
        
    def load_data(self):
        """load the data from anidb"""
        if self.filePath and not (self.ed2k or self.size):
            (self.ed2k, self.size) = self._calculate_file_stuff(self.filePath)
        
        self.rawData = self.aniDB.file(fid=self.fid,size=self.size,ed2k=self.ed2k,aid=self.aid,aname=None,gid=None,gname=None,epno=self.epno,fmask=self.bitCodeF,amask=self.bitCodeA)
        self._fill(self.rawData.datalines[0])
        self._build_names()
        self.laoded = True
        
    def add_to_mylist(self,status=None):
        """
        status:
        0    unknown    - state is unknown or the user doesn't want to provide this information (default)
        1    on hdd    - the file is stored on hdd
        2    on cd    - the file is stored on cd
        3    deleted    - the file has been deleted or is not available for other reasons (i.e. reencoded)
        
        """
        if self.filePath and not (self.ed2k or self.size):
            (self.ed2k, self.size) = self._calculate_file_stuff(self.filePath)
            
        try:
            self.aniDB.mylistadd(size=self.size,ed2k=self.ed2k,state=status)
        except Exception,e :
            self.log(u"exception msg: "+str(e))
        else:
            # TODO: add the name or something
            self.log(u"Added the episode to anidb")

    
    def _calculate_file_stuff(self, filePath):
        if not filePath:
            return (None, None)
        self.log("Calculating the ed2k. Please wait...")
        ed2k = fileInfo.get_file_hash(filePath)
        size = fileInfo.get_file_size(filePath)
        return (ed2k, size)
    
    